"""
This example demonstrates executing manual SQL queries
"""
from tortoise import Tortoise, fields, run_async
from tortoise.models import Model
from tortoise.transactions import in_transaction


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    timestamp = fields.DatetimeField(auto_now_add=True)


async def run():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    # Need to get a connection. Unless explicitly specified, the name should be 'default'
    conn = Tortoise.get_connection("default")

    # Now we can execute queries in the normal autocommit mode
    await conn.execute_query("INSERT INTO event (name) VALUES ('Foo')")

    # You can also you parameters, but you need to use the right param strings for each dialect
    await conn.execute_query("INSERT INTO event (name) VALUES (?)", ["Bar"])

    # To do a transaction you'd need to use the in_transaction context manager
    async with in_transaction("default") as tconn:
        await tconn.execute_query("INSERT INTO event (name) VALUES ('Moo')")
        # Unless an exception happens it should commit automatically

    # This transaction is rolled back
    async with in_transaction("default") as tconn:
        await tconn.execute_query("INSERT INTO event (name) VALUES ('Sheep')")
        # Rollback to fail transaction
        await tconn.rollback()

    # Consider using execute_query_dict to get return values as a dict
    val = await conn.execute_query_dict("SELECT * FROM event")
    print(val)
    # Note that the result doesn't contain the rolled-back "Sheep" entry.


if __name__ == "__main__":
    run_async(run())
