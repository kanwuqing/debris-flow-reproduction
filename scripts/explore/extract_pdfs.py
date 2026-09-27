"""Extract text from the Zenodo 'Read me.pdf' and 'References of data sources.pdf'."""
import os

from pypdf import PdfReader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "docs", "raw")
os.makedirs(OUT, exist_ok=True)

for name in ["Read me.pdf", "References of data sources.pdf"]:
    src = os.path.join(RAW, name)
    reader = PdfReader(src)
    parts = []
    for i, page in enumerate(reader.pages):
        parts.append("\n=== PAGE %d ===\n" % (i + 1))
        parts.append(page.extract_text() or "")
    text = "".join(parts)
    dst = os.path.join(OUT, os.path.splitext(name)[0] + ".txt")
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("=", name, "pages=", len(reader.pages), "chars=", len(text), "->", dst)
