from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from tortoise.exceptions import ConfigurationError

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model

CASCADE = "CASCADE"
RESTRICT = "RESTRICT"
SET_NULL = "SET NULL"
SET_DEFAULT = "SET DEFAULT"


class _FieldMeta(type):
    def __new__(mcs, name, bases, attrs):
        if len(bases) > 1 and bases[0] is Field:
            # Instantiate class with only the 1st base class (should be Field)
            cls = type.__new__(mcs, name, (bases[0],), attrs)  # type: Type[Field]
            # All other base classes are our meta types, we store them in class attributes
            cls.field_type = bases[1] if len(bases) == 2 else bases[1:]
            return cls
        return type.__new__(mcs, name, bases, attrs)


class Field(metaclass=_FieldMeta):
    """
    Base Field type.
    """

    # Field_type is a readonly property for the instance, it is set by _FieldMeta
    field_type: Type[Any] = None  # type: ignore
    indexable: bool = True
    has_db_field = True
    skip_to_python_if_native = False
    allows_generated = False
    function_cast = None

    # This method is just to make IDE/Linters happy
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(
        self,
        source_field: Optional[str] = None,
        generated: bool = False,
        pk: bool = False,
        null: bool = False,
        default: Any = None,
        unique: bool = False,
        index: bool = False,
        reference: Optional[str] = None,
        model: "Optional[Model]" = None,
        description: Optional[str] = None,
        **kwargs,
    ) -> None:
        if not self.indexable and (unique or index):
            raise ConfigurationError(f"{self.__class__.__name__} can't be indexed")
        if pk:
            index = True
            unique = True
        self.source_field = source_field
        self.generated = generated
        self.pk = pk
        self.default = default
        self.null = null
        self.unique = unique
        self.index = index
        self.model_field_name = ""
        self.model = model
        self.reference = reference
        self.description = description

    def to_db_value(self, value: Any, instance) -> Any:
        if value is None or isinstance(value, self.field_type):
            return value
        return self.field_type(value)  # pylint: disable=E1102

    def to_python_value(self, value: Any) -> Any:
        if value is None or isinstance(value, self.field_type):
            return value
        return self.field_type(value)  # pylint: disable=E1102

    @property
    def required(self):
        return self.default is None and not self.null and not self.generated

    def _get_dialects(self) -> Dict[str, dict]:
        return {
            dialect[4:]: {
                key: val
                for key, val in getattr(self, dialect).__dict__.items()
                if not key.startswith("_")
            }
            for dialect in [key for key in dir(self) if key.startswith("_db_")]
        }

    def get_db_field_types(self) -> Optional[Dict[str, str]]:
        if not self.has_db_field:
            return None
        return {
            "": getattr(self, "SQL_TYPE"),
            **{
                dialect: _db["SQL_TYPE"]
                for dialect, _db in self._get_dialects().items()
                if "SQL_TYPE" in _db
            },
        }

    def get_for_dialect(self, dialect: str, key: str) -> Any:
        dialect_data = self._get_dialects().get(dialect, {})
        return dialect_data.get(key, getattr(self, key, None))
