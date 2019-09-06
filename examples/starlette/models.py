from tortoise import fields, models


class Users(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=20)

    def __str__(self) -> str:
        return "User {}: {}".format(self.id, self.username)
