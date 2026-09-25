"""The committed data files the images are drawn from.

data/stats.json holds aggregates only: daily contribution counts and language byte totals.
It never contains a repository or organisation name.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path

from .theme import ROOT

STATS = ROOT / "data" / "stats.json"
PUBLICATIONS = ROOT / "data" / "publications.json"


@dataclass(frozen=True)
class Stats:
    as_of: str | None = None
    total: int | None = None
    private_counted: int = 0  # private contributions GitHub reports as counts only
    days: tuple[tuple[str, int], ...] = ()
    languages: tuple[tuple[str, int], ...] = ()
    language_scope: str = ""
    language_orgs: tuple[str, ...] = ()
    excluded_languages: tuple[str, ...] = ()

    @property
    def includes_private(self) -> bool:
        """True only when GitHub counted private work (Luke's "Private contributions" setting)."""
        return self.private_counted > 0

    @property
    def languages_include_private(self) -> bool:
        """True only when a private repository added bytes to the language totals."""
        return self.language_scope.endswith("private included")

    @property
    def contribution_label(self) -> str:
        return (
            "contributions, private work included"
            if self.includes_private
            else "public contributions"
        )

    @property
    def ready(self) -> bool:
        return self.total is not None and bool(self.days)

    def weeks(self) -> list[list[tuple[int, int]]]:
        """Days grouped into Sunday-first weeks as (weekday, count), GitHub's calendar layout."""
        if not self.days:
            return []
        first = dt.date.fromisoformat(self.days[0][0])
        start = first - dt.timedelta(days=(first.weekday() + 1) % 7)
        grid: dict[int, list[tuple[int, int]]] = {}
        for iso, count in self.days:
            day = dt.date.fromisoformat(iso)
            offset = (day - start).days
            grid.setdefault(offset // 7, []).append((offset % 7, count))
        return [grid[k] for k in sorted(grid)]

    def language_shares(self, top: int) -> tuple[list[tuple[str, float]], float]:
        total = sum(size for _, size in self.languages)
        if not total:
            return [], 0.0
        ranked = sorted(self.languages, key=lambda item: (-item[1], item[0]))
        head = [(name, size / total) for name, size in ranked[:top]]
        other = sum(size for _, size in ranked[top:]) / total
        return head, other


@dataclass(frozen=True)
class Publication:
    title: str
    year: str = ""
    venue: str = ""
    doi: str = ""
    url: str = ""
    code: str = ""
    kind: str = ""


@dataclass(frozen=True)
class Publications:
    works: tuple[Publication, ...] = field(default_factory=tuple)


def load_stats(path: Path = STATS) -> Stats:
    if not path.exists():
        return Stats()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Stats(
        as_of=raw.get("as_of"),
        total=raw.get("contributions", {}).get("total"),
        private_counted=int(raw.get("contributions", {}).get("private_counted") or 0),
        days=tuple((str(d), int(c)) for d, c in raw.get("contributions", {}).get("days", [])),
        languages=tuple(
            (str(n), int(b)) for n, b in raw.get("languages", {}).get("bytes", {}).items()
        ),
        language_scope=raw.get("languages", {}).get("scope", ""),
        language_orgs=tuple(raw.get("languages", {}).get("orgs", [])),
        excluded_languages=tuple(raw.get("languages", {}).get("excluded", [])),
    )


def dump_stats(stats: Stats) -> str:
    payload = {
        "as_of": stats.as_of,
        "contributions": {
            "total": stats.total,
            "private_counted": stats.private_counted,
            "days": [[d, c] for d, c in stats.days],
        },
        "languages": {
            "scope": stats.language_scope,
            "orgs": list(stats.language_orgs),
            "excluded": list(stats.excluded_languages),
            "bytes": dict(sorted(stats.languages, key=lambda item: (-item[1], item[0]))),
        },
    }
    return json.dumps(payload, indent=1, ensure_ascii=False) + "\n"


def load_publications(path: Path = PUBLICATIONS) -> Publications:
    if not path.exists():
        return Publications()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Publications(works=tuple(Publication(**item) for item in raw.get("works", [])))


def dump_publications(pubs: Publications) -> str:
    works = [{k: v for k, v in vars(work).items() if v} for work in pubs.works]
    return json.dumps({"works": works}, indent=1, ensure_ascii=False) + "\n"
