"""Ask every stack the same three questions, in turns, and time them.

Rounds are interleaved: within a round each stack answers once, so a
machine that speeds up or slows down over the run does it to all of them
at once. A round reports the best of its calls; the table reports the
median of the rounds, with a bootstrap interval around it.
"""

import argparse
import datetime
import gc
import os
import random
import statistics
import sys
import time
import uuid

import orjson
import psycopg

from bench import config
from bench import database
from bench import machine
from bench import payload
from bench import stacks as stack_registry
from bench import stats

FIRST_ID = str(uuid.UUID(int=1))
CREATE_BODY = orjson.dumps(
    {
        "name": "created item",
        "description": "an item a POST made",
        "enabled": True,
        "quantity": 10_000_000,
        "project_id": str(uuid.UUID(int=0x51)),
    }
)

# What to ask a stack, and what the answer is called in the report. The
# quantity a POST writes is out of the range the seeded rows use, so the
# rows a run creates are the rows it sweeps.
ASK = {
    "collection": lambda stack: stack.collection(),
    "resource": lambda stack: stack.resource(FIRST_ID),
    "create": lambda stack: stack.create(CREATE_BODY),
}
SCENARIOS = tuple(ASK)


def check(stack, rows):
    """Nobody is timed before answering the same as the table."""
    status, body = stack.collection()
    assert status == 200, f"{stack.name}: collection answered {status}"
    documents = orjson.loads(body)
    assert payload.same(documents, rows), f"{stack.name}: collection differs"

    status, body = stack.resource(FIRST_ID)
    assert status == 200, f"{stack.name}: resource answered {status}"
    assert payload.same(orjson.loads(body), rows[0]), f"{stack.name}: resource differs"

    status, body = stack.create(CREATE_BODY)
    assert status == 201, f"{stack.name}: create answered {status}"
    created = orjson.loads(body)
    posted = orjson.loads(CREATE_BODY)
    assert all(created[field] == posted[field] for field in posted), (
        f"{stack.name}: create echoes the posted fields back wrong"
    )
    assert all(field in created for field in payload.FIELDS), (
        f"{stack.name}: create answers with less than a read does"
    )


def warm(stack, seconds):
    """Run every scenario until nothing about the stack is cold.

    The first calls into a stack fill what it fills lazily: compiled
    statements, validators built per model, routes resolved, a pool
    opened, and the pages the query reads land in the database's cache.
    Timing those measures the first request a process ever serves,
    which is not what anyone runs.
    """
    calls = 0
    for ask in ASK.values():
        started = time.perf_counter()
        while calls < 1 or time.perf_counter() - started < seconds:
            ask(stack)
            calls += 1
    gc.collect()
    return calls


def time_scenario(stack, scenario, calls):
    ask = ASK[scenario]
    best = None
    for _ in range(calls):
        started = time.perf_counter()
        ask(stack)
        elapsed = time.perf_counter() - started
        best = elapsed if best is None else min(best, elapsed)
    return best * 1e6


def sweep_created():
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as connection:
        connection.execute(f"DELETE FROM {config.TABLE} WHERE quantity >= 10000000")


def table(header, alignment, rows):
    return "\n".join(["| {} |".format(" | ".join(header)), alignment] + rows)


def report(samples, order, rounds, calls, warmup, postgres=None, load=None):
    medians = {
        scenario: {
            stack: statistics.median(samples[stack][scenario]) for stack in order
        }
        for scenario in SCENARIOS
    }
    fixed = medians["resource"]
    marginal = {
        stack: (medians["collection"][stack] - fixed[stack]) / (config.PAGE - 1)
        for stack in order
    }
    restalchemy = next((s for s in order if s.startswith("RestAlchemy")), None)

    sections = {}
    for scenario in SCENARIOS:
        median = medians[scenario]
        fastest = min(median.values())
        rows = []
        for stack in sorted(order, key=median.get):
            low, high = stats.interval(samples[stack][scenario])
            rows.append(
                "| {} | {:.0f} µs | {:.0f} … {:.0f} | {:.2f}× | {} |".format(
                    stack,
                    median[stack],
                    low,
                    high,
                    median[stack] / fastest,
                    (
                        "%.2f×" % (median[stack] / median[restalchemy])
                        if restalchemy
                        else "—"
                    ),
                )
            )
        sections[scenario] = table(
            ("Stack", "Median", "95% CI", "× fastest", "× RestAlchemy"),
            "| --- | ---: | :---: | ---: | ---: |",
            rows,
        )

    quickest = min(marginal.values())
    sections["rowcost"] = table(
        ("Stack", "Fixed, per request", "Per row", "× fastest per row"),
        "| --- | ---: | ---: | ---: |",
        [
            f"| {stack} | {fixed[stack]:.0f} µs | {marginal[stack]:.1f} µs | {marginal[stack] / quickest:.2f}× |"
            for stack in sorted(order, key=marginal.get)
        ],
    )

    with open(os.path.join(os.path.dirname(__file__), "report.md")) as report:
        template = report.read()
    return template.format(
        stacks=len(order),
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        ),
        rounds=rounds,
        calls=calls,
        warmup=warmup,
        rows=config.ROWS,
        page=config.PAGE,
        rest=config.PAGE - 1,
        python=sys.version.split()[0],
        machine=machine.describe(postgres=postgres, load=load),
        **sections,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=config.ROUNDS)
    parser.add_argument("--calls", type=int, default=config.CALLS)
    parser.add_argument("--only", nargs="*", default=())
    parser.add_argument(
        "--warmup",
        type=float,
        default=config.WARMUP,
        help="seconds of warm-up per scenario per stack before timing",
    )
    parser.add_argument(
        "--out", default=os.path.join(config.HERE, "results", "results.md")
    )
    arguments = parser.parse_args()

    random.seed(20260816)
    rows = database.expected()
    loaded = stack_registry.load(arguments.only)
    for stack in loaded:
        stack.setup()
        check(stack, rows)
        warmed = warm(stack, arguments.warmup)
        sys.stderr.write(f"{stack.name}: warmed with {warmed} calls\n")
    sweep_created()

    order = [stack.name for stack in loaded]
    samples = {name: {scenario: [] for scenario in SCENARIOS} for name in order}
    # Before the first round, because after the last one the benchmark is
    # itself most of what the machine has been doing.
    load_before = machine.load_average()

    for round_number in range(arguments.rounds):
        turn = list(loaded)
        # A different order each round, so being first is not an advantage
        # anyone keeps.
        turn = turn[round_number % len(turn) :] + turn[: round_number % len(turn)]
        for stack in turn:
            for scenario in SCENARIOS:
                samples[stack.name][scenario].append(
                    time_scenario(stack, scenario, arguments.calls)
                )
            # Swept per turn, so every stack reads the table the first
            # one read, wherever the rotation put it.
            sweep_created()
        sys.stderr.write(f"round {round_number + 1}/{arguments.rounds}\n")

    # Checked again after the last round: a stack that broke mid-run
    # would have been timed answering something cheaper than the work.
    for stack in loaded:
        check(stack, rows)
    sweep_created()

    for stack in loaded:
        stack.teardown()

    text = report(
        samples,
        order,
        arguments.rounds,
        arguments.calls,
        arguments.warmup,
        postgres=database.server_version(),
        load=load_before,
    )
    os.makedirs(os.path.dirname(arguments.out), exist_ok=True)
    with open(arguments.out, "w") as handle:
        handle.write(text)
    raw = arguments.out.replace(".md", ".json")
    with open(raw, "w") as handle:
        handle.write(orjson.dumps(samples, option=orjson.OPT_INDENT_2).decode())
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
