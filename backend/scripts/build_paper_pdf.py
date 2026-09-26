"""Build docs/Aletheia-Research-Paper.pdf from docs/aletheia-ieee-paper.md.

pandoc renders every Markdown table as a ``longtable``, which may split across pages
and, together with the italic caption paragraph written above each table, lets a
caption drift away from its table. This script keeps pandoc's LaTeX but rewrites each
``longtable`` into an unbreakable ``tabular`` block that carries its caption with it,
so no table is ever split or orphaned from its caption. Then it compiles with xelatex.

    python3 backend/scripts/build_paper_pdf.py

Requires pandoc and a TeX distribution with xelatex and the Times New Roman font.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2] / "docs"
SOURCE = DOCS / "aletheia-ieee-paper.md"
OUTPUT = DOCS / "Aletheia-Research-Paper.pdf"


def _spec_end(text: str, start: int) -> int:
    """Index just past the balanced ``{...}`` column spec that opens at ``start``."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("unbalanced longtable column spec")


def unbreakable_tables(tex: str) -> str:
    """Rewrite every ``longtable`` (and the caption paragraph above it) as one block."""
    out: list[str] = []
    pos = 0
    opener = "\\begin{longtable}[]"
    while (start := tex.find(opener, pos)) != -1:
        spec_start = start + len(opener)
        spec_stop = _spec_end(tex, spec_start)
        stop = tex.index("\\end{longtable}", spec_stop)
        body = tex[spec_stop:stop]
        skip = {"\\endhead", "\\endfirsthead"}
        body = "\n".join(line for line in body.splitlines() if line.strip() not in skip)

        # Pull a directly preceding "\emph{Table N. ...}" caption paragraph into the block.
        before = tex[pos:start]
        caption = ""
        match = re.search(r"\\emph\{Table \d+\.(?:[^{}]|\{[^{}]*\})*\}\s*$", before)
        if match:
            caption = match.group(0).rstrip() + "\\par\\smallskip\n"
            before = before[: match.start()]

        out.append(before)
        out.append(
            "\\par\\noindent\\begin{minipage}{\\linewidth}\n"
            + caption
            + "\\centering\\footnotesize\n"
            + "\\begin{tabular}"
            + tex[spec_start:spec_stop]
            + body
            + "\\end{tabular}\n\\end{minipage}\\par\\medskip\n"
        )
        pos = stop + len("\\end{longtable}")
    out.append(tex[pos:])
    return "".join(out)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tex_path = Path(tmp) / "paper.tex"
        subprocess.run(
            ["pandoc", str(SOURCE), "-s", "-o", str(tex_path), "-V", "mainfont=Times New Roman"],
            check=True,
        )
        tex_path.write_text(unbreakable_tables(tex_path.read_text()))
        for _ in range(2):  # second pass settles cross-references
            subprocess.run(
                [
                    "xelatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    f"-output-directory={tmp}",
                    str(tex_path),
                ],
                check=True,
                cwd=DOCS,
                stdout=subprocess.DEVNULL,
            )
        shutil.copy(Path(tmp) / "paper.pdf", OUTPUT)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
