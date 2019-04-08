from tortoise import Model, fields


class Users(Model):
    id = fields.IntField(pk=True)
    status = fields.CharField(20)

    def __str__(self):
        return "User {}: {}".format(self.id, self.status)


class Workers(Model):
    id = fields.IntField(pk=True)
    status = fields.CharField(20)

    def __str__(self):
        return "Worker {}: {}".format(self.id, self.status)
