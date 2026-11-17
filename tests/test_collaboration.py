import csv

import pytest

from algorithms import collaboration, data_manager


@pytest.fixture
def ds(tmp_path, monkeypatch):
    """A small dataset with one genuine co-authored paper and one solo paper."""
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    tables = [
        ("faculty.csv", data_manager.FACULTY_COLUMNS, [
            {"faculty_id": "f1", "name": "Alice", "department": "IT"},
            {"faculty_id": "f2", "name": "Bob", "department": "IT"},
            {"faculty_id": "f3", "name": "Cara", "department": "EXTC"},
        ]),
        ("papers.csv", data_manager.PAPER_COLUMNS, [
            {"paper_id": "p1", "title": "Shared Paper", "year": "2024"},
            {"paper_id": "p2", "title": "Second Shared Paper", "year": "2025"},
            {"paper_id": "p3", "title": "Solo Paper", "year": "2023"},
        ]),
        ("authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [
            {"paper_id": "p1", "faculty_id": "f1", "author_order": "1"},
            {"paper_id": "p1", "faculty_id": "f2", "author_order": "2"},
            {"paper_id": "p2", "faculty_id": "f1", "author_order": "1"},
            {"paper_id": "p2", "faculty_id": "f2", "author_order": "2"},
            {"paper_id": "p3", "faculty_id": "f3", "author_order": "1"},
        ]),
    ]
    for filename, columns, rows in tables:
        with (tmp_path / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    return data_manager.Dataset()


def test_build_graph_creates_all_faculty_nodes_and_verified_edges(ds):
    graph = collaboration.build_graph(ds)
    assert set(graph.nodes) == {"f1", "f2", "f3"}
    assert graph.number_of_edges() == 1
    assert graph["f1"]["f2"]["weight"] == 2
    assert graph["f1"]["f2"]["papers"] == ["p1", "p2"]
    assert not graph.has_edge("f1", "f3")


def test_network_stats_reports_collaboration_counts(ds):
    graph = collaboration.build_graph(ds)
    stats = collaboration.network_stats(graph, ds)
    assert stats["faculty"] == 3
    assert stats["links"] == 1
    assert stats["collaborating"] == 2
    assert stats["isolated"] == 1
    assert stats["multi_author_papers"] == 2
    assert stats["top_pairs"][0]["titles"] == ["Shared Paper", "Second Shared Paper"]


def test_collaborators_of_returns_weighted_collaborators(ds):
    graph = collaboration.build_graph(ds)
    found = collaboration.collaborators_of(graph, ds, "f1")
    assert [(faculty["faculty_id"], weight) for faculty, weight in found] == [("f2", 2)]
    assert collaboration.collaborators_of(graph, ds, "unknown") == []


def test_network_for_plot_contains_nodes_and_edges(ds):
    graph = collaboration.build_graph(ds)
    result = collaboration.network_for_plot(graph, ds)
    assert len(result["nodes"]) == 3
    assert len(result["edges"]) == 1
    alice = next(node for node in result["nodes"] if node["id"] == "f1")
    assert alice["degree"] == 1
    assert alice["collaborators"] == [{"name": "Bob", "shared": 2}]


def test_empty_graph_helpers_are_safe():
    import networkx as nx

    class EmptyDataset:
        faculty = []
        faculty_by_id = {}
        paper_authors = {}
        papers_by_id = {}

    graph = nx.Graph()
    stats = collaboration.network_stats(graph, EmptyDataset())
    assert stats["faculty"] == 0
    assert stats["links"] == 0
    assert stats["density"] == 0
    assert collaboration.network_for_plot(graph, EmptyDataset()) == {"nodes": [], "edges": []}
