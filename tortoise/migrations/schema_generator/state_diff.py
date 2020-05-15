from typing import Dict, Callable, List, TYPE_CHECKING

from tortoise.migrations.operations import TortoiseOperation

if TYPE_CHECKING:
    from tortoise.migrations.schema_generator.state import FieldState, ModelState


class StateModelDiff:
    def __init__(self, old_state: "ModelState", new_state: "ModelState"):
        self.old_state = old_state
        self.new_state = new_state
        self.change_handler_map = self.generate_change_handler_map()

    def generate_change_handler_map(self) -> Dict[tuple, Callable]:
        return {
            ("name",): self.handle_change_name,
        }

    def handle_change_name(self) -> List[TortoiseOperation]:
        pass

    def generate_operations(self) -> List[TortoiseOperation]:
        if self.old_state == self.new_state:
            return []

        if self.old_state.name != self.new_state.name:
            pass


class StateFieldDiff:
    def __init__(self, old_state: "FieldState", new_state: "FieldState"):
        self.old_state = old_state
        self.new_state = new_state

    async def generate_operations(self,) -> List[TortoiseOperation]:
        pass