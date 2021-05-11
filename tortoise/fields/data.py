import datetime
import functools
import json
import warnings
from decimal import Decimal
from enum import Enum, IntEnum
from typing import TYPE_CHECKING, Any, Callable, Optional, Type, TypeVar, Union
from uuid import UUID, uuid4

from pypika import functions
from pypika.enums import SqlTypes
from pypika.terms import Term

from tortoise import timezone
from tortoise.exceptions import ConfigurationError, FieldError
from tortoise.fields.base import Field
from tortoise.timezone import get_timezone, get_use_tz, localtime
from tortoise.validators import MaxLengthValidator

try:
    from ciso8601 import parse_datetime
except ImportError:  # pragma: nocoverage
    from iso8601 import parse_date

    parse_datetime = functools.partial(parse_date, default_timezone=None)

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model

__all__ = (
    "BigIntField",
    "BinaryField",
    "BooleanField",
    "CharEnumField",
    "CharField",
    "DateField",
    "DatetimeField",
    "DecimalField",
    "FloatField",
    "IntEnumField",
    "IntField",
    "JSONField",
    "SmallIntField",
    "TextField",
    "TimeDeltaField",
    "UUIDField",
)

# Doing this we can replace json dumps/loads with different implementations
JsonDumpsFunc = Callable[[Any], str]
JsonLoadsFunc = Callable[[str], Any]
JSON_DUMPS: JsonDumpsFunc = functools.partial(json.dumps, separators=(",", ":"))
JSON_LOADS: JsonLoadsFunc = json.loads

try:
    # Use python-rapidjson as an optional accelerator
    import rapidjson

    JSON_DUMPS = rapidjson.dumps
    JSON_LOADS = rapidjson.loads
except ImportError:  # pragma: nocoverage
    pass


class IntField(Field, int):
    """
    Integer field. (32-bit signed)

    ``pk`` (bool):
        True if field is Primary Key.
    """

    SQL_TYPE = "INT"
    allows_generated = True

    def __init__(self, pk: bool = False, **kwargs: Any) -> None:
        if pk:
            kwargs["generated"] = bool(kwargs.get("generated", True))
        super().__init__(pk=pk, **kwargs)

    @property
    def constraints(self) -> dict:
        return {
            "ge": 1 if self.generated or self.reference else -2147483648,
            "le": 2147483647,
        }

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

    def __init__(self, pk: bool = False, **kwargs: Any) -> None:
        if pk:
            kwargs["generated"] = bool(kwargs.get("generated", True))
        super().__init__(pk=pk, **kwargs)

    @property
    def constraints(self) -> dict:
        return {
            "ge": 1 if self.generated or self.reference else -9223372036854775808,
            "le": 9223372036854775807,
        }

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

    def __init__(self, pk: bool = False, **kwargs: Any) -> None:
        if pk:
            kwargs["generated"] = bool(kwargs.get("generated", True))
        super().__init__(pk=pk, **kwargs)

    @property
    def constraints(self) -> dict:
        return {
            "ge": 1 if self.generated or self.reference else -32768,
            "le": 32767,
        }

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

    def __init__(self, max_length: int, **kwargs: Any) -> None:
        if int(max_length) < 1:
            raise ConfigurationError("'max_length' must be >= 1")
        self.max_length = int(max_length)
        super().__init__(**kwargs)
        self.validators.append(MaxLengthValidator(self.max_length))

    @property
    def constraints(self) -> dict:
        return {
            "max_length": self.max_length,
        }

    @property
    def SQL_TYPE(self) -> str:  # type: ignore
        return f"VARCHAR({self.max_length})"


class TextField(Field, str):  # type: ignore
    """
    Large Text field.
    """

    indexable = False
    SQL_TYPE = "TEXT"

    def __init__(
        self, pk: bool = False, unique: bool = False, index: bool = False, **kwargs: Any
    ) -> None:
        if pk:
            warnings.warn(
                "TextField as a PrimaryKey is Deprecated, use CharField instead",
                DeprecationWarning,
                stacklevel=2,
            )
        if unique:
            raise ConfigurationError(
                "TextField doesn't support unique indexes, consider CharField or another strategy"
            )
        if index:
            raise ConfigurationError("TextField can't be indexed, consider CharField")

        super().__init__(pk=pk, **kwargs)

    class _db_mysql:
        SQL_TYPE = "LONGTEXT"


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

    skip_to_python_if_native = True

    def __init__(self, max_digits: int, decimal_places: int, **kwargs: Any) -> None:
        if int(max_digits) < 1:
            raise ConfigurationError("'max_digits' must be >= 1")
        if int(decimal_places) < 0:
            raise ConfigurationError("'decimal_places' must be >= 0")
        super().__init__(**kwargs)
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        self.quant = Decimal("1" if decimal_places == 0 else f"1.{('0' * decimal_places)}")

    def to_python_value(self, value: Any) -> Optional[Decimal]:

        if value is None:
            value = None
        else:
            value = Decimal(value).quantize(self.quant).normalize()
        self.validate(value)
        return value

    @property
    def SQL_TYPE(self) -> str:  # type: ignore
        return f"DECIMAL({self.max_digits},{self.decimal_places})"

    class _db_sqlite:
        SQL_TYPE = "VARCHAR(40)"

        def function_cast(self, term: Term) -> Term:
            return functions.Cast(term, SqlTypes.NUMERIC)


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

    SQL_TYPE = "TIMESTAMP"

    class _db_mysql:
        SQL_TYPE = "DATETIME(6)"

    class _db_postgres:
        SQL_TYPE = "TIMESTAMPTZ"

    def __init__(self, auto_now: bool = False, auto_now_add: bool = False, **kwargs: Any) -> None:
        if auto_now_add and auto_now:
            raise ConfigurationError("You can choose only 'auto_now' or 'auto_now_add'")
        super().__init__(**kwargs)
        self.auto_now = auto_now
        self.auto_now_add = auto_now | auto_now_add

    def to_python_value(self, value: Any) -> Optional[datetime.datetime]:
        if value is None:
            value = None
        else:
            if isinstance(value, datetime.datetime):
                value = value
            elif isinstance(value, int):
                value = datetime.datetime.fromtimestamp(value)
            else:
                value = parse_datetime(value)
            if timezone.is_naive(value):
                value = timezone.make_aware(value, get_timezone())
            else:
                value = localtime(value)
        self.validate(value)
        return value

    def to_db_value(
        self, value: Optional[datetime.datetime], instance: "Union[Type[Model], Model]"
    ) -> Optional[datetime.datetime]:

        # Only do this if it is a Model instance, not class. Test for guaranteed instance var
        if hasattr(instance, "_saved_in_db") and (
            self.auto_now
            or (self.auto_now_add and getattr(instance, self.model_field_name) is None)
        ):
            value = timezone.now()
            setattr(instance, self.model_field_name, value)
            return value
        if value is not None:
            if get_use_tz():
                if timezone.is_naive(value):
                    warnings.warn(
                        "DateTimeField %s received a naive datetime (%s)"
                        " while time zone support is active." % (self.model_field_name, value),
                        RuntimeWarning,
                    )
                    value = timezone.make_aware(value, "UTC")
        self.validate(value)
        return value

    @property
    def constraints(self) -> dict:
        data = {}
        if self.auto_now_add:
            data["readOnly"] = True
        return data

    def describe(self, serializable: bool) -> dict:
        desc = super().describe(serializable)
        desc["auto_now_add"] = self.auto_now_add
        desc["auto_now"] = self.auto_now
        return desc


class DateField(Field, datetime.date):
    """
    Date field.
    """

    skip_to_python_if_native = True
    SQL_TYPE = "DATE"

    def to_python_value(self, value: Any) -> Optional[datetime.date]:

        if value is not None and not isinstance(value, datetime.date):
            value = parse_datetime(value).date()
        self.validate(value)
        return value

    def to_db_value(
        self, value: Optional[Union[datetime.date, str]], instance: "Union[Type[Model], Model]"
    ) -> Optional[datetime.date]:

        if value is not None and not isinstance(value, datetime.date):
            return_value = parse_datetime(value).date()
        else:
            return_value = value
        self.validate(return_value)
        return return_value


class TimeDeltaField(Field, datetime.timedelta):
    """
    A field for storing time differences.
    """

    SQL_TYPE = "BIGINT"

    def to_python_value(self, value: Any) -> Optional[datetime.timedelta]:
        self.validate(value)

        if value is None or isinstance(value, datetime.timedelta):
            return value
        return datetime.timedelta(microseconds=value)

    def to_db_value(
        self, value: Optional[datetime.timedelta], instance: "Union[Type[Model], Model]"
    ) -> Optional[int]:
        self.validate(value)

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

    SQL_TYPE = "JSON"
    indexable = False

    class _db_postgres:
        SQL_TYPE = "JSONB"

    def __init__(
        self,
        encoder: JsonDumpsFunc = JSON_DUMPS,
        decoder: JsonLoadsFunc = JSON_LOADS,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.encoder = encoder
        self.decoder = decoder

    def to_db_value(
        self, value: Optional[Union[dict, list, str]], instance: "Union[Type[Model], Model]"
    ) -> Optional[str]:
        self.validate(value)

        if isinstance(value, str):
            try:
                self.decoder(value)
            except Exception:
                raise FieldError(f"Value {value} is invalid json value.")
            return value
        return None if value is None else self.encoder(value)

    def to_python_value(
        self, value: Optional[Union[str, dict, list]]
    ) -> Optional[Union[dict, list]]:
        if isinstance(value, str):
            try:
                return self.decoder(value)
            except Exception:
                raise FieldError(f"Value {value} is invalid json value.")

        self.validate(value)
        return value


class UUIDField(Field, UUID):
    """
    UUID Field

    This field can store uuid value.

    If used as a primary key, it will auto-generate a UUID4 by default.
    """

    SQL_TYPE = "CHAR(36)"

    class _db_postgres:
        SQL_TYPE = "UUID"

    def __init__(self, **kwargs: Any) -> None:
        if kwargs.get("pk", False) and "default" not in kwargs:
            kwargs["default"] = uuid4
        super().__init__(**kwargs)

    def to_db_value(self, value: Any, instance: "Union[Type[Model], Model]") -> Optional[str]:
        return value and str(value)

    def to_python_value(self, value: Any) -> Optional[UUID]:
        if value is None or isinstance(value, UUID):
            return value
        return UUID(value)


class BinaryField(Field, bytes):  # type: ignore
    """
    Binary field.

    This is for storing ``bytes`` objects.
    Note that filter or queryset-update operations are not supported.
    """

    indexable = False
    SQL_TYPE = "BLOB"

    class _db_postgres:
        SQL_TYPE = "BYTEA"

    class _db_mysql:
        SQL_TYPE = "LONGBLOB"


class IntEnumFieldInstance(SmallIntField):
    def __init__(
        self, enum_type: Type[IntEnum], description: Optional[str] = None, **kwargs: Any
    ) -> None:
        # Validate values
        for item in enum_type:
            try:
                value = int(item.value)
            except ValueError:
                raise ConfigurationError("IntEnumField only supports integer enums!")
            if not 0 <= value < 32768:
                raise ConfigurationError("The valid range of IntEnumField's values is 0..32767!")

        # Automatic description for the field if not specified by the user
        if description is None:
            description = "\n".join([f"{e.name}: {int(e.value)}" for e in enum_type])[:2048]

        super().__init__(description=description, **kwargs)
        self.enum_type = enum_type

    def to_python_value(self, value: Union[int, None]) -> Union[IntEnum, None]:

        value = self.enum_type(value) if value is not None else None
        self.validate(value)
        return value

    def to_db_value(
        self, value: Union[IntEnum, None, int], instance: "Union[Type[Model], Model]"
    ) -> Union[int, None]:

        if isinstance(value, IntEnum):
            value = int(value.value)
        if isinstance(value, int):
            value = int(self.enum_type(value))
        self.validate(value)
        return value


IntEnumType = TypeVar("IntEnumType", bound=IntEnum)


def IntEnumField(
    enum_type: Type[IntEnumType],
    description: Optional[str] = None,
    **kwargs: Any,
) -> IntEnumType:
    """
    Enum Field

    A field representing an integer enumeration.

    The description of the field is set automatically if not specified to a multiline list of
    "name: value" pairs.

    **Note**: Valid int value of ``enum_type`` is acceptable.

    ``enum_type``:
        The enum class
    ``description``:
        The description of the field. It is set automatically if not specified to a multiline list
        of "name: value" pairs.

    """
    return IntEnumFieldInstance(enum_type, description, **kwargs)  # type: ignore


class CharEnumFieldInstance(CharField):
    def __init__(
        self,
        enum_type: Type[Enum],
        description: Optional[str] = None,
        max_length: int = 0,
        **kwargs: Any,
    ) -> None:
        # Automatic description for the field if not specified by the user
        if description is None:
            description = "\n".join([f"{e.name}: {str(e.value)}" for e in enum_type])[:2048]

        # Automatic CharField max_length
        if max_length == 0:
            for item in enum_type:
                item_len = len(str(item.value))
                if item_len > max_length:
                    max_length = item_len

        super().__init__(description=description, max_length=max_length, **kwargs)
        self.enum_type = enum_type

    def to_python_value(self, value: Union[str, None]) -> Union[Enum, None]:
        self.validate(value)

        return self.enum_type(value) if value is not None else None

    def to_db_value(
        self, value: Union[Enum, None, str], instance: "Union[Type[Model], Model]"
    ) -> Union[str, None]:
        self.validate(value)
        if isinstance(value, Enum):
            return str(value.value)
        if isinstance(value, str):
            return str(self.enum_type(value).value)
        return value


CharEnumType = TypeVar("CharEnumType", bound=Enum)


def CharEnumField(
    enum_type: Type[CharEnumType],
    description: Optional[str] = None,
    max_length: int = 0,
    **kwargs: Any,
) -> CharEnumType:
    """
    Char Enum Field

    A field representing a character enumeration.

    **Warning**: If ``max_length`` is not specified or equals to zero, the size of represented
    char fields is automatically detected. So if later you update the enum, you need to update your
    table schema as well.

    **Note**: Valid str value of ``enum_type`` is acceptable.

    ``enum_type``:
        The enum class
    ``description``:
        The description of the field. It is set automatically if not specified to a multiline list
        of "name: value" pairs.
    ``max_length``:
        The length of the created CharField. If it is zero it is automatically detected from
        enum_type.

    """

    return CharEnumFieldInstance(enum_type, description, max_length, **kwargs)  # type: ignore
