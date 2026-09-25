"""Deterministic SVG string building.

Everything here is plain string assembly with stable attribute order and rounded numbers, so
the same inputs always produce byte-identical files (the build test depends on it).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from xml.sax.saxutils import escape as _escape

AttrValue = str | float | int | None


def fmt(value: float, digits: int = 2) -> str:
    """Compact, stable number formatting: 12.50 -> 12.5, 3.0 -> 3, -0.0 -> 0."""
    text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def esc(text: str) -> str:
    return _escape(text, {'"': "&quot;"})


def attrs(values: Mapping[str, AttrValue]) -> str:
    parts: list[str] = []
    for key, value in values.items():
        if value is None:
            continue
        rendered = fmt(value) if isinstance(value, float) else str(value)
        parts.append(f' {key}="{esc(rendered)}"')
    return "".join(parts)


def el(tag: str, values: Mapping[str, AttrValue] | None = None, body: str | None = None) -> str:
    rendered = attrs(values or {})
    if body is None:
        return f"<{tag}{rendered}/>"
    return f"<{tag}{rendered}>{body}</{tag}>"


def group(children: Iterable[str], values: Mapping[str, AttrValue] | None = None) -> str:
    return el("g", values, "".join(children))


def text(
    content: str,
    x: float,
    y: float,
    cls: str,
    anchor: str | None = None,
    extra: Mapping[str, AttrValue] | None = None,
) -> str:
    values: dict[str, AttrValue] = {"x": x, "y": y, "class": cls}
    if anchor:
        values["text-anchor"] = anchor
    values.update(extra or {})
    return el("text", values, esc(content))


def tracked(content: str, x: float, y: float, cls: str, positions: list[float]) -> str:
    """Letter-spaced text drawn with explicit per-glyph x positions.

    SVG ``letter-spacing`` is unreliable across engines, so tracking is baked into the
    coordinates instead.
    """
    xs = " ".join(fmt(x + p) for p in positions)
    return f'<text x="{xs}" y="{fmt(y)}" class="{cls}">{esc(content)}</text>'


def document(
    *,
    width: float,
    height: float,
    title: str,
    desc: str,
    css: str,
    body: str,
) -> str:
    w, h = fmt(width), fmt(height)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">'
        f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>'
        f"<style>{css}</style>{body}</svg>\n"
    )


def write_if_changed(path: Path, content: str) -> bool:
    """Write ``content`` to ``path`` only when it differs. Returns True on change."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8", newline="\n")
    return True
