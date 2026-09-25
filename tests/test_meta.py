"""Repository invariants: pinned dependencies agree, tokens are complete, fonts are licensed."""

from __future__ import annotations

import json
import re
import tomllib

from conftest import ROOT


def inline_dependencies(script: str) -> list[str]:
    text = (ROOT / "scripts" / script).read_text(encoding="utf-8")
    block = re.search(r"^# /// script\n(.*?)^# ///$", text, flags=re.MULTILINE | re.DOTALL)
    assert block, f"{script} has no PEP 723 block"
    lines = block.group(1).splitlines()
    body = "\n".join(line.removeprefix("# ").removeprefix("#") for line in lines)
    return sorted(tomllib.loads(body)["dependencies"])


def test_pep723_blocks_match_pyproject() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pinned = sorted(project["project"]["dependencies"])
    for script in ("build_assets.py", "refresh.py"):
        assert inline_dependencies(script) == pinned, script


def test_tokens_define_every_colour_for_both_themes() -> None:
    tokens = json.loads((ROOT / "design" / "tokens.json").read_text(encoding="utf-8"))
    keys = [set(theme) for theme in tokens["themes"].values()]
    assert set(tokens["themes"]) == {"dark", "light"}
    assert keys[0] == keys[1]


def test_every_font_ships_with_its_licence() -> None:
    fonts = sorted((ROOT / "design" / "fonts").glob("*.ttf"))
    assert fonts
    for font in fonts:
        family = font.stem.split("-")[0]
        assert (font.parent / f"OFL-{family}.txt").exists(), font.name


def test_readme_keeps_its_markers() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in ("LINKS", "PUBLICATIONS", "FEATURES", "STACK", "ACTIVITY"):
        assert readme.count(f"<!-- {name}:START -->") == 1
        assert readme.count(f"<!-- {name}:END -->") == 1
