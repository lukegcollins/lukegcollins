"""Refuse output that names something private.

Only what a reader can see is checked: SVG text, titles, descriptions and labels, and the
Markdown and JSON files verbatim. Embedded font data and path coordinates are skipped, since
random base64 could contain any short string by chance.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path

_SVG = "{http://www.w3.org/2000/svg}"
_LABEL_ATTRS = ("aria-label", "alt", "title")


def visible_text(name: str, content: str) -> str:
    if not name.endswith(".svg"):
        return content
    root = ET.fromstring(content)  # noqa: S314 (our own generated SVG)
    chunks: list[str] = []
    for element in root.iter():
        if element.tag in (f"{_SVG}style", "style"):
            continue
        if element.text:
            chunks.append(element.text)
        chunks.extend(element.attrib[a] for a in _LABEL_ATTRS if a in element.attrib)
    return "\n".join(chunks)


def _pattern(name: str) -> re.Pattern[str]:
    # A name only counts as a whole token: "deepfake-detection" must not match
    # "deepfake detection", and "abc" must not match inside "abcd".
    return re.compile(rf"(?<![\w.-]){re.escape(name)}(?![\w-]|\.\w)", re.IGNORECASE)


def find_leaks(
    outputs: dict[str, str], forbidden: Iterable[str], allowed: Iterable[str] = ()
) -> list[str]:
    """Return one message per (file, name) where a forbidden name is visible."""
    allow = {a.lower() for a in allowed}
    names = sorted({n for n in forbidden if n and n.lower() not in allow})
    patterns = [(n, _pattern(n)) for n in names]
    found: list[str] = []
    for label, content in sorted(outputs.items()):
        text = visible_text(label, content)
        for name, pattern in patterns:
            if pattern.search(text):
                found.append(f"{label}: private name {name!r} is visible")
    return found


def read_allowlist(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = (
        line.split("#", 1)[0].strip() for line in path.read_text(encoding="utf-8").splitlines()
    )
    return [line for line in lines if line]
