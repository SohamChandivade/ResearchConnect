import csv

import pytest

from algorithms import data_manager
import app as app_module


def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def paper_data(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    write_csv(tmp_path / "faculty.csv", data_manager.FACULTY_COLUMNS, [
        {"faculty_id": "f1", "name": "Alice", "department": "IT"},
    ])
    write_csv(tmp_path / "papers.csv", data_manager.PAPER_COLUMNS, [
        {
            "paper_id": "p1",
            "title": "Graph Research",
            "year": "2025",
            "venue": "Test Journal",
            "doi": "10.1234/graph",
            "keywords": "graphs; networks",
            "source_url": "https://example.com/paper",
            "data_status": "verified",
        },
    ])
    write_csv(tmp_path / "authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [
        {"paper_id": "p1", "faculty_id": "f1", "author_order": "1"},
    ])
    return data_manager.Dataset()


def test_get_paper_returns_paper_with_linked_authors(paper_data):
    paper = paper_data.get_paper("p1")
    assert paper["title"] == "Graph Research"
    assert paper["year_num"] == 2025
    assert [author["name"] for author in paper["authors"]] == ["Alice"]


def test_get_paper_returns_none_for_unknown_id(paper_data):
    assert paper_data.get_paper("unknown") is None


def test_get_paper_strips_surrounding_whitespace(paper_data):
    assert paper_data.get_paper(" p1 ")["paper_id"] == "p1"


def test_publication_detail_route_renders_paper(paper_data, monkeypatch):
    monkeypatch.setattr(app_module, "Dataset", lambda: paper_data)
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()

    response = client.get("/publications/p1")
    assert response.status_code == 200
    assert b"Graph Research" in response.data
    assert b"Alice" in response.data


def test_publication_detail_route_returns_404_for_unknown_id(paper_data, monkeypatch):
    monkeypatch.setattr(app_module, "Dataset", lambda: paper_data)
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()

    response = client.get("/publications/not-a-real-paper")
    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_publications_table_contains_internal_paper_detail_links(paper_data, monkeypatch):
    monkeypatch.setattr(app_module, "Dataset", lambda: paper_data)
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()

    response = client.get("/publications")
    assert response.status_code == 200
    assert b'/publications/p1' in response.data
