#!/usr/bin/env python3
"""Fail if the documented model count disagrees with the modules in the pipeline.

A model is a module in modules/local/ that is not a fine-tuning or head-only module. The
README, docs/index.md and docs/models/overview.md must all state that number, and the
overview table must have one row per model.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
modules = sorted(p.stem for p in (ROOT / "modules" / "local").glob("*.nf")
                 if not p.stem.endswith("_finetune") and p.stem != "finetune_head_only")
n = len(modules)
errors = []
for doc in ("README.md", "docs/index.md", "docs/models/overview.md"):
    text = (ROOT / doc).read_text()
    stated = {int(m) for m in re.findall(r"\b(\d+) (?:RNA deep learning )?models\b", text)}
    if n not in stated:
        errors.append(f"{doc}: states {sorted(stated) or 'no count'}, modules give {n}")
rows = [ln for ln in (ROOT / "docs/models/overview.md").read_text().split("## By track")[0]
        .splitlines() if ln.startswith("| [")]
if len(rows) != n:
    errors.append(f"docs/models/overview.md: {len(rows)} table rows, modules give {n}")
for e in errors:
    print("ERROR", e)
print(f"{n} models: {', '.join(modules)}")
sys.exit(1 if errors else 0)
