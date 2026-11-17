import csv

import pandas as pd
import pytest

from algorithms import data_manager


def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_clean_year_accepts_valid_integer_and_decimal_strings():
    assert data_manager.clean_year("2024") == 2024
    assert data_manager.clean_year("2024.0") == 2024
    assert data_manager.clean_year("1899") is None
    assert data_manager.clean_year("2101") is None
    assert data_manager.clean_year("unknown") is None
    assert data_manager.clean_year("") is None


def test_clean_int_uses_default_for_invalid_values():
    assert data_manager.clean_int("2") == 2
    assert data_manager.clean_int("2.0") == 2
    assert data_manager.clean_int("bad") == 9999
    assert data_manager.clean_int("bad", default=-1) == -1


@pytest.mark.parametrize("text,expected", [
    ("AI; IoT; Robotics", ["AI", "IoT", "Robotics"]),
    ("AI; ai;  IoT  ", ["AI", "IoT"]),
    ("Deep Learning, Computer Vision", ["Deep Learning", "Computer Vision"]),
    ("", []),
    (None, []),
])
def test_split_keywords(text, expected):
    assert data_manager.split_keywords(text) == expected


def test_split_keywords_can_parse_comma_separated_query():
    assert data_manager.split_keywords("AI, IoT; Robotics", semicolon_first=False) == ["AI", "IoT", "Robotics"]


def test_safe_url_only_allows_http_and_https():
    assert data_manager.safe_url(" https://example.com ") == "https://example.com"
    assert data_manager.safe_url("http://example.com") == "http://example.com"
    assert data_manager.safe_url("javascript:alert(1)") == ""
    assert data_manager.safe_url("") == ""


def test_doi_to_url_handles_blank_url_and_existing_url():
    assert data_manager.doi_to_url("") == ""
    assert data_manager.doi_to_url("10.1234/example") == "https://doi.org/10.1234/example"
    assert data_manager.doi_to_url("https://doi.org/10.1234/example") == "https://doi.org/10.1234/example"


def test_read_csv_safe_returns_expected_columns_and_stripped_values(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    write_csv(tmp_path / "faculty.csv", ["faculty_id", "name"], [
        {"faculty_id": " f1 ", "name": " Alice "},
    ])
    result = data_manager.read_csv_safe("faculty.csv", data_manager.FACULTY_COLUMNS)
    assert list(result.columns) == data_manager.FACULTY_COLUMNS
    assert result.iloc[0]["faculty_id"] == "f1"
    assert result.iloc[0]["name"] == "Alice"
    assert result.iloc[0]["department"] == ""


def test_read_csv_safe_missing_file_returns_empty_table(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    result = data_manager.read_csv_safe("missing.csv", data_manager.PAPER_COLUMNS)
    assert isinstance(result, pd.DataFrame)
    assert result.empty
    assert list(result.columns) == data_manager.PAPER_COLUMNS


def test_dataset_links_papers_authors_and_keywords(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, "DATA_DIR", str(tmp_path))
    write_csv(tmp_path / "faculty.csv", data_manager.FACULTY_COLUMNS, [
        {"faculty_id": "f1", "name": "Alice", "expertise": "Networks"},
    ])
    write_csv(tmp_path / "papers.csv", data_manager.PAPER_COLUMNS, [
        {"paper_id": "p1", "title": "Research Paper", "year": "2024", "keywords": "AI; IoT"},
    ])
    write_csv(tmp_path / "authorship.csv", data_manager.AUTHORSHIP_COLUMNS, [
        {"paper_id": "p1", "faculty_id": "f1", "author_order": "1"},
    ])

    ds = data_manager.Dataset()
    assert ds.faculty_by_id["f1"]["paper_count"] == 1
    assert ds.papers_by_id["p1"]["authors"][0]["name"] == "Alice"
    assert ds.faculty_by_id["f1"]["paper_keywords"] == ["AI", "IoT"]
    assert ds.keyword_options() == [("ai", "AI"), ("iot", "IoT"), ("networks", "Networks")]
