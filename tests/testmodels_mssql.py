from tortoise import Model, fields
from tortoise.contrib.mssql.fields import NVARCHAR

class NVARCHARFields(Model):
    id = fields.IntField(pk=True)
    nvarchar = NVARCHAR(max_length=255)
    nvarchar_null = NVARCHAR(max_length=255,null=True)