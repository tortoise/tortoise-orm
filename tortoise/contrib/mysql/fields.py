from tortoise.fields import Field
from tortoise.fields.data import UUIDField as UUIDFieldBase
from uuid import UUID, uuid4
from typing import Any, Optional, Type, Union, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model


class GeometryField(Field):
    SQL_TYPE = "GEOMETRY"

class UUIDField(UUIDFieldBase[Union[UUID, bytes]], bytes, UUID):
    """
    UUID Field

    This field can store uuid value, but with the option to add binary compression.

    If used as a primary key, it will auto-generate a UUID4 by default.

    ``binary_compression``: (bool)
        If True, the UUID will be stored in binary format.
        This will save 6 bytes per UUID in the database.
        Note: that this is a MySQL-only feature. 
        See https://dev.mysql.com/blog-archive/mysql-8-0-uuid-support/ for more details.
    """

    SQL_TYPE = "CHAR(36)"

    def __init__(self, binary_compression: bool = True, **kwargs: Any) -> None:
        if kwargs.get("pk", False) and "default" not in kwargs:
            kwargs["default"] = uuid4
        super().__init__(**kwargs)

        if binary_compression:
            self.SQL_TYPE = "BINARY(16)"
        self._binary_compression = binary_compression

    def to_db_value(self, value: Any) -> Optional[Union[str, bytes]]:
       # Make sure that value is a UUIDv4
       # If not, raise an error
       # This is to prevent UUIDv1 or any other version from being stored in the database
        if self._binary_compression and isinstance(value, UUID):
            return value.bytes
        return value and str(value)
    
    def to_python_value(self, value: Any) -> Optional[Union[UUID, bytes]]:
        if value is None or isinstance(value, UUID):
            # Convert to UUID if binary_compression is True
            # and value is bytes Type
            if self._binary_compression and isinstance(value, bytes):
                return UUID(bytes=bytes(value))
            return value
        return UUID(value)