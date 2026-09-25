"""Shared helpers: fixture loading and golden-file comparison.

Regenerate goldens after an intentional change with ``UPDATE_GOLDEN=1 uv run pytest``.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
GOLDEN = ROOT / "tests" / "golden"


def fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def assert_golden(name: str, actual: str) -> None:
    path = GOLDEN / name
    if os.environ.get("UPDATE_GOLDEN") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8", newline="\n")
    assert path.exists(), f"missing golden {name}; run with UPDATE_GOLDEN=1"
    assert actual == path.read_text(encoding="utf-8"), f"{name} differs from its golden file"


def fake_fetch(url: str, headers: Mapping[str, str]) -> Any:
    """Stand-in for the ORCID and Crossref HTTP calls."""
    if url.startswith("https://pub.orcid.org/"):
        return fixture("orcid_works.json")
    if "10.1234/example.2" in url:
        return fixture("crossref_example_2.json")
    return {"message": {}}


def fake_post(token: str, query: str, variables: Mapping[str, Any]) -> Mapping[str, Any]:
    """Stand-in for GitHub GraphQL, including a second page of owned repositories."""
    if "contributionCalendar" in query:
        data: Mapping[str, Any] = fixture("graphql_calendar.json")
        return data
    if "organization(" in query:
        org: Mapping[str, Any] = fixture("graphql_org_1.json")
        return org
    page = "graphql_owned_2.json" if variables.get("cursor") == "c1" else "graphql_owned_1.json"
    owned: Mapping[str, Any] = fixture(page)
    return owned
