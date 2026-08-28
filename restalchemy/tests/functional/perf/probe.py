#    Copyright 2026 Genesis Corporation.
#
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""What the guards measure, measured in a process of its own.

A process, not a fixture, for two reasons. RestAlchemy keeps one
application per process -- the resource map is class-wide -- so building
one here inside the suite would take the map away from the microservice
the other tests call. And a leak is counted in what the process holds,
which in a shared process is mostly what somebody else's test left.

Run by hand to see the numbers a guard read:

    DATABASE_URI=postgresql://... python -m \\
        restalchemy.tests.functional.perf.probe --mode speed
    DATABASE_URI=postgresql://... python -m \\
        restalchemy.tests.functional.perf.probe --mode memory
"""

import argparse
import gc
import statistics
import sys
import time
import tracemalloc

import orjson

from restalchemy.tests.functional import consts
from restalchemy.tests.functional.perf import stacks

ROWS = 200
PAGE = 50
ROUNDS = 9
CALLS = 20
WARMUP = 0.3
BATCH = 250
BATCHES = 8


def note(text):
    """Progress goes to stderr; stdout carries the answer alone."""
    sys.stderr.write(text + "\n")
    sys.stderr.flush()


def warm(stack, seconds):
    """Run every request until nothing about the stack is cold.

    The first calls fill what a stack fills lazily -- statements, the
    plan a model is filled in by, routes, a connection -- and put the
    pages the query reads in the database's cache. Timing those measures
    the first request a process ever serves, which is nobody's load.
    """
    calls = 0
    for ask in stacks.ASK.values():
        started = time.perf_counter()
        while calls < 1 or time.perf_counter() - started < seconds:
            ask(stack)
            calls += 1
    gc.collect()
    return calls


def best_of(stack, scenario, calls):
    """The best of a handful: a scheduling hiccup is not the answer."""
    ask = stacks.ASK[scenario]
    best = None
    for _ in range(calls):
        started = time.perf_counter()
        ask(stack)
        elapsed = time.perf_counter() - started
        best = elapsed if best is None else min(best, elapsed)
    return best * 1e6


def measure_speed(db_url, book, arguments):
    """Time both stacks, turn by turn, and read one against the other.

    Rounds are interleaved: within a round each stack answers once, so a
    machine that slows down mid-run slows both of them down together and
    the ratio survives it.
    """
    stacks.seed(book, arguments.rows)
    both = [
        stacks.RawStack(db_url, arguments.page),
        stacks.RestAlchemyStack(db_url, arguments.page),
    ]
    for stack in both:
        stack.setup()
        stacks.check(stack, arguments.page)
        note(f"{stack.name}: warmed with {warm(stack, arguments.warmup)} calls")
    stacks.sweep(book)

    samples = {
        stack.name: {scenario: [] for scenario in stacks.SCENARIOS} for stack in both
    }
    for number in range(arguments.rounds):
        # A different order each round, so being first is not an
        # advantage anyone keeps.
        turn = both[number % len(both) :] + both[: number % len(both)]
        for stack in turn:
            for scenario in stacks.SCENARIOS:
                samples[stack.name][scenario].append(
                    best_of(stack, scenario, arguments.calls)
                )
            # Swept per turn, so every stack reads the table the first
            # one read, wherever the rotation put it.
            stacks.sweep(book)
        note(f"round {number + 1}/{arguments.rounds}")

    # Checked again: a stack that broke mid-run would have been timed
    # answering something cheaper than the work.
    for stack in both:
        stacks.check(stack, arguments.page)
        stack.teardown()
    stacks.sweep(book)

    raw, ours = (stack.name for stack in both)
    median = {
        name: {
            scenario: statistics.median(samples[name][scenario])
            for scenario in stacks.SCENARIOS
        }
        for name in samples
    }
    return {
        "rounds": arguments.rounds,
        "calls": arguments.calls,
        "rows": arguments.rows,
        "page": arguments.page,
        "samples": samples,
        "floor": median[raw],
        "restalchemy": median[ours],
        "ratio": {
            scenario: median[ours][scenario] / median[raw][scenario]
            for scenario in stacks.SCENARIOS
        },
    }


def measure_memory(db_url, book, arguments):
    """Serve batch after batch and watch what the process keeps.

    Every request builds a model, a document and a query and should hand
    all three back. What a stack fills once -- caches a declaration
    settles, a connection, a statement -- is filled during the warm-up,
    before the first count is taken, so what a later batch adds is what a
    request does not give back.
    """
    stacks.seed(book, arguments.rows)
    stack = stacks.RestAlchemyStack(db_url, arguments.page)
    stack.setup()
    stacks.check(stack, arguments.page)
    note(f"{stack.name}: warmed with {warm(stack, arguments.warmup)} calls")

    asks = list(stacks.ASK.values())
    series = []
    tracemalloc.start()
    for number in range(arguments.batches):
        for call in range(arguments.batch):
            asks[call % len(asks)](stack)
        stacks.sweep(book)
        gc.collect()
        tracked = gc.get_objects()
        objects = len(tracked)
        del tracked
        series.append(
            {
                "requests": (number + 1) * arguments.batch,
                "objects": objects,
                "bytes": tracemalloc.get_traced_memory()[0],
            }
        )
        note(
            f"batch {number + 1}/{arguments.batches}:"
            f" {objects} objects, {series[-1]['bytes']} bytes"
        )
    tracemalloc.stop()

    stacks.check(stack, arguments.page)
    stack.teardown()
    stacks.sweep(book)

    # Read over the second half only. A cache that converges does its
    # growing early -- the first batches hold what the warm-up had not
    # settled yet -- while anything a request keeps for good keeps
    # arriving at the same rate to the end.
    middle, last = series[len(series) // 2], series[-1]
    served = last["requests"] - middle["requests"]
    return {
        "batch": arguments.batch,
        "batches": arguments.batches,
        "series": series,
        "served": served,
        "per_request": {
            "objects": (last["objects"] - middle["objects"]) / served,
            "bytes": (last["bytes"] - middle["bytes"]) / served,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("speed", "memory"), required=True)
    parser.add_argument("--rows", type=int, default=ROWS)
    parser.add_argument("--page", type=int, default=PAGE)
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    parser.add_argument("--calls", type=int, default=CALLS)
    parser.add_argument("--warmup", type=float, default=WARMUP)
    parser.add_argument("--batch", type=int, default=BATCH)
    parser.add_argument("--batches", type=int, default=BATCHES)
    arguments = parser.parse_args()

    db_url = consts.get_database_uri()
    if not db_url.startswith("postgresql"):
        raise SystemExit(f"the probe reads a PostgreSQL floor: {db_url}")

    # One connection for the table this run seeds, sweeps and drops,
    # held from here to the end: a cluster with ten workers on it has
    # none to spare for a guard opening one per statement.
    book = stacks.connect(db_url)
    try:
        if arguments.mode == "speed":
            answer = measure_speed(db_url, book, arguments)
        else:
            answer = measure_memory(db_url, book, arguments)
    finally:
        try:
            stacks.drop(book)
        finally:
            book.close()

    sys.stdout.write(orjson.dumps(answer, option=orjson.OPT_INDENT_2).decode())
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
