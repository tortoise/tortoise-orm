from tortoise.fields import Field


def is_read_only(field: Field) -> bool:
    return (
        field.pk
        or getattr(field, "auto_now", False)
        or getattr(field, "auto_now_add", False)
    )
