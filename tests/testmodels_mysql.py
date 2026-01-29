from tortoise import fields
from tortoise.contrib.mysql import fields as mysql_fields
from tortoise.models import Model


class UUIDPkModel(Model):
    id = mysql_fields.UUIDField(primary_key=True)

    children: fields.ReverseRelation["UUIDFkRelatedModel"]
    children_null: fields.ReverseRelation["UUIDFkRelatedNullModel"]
    peers: fields.ManyToManyRelation["UUIDM2MRelatedModel"]


class UUIDFkRelatedModel(Model):
    id = mysql_fields.UUIDField(primary_key=True)
    name = fields.CharField(max_length=50, null=True)
    model: fields.ForeignKeyRelation[UUIDPkModel] = fields.ForeignKeyField(
        "models.UUIDPkModel", related_name="children"
    )


class UUIDFkRelatedNullModel(Model):
    id = mysql_fields.UUIDField(primary_key=True)
    name = fields.CharField(max_length=50, null=True)
    model: fields.ForeignKeyNullableRelation[UUIDPkModel] = fields.ForeignKeyField(
        "models.UUIDPkModel", related_name=False, null=True
    )
    parent: fields.OneToOneNullableRelation[UUIDPkModel] = fields.OneToOneField(
        "models.UUIDPkModel", related_name=False, null=True, on_delete=fields.NO_ACTION
    )


class UUIDM2MRelatedModel(Model):
    id = mysql_fields.UUIDField(primary_key=True)
    value = fields.TextField(default="test")
    models: fields.ManyToManyRelation[UUIDPkModel] = fields.ManyToManyField(
        "models.UUIDPkModel", related_name="peers"
    )


class UUIDPkSourceModel(Model):
    id = mysql_fields.UUIDField(primary_key=True, source_field="a")

    class Meta:
        table = "upsm"


class UUIDFkRelatedSourceModel(Model):
    id = mysql_fields.UUIDField(primary_key=True, source_field="b")
    name = fields.CharField(max_length=50, null=True, source_field="c")
    model: fields.ForeignKeyRelation[UUIDPkSourceModel] = fields.ForeignKeyField(
        "models.UUIDPkSourceModel", related_name="children", source_field="d"
    )

    class Meta:
        table = "ufrsm"


class UUIDFkRelatedNullSourceModel(Model):
    id = mysql_fields.UUIDField(primary_key=True, source_field="i")
    name = fields.CharField(max_length=50, null=True, source_field="j")
    model: fields.ForeignKeyNullableRelation[UUIDPkSourceModel] = fields.ForeignKeyField(
        "models.UUIDPkSourceModel", related_name="children_null", source_field="k", null=True
    )

    class Meta:
        table = "ufrnsm"


class UUIDM2MRelatedSourceModel(Model):
    id = mysql_fields.UUIDField(primary_key=True, source_field="e")
    value = fields.TextField(default="test", source_field="f")
    models: fields.ManyToManyRelation[UUIDPkSourceModel] = fields.ManyToManyField(
        "models.UUIDPkSourceModel", related_name="peers", forward_key="e", backward_key="h"
    )

    class Meta:
        table = "umrsm"
