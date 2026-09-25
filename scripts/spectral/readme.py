"""Generate the README blocks that sit between <!-- NAME:START --> and <!-- NAME:END --> markers."""

from __future__ import annotations

import re

from . import stack
from .assets import FEATURES, LINKS
from .data import Publications, Stats

ORCID = "https://orcid.org/0009-0002-7771-1081"
SCHOLAR = "https://scholar.google.com/citations?user=KIZQVFAAAAAJ&hl=en"

_MD_SPECIAL = re.compile(r"([\\`*_\[\]<>$|#])")


def md_escape(text: str) -> str:
    """Escape Markdown syntax (and ``$``, which GitHub may read as maths) in plain text."""
    return _MD_SPECIAL.sub(r"\\\1", " ".join(text.split()))


def picture(base: str, alt: str, *, width: int | None = None, height: int | None = None) -> str:
    """A theme-aware image: ``{base}-dark.svg`` in dark mode, ``{base}-light.svg`` otherwise."""
    size = (f' width="{width}"' if width else "") + (f' height="{height}"' if height else "")
    alt = alt.replace('"', "&quot;")
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="{base}-dark.svg">'
        f'<img alt="{alt}" src="{base}-light.svg"{size}></picture>'
    )


def links_block() -> str:
    return "\n".join(
        f'<a href="{link.href.replace("&", "&amp;")}">'
        f"{picture(f'assets/links/{link.slug}', link.label, height=32)}</a>"
        for link in LINKS
    )


def features_block() -> str:
    blocks = []
    for card in FEATURES:
        alt = f"{card.title}. {card.lines[0]} {card.lines[1]}"
        blocks.append(
            f'<a href="{card.href}">{picture(f"assets/cards/{card.slug}", alt, width=400)}</a>'
        )
    return "\n".join(blocks)


def stack_block() -> str:
    rows: list[str] = []
    for title, tools in stack.GROUPS:
        tiles = "\n".join(
            picture(f"assets/stack/{tool.slug}", tool.label, height=40) for tool in tools
        )
        rows.append(f"<p><b>{title.replace('&', '&amp;')}</b><br>\n{tiles}\n</p>")
    return "\n\n".join(rows)


def publications_block(pubs: Publications) -> str:
    if not pubs.works:
        return (
            "Papers will be listed here as they're published. Until then, see "
            f"[ORCID]({ORCID}) and [Google Scholar]({SCHOLAR})."
        )
    lines = []
    for work in pubs.works:
        title = md_escape(work.title)
        if work.doi:
            head = f"[{title}](https://doi.org/{work.doi})"
        elif work.url:
            head = f"[{title}]({work.url})"
        else:
            head = title
        bits = [head]
        if work.venue:
            bits.append(f"*{md_escape(work.venue)}*")
        if work.year:
            bits.append(work.year)
        if work.code:
            bits.append(f"[code]({work.code})")
        lines.append("- " + " · ".join(bits))
    return "\n".join(lines)


def activity_block(stats: Stats) -> str:
    images = (
        picture(
            "assets/activity/skyline",
            "Contribution skyline for the last 12 months: "
            "one column per day, taller for busier days.",
        )
        + "\n\n<p>\n"
        + picture(
            "assets/activity/contributions",
            "Contributions in the last 12 months.",
            width=400,
        )
        + "\n"
        + picture("assets/activity/languages", "Top languages by bytes.", width=400)
        + "\n</p>"
    )
    if not stats.ready or stats.total is None:
        summary = "These fill in after the first data refresh."
    else:
        shares, _ = stats.language_shares(4)
        langs = ", ".join(f"{md_escape(name)} {share * 100:.1f}%" for name, share in shares)
        whose = "my own repositories" + "".join(f" and {org}'s" for org in stats.language_orgs)
        notebooks = ", notebooks left out" if "Jupyter Notebook" in stats.excluded_languages else ""
        summary = (
            f"{stats.total:,} {stats.contribution_label} in the last 12 months. "
            f"Top languages by bytes across {whose}, private ones included{notebooks}: {langs}."
        )
    return f"{images}\n\n{summary}"


def replace_block(text: str, name: str, content: str) -> str:
    pattern = re.compile(rf"(<!-- {name}:START -->\n)(.*?)(<!-- {name}:END -->)", flags=re.DOTALL)
    if not pattern.search(text):
        raise ValueError(f"README is missing the {name} markers")
    return pattern.sub(lambda m: f"{m.group(1)}{content}\n{m.group(3)}", text, count=1)


def render(text: str, stats: Stats, pubs: Publications) -> str:
    text = replace_block(text, "LINKS", links_block())
    text = replace_block(text, "PUBLICATIONS", publications_block(pubs))
    text = replace_block(text, "FEATURES", features_block())
    text = replace_block(text, "STACK", stack_block())
    return replace_block(text, "ACTIVITY", activity_block(stats))
