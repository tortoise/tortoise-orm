from typing import Dict, List, Optional

from quart import Quart

from tortoise import Tortoise

STATUSES = ["New", "Old", "Gone"]
app = Quart(__name__)


def register_tortoise(
    app: Quart,
    config: Optional[dict] = None,
    config_file: Optional[str] = None,
    db_url: Optional[str] = None,
    modules: Optional[Dict[str, List[str]]] = None,
    generate_schemas: bool = False,
):
    @app.before_serving
    async def init_orm():
        await Tortoise.init(
            config=config, config_file=config_file, db_url=db_url, modules=modules
        )
        print(
            f"Tortoise-ORM started, {Tortoise._connections}, {Tortoise.apps}"
        )
        if generate_schemas:
            print("Tortoise-ORM generating schema")
            await Tortoise.generate_schemas()

    @app.after_serving
    async def close_orm():
        await Tortoise.close_connections()
        print("Tortoise-ORM shutdown")
