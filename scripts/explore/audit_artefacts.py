"""Audit every manifest artefact: hash, size, and pairwise uniqueness.

Writes docs/_audit.txt because long console output is unreliable in this
environment. Read-only: does not modify any tracked artefact.
"""
from __future__ import annotations

import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN = os.path.join(ROOT, "results", "repro_manifest.json")
OUT = os.path.join(ROOT, "docs", "_audit.txt")

with open(MAN, encoding="utf-8") as fh:
    files = json.load(fh)["files"]

lines: list[str] = []
bad = 0
hashes: dict[str, list[str]] = {}
for rel in sorted(files):
    path = os.path.join(ROOT, rel.replace("/", os.sep))
    exists = os.path.exists(path)
    if not exists:
        lines.append(f"MISSING {rel}")
        bad += 1
        continue
    digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
    ok = digest == files[rel]["sha256"]
    bad += (not ok)
    lines.append(f"{'OK ' if ok else 'BAD'} {rel} size={os.path.getsize(path)} "
                 f"sha={digest[:12]}")
    hashes.setdefault(digest, []).append(rel)

lines.append("")
lines.append(f"artefacts={len(files)} mismatches={bad}")

lines.append("")
lines.append("duplicate-content groups:")
dupes = {h: v for h, v in hashes.items() if len(v) > 1}
if not dupes:
    lines.append("  none - every artefact has unique content")
for h, v in dupes.items():
    lines.append(f"  {h[:12]}: {', '.join(v)}")

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("audit written:", OUT)