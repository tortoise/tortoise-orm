from tortoise import fields, models


class Users(models.Model):
    id = fields.IntField(primary_key=True)
    username = fields.CharField(max_length=20)

    def __str__(self) -> str:
        return f"User {self.id}: {self.username}"
