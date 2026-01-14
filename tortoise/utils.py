from __future__ import annotations

import contextlib
import datetime
import re
import sys
from collections.abc import Iterable
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from tortoise.log import logger

if sys.version_info >= (3, 12):
    from itertools import batched
else:
    from itertools import islice

    def batched(iterable: Iterable[Any], n: int) -> Iterable[tuple[Any]]:
        it = iter(iterable)
        while batch := tuple(islice(it, n)):
            yield batch


if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.base.client import BaseDBAsyncClient


def get_schema_sql(client: BaseDBAsyncClient, safe: bool) -> str:
    """
    Generates the SQL schema for the given client.

    :param client: The DB client to generate Schema SQL for
    :param safe: When set to true, creates the table only when it does not already exist.
    """
    generator = client.schema_generator(client)
    return generator.get_create_schema_sql(safe)


async def generate_schema_for_client(client: BaseDBAsyncClient, safe: bool) -> None:
    """
    Generates and applies the SQL schema directly to the given client.

    :param client: The DB client to generate Schema SQL for
    :param safe: When set to true, creates the table only when it does not already exist.
    """
    generator = client.schema_generator(client)
    schema = get_schema_sql(client, safe)
    logger.debug("Creating schema: %s", schema)
    if schema:  # pragma: nobranch
        await generator.generate_from_string(schema)


def chunk(instances: Iterable[Any], batch_size: int | None = None) -> Iterable[Iterable[Any]]:
    """
    Generate iterable chunk by batch_size
    # noqa: DAR301
    """
    if not batch_size:
        yield instances
    else:
        yield from batched(instances, batch_size)


# Copied from https://github.com/micktwomey/pyiso8601/blob/main/iso8601/iso8601.py
ISO8601_REGEX = re.compile(
    r"""
    (?P<year>[0-9]{4})
    (
        (
            (-(?P<monthdash>[0-9]{1,2}))
            |
            (?P<month>[0-9]{2})
            (?!$)  # Don't allow YYYYMM
        )
        (
            (
                (-(?P<daydash>[0-9]{1,2}))
                |
                (?P<day>[0-9]{2})
            )
            (
                (
                    (?P<separator>[ T])
                    (?P<hour>[0-9]{2})
                    (:{0,1}(?P<minute>[0-9]{2})){0,1}
                    (
                        :{0,1}(?P<second>[0-9]{1,2})
                        ([.,](?P<second_fraction>[0-9]+)){0,1}
                    ){0,1}
                    (?P<timezone>
                        Z
                        |
                        (
                            (?P<tz_sign>[-+])
                            (?P<tz_hour>[0-9]{2})
                            :{0,1}
                            (?P<tz_minute>[0-9]{2}){0,1}
                        )
                    ){0,1}
                ){0,1}
            )
        ){0,1}  # YYYY-MM
    ){0,1}  # YYYY only
    $
    """,
    re.VERBOSE,
)


def parse_datetime(datetime_string: str) -> datetime.datetime:
    datetime_string = datetime_string.upper()
    with contextlib.suppress(ValueError):
        return datetime.datetime.fromisoformat(datetime_string)
    if not (m := ISO8601_REGEX.match(datetime_string)):
        raise ValueError(f"Unable to parse date string {datetime_string!r}")
    # Drop any Nones from the regex matches
    # TODO: check if there's a way to omit results in regexes
    groups: dict[str, str] = {k: v for k, v in m.groupdict().items() if v is not None}
    zone = None
    if tz := groups.get("timezone", None):
        if tz == "Z":
            zone = datetime.timezone.utc
        else:
            sign = groups.get("tz_sign", None)
            hours = int(groups.get("tz_hour", 0))
            minutes = int(groups.get("tz_minute", 0))
            description = f"{sign}{hours:02d}:{minutes:02d}"
            if sign == "-":
                hours = -hours
                minutes = -minutes
            zone = datetime.timezone(datetime.timedelta(hours=hours, minutes=minutes), description)
    return datetime.datetime(
        year=int(groups.get("year", 0)),
        month=int(groups.get("month", groups.get("monthdash", 1))),
        day=int(groups.get("day", groups.get("daydash", 1))),
        hour=int(groups.get("hour", 0)),
        minute=int(groups.get("minute", 0)),
        second=int(groups.get("second", 0)),
        microsecond=int(Decimal(f"0.{groups.get('second_fraction', 0)}") * Decimal("1000000.0")),
        tzinfo=zone,
    )
