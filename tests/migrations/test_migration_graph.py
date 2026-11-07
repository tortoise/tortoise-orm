"""Tests for app-scoped `MigrationGraph.leaf_nodes()` / `root_nodes()`."""

from __future__ import annotations

from tortoise.migrations.graph import MigrationGraph, MigrationKey
from tortoise.migrations.migration import Migration


def _build_cross_app_graph() -> MigrationGraph:
    graph = MigrationGraph()
    a1 = MigrationKey("a", "0001_initial")
    a2 = MigrationKey("a", "0002_second")
    b1 = MigrationKey("b", "0001_initial")
    for key in (a1, a2, b1):
        graph.add_node(key, Migration(key.name, key.app_label))
    graph.add_dependency(a2, a2, a1)  # a.0002 depends on a.0001
    graph.add_dependency(b1, b1, a2)  # b.0001 depends on a.0002 (cross-app edge)
    return graph


def test_leaf_and_root_nodes_ignore_cross_app_edges() -> None:
    graph = _build_cross_app_graph()
    # a.0002 is depended on by b.0001, but that edge is not an `a` migration, so `a` still
    # has a leaf; the same holds for the root of `b`.
    assert graph.leaf_nodes("a") == [MigrationKey("a", "0002_second")]
    assert graph.root_nodes("b") == [MigrationKey("b", "0001_initial")]


def test_leaf_and_root_nodes_without_app_label_keep_any_app_edges() -> None:
    graph = _build_cross_app_graph()
    # The global call still counts edges from every app.
    assert graph.leaf_nodes() == [MigrationKey("b", "0001_initial")]
    assert graph.root_nodes() == [MigrationKey("a", "0001_initial")]
