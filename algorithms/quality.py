"""
quality.py
----------
Data-quality checks for ResearchConnect's three source CSV files.

The Dataset object retains normalized source rows so these checks can detect
records that the cleaned application data intentionally skips.
"""
import re
from collections import Counter


_DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
_DOI_URL_PREFIX = re.compile(r"^https?://(?:dx\.)?doi\.org/", re.IGNORECASE)


def _duplicate_values(rows, field):
    """Return duplicate non-empty identifiers, preserving first-seen order."""
    counts = Counter(
        str(row.get(field, "")).strip()
        for row in rows
        if str(row.get(field, "")).strip()
    )
    return [
        {"id": identifier, "count": count}
        for identifier, count in counts.items()
        if count > 1
    ]


def _normalise_doi(value):
    """Remove a DOI URL prefix or doi: label before validating the identifier."""
    doi = str(value or "").strip()
    if not doi:
        return ""
    doi = _DOI_URL_PREFIX.sub("", doi)
    if doi.lower().startswith("doi:"):
        doi = doi[4:].strip()
    return doi


def quality_report(ds):
    """
    Return a dictionary of data-quality issue lists.

    Blank DOI values are not marked malformed because a publication may
    legitimately have no DOI recorded. Blank IDs are ignored for duplicate
    checks; missing-link problems are reported through orphan authorship rows.
    """
    faculty_rows = ds.raw_faculty.to_dict("records")
    paper_rows = ds.raw_papers.to_dict("records")
    authorship_rows = ds.raw_authorship.to_dict("records")

    faculty_ids = {
        str(row.get("faculty_id", "")).strip()
        for row in faculty_rows
        if str(row.get("faculty_id", "")).strip()
    }
    paper_ids = {
        str(row.get("paper_id", "")).strip()
        for row in paper_rows
        if str(row.get("paper_id", "")).strip()
    }

    orphan_authorship_rows = []
    for row_number, row in enumerate(authorship_rows, start=2):
        paper_id = str(row.get("paper_id", "")).strip()
        faculty_id = str(row.get("faculty_id", "")).strip()
        missing = []
        if not paper_id or paper_id not in paper_ids:
            missing.append("paper_id")
        if not faculty_id or faculty_id not in faculty_ids:
            missing.append("faculty_id")
        if missing:
            orphan_authorship_rows.append({
                "row": row_number,
                "paper_id": paper_id,
                "faculty_id": faculty_id,
                "missing": missing,
            })

    malformed_dois = []
    for row in paper_rows:
        raw_doi = str(row.get("doi", "")).strip()
        if not raw_doi:
            continue
        normalized = _normalise_doi(raw_doi)
        if not _DOI_PATTERN.fullmatch(normalized):
            malformed_dois.append({
                "paper_id": str(row.get("paper_id", "")).strip(),
                "title": str(row.get("title", "")).strip() or "Title not listed",
                "doi": raw_doi,
            })

    authored_paper_ids = {
        str(row.get("paper_id", "")).strip()
        for row in authorship_rows
        if str(row.get("paper_id", "")).strip()
        and str(row.get("paper_id", "")).strip() in paper_ids
        and str(row.get("faculty_id", "")).strip() in faculty_ids
    }
    papers_without_authors = [
        {
            "paper_id": str(row.get("paper_id", "")).strip(),
            "title": str(row.get("title", "")).strip() or "Title not listed",
        }
        for row in paper_rows
        if str(row.get("paper_id", "")).strip()
        and str(row.get("paper_id", "")).strip() not in authored_paper_ids
    ]

    return {
        "duplicate_faculty_ids": _duplicate_values(faculty_rows, "faculty_id"),
        "duplicate_paper_ids": _duplicate_values(paper_rows, "paper_id"),
        "orphan_authorship_rows": orphan_authorship_rows,
        "malformed_dois": malformed_dois,
        "papers_without_authors": papers_without_authors,
    }
