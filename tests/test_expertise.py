import csv

import pytest

from algorithms import data_manager, expertise


@pytest.fixture
def ds(tmp_path, monkeypatch):
    """A tiny, isolated dataset for expertise tests."""
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    tables = [
        ("faculty.csv", data_manager.FACULTY_COLUMNS, [
            {"faculty_id": "f1", "name": "Alice", "expertise": "AI; IoT"},
            {"faculty_id": "f2", "name": "Bob", "expertise": "Networks; AI"},
            {"faculty_id": "f3", "name": "Cara", "expertise": "Robotics"},
            {"faculty_id": "f4", "name": "Empty", "expertise": ""},
        ]),
        ("papers.csv", data_manager.PAPER_COLUMNS, [
            {"paper_id": "p1", "title": "Paper One", "keywords": "Cybersecurity; IoT"},
            {"paper_id": "p2", "title": "Paper Two", "keywords": "AI; Vision"},
        ]),
        ("authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [
            {"paper_id": "p1", "faculty_id": "f1", "author_order": "1"},
            {"paper_id": "p2", "faculty_id": "f2", "author_order": "1"},
        ]),
    ]
    for filename, columns, rows in tables:
        with (tmp_path / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    return data_manager.Dataset()


def test_jaccard_percent_normal_and_empty_sets():
    assert expertise.jaccard_percent({"ai", "iot"}, {"ai", "networks"}) == pytest.approx(33.333333)
    assert expertise.jaccard_percent(set(), set()) == 0.0
    assert expertise.jaccard_percent({"ai"}, {"ai"}) == 100.0


def test_parse_query_normalizes_and_removes_duplicates():
    assert expertise.parse_query("AI, IoT; robotics; ai") == {"ai", "iot", "robotics"}
    assert expertise.parse_query("") == set()


def test_build_profiles_combines_listed_and_paper_keywords(ds):
    profiles = expertise.build_profiles(ds)
    by_id = {item["faculty"]["faculty_id"]: item["keywords"] for item in profiles}
    assert by_id["f1"] == {"ai", "iot", "cybersecurity"}
    assert by_id["f2"] == {"ai", "networks", "vision"}
    assert by_id["f4"] == set()


def test_find_matches_returns_only_overlaps_sorted_by_score_then_name(ds):
    profiles = expertise.build_profiles(ds)
    results = expertise.find_matches({"ai", "iot"}, profiles, ds.keyword_labels)
    assert [row["faculty"]["faculty_id"] for row in results] == ["f1", "f2"]
    assert results[0]["matching"] == ["AI", "IoT"]
    assert results[0]["score"] == 66.7
    assert results[1]["score"] == 25.0


def test_find_matches_empty_query_returns_no_results(ds):
    assert expertise.find_matches(set(), expertise.build_profiles(ds), ds.keyword_labels) == []
