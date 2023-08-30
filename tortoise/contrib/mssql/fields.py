from tortoise.fields.data import CharField
from tortoise.contrib.mssql.field_types import NVARCHAR


class NVARCHAR(CharField):

    field_type = NVARCHAR
    
    @property
    def SQL_TYPE(self) -> str:
        return f"NVARCHAR({self.field.max_length})"