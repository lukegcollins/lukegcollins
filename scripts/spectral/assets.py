"""The list of every image the profile uses, and how to build, write and verify them."""

from __future__ import annotations

from pathlib import Path

from svgkit.color import Ledger
from svgkit.svg import write_if_changed

from . import activity, cards, hero, stack
from .data import Publications, Stats, load_publications, load_stats
from .theme import ROOT, load

TOKENS = load()
ASSETS = ROOT / "assets"
__all__ = ["ASSETS", "FEATURES", "LINKS", "README", "ROOT", "TOKENS", "build_all", "stale", "write"]

LINKS = (
    cards.Link("orcid", "ORCID", "https://orcid.org/0009-0002-7771-1081"),
    cards.Link(
        "scholar", "Google Scholar", "https://scholar.google.com/citations?user=KIZQVFAAAAAJ&hl=en"
    ),
    cards.Link("linkedin", "LinkedIn", "https://www.linkedin.com/in/lukegcollins/"),
    cards.Link("email", "Email", "mailto:luke.collins@research.deakin.edu.au"),
    cards.Link("dynamis", "dynamisgroup.com.au", "https://dynamisgroup.com.au/"),
)

FEATURES = (
    cards.Feature(
        "dfwb",
        "lead maintainer",
        "DFWB Research",
        ("Open, reproducible tooling for", "deepfake detection research."),
        "github.com/dfwb-research",
        "https://github.com/dfwb-research",
    ),
    cards.Feature(
        "dynamis",
        "managing director",
        "Dynamis Group",
        ("Software engineering, systems advice", "and a small R&D lab, in Melbourne."),
        "github.com/dynamis-group",
        "https://github.com/dynamis-group",
    ),
)


README = ROOT / "README.md"


def build_all(
    stats: Stats | None = None, pubs: Publications | None = None
) -> tuple[dict[Path, str], Ledger]:
    """Every generated file (images and the README) keyed by path, plus the text ledger."""
    from . import readme  # imported late: readme reads LINKS and FEATURES from this module

    stats = stats if stats is not None else load_stats()
    pubs = pubs if pubs is not None else load_publications()
    ledger = Ledger()
    out: dict[Path, str] = {}

    def add(rel: str, content: str) -> None:
        out[ASSETS / rel] = content

    for name, theme in sorted(TOKENS.themes.items()):
        add(f"hero-{name}.svg", hero.render(TOKENS, theme, hero.WIDE, ledger, f"hero-{name}.svg"))
        add(
            f"hero-{name}-compact.svg",
            hero.render(TOKENS, theme, hero.COMPACT, ledger, f"hero-{name}-compact.svg"),
        )
        for link in LINKS:
            rel = f"links/{link.slug}-{name}.svg"
            add(rel, cards.badge(TOKENS, theme, link, ledger, rel))
        for feature in FEATURES:
            rel = f"cards/{feature.slug}-{name}.svg"
            add(rel, cards.feature(TOKENS, theme, feature, ledger, rel))
        for _, tools in stack.GROUPS:
            for tool in tools:
                rel = f"stack/{tool.slug}-{name}.svg"
                add(rel, stack.render(TOKENS, theme, tool, ledger, rel))
        add(
            f"activity/skyline-{name}.svg",
            activity.skyline(TOKENS, theme, stats, ledger, f"activity/skyline-{name}.svg"),
        )
        add(
            f"activity/contributions-{name}.svg",
            activity.contributions_card(
                TOKENS, theme, stats, ledger, f"activity/contributions-{name}.svg"
            ),
        )
        add(
            f"activity/languages-{name}.svg",
            activity.languages_card(TOKENS, theme, stats, ledger, f"activity/languages-{name}.svg"),
        )
    out[README] = readme.render(README.read_text(encoding="utf-8"), stats, pubs)
    return out, ledger


def write(built: dict[Path, str]) -> list[Path]:
    return [path for path, content in sorted(built.items()) if write_if_changed(path, content)]


def stale(built: dict[Path, str]) -> list[Path]:
    expected = set(built)
    present = {p for p in ASSETS.rglob("*.svg")}
    orphans = sorted(present - expected)
    changed = [
        path
        for path, content in sorted(built.items())
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    return changed + orphans
