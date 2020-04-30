from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Type, Union

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
        **kwargs: Any,
    ) -> None:
        # TODO: Rename pk to primary_key, alias pk, deprecate
        # TODO: Rename index to db_index, alias index, deprecate
        if not self.indexable and (unique or index):
            raise ConfigurationError(f"{self.__class__.__name__} can't be indexed")
        if pk and null:
            raise ConfigurationError(
                f"{self.__class__.__name__} can't be both null=True and pk=True"
            )
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
        self.reference: "Optional[Field]" = None

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
        if not self.has_db_field:  # pragma: nocoverage
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

    def describe(self, serializable: bool) -> dict:
        """
        Describes the field.

        :param serializable:
            ``False`` if you want raw python objects,
            ``True`` for JSON-serialisable data. (Defaults to ``True``)

        :return:
            A dictionary containing the field description.

            (This assumes ``serializable=True``, which is the default):

            .. code-block:: python3

                {
                    "name":         str     # Field name
                    "field_type":   str     # Field type
                    "db_column":    str     # Name of DB column
                                            #  Optional: Only for pk/data fields
                    "raw_field":    str     # Name of raw field of the Foreign Key
                                            #  Optional: Only for Foreign Keys
                    "db_field_types": dict  # DB Field types for default and DB overrides
                    "python_type":  str     # Python type
                    "generated":    bool    # Is the field generated by the DB?
                    "nullable":     bool    # Is the column nullable?
                    "unique":       bool    # Is the field unique?
                    "indexed":      bool    # Is the field indexed?
                    "default":      ...     # The default value (coerced to int/float/str/bool/null)
                    "description":  str     # Description of the field (nullable)
                    "docstring":    str     # Field docstring (nullable)
                }

            When ``serializable=False`` is specified some fields are not coerced to valid
            JSON types. The changes are:

            .. code-block:: python3

                {
                    "field_type":   Field   # The Field class used
                    "python_type":  Type    # The actual Python type
                    "default":      ...     # The default value as native type OR a callable
                }
        """

        def _type_name(typ: Type) -> str:
            if typ.__module__ == "builtins":
                return typ.__name__
            if typ.__module__ == "typing":
                return str(typ).replace("typing.", "")
            return f"{typ.__module__}.{typ.__name__}"

        def type_name(typ: Any) -> Union[str, List[str]]:
            try:
                return typ._meta.full_name
            except (AttributeError, TypeError):
                pass
            try:
                return _type_name(typ)
            except AttributeError:
                try:
                    return [_type_name(_typ) for _typ in typ]  # pragma: nobranch
                except TypeError:
                    return str(typ)

        def default_name(default: Any) -> Optional[Union[int, float, str, bool]]:
            if isinstance(default, (int, float, str, bool, type(None))):
                return default
            if callable(default):
                return f"<function {default.__module__}.{default.__name__}>"
            return str(default)

        field_type = getattr(self, "related_model", self.field_type)
        desc = {
            "name": self.model_field_name,
            "field_type": self.__class__.__name__ if serializable else self.__class__,
            "db_column": self.source_field or self.model_field_name,
            "python_type": type_name(field_type) if serializable else field_type,
            "generated": self.generated,
            "nullable": self.null,
            "unique": self.unique,
            "indexed": self.index or self.unique,
            "default": default_name(self.default) if serializable else self.default,
            "description": self.description,
            "docstring": self.docstring,
            "constraints": self.constraints,
        }

        if self.has_db_field:
            desc["db_field_types"] = self.get_db_field_types()

        return desc
