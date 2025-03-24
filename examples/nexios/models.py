from tortoise import fields
from tortoise.models import Model

class Task(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    description = fields.TextField(null=True, blank=True)
    def __str__(self):
        return self.title