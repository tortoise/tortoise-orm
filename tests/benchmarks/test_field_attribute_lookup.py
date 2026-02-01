from tortoise.fields import Field


class MyField(Field):
    @property
    def MY_PROPERTY(self):
        return f"hi from {self.__class__.__name__}!"

    OTHER_PROPERTY = "something else"

    class _db_property:
        def __init__(self, field: "Field"):
            self.field = field

        @property
        def MY_PROPERTY(self):
            return f"hi from {self.__class__.__name__} of {self.field.__class__.__name__}!"

    class _db_cls_attribute:
        MY_PROPERTY = "cls_attribute"


def test_field_attribute_lookup_get_for_dialect(benchmark):
    field = MyField()

    @benchmark
    def bench():
        field.get_for_dialect("property", "MY_PROPERTY")
        field.get_for_dialect("postgres", "MY_PROPERTY")
        field.get_for_dialect("cls_attribute", "MY_PROPERTY")
        field.get_for_dialect("property", "OTHER_PROPERTY")
        field.get_for_dialect("property", "MY_PROPERTY")
