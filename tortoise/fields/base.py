from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple, Type, Union

from pypika.terms import Term

from tortoise.exceptions import ConfigurationError

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model

# TODO: Replace this with an enum
CASCADE = "CASCADE"
RESTRICT = "RESTRICT"
SET_NULL = "SET NULL"
SET_DEFAULT = "SET DEFAULT"


class _FieldMeta(type):
    # TODO: Require functions to return field instances instead of this hack
    def __new__(mcs, name: str, bases: Tuple[Type, ...], attrs: dict):
        if len(bases) > 1 and bases[0] is Field:
            # Instantiate class with only the 1st base class (should be Field)
            cls = type.__new__(mcs, name, (bases[0],), attrs)  # type: Type[Field]
            # All other base classes are our meta types, we store them in class attributes
            cls.field_type = bases[1] if len(bases) == 2 else Union[bases[1:]]
            return cls
        return type.__new__(mcs, name, bases, attrs)


class Field(metaclass=_FieldMeta):
    """
    Base Field type.

    :param source_field: Provide a source_field name if the DB column name needs to be
        something specific instead of enerated off the field name.
    :param generated: Is this field DB-generated?
    :param pk: Is this field a Primary Key? Can only have a single such field on the Model,
        and if none is specified it will autogenerate a default primary key called ``id``.
    :param null: Is this field nullable?
    :param default: A default value for the field if not specified on Model creation.
        This can also be a callable for dynamic defaults in which case we will call it.
        The default value will not be part of the schema.
    :param unique: Is this field unique?
    :param index: Should this field be indexed by itself?
    :param description: Field description. Will also appear in ``Tortoise.describe_model()``
        and as DB comments in the generated DDL.

    **Class Attributes:**
    These attributes needs to be defined when defining an actual field type.

    .. attribute:: field_type
        :annotation: Type[Any]

        The Python type the field is.
        If adding a type as a mixin, _FieldMeta will automatically set this to that.

    .. attribute:: indexable
        :annotation: bool = True

        Is the field indexable? Set to False if this field can't be indexed reliably.

    .. attribute:: has_db_field
        :annotation: bool = True

        Does this field have a direct corresponding DB column? Or is the field virtualized?

    .. attribute:: skip_to_python_if_native
        :annotation: bool = False

        If the DB driver natively supports this Python type, should we skip it?
        This is for optimization purposes only, where we don't need to force type conversion
        to and fro between Python and the DB.

    .. attribute:: allows_generated
        :annotation: bool = False

        Is this field able to be DB-generated?

    .. attribute:: function_cast
        :annotation: Optional[pypika.Term] = None

        A casting term that we need to apply in case the DB needs emulation help.

    .. attribute:: SQL_TYPE
        :annotation: str

        The SQL type as a string that the DB will use.

    .. attribute:: GENERATED_SQL
        :annotation: str

        The SQL that instructs the DB to auto-generate this field.
        Required if ``allows_generated`` is ``True``.

    **Per-DB overrides:**

    One can specify per-DB overrides of any of the class attributes,
    or the ``to_db_value`` or ``to_python_value`` methods.

    To do so, specify a inner class in the form of :samp:`class _db__{SQL_DIALECT}:` like so:

    .. code-block:: py3

        class _db_sqlite:
            SQL_TYPE = "VARCHAR(40)"
            skip_to_python_if_native = False

            def function_cast(self, term: Term) -> Term:
                return functions.Cast(term, SqlTypes.NUMERIC)

    Tortoise will then use the overridden attributes/functions for that dialect.
    If you need a dynamic attribute, you can use a property.
    """

    # Field_type is a readonly property for the instance, it is set by _FieldMeta
    field_type: Type[Any] = None  # type: ignore
    indexable: bool = True
    has_db_field: bool = True
    skip_to_python_if_native: bool = False
    allows_generated: bool = False
    function_cast: Optional[Callable[[Term], Term]] = None
    SQL_TYPE: str = None  # type: ignore
    GENERATED_SQL: str = None  # type: ignore

    # This method is just to make IDE/Linters happy
    def __new__(cls, *args: Any, **kwargs: Any) -> "Field":
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
        description: Optional[str] = None,
        model: "Optional[Model]" = None,
        reference: "Optional[Field]" = None,
        **kwargs: Any,
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
        self.description = description
        self.docstring: Optional[str] = None
        # TODO: consider making this not be set from constructor
        self.model: Type["Model"] = model  # type: ignore
        # TODO: consider moving this to RelationalField
        self.reference = reference

    def to_db_value(self, value: Any, instance: "Union[Type[Model], Model]") -> Any:
        """
        Converts from the Python type to the DB type.

        :param value: Current python value in model.
        :param instance: Model class or Model instance provided to look up.

            Due to metacoding, to determine if this is an instance reliably, please do a:

            .. code-block:: py3

                if hasattr(instance, "_saved_in_db"):
        """
        if value is None or isinstance(value, self.field_type):
            return value
        return self.field_type(value)  # pylint: disable=E1102

    def to_python_value(self, value: Any) -> Any:
        """
        Converts from the DB type to the Python type.

        :param value: Value from DB
        """
        if value is None or isinstance(value, self.field_type):
            return value
        return self.field_type(value)  # pylint: disable=E1102

    @property
    def required(self) -> bool:
        """
        Returns ``True`` if the field is required to be provided.

        It needs to be non-nullable and not have a default or be DB-generated to be required.
        """
        return self.default is None and not self.null and not self.generated

    @property
    def constraints(self) -> dict:
        """
        Returns a dict with constraints defined in the Pydantic/JSONSchema format.
        """
        return {}

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
        """
        Returns the DB types for this field.

        :return: A dictionary that is keyed by dialect.
            A blank dialect `""` means it is the default DB field type.
        """
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
        """
        Returns a field by dialect override.

        :param dialect: The requested SQL Dialect.
        :param key: The attribute/method name.
        """
        dialect_data = self._get_dialects().get(dialect, {})
        return dialect_data.get(key, getattr(self, key, None))
