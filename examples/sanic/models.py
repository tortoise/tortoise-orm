from tortoise import Model, fields


class Users(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(50)

    def __str__(self):
        return "User {}: {}".format(self.id, self.name)
