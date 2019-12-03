import datetime
import functools
import json
from decimal import Decimal
from typing import Any, Optional, Union
from uuid import UUID, uuid4

import ciso8601

from tortoise.exceptions import ConfigurationError
from tortoise.fields.base import Field

# Doing this we can replace json dumps/loads with different implementations
JSON_DUMPS = functools.partial(json.dumps, separators=(",", ":"))
JSON_LOADS = json.loads

try:
    # Use python-rapidjson as an optional accelerator
    import rapidjson

    JSON_DUMPS = rapidjson.dumps
    JSON_LOADS = rapidjson.loads
except ImportError:
    pass


class IntField(Field, int):
    """
    Integer field. (32-bit signed)

    ``pk`` (bool):
        True if field is Primary Key.
    """

    SQL_TYPE = "INT"
    allows_generated = True

    def __init__(self, pk: bool = False, **kwargs) -> None:
        if pk:
            kwargs["generated"] = bool(kwargs.get("generated", True))
        super().__init__(pk=pk, **kwargs)

    class _db_postgres:
        GENERATED_SQL = "SERIAL NOT NULL PRIMARY KEY"

    class _db_sqlite:
        GENERATED_SQL = "INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"

    class _db_mysql:
        GENERATED_SQL = "INT NOT NULL PRIMARY KEY AUTO_INCREMENT"


class BigIntField(Field, int):
    """
    Big integer field. (64-bit signed)

    ``pk`` (bool):
        True if field is Primary Key.
    """

    SQL_TYPE = "BIGINT"
    allows_generated = True

    def __init__(self, pk: bool = False, **kwargs) -> None:
        if pk:
            kwargs["generated"] = bool(kwargs.get("generated", True))
        super().__init__(pk=pk, **kwargs)

    class _db_postgres:
        GENERATED_SQL = "BIGSERIAL NOT NULL PRIMARY KEY"

    class _db_sqlite:
        GENERATED_SQL = "INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"

    class _db_mysql:
        GENERATED_SQL = "BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT"


class SmallIntField(Field, int):
    """
    Small integer field. (16-bit signed)

    ``pk`` (bool):
        True if field is Primary Key.
    """

    SQL_TYPE = "SMALLINT"
    allows_generated = True

    def __init__(self, pk: bool = False, **kwargs) -> None:
        if pk:
            kwargs["generated"] = bool(kwargs.get("generated", True))
        super().__init__(pk=pk, **kwargs)

    class _db_postgres:
        GENERATED_SQL = "SMALLSERIAL NOT NULL PRIMARY KEY"

    class _db_sqlite:
        GENERATED_SQL = "INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"

    class _db_mysql:
        GENERATED_SQL = "SMALLINT NOT NULL PRIMARY KEY AUTO_INCREMENT"


class CharField(Field, str):  # type: ignore
    """
    Character field.

    You must provide the following:

    ``max_length`` (int):
        Maximum length of the field in characters.
    """

    def __init__(self, max_length: int, **kwargs) -> None:
        if int(max_length) < 1:
            raise ConfigurationError("'max_length' must be >= 1")
        self.max_length = int(max_length)
        super().__init__(**kwargs)

    @property
    def SQL_TYPE(self) -> str:
        return f"VARCHAR({self.max_length})"


class TextField(Field, str):  # type: ignore
    """
    Large Text field.
    """

    indexable = False
    SQL_TYPE = "TEXT"


class BooleanField(Field):
    """
    Boolean field.
    """

    # Bool is not subclassable, so we specify type here
    field_type = bool
    SQL_TYPE = "BOOL"

    class _db_sqlite:
        SQL_TYPE = "INT"


class DecimalField(Field, Decimal):
    """
    Accurate decimal field.

    You must provide the following:

    ``max_digits`` (int):
        Max digits of significance of the decimal field.
    ``decimal_places`` (int):
        How many of those signifigant digits is after the decimal point.
    """

    def __init__(self, max_digits: int, decimal_places: int, **kwargs) -> None:
        if int(max_digits) < 1:
            raise ConfigurationError("'max_digits' must be >= 1")
        if int(decimal_places) < 0:
            raise ConfigurationError("'decimal_places' must be >= 0")
        super().__init__(**kwargs)
        self.max_digits = max_digits
        self.decimal_places = decimal_places

    @property
    def SQL_TYPE(self) -> str:
        return f"DECIMAL({self.max_digits},{self.decimal_places})"

    class _db_sqlite:
        SQL_TYPE = "VARCHAR(40)"


class DatetimeField(Field, datetime.datetime):
    """
    Datetime field.

    ``auto_now`` and ``auto_now_add`` is exclusive.
    You can opt to set neither or only ONE of them.

    ``auto_now`` (bool):
        Always set to ``datetime.utcnow()`` on save.
    ``auto_now_add`` (bool):
        Set to ``datetime.utcnow()`` on first save only.
    """

    skip_to_python_if_native = True
    SQL_TYPE = "TIMESTAMP"

    class _db_mysql:
        SQL_TYPE = "DATETIME(6)"

    def __init__(self, auto_now: bool = False, auto_now_add: bool = False, **kwargs) -> None:
        if auto_now_add and auto_now:
            raise ConfigurationError("You can choose only 'auto_now' or 'auto_now_add'")
        super().__init__(**kwargs)
        self.auto_now = auto_now
        self.auto_now_add = auto_now | auto_now_add

    def to_python_value(self, value: Any) -> Optional[datetime.datetime]:
        if value is None or isinstance(value, datetime.datetime):
            return value
        return ciso8601.parse_datetime(value)

    def to_db_value(
        self, value: Optional[datetime.datetime], instance
    ) -> Optional[datetime.datetime]:
        if hasattr(instance, "_saved_in_db"):
            # Only do this if it is a Model instance, not class. Test for guaranteed instance var
            if self.auto_now or (
                self.auto_now_add and getattr(instance, self.model_field_name) is None
            ):
                value = datetime.datetime.utcnow()
                setattr(instance, self.model_field_name, value)
                return value
        return value


class DateField(Field, datetime.date):
    """
    Date field.
    """

    skip_to_python_if_native = True
    SQL_TYPE = "DATE"

    def to_python_value(self, value: Any) -> Optional[datetime.date]:
        if value is None or isinstance(value, datetime.date):
            return value
        return ciso8601.parse_datetime(value).date()


class TimeDeltaField(Field, datetime.timedelta):
    """
    A field for storing time differences.
    """

    SQL_TYPE = "BIGINT"

    def to_python_value(self, value: Any) -> Optional[datetime.timedelta]:
        if value is None or isinstance(value, datetime.timedelta):
            return value
        return datetime.timedelta(microseconds=value)

    def to_db_value(self, value: Optional[datetime.timedelta], instance) -> Optional[int]:
        if value is None:
            return None
        return (value.days * 86400000000) + (value.seconds * 1000000) + value.microseconds


class FloatField(Field, float):
    """
    Float (double) field.
    """

    SQL_TYPE = "DOUBLE PRECISION"

    class _db_sqlite:
        SQL_TYPE = "REAL"

    class _db_mysql:
        SQL_TYPE = "DOUBLE"


class JSONField(Field, dict, list):  # type: ignore
    """
    JSON field.

    This field can store dictionaries or lists of any JSON-compliant structure.

    You can specify your own custom JSON encoder/decoder, leaving at the default should work well.
    If you have ``python-rapidjson`` installed, we default to using that,
    else the default ``json`` module will be used.

    ``encoder``:
        The custom JSON encoder.
    ``decoder``:
        The custom JSON decoder.

    """

    SQL_TYPE = "TEXT"
    indexable = False

    class _db_postgres:
        SQL_TYPE = "JSONB"

    def __init__(self, encoder=JSON_DUMPS, decoder=JSON_LOADS, **kwargs) -> None:
        super().__init__(**kwargs)
        self.encoder = encoder
        self.decoder = decoder

    def to_db_value(self, value: Optional[Union[dict, list]], instance) -> Optional[str]:
        return None if value is None else self.encoder(value)

    def to_python_value(
        self, value: Optional[Union[str, dict, list]]
    ) -> Optional[Union[dict, list]]:
        return self.decoder(value) if isinstance(value, str) else value


class UUIDField(Field, UUID):
    """
    UUID Field

    This field can store uuid value.

    If used as a primary key, it will auto-generate a UUID4 by default.
    """

    SQL_TYPE = "CHAR(36)"

    class _db_postgres:
        SQL_TYPE = "UUID"

    def __init__(self, **kwargs) -> None:
        if kwargs.get("pk", False):
            if "default" not in kwargs:
                kwargs["default"] = uuid4
        super().__init__(**kwargs)

    def to_db_value(self, value: Any, instance) -> Optional[str]:
        return value and str(value)

    def to_python_value(self, value: Any) -> Optional[UUID]:
        if value is None or isinstance(value, UUID):
            return value
        return UUID(value)
