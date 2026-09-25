"""Checks every generated file must pass before it is written or committed.

The refresh workflow commits with GITHUB_TOKEN, and those pushes trigger no other workflow,
so the refresh job runs these itself instead of relying on CI.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

SVG_NS = "{http://www.w3.org/2000/svg}"
HERO_BUDGET = 250_000
CARD_BUDGET = 80_000
_LARGE = ("hero-", "activity/skyline-")
_EXTERNAL = re.compile(
    r"""(?:href|src)\s*=\s*["'](?!#|data:)[^"']+|url\(\s*["']?(?!#|data:)|@import"""
)
_KEYFRAMES = re.compile(r"@keyframes\s+[\w-]+\s*\{((?:[^{}]*\{[^{}]*\})*)\s*\}")
_DECLARATION = re.compile(r"([a-z-]+)\s*:")


def budget(rel: str) -> int:
    return HERO_BUDGET if any(marker in rel for marker in _LARGE) else CARD_BUDGET


def check_svg(rel: str, content: str) -> list[str]:
    problems: list[str] = []
    try:
        root = ET.fromstring(content)  # noqa: S314 (our own generated SVG)
    except ET.ParseError as exc:
        return [f"{rel}: not well-formed XML ({exc})"]
    if root.tag != f"{SVG_NS}svg":
        problems.append(f"{rel}: root element is not <svg>")
    if "viewBox" not in root.attrib:
        problems.append(f"{rel}: missing viewBox")
    if root.attrib.get("role") != "img":
        problems.append(f"{rel}: missing role=img")
    if root.find(f"{SVG_NS}title") is None or root.find(f"{SVG_NS}desc") is None:
        problems.append(f"{rel}: missing <title> or <desc>")
    size = len(content.encode("utf-8"))
    if size > budget(rel):
        problems.append(f"{rel}: {size} bytes is over the {budget(rel)} byte budget")
    body = re.sub(r'xmlns(:\w+)?="[^"]*"', "", content)
    if _EXTERNAL.search(body):
        problems.append(f"{rel}: references something outside the file")
    if "<animate" in content or "<set " in content:
        problems.append(f"{rel}: uses SMIL; animate with CSS transform and opacity only")
    frames = _KEYFRAMES.findall(content)
    if frames:
        properties = {p for block in frames for p in _DECLARATION.findall(block)}
        if not properties <= {"transform", "opacity"}:
            problems.append(f"{rel}: animates {sorted(properties - {'transform', 'opacity'})}")
        if "prefers-reduced-motion:reduce" not in content.replace(" ", ""):
            problems.append(f"{rel}: animated without a prefers-reduced-motion fallback")
    return problems
