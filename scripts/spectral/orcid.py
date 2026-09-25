"""Publications from the ORCID public API, optionally enriched with venues from Crossref.

ORCID is the only source: it holds published or accepted work that Luke has chosen to list.
One ORCID call per run (the anonymous quota is per IP and runner IPs are shared), and at most
``CROSSREF_LIMIT`` Crossref look-ups, only for records that lack a venue.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any

from .data import Publication, Publications

ORCID_ID = "0009-0002-7771-1081"
ORCID_WORKS = f"https://pub.orcid.org/v3.0/{ORCID_ID}/works"
CONTACT = "luke.collins@research.deakin.edu.au"
USER_AGENT = (
    f"lukegcollins-profile/1.0 (+https://github.com/lukegcollins/lukegcollins; mailto:{CONTACT})"
)
CROSSREF_LIMIT = 20
CODE_HOSTS = ("github.com", "gitlab.com", "codeberg.org", "bitbucket.org", "huggingface.co")

Fetch = Callable[[str, Mapping[str, str]], Any]


def http_json(url: str, headers: Mapping[str, str]) -> Any:
    # Only ever called with the fixed https:// ORCID and Crossref URLs built in this module.
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})  # noqa: S310
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return json.load(response)


def _value(node: Any, *path: str) -> str:
    for key in path:
        if not isinstance(node, dict):
            return ""
        node = node.get(key)
    return str(node).strip() if isinstance(node, str | int) else ""


def _preferred(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    """ORCID's preferred version of a grouped work is the one with the highest display index."""

    def rank(summary: dict[str, Any]) -> int:
        try:
            return int(summary.get("display-index") or 0)
        except ValueError:
            return 0

    return max(summaries, key=rank)


def _doi(summary: dict[str, Any], group: dict[str, Any]) -> str:
    ids: list[dict[str, Any]] = []
    for source in (summary, group):
        ids.extend((source.get("external-ids") or {}).get("external-id") or [])
    dois = [i for i in ids if (i.get("external-id-type") or "").lower() == "doi"]
    dois.sort(key=lambda i: 0 if i.get("external-id-relationship") == "self" else 1)
    for item in dois:
        value = _value(item, "external-id-normalized", "value") or _value(item, "external-id-value")
        value = value.removeprefix("https://doi.org/").removeprefix("http://dx.doi.org/")
        if value.startswith("10."):
            return value.lower()
    return ""


def _int(text: str) -> int:
    return int(text) if text.isdigit() else 0


def _is_code(url: str) -> bool:
    host = urllib.parse.urlsplit(url).netloc.lower().removeprefix("www.")
    return host in CODE_HOSTS


def parse_works(payload: Mapping[str, Any]) -> list[tuple[tuple[int, int, int], Publication]]:
    """Turn an ORCID /works response into (date key, publication) pairs."""
    out: list[tuple[tuple[int, int, int], Publication]] = []
    for group in payload.get("group") or []:
        summaries = group.get("work-summary") or []
        if not summaries:
            continue
        summary = _preferred(summaries)
        title = _value(summary, "title", "title", "value")
        if not title:
            continue
        year = _value(summary, "publication-date", "year", "value")
        month = _value(summary, "publication-date", "month", "value")
        day = _value(summary, "publication-date", "day", "value")
        url = _value(summary, "url", "value")
        publication = Publication(
            title=title,
            year=year,
            venue=_value(summary, "journal-title", "value"),
            doi=_doi(summary, group),
            url=url if url and not _is_code(url) else "",
            code=url if url and _is_code(url) else "",
            kind=_value(summary, "type"),
        )
        key = (_int(year), _int(month), _int(day))
        out.append((key, publication))
    return out


def crossref_venue(doi: str, fetch: Fetch) -> str:
    query = urllib.parse.urlencode({"mailto": CONTACT})
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='/')}?{query}"
    message = (fetch(url, {"Accept": "application/json"}) or {}).get("message") or {}
    containers = message.get("container-title") or []
    if containers and isinstance(containers[0], str):
        return containers[0].strip()
    event = message.get("event") or {}
    return str(event.get("name") or "").strip()


def fetch_publications(fetch: Fetch = http_json) -> Publications:
    payload = fetch(ORCID_WORKS, {"Accept": "application/json"})
    works = parse_works(payload)
    enriched: list[tuple[tuple[int, int, int], Publication]] = []
    lookups = 0
    for key, work in works:
        if work.doi and not work.venue and lookups < CROSSREF_LIMIT:
            lookups += 1
            try:
                venue = crossref_venue(work.doi, fetch)
            except OSError:
                venue = ""
            if venue:
                work = Publication(**{**vars(work), "venue": venue})
        enriched.append((key, work))
    enriched.sort(key=lambda item: (-item[0][0], -item[0][1], -item[0][2], item[1].title.lower()))
    return Publications(works=tuple(work for _, work in enriched))
