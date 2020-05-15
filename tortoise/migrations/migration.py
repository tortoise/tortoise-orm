from typing import List

from tortoise.migrations.operations import Operation


class Migration:
    operations: List[Operation] = []

    def __init__(self, name: str):
        self.name = name

    async def run_operations(self):
        for operation in self.operations:
            await operation.run()
