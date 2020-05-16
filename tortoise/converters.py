import datetime
import time
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, Sequence, Set

_escape_table = [chr(x) for x in range(128)]
_escape_table[0] = "\\0"
_escape_table[ord("\\")] = "\\\\"
_escape_table[ord("\n")] = "\\n"
_escape_table[ord("\r")] = "\\r"
_escape_table[ord("\032")] = "\\Z"
_escape_table[ord('"')] = '\\"'
_escape_table[ord("'")] = "\\'"


def _escape_unicode(value: str, mapping=None):
    """escapes *value* without adding quote.

    Value should be unicode
    """
    return value.translate(_escape_table)


escape_string = _escape_unicode


def escape_item(val: Any, charset, mapping=None) -> str:
    if mapping is None:
        mapping = encoders
    encoder = mapping.get(type(val))

    # Fallback to default when no encoder found
    if not encoder:
        try:
            encoder = mapping[str]
        except KeyError:
            raise TypeError("no default type converter defined")

    if encoder in (escape_dict, escape_sequence):
        val = encoder(val, charset, mapping)
    else:
        val = encoder(val, mapping)
    return val


def escape_dict(val: Dict, charset, mapping=None) -> dict:
    n = {}
    for k, v in val.items():
        quoted = escape_item(v, charset, mapping)
        n[k] = quoted
    return n


def escape_sequence(val: Sequence, charset, mapping=None) -> str:
    n = []
    for item in val:
        quoted = escape_item(item, charset, mapping)
        n.append(quoted)
    return "(" + ",".join(n) + ")"


def escape_set(val: Set, charset, mapping=None) -> str:
    return ",".join([escape_item(x, charset, mapping) for x in val])


def escape_bool(value: bool, mapping=None) -> str:
    return str(int(value))


def escape_object(value: Any, mapping=None) -> str:
    return str(value)


def escape_int(value: int, mapping=None) -> str:
    return str(value)


def escape_float(value: float, mapping=None) -> str:
    return "%.15g" % value


def escape_unicode(value: str, mapping=None) -> str:
    return "'%s'" % _escape_unicode(value)


def escape_str(value: str, mapping=None) -> str:
    return "'%s'" % escape_string(str(value), mapping)


def escape_None(value: None, mapping=None) -> str:
    return "NULL"


def escape_timedelta(obj: timedelta, mapping=None) -> str:
    seconds = int(obj.seconds) % 60
    minutes = int(obj.seconds // 60) % 60
    hours = int(obj.seconds // 3600) % 24 + int(obj.days) * 24
    if obj.microseconds:
        fmt = "'{0:02d}:{1:02d}:{2:02d}.{3:06d}'"
    else:
        fmt = "'{0:02d}:{1:02d}:{2:02d}'"
    return fmt.format(hours, minutes, seconds, obj.microseconds)


def escape_time(obj: datetime.datetime, mapping=None) -> str:
    if obj.microsecond:
        fmt = "'{0.hour:02}:{0.minute:02}:{0.second:02}.{0.microsecond:06}'"
    else:
        fmt = "'{0.hour:02}:{0.minute:02}:{0.second:02}'"
    return fmt.format(obj)


def escape_datetime(obj: datetime.datetime, mapping=None) -> str:
    if obj.microsecond:
        fmt = "'{0.year:04}-{0.month:02}-{0.day:02} {0.hour:02}:{0.minute:02}:{0.second:02}.{0.microsecond:06}'"
    else:
        fmt = "'{0.year:04}-{0.month:02}-{0.day:02} {0.hour:02}:{0.minute:02}:{0.second:02}'"
    return fmt.format(obj)


def escape_date(obj: datetime.date, mapping=None) -> str:
    fmt = "'{0.year:04}-{0.month:02}-{0.day:02}'"
    return fmt.format(obj)


def escape_struct_time(obj: time.struct_time, mapping=None) -> str:
    return escape_datetime(datetime.datetime(*obj[:6]))


def _convert_second_fraction(s) -> int:
    if not s:
        return 0
    # Pad zeros to ensure the fraction length in microseconds
    s = s.ljust(6, "0")
    return int(s[:6])


encoders = {
    bool: escape_bool,
    int: escape_int,
    float: escape_float,
    str: escape_str,
    tuple: escape_sequence,
    list: escape_sequence,
    set: escape_sequence,
    frozenset: escape_sequence,
    dict: escape_dict,
    type(None): escape_None,
    datetime.date: escape_date,
    datetime.datetime: escape_datetime,
    datetime.timedelta: escape_timedelta,
    datetime.time: escape_time,
    time.struct_time: escape_struct_time,
    Decimal: escape_object,
}
