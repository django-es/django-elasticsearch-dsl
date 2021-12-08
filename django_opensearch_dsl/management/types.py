import datetime
from typing import Union, List

from dateutil.parser import isoparse
from django.conf import settings
from django.utils.timezone import make_aware, is_aware

Nothing = type(Ellipsis)
Values = Union[None, int, float, datetime.datetime, str, List['Values']]


def datetime_parser(value: str) -> Union[Nothing, datetime.datetime]:
    """Try to parse the given value as a ISO 8601's datetime."""
    try:
        date = isoparse(value)
        if not is_aware(date):
            date = make_aware(isoparse(value))
        return date
    except ValueError as e:
        return ...


def int_parser(value: str) -> Union[Nothing, int]:
    """Try to parse the given value as an integer."""
    try:
        return int(value)
    except ValueError:
        return ...


def float_parser(value: str) -> Union[Nothing, float]:
    """Try to parse the given value as a float."""
    try:
        return float(value)
    except ValueError:
        return ...


def none_parser(value: str) -> Union[Nothing, None]:
    """Try to parse the given value as a float."""
    return None if value == "" else ...


def list_parser(value: str) -> Values:
    """Try to parse the given value as a ISO 8601's datetime."""
    if "," in value:
        return [parse(v.strip()) for v in value.split(",")]
    return ...


def parse(value: str) -> Values:
    """Try to coerce a string into a different type.

    The order in which the parsers are called matters as some type might include
    other, e.g. `float_parser()` would match an `int` as a `float` if called
    before `int_parser()`.

    If no parser was able to parse the value, it is returned as a string."""
    parsers = getattr(
        settings, 'OPENSEARCH_DSL_VALUE_PARSERS',
        [none_parser, int_parser, float_parser, datetime_parser, list_parser]
    )
    for parser in parsers:
        v = parser(value)
        if v != ...:  # noqa
            return v
    return value
