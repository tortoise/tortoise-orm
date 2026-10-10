from tortoise import Model, fields


class TextIndex(Model):
    unique_text = fields.TextField(unique=True)
    indexed_text = fields.TextField(db_index=True)
