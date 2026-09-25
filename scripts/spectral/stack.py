"""Stack tiles: vendored skill-icons plus matching chips for tools skill-icons does not cover.

skill-icons (MIT, tandpfun/skill-icons) draw each logo on a neutral rounded tile. The neutral
tile is recoloured to the Spectral surface and given a hairline, so the vendored icons and the
generated chips read as one set. Icons whose tile *is* the brand colour (TypeScript, Astro,
Docker, Git) are kept exactly as published.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from svgkit.canvas import Canvas
from svgkit.color import Ledger
from svgkit.svg import el, esc, fmt

from .theme import ROOT, Theme, Tokens

SKILL_DIR = ROOT / "design" / "icons" / "skill-icons"
SIMPLE_DIR = ROOT / "design" / "icons" / "simple-icons"
NEUTRAL_TILE = {"dark": "#242938", "light": "#F4F2ED"}
TILE = 40


@dataclass(frozen=True)
class Tool:
    slug: str
    label: str
    skill: str | None = None  # skill-icons file stem, e.g. "Python" or "TypeScript"
    themed: bool = True  # skill-icons ships -Dark and -Light variants
    logo: str | None = None  # simple-icons slug (verified list only)
    short: str | None = None  # label drawn on the chip when the full name is long

    @property
    def chip_label(self) -> str:
        return self.short or self.label


GROUPS: tuple[tuple[str, tuple[Tool, ...]], ...] = (
    (
        "Research & ML",
        (
            Tool("python", "Python", "Python"),
            Tool("pytorch", "PyTorch", "PyTorch"),
            Tool("lightning", "Lightning", logo="lightning"),
            Tool("huggingface", "Hugging Face", logo="huggingface"),
            Tool("timm", "timm"),
            Tool("opencv", "OpenCV", "OpenCV"),
            Tool("wandb", "Weights & Biases", logo="weightsandbiases", short="W&B"),
            Tool("jupyter", "Jupyter", logo="jupyter"),
            Tool("latex", "LaTeX", "LaTeX"),
        ),
    ),
    (
        "Web & edge",
        (
            Tool("ts", "TypeScript", "TypeScript", themed=False),
            Tool("astro", "Astro", "Astro", themed=False),
            Tool("tailwind", "Tailwind CSS", "TailwindCSS"),
            Tool("solidjs", "SolidJS", "SolidJS"),
            Tool("cloudflare", "Cloudflare", "Cloudflare"),
            Tool("workers", "Cloudflare Workers", "Workers"),
            Tool("vitest", "Vitest", "Vitest"),
            Tool("playwright", "Playwright"),
            Tool("stripe", "Stripe"),
        ),
    ),
    (
        "Infra & tooling",
        (
            Tool("docker", "Docker", "Docker", themed=False),
            Tool("linux", "Linux", "Linux"),
            Tool("bash", "Bash", "Bash"),
            Tool("git", "Git", "Git", themed=False),
            Tool("githubactions", "GitHub Actions", "GithubActions"),
            Tool("uv", "uv", logo="uv"),
            Tool("ruff", "Ruff", logo="ruff"),
            Tool("pytest", "pytest"),
            Tool("mypy", "mypy"),
        ),
    ),
)

_OPEN = re.compile(r"<svg\b([^>]*)>")


def skill_tile(tool: Tool, theme: Theme) -> str:
    assert tool.skill
    stem = f"{tool.skill}-{theme.name.capitalize()}" if tool.themed else tool.skill
    source = (SKILL_DIR / f"{stem}.svg").read_text(encoding="utf-8").strip()
    if tool.themed:
        source = source.replace(f'"{NEUTRAL_TILE[theme.name]}"', f'"{theme.surface}"')
    match = _OPEN.search(source)
    assert match, f"no <svg> in {stem}"
    head = (
        f'<svg{match.group(1)} role="img" aria-labelledby="t d">'
        f'<title id="t">{esc(tool.label)}</title>'
        f'<desc id="d">{esc(tool.label)} logo (skill-icons, MIT).</desc>'
    )
    border = ""
    if tool.themed:
        # A one-pixel hairline at 40 px display size is 6.4 units in the 256-unit viewBox.
        border = el(
            "rect",
            {
                "x": 3.2,
                "y": 3.2,
                "width": 249.6,
                "height": 249.6,
                "rx": 56.8,
                "fill": "none",
                "stroke": theme.hairline_strong,
                "stroke-width": 6.4,
            },
        )
    body = source[match.end() :]
    closing = body.rfind("</svg>")
    return head + body[:closing] + border + "</svg>\n"


def _logo_path(slug: str) -> str:
    source = (SIMPLE_DIR / f"{slug}.svg").read_text(encoding="utf-8")
    found = re.search(r'<path d="([^"]+)"', source)
    assert found, f"no path in simple-icons/{slug}.svg"
    return found.group(1)


def chip(tokens: Tokens, theme: Theme, tool: Tool, ledger: Ledger, asset: str) -> str:
    """Tile-height chip: optional monochrome simple-icons logo, then a mono label."""
    probe = Canvas(asset, 0, TILE, ledger=Ledger(), bg=theme.surface, min_scale=1)
    probe.style("t", tokens.fonts.mono, 14, theme.text)
    logo = 18 if tool.logo else 0
    pad = 14
    width = round(pad + (logo + 10 if logo else 0) + probe.measure(tool.chip_label, "t") + pad)
    c = Canvas(
        asset, width, TILE, ledger=ledger, bg=theme.surface, min_scale=tokens.min_scale(width)
    )
    c.style("t", tokens.fonts.mono, 14, theme.text)
    parts = [
        el(
            "rect",
            {
                "x": 0.5,
                "y": 0.5,
                "width": width - 1,
                "height": TILE - 1,
                "rx": 8.9,
                "fill": theme.surface,
                "stroke": theme.hairline_strong,
            },
        )
    ]
    x = pad
    if tool.logo:
        scale = logo / 24
        parts.append(
            el(
                "path",
                {
                    "d": _logo_path(tool.logo),
                    "fill": theme.muted,
                    "transform": (
                        f"translate({fmt(x)} {fmt((TILE - logo) / 2)}) scale({fmt(scale, 4)})"
                    ),
                },
            )
        )
        x += logo + 10
    parts.append(c.text(tool.chip_label, x, 25, "t", label=tool.label))
    desc = f"{tool.label}" + (" (logo: Simple Icons, CC0)." if tool.logo else ".")
    return c.render(title=tool.label, desc=desc, body="".join(parts))


def render(tokens: Tokens, theme: Theme, tool: Tool, ledger: Ledger, asset: str) -> str:
    if tool.skill:
        return skill_tile(tool, theme)
    return chip(tokens, theme, tool, ledger, asset)
