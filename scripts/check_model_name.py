#!/usr/bin/env python3
"""SUBMISSION.md once named the engine's default model by hand, and the engine's
default moved on without it — a retired model id sat in the submission doc for
readers to copy. This reads the default straight out of engine.py and fails if
any markdown file names a retired generation, or if SUBMISSION.md's own account
of the default has drifted from the code.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine.py"
SUBMISSION = ROOT / "SUBMISSION.md"

# Generations this repo has moved on from (see the comment above MODEL in engine.py).
RETIRED = ["claude-opus-4-8", "claude-sonnet-4-6"]


def current_default() -> str:
    m = re.search(r'MODEL = os\.environ\.get\("TENDERE_MODEL", "([^"]+)"\)', ENGINE.read_text())
    if not m:
        raise SystemExit("could not find the MODEL default in engine.py")
    return m.group(1)


def main() -> int:
    problems = 0
    default = current_default()

    for md in ROOT.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        for old in RETIRED:
            if old in text:
                print(f"  ✗ {md.name} names a retired model: {old}")
                problems += 1

    if default not in SUBMISSION.read_text(encoding="utf-8"):
        print(f"  ✗ SUBMISSION.md does not name the current default ({default}) anywhere")
        problems += 1

    print(f"\n{'✗' if problems else '✓'} {problems} stale model reference(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
