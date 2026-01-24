from __future__ import annotations

from dataclasses import dataclass
from functools import total_ordering
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tortoise.migrations.migration import Migration


@dataclass(frozen=True, order=True)
class MigrationKey:
    app_label: str
    name: str

    def __str__(self) -> str:
        return f"{self.app_label}.{self.name}"


@total_ordering
class Node:
    def __init__(self, key: MigrationKey):
        self.key = key
        self.children: set[Node] = set()
        self.parents: set[Node] = set()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Node):
            return self.key == other.key
        return self.key == other

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Node):
            return self.key < other.key
        return self.key < other  # type: ignore[operator]

    def __hash__(self) -> int:
        return hash(self.key)

    def __getitem__(self, item: int) -> str:
        return (self.key.app_label, self.key.name)[item]

    def __str__(self) -> str:
        return str(self.key)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: ({self.key.app_label!r}, {self.key.name!r})>"

    def add_child(self, child: Node) -> None:
        self.children.add(child)

    def add_parent(self, parent: Node) -> None:
        self.parents.add(parent)


class DummyNode(Node):
    def __init__(self, key: MigrationKey, origin: MigrationKey, error_message: str):
        super().__init__(key)
        self.origin = origin
        self.error_message = error_message

    def raise_error(self) -> None:
        raise ValueError(self.error_message)


class MigrationGraph:
    def __init__(self) -> None:
        self.node_map: dict[MigrationKey, Node] = {}
        self.nodes: dict[MigrationKey, Migration | None] = {}

    def add_node(self, key: MigrationKey, migration: Migration) -> None:
        if key in self.node_map:
            raise ValueError(f"Duplicate migration node {key}")
        node = Node(key)
        self.node_map[key] = node
        self.nodes[key] = migration

    def add_dummy_node(self, key: MigrationKey, origin: MigrationKey, error_message: str) -> None:
        node = DummyNode(key, origin, error_message)
        self.node_map[key] = node
        self.nodes[key] = None

    def add_dependency(
        self,
        migration: MigrationKey,
        child: MigrationKey,
        parent: MigrationKey,
        *,
        skip_validation: bool = False,
    ) -> None:
        if child not in self.nodes:
            self.add_dummy_node(
                child,
                migration,
                f"Migration {migration} references nonexistent child {child}",
            )
        if parent not in self.nodes:
            self.add_dummy_node(
                parent,
                migration,
                f"Migration {migration} references nonexistent parent {parent}",
            )
        self.node_map[child].add_parent(self.node_map[parent])
        self.node_map[parent].add_child(self.node_map[child])
        if not skip_validation:
            self.validate_consistency()

    def validate_consistency(self) -> None:
        for node in self.node_map.values():
            if isinstance(node, DummyNode):
                node.raise_error()

    def root_nodes(self, app_label: str | None = None) -> list[MigrationKey]:
        nodes = [
            node.key
            for node in self.node_map.values()
            if not node.parents and (app_label is None or node.key.app_label == app_label)
        ]
        return sorted(nodes)

    def leaf_nodes(self, app_label: str | None = None) -> list[MigrationKey]:
        nodes = [
            node.key
            for node in self.node_map.values()
            if not node.children and (app_label is None or node.key.app_label == app_label)
        ]
        return sorted(nodes)

    def forwards_plan(self, target: MigrationKey) -> list[MigrationKey]:
        if target not in self.nodes:
            raise ValueError(f"Unknown migration target {target}")
        return self._iterative_dfs(self.node_map[target], forwards=True)

    def backwards_plan(self, target: MigrationKey) -> list[MigrationKey]:
        if target not in self.nodes:
            raise ValueError(f"Unknown migration target {target}")
        return self._iterative_dfs(self.node_map[target], forwards=False)

    def _iterative_dfs(self, start: Node, *, forwards: bool) -> list[MigrationKey]:
        visited: list[MigrationKey] = []
        visited_set: set[Node] = set()
        stack: list[tuple[Node, bool]] = [(start, False)]
        while stack:
            node, processed = stack.pop()
            if node in visited_set:
                continue
            if processed:
                visited_set.add(node)
                visited.append(node.key)
                continue
            stack.append((node, True))
            neighbors = node.parents if forwards else node.children
            stack.extend((n, False) for n in sorted(neighbors))
        return visited
