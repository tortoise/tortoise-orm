from __future__ import annotations

from typing import Callable, Dict, List, TYPE_CHECKING

from tortoise.migrations.operations import TortoiseOperation

if TYPE_CHECKING:
    from tortoise.migrations.schema_generator.state import ModelState


class StateModelDiff:
    def __init__(self, old_state: "ModelState", new_state: "ModelState") -> None:
        self.old_state = old_state
        self.new_state = new_state
        self.change_handler_map = self.generate_change_handler_map()

    def generate_change_handler_map(self) -> Dict[tuple, Callable]:
        return {
            ("name",): self.handle_change_name,
        }

    def handle_change_name(self) -> List[TortoiseOperation]:
        return []

    def generate_operations(self) -> List[TortoiseOperation]:
        if self.old_state == self.new_state:
            return []

        if self.old_state.name != self.new_state.name:
            return self.handle_change_name()

        return []


class StateFieldDiff:
    def __init__(self, old_state, new_state) -> None:
        self.old_state = old_state
        self.new_state = new_state

    async def generate_operations(self) -> List[TortoiseOperation]:
        return []
