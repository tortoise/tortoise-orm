from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator


class Users(models.Model):
    """
    This contains users

    Starting off very basic.
    """

    id = fields.IntField(pk=True)
    #: This is a username
    username = fields.CharField(max_length=20)

    def pretty_name(self) -> str:
        """
        Returns a prettified name
        """
        return f"User {self.id}: {self.username}"


User_Pydantic = pydantic_model_creator(Users, name="User")
