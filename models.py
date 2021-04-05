from tortoise import Model
from tortoise.fields import DatetimeField, TextField


class Companies(Model):
    name = TextField()
    created_at = DatetimeField(auto_now=True, pk=True)

    class Meta:
        partition_by = ('range', 'created_at')





from tortoise import Tortoise, run_async

TORTOISE_ORM = {
    'connections': {
        'default': {
            'engine': 'tortoise.backends.asyncpg',
            'credentials': {
                'host': 'localhost',
                'port': 5432,
                'user': 'evstrat',
                'password': '1235',
                'database': 'test',
            }
        }
    },
    'apps': {
        'models': {
            'models': ['models', 'aerich.models'],
            'default_connection': 'default'
        }
    }
}


async def init():
    # Here we connect to a SQLite DB file.
    # also specify the app name of "models"
    # which contain models from "app.models"
    await Tortoise.init(
        config=TORTOISE_ORM
    )
    # Generate the schema
    await Tortoise.generate_schemas()


if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init())

