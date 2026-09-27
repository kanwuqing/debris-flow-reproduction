"""List (and extract) the Europe PMC supplementary archive for the paper."""
from __future__ import annotations

import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "docs", "raw")
ZIP = os.path.join(RAW, "PMC9420130_supp.zip")
OUT = os.path.join(RAW, "supp")

with zipfile.ZipFile(ZIP) as zf:
    for info in zf.infolist():
        print(f"{info.file_size:>10}  {info.filename}")
    os.makedirs(OUT, exist_ok=True)
    zf.extractall(OUT)
print("extracted ->", OUT)
