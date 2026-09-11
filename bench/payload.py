"""The one shape every stack has to produce.

A benchmark that lets one stack answer with less than another measures
nothing, so each stack's output is parsed and compared against the same
rows before anything is timed. Timestamps are compared as instants, not
as strings: the stacks spell them differently (`Z` against `+00:00`),
and that is a formatting difference, not less work.
"""

import datetime

FIELDS = (
    "id",
    "name",
    "description",
    "enabled",
    "quantity",
    "project_id",
    "created_at",
    "updated_at",
)


def normalise(document):
    """One object, in a form two stacks can be compared by."""
    result = {}
    for field in FIELDS:
        value = document[field]
        if field in ("created_at", "updated_at"):
            value = _instant(value)
        elif field in ("id", "project_id"):
            value = str(value).lower()
        result[field] = value
    return result


def _instant(value):
    if isinstance(value, datetime.datetime):
        moment = value
    else:
        text = value.replace("Z", "+00:00")
        moment = datetime.datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=datetime.timezone.utc)
    return moment.astimezone(datetime.timezone.utc).isoformat()


def same(left, right):
    if isinstance(left, list) != isinstance(right, list):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(
            normalise(a) == normalise(b) for a, b in zip(left, right)
        )
    return normalise(left) == normalise(right)
