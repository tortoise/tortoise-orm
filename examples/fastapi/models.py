from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator


class Users(models.Model):
    """
    The User model
    """

    id = fields.IntField(pk=True)
    #: This is a username
    username = fields.CharField(max_length=20)
    name = fields.CharField(max_length=30, null=True)
    family_name = fields.CharField(max_length=30, default="foo")
    password_hash = fields.CharField(max_length=128, null=True)

    def full_name(self) -> str:
        """
        Returns the best name
        """
        if self.name or self.family_name:
            return f"{self.name} {self.family_name}".strip()
        return self.username

    def set_password(self, password: str, repeat_password: str) -> bool:
        """
        Sets the password_hash

        """

    class PydanticMeta:
        computed = ["full_name"]
        exclude = ["password_hash"]


User_Pydantic = pydantic_model_creator(Users, name="User")
UserIn_Pydantic = pydantic_model_creator(Users, name="UserIn", exclude_readonly=True)
