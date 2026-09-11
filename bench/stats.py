"""Paired statistics, the same ones the RestAlchemy branch was measured with."""

import math
import random
import statistics

SHUFFLES = 20000


def permutation_p(differences):
    """How often chance alone shifts the differences this far from zero.

    The statistic is the mean: flipping a sign does not change a value's
    size, so a median would call a real, one-sided effect nothing.
    """
    if not differences:
        return 1.0
    observed = abs(statistics.fmean(differences))
    hits = 0
    for _ in range(SHUFFLES):
        flipped = [d if random.random() < 0.5 else -d for d in differences]
        if abs(statistics.fmean(flipped)) >= observed:
            hits += 1
    return (hits + 1) / (SHUFFLES + 1)


def sign_p(differences):
    negative = sum(1 for d in differences if d < 0)
    positive = sum(1 for d in differences if d > 0)
    total = negative + positive
    if not total:
        return 1.0
    extreme = max(negative, positive)
    tail = sum(math.comb(total, k) for k in range(extreme, total + 1)) / 2**total
    return min(1.0, 2 * tail)


def interval(values, level=0.95, draws=5000):
    picks = []
    size = len(values)
    for _ in range(draws):
        sample = [values[random.randrange(size)] for _ in range(size)]
        picks.append(statistics.median(sample))
    picks.sort()
    return (
        picks[int((1 - level) / 2 * len(picks))],
        picks[int((1 + level) / 2 * len(picks)) - 1],
    )
