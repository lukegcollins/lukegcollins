# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "brotli==1.2.0",
#   "fonttools[woff]==4.66.0",
#   "uharfbuzz==0.56.2",
# ]
# ///
"""Build every Spectral image from design/tokens.json and the data files.

    uv run scripts/build_assets.py           # write assets/ (only files that changed)
    uv run scripts/build_assets.py --check   # fail if assets/ differs from a fresh build

The build also refuses text that fails WCAG AA or renders below the minimum size.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from spectral import assets, data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify instead of writing")
    parser.add_argument(
        "--stats", type=Path, help="stats file to draw from (default data/stats.json)"
    )
    args = parser.parse_args(argv)
    stats = data.load_stats(args.stats) if args.stats else None
    built, ledger = assets.build_all(stats)
    problems = ledger.failures(assets.TOKENS.min_text_px)
    for problem in problems:
        print(f"illegible: {problem}", file=sys.stderr)
    if problems:
        return 1
    if args.check:
        stale = assets.stale(built)
        for path in stale:
            print(f"out of date: {path.relative_to(assets.ROOT)}", file=sys.stderr)
        return 1 if stale else 0
    changed = assets.write(built)
    for path in changed:
        print(f"wrote {path.relative_to(assets.ROOT)}")
    print(f"{len(built)} assets, {len(changed)} changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
