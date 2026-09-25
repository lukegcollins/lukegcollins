"""ORCID parsing, Crossref enrichment, GitHub aggregation and the private-name leak check."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from conftest import assert_golden, fake_fetch, fake_post, fixture
from spectral import assets, data, github_stats, orcid, readme
from svgkit import leaks


def test_orcid_picks_the_preferred_record_and_normalises_dois() -> None:
    works = [w for _, w in orcid.parse_works(fixture("orcid_works.json"))]
    titles = [w.title for w in works]
    assert "Example paper A" in titles
    assert "Example paper A: an older duplicate record" not in titles
    paper_a = next(w for w in works if w.title == "Example paper A")
    assert paper_a.doi == "10.1234/example.1"
    assert paper_a.venue == "Example Journal of Forensics"


def test_orcid_code_links_only_for_code_hosts() -> None:
    works = {w.title: w for _, w in orcid.parse_works(fixture("orcid_works.json"))}
    assert works["Example paper B"].code == "https://github.com/example/example-b"
    assert works["Example paper B"].url == ""
    preprint = works["Example paper C: costs under $5 and *starred* terms"]
    assert preprint.code == ""
    assert preprint.url == "https://arxiv.org/abs/2501.00001"


def test_publications_are_enriched_sorted_and_rendered() -> None:
    pubs = orcid.fetch_publications(fetch=fake_fetch)
    assert [w.year for w in pubs.works] == ["2025", "2025", "2024"]
    paper_b = next(w for w in pubs.works if w.title == "Example paper B")
    assert paper_b.venue == "Proceedings of the Example Conference on Media Forensics"
    assert_golden("publications.json", data.dump_publications(pubs))
    block = readme.publications_block(pubs)
    assert r"\$5" in block and r"\*starred\*" in block
    assert_golden("publications-block.md", block + "\n")


def test_publications_round_trip_through_json(tmp_path: Path) -> None:
    pubs = orcid.fetch_publications(fetch=fake_fetch)
    path = tmp_path / "publications.json"
    path.write_text(data.dump_publications(pubs), encoding="utf-8")
    assert data.load_publications(path) == pubs


def test_stats_are_aggregates_with_notebooks_left_out() -> None:
    collected = github_stats.collect("t", org_token="o", org="example-org", post=fake_post)
    stats = collected.stats
    assert stats.total == 40
    assert stats.as_of == "2025-10-11"
    languages = dict(stats.languages)
    assert "Jupyter Notebook" not in languages
    assert languages["Python"] == 5000 + 1200 + 7000
    assert languages["TypeScript"] == 6000 + 2500
    assert stats.language_scope == "owned + org repos · private included"
    assert_golden("stats.json", data.dump_stats(stats))


def test_languages_claim_private_work_only_when_a_private_repo_counted() -> None:
    repos = [
        {
            "name": "open-tool",
            "isPrivate": False,
            "languages": {"edges": [{"size": 10, "node": {"name": "Python"}}]},
        },
        # A private repository that adds no bytes adds no claim either.
        {"name": "empty-private", "isPrivate": True, "languages": {"edges": []}},
    ]
    calendar = fixture("graphql_calendar.json")
    stats = github_stats.aggregate(calendar, repos, scope="owned repos").stats
    assert stats.language_scope == "owned repos"
    assert not stats.languages_include_private
    assert "private ones included" not in readme.activity_block(stats)


def test_private_names_are_collected_but_never_written() -> None:
    collected = github_stats.collect("t", org_token="o", org="example-org", post=fake_post)
    assert collected.forbidden == {
        "secret-thesis-draft",
        "example-user/secret-thesis-draft",
        "hiddenmethodnet",
        "example-user/hiddenmethodnet",
        "client-acmeco-website",
        "example-org/client-acmeco-website",
    }
    built, _ = assets.build_all(collected.stats, orcid.fetch_publications(fetch=fake_fetch))
    outputs = {str(p.relative_to(assets.ROOT)): c for p, c in built.items()}
    outputs["data/stats.json"] = data.dump_stats(collected.stats)
    assert leaks.find_leaks(outputs, collected.forbidden) == []
    everything = json.dumps(outputs)
    for name in collected.forbidden:
        assert name not in everything


def test_leak_check_catches_a_visible_name() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"><style>@font-face{src:url(data:x;base64,'
        "hiddenmethodnet)}</style><title>ok</title><text>by hiddenmethodnet</text></svg>"
    )
    found = leaks.find_leaks(
        {"a.svg": svg, "README.md": "see secret-thesis-draft"},
        {"hiddenmethodnet", "secret-thesis-draft"},
    )
    assert found == [
        "README.md: private name 'secret-thesis-draft' is visible",
        "a.svg: private name 'hiddenmethodnet' is visible",
    ]


def test_leak_check_matches_whole_names_only() -> None:
    outputs = {"README.md": "Deepfake detection, abcd, see github.com/x/abc.io"}
    assert leaks.find_leaks(outputs, {"deepfake-detection", "abc"}) == []
    assert leaks.find_leaks({"README.md": "the abc repo"}, {"abc"}) != []
    assert leaks.find_leaks({"README.md": "the abc repo"}, {"abc"}, allowed={"ABC"}) == []


def test_graphql_errors_surface() -> None:
    def broken(token: str, query: str, variables: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"viewer": {"repositories": None}}

    with pytest.raises((github_stats.GraphQLError, KeyError, TypeError)):
        github_stats.collect("t", post=broken)


def test_private_work_is_only_claimed_when_github_counted_it() -> None:
    collected = github_stats.collect("t", post=fake_post)
    assert collected.stats.private_counted == 12
    assert collected.stats.contribution_label == "contributions, private work included"
    public_only = data.Stats(total=5, days=(("2026-01-01", 5),))
    assert public_only.contribution_label == "public contributions"
    assert "private" not in readme.activity_block(public_only).split("\n\n")[-1].split(".")[0]
