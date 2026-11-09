"""Compile the Typst sources to PDF.

    python report/build.py            # report.pdf, milestone1.pdf, slides.pdf
"""
from pathlib import Path

import typst

ROOT = Path(__file__).resolve().parents[1]
DOCS = {"report/main.typ": "report/report.pdf",
        "report/milestone1.typ": "report/milestone1.pdf",
        "slides/slides.typ": "slides/slides.pdf"}

if __name__ == "__main__":
    for src, out in DOCS.items():
        if (ROOT / src).exists():
            typst.compile(str(ROOT / src), output=str(ROOT / out), root=str(ROOT))
            print("built", out)
