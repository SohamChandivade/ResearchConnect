import csv

import pytest

from algorithms import data_manager, quality


def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def quality_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    write_csv(tmp_path / "faculty.csv", data_manager.FACULTY_COLUMNS, [
        {"faculty_id": "f1", "name": "Alice"},
        {"faculty_id": "f1", "name": "Alice Duplicate"},
        {"faculty_id": "f2", "name": "Bob"},
    ])
    write_csv(tmp_path / "papers.csv", data_manager.PAPER_COLUMNS, [
        {"paper_id": "p1", "title": "Valid DOI", "doi": "10.1234/example"},
        {"paper_id": "p2", "title": "Bad DOI", "doi": "not-a-doi"},
        {"paper_id": "p3", "title": "No author", "doi": ""},
        {"paper_id": "p3", "title": "Duplicate paper ID", "doi": "https://doi.org/10.1000/test"},
    ])
    write_csv(tmp_path / "authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [
        {"paper_id": "p1", "faculty_id": "f1", "author_order": "1"},
        {"paper_id": "missing-paper", "faculty_id": "f1", "author_order": "1"},
        {"paper_id": "p2", "faculty_id": "missing-faculty", "author_order": "1"},
    ])
    return data_manager.Dataset()


def test_quality_report_detects_duplicate_faculty_and_paper_ids(quality_dataset):
    report = quality.quality_report(quality_dataset)
    assert report["duplicate_faculty_ids"] == [{"id": "f1", "count": 2}]
    assert report["duplicate_paper_ids"] == [{"id": "p3", "count": 2}]


def test_quality_report_detects_orphan_authorship_rows(quality_dataset):
    report = quality.quality_report(quality_dataset)
    assert len(report["orphan_authorship_rows"]) == 2
    assert report["orphan_authorship_rows"][0]["missing"] == ["paper_id"]
    assert report["orphan_authorship_rows"][1]["missing"] == ["faculty_id"]


def test_quality_report_detects_malformed_dois_but_allows_blank_and_url_doi(quality_dataset):
    report = quality.quality_report(quality_dataset)
    assert len(report["malformed_dois"]) == 1
    assert report["malformed_dois"][0]["doi"] == "not-a-doi"


def test_quality_report_detects_papers_without_valid_linked_authors(quality_dataset):
    report = quality.quality_report(quality_dataset)
    ids = [item["paper_id"] for item in report["papers_without_authors"]]
    assert ids == ["p2", "p3", "p3"]


def test_quality_report_returns_empty_lists_for_clean_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    write_csv(tmp_path / "faculty.csv", data_manager.FACULTY_COLUMNS, [
        {"faculty_id": "f1", "name": "Alice"},
    ])
    write_csv(tmp_path / "papers.csv", data_manager.PAPER_COLUMNS, [
        {"paper_id": "p1", "title": "Valid", "doi": "10.1234/example"},
    ])
    write_csv(tmp_path / "authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [
        {"paper_id": "p1", "faculty_id": "f1", "author_order": "1"},
    ])
    report = quality.quality_report(data_manager.Dataset())
    assert all(items == [] for items in report.values())
