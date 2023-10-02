import datetime
from typing import Union, List

from dateutil.parser import isoparse
from django.conf import settings
from django.utils.timezone import make_aware, is_aware


def datetime_parser(value):
    """Try to parse the given value as an ISO 8601's datetime."""
    try:
        date = isoparse(value)
        if not is_aware(date):
            date = make_aware(date)
        return date
    except ValueError:
        return ...


def int_parser(value):
    """Try to parse the given value as an integer."""
    try:
        return int(value)
    except ValueError:
        return ...


def float_parser(value):
    """Try to parse the given value as a float."""
    try:
        return float(value)
    except ValueError:
        return ...


def none_parser(value):
    """Try to parse the given value as a float."""
    return None if value == "" else ...


def list_parser(value):
    """Try to parse the given value as a comma-separated list of values."""
    if "," in value:
        return [parse(v.strip()) for v in value.split(",")]
    return ...


def parse(value):
    """Try to coerce a string into a different type.

    The order in which the parsers are called matters as some type might include
    other, e.g. `float_parser()` would match an `int` as a `float` if called
    before `int_parser()`.

    If no parser were able to parse the value, it is returned as a string.
    """
    parsers = getattr(
        settings,
        "OPENSEARCH_DSL_VALUE_PARSERS",
        [none_parser, int_parser, float_parser, datetime_parser, list_parser]
    )
    for parser in parsers:
        v = parser(value)
        if v != ...:  # noqa
            return v
    return value
