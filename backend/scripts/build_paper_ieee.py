"""Build docs/Aletheia-Research-Paper.pdf in IEEE two-column conference format.

The canonical source is docs/aletheia-ieee-paper.md. Its YAML front matter supplies the
title, authors, abstract and keywords; its body is converted to a LaTeX fragment by
pandoc and wrapped in an IEEEtran (conference) preamble here, so the one Markdown file
stays the single source of truth. Post-processing does the IEEE-specific work pandoc
cannot: it turns each pandoc ``longtable`` into an unbreakable ``table``/``table*`` float
with the caption paragraph pulled in above it, promotes figures to full-width ``figure*``,
and renders the reference list as a ``thebibliography``.

    python3 backend/scripts/build_paper_ieee.py

Requires pandoc, a TeX install with IEEEtran.cls and xelatex, and the Times New Roman font.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

DOCS = Path(__file__).resolve().parents[2] / "docs"
SOURCE = DOCS / "aletheia-ieee-paper.md"
OUTPUT = DOCS / "Aletheia-Research-Paper.pdf"

# The two authors' affiliation blocks, and the page-1 footnote for the first author.
AUTHORS = [
    (
        "Jay Gautam",
        "Department of Computer Science and Engineering (AI \\& ML)\\\\"
        "P P Savani University\\\\Surat, India\\\\jaygautam561@gmail.com",
        "Corresponding author. Source code, run traces, and the evaluation record: "
        "https://github.com/jaygautam-creator/Aletheia",
    ),
    (
        "Rahul Kumar",
        "Department of Computer Science and Engineering\\\\"
        "P P Savani University\\\\Surat, India",
        None,
    ),
]

PREAMBLE = r"""\documentclass[conference]{IEEEtran}
\IEEEoverridecommandlockouts
\usepackage{fontspec}
\setmainfont{Times New Roman}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{array}
\usepackage{booktabs}
\usepackage{calc}
\usepackage{graphicx}
\setkeys{Gin}{keepaspectratio}
\usepackage{xcolor}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,shapes.geometric}
\usepackage{stfloats}
\usepackage[hyphens]{url}
\usepackage[hidelinks]{hyperref}
% Helpers that pandoc's standalone template would normally define.
\providecommand{\real}[1]{#1}
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\providecommand{\pandocbounded}[1]{#1}
\newcommand{\emaddress}[1]{\texttt{#1}}
% Give LaTeX room for this table-heavy paper's two-column floats.
\extrafloats{60}
\renewcommand{\topfraction}{0.95}
\renewcommand{\bottomfraction}{0.95}
\renewcommand{\textfraction}{0.05}
\renewcommand{\floatpagefraction}{0.85}
\renewcommand{\dbltopfraction}{0.95}
\renewcommand{\dblfloatpagefraction}{0.85}
\setcounter{topnumber}{4}
\setcounter{bottomnumber}{4}
\setcounter{totalnumber}{8}
\setcounter{dbltopnumber}{4}
\sloppy
% Arabic section/subsection numbers so the paper's decimal cross-references
% ("Section 6.3", "9.1") match the headings; appendices stay lettered (A-K).
\renewcommand{\thesection}{\arabic{section}}
\renewcommand{\thesubsection}{\thesection.\arabic{subsection}}
\renewcommand{\thesectiondis}{\thesection.}
\renewcommand{\thesubsectiondis}{\thesection.\arabic{subsection}}
"""


def _tex_escape(text: str) -> str:
    """Escape the few LaTeX specials that can appear in YAML metadata strings."""
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
                 ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"),
                 ("^", r"\textasciicircum{}")):
        text = text.replace(a, b)
    return text.replace("---", "\\textemdash{}").replace("--", "\\textendash{}")


def _front_matter(meta: dict) -> str:
    blocks = []
    for name, affil, thanks in AUTHORS:
        note = f"\\thanks{{{_tex_escape(thanks)}}}" if thanks else ""
        blocks.append(f"\\IEEEauthorblockN{{{name}{note}}}\n\\IEEEauthorblockA{{{affil}}}")
    author = "\n\\and\n".join(blocks)
    title = _tex_escape(meta["title"])
    abstract = _tex_escape(" ".join(meta["abstract"].split()))
    keywords = _tex_escape(meta["keywords"])
    return (
        f"\\title{{{title}}}\n"
        f"\\author{{\n{author}\n}}\n"
        "\\maketitle\n"
        f"\\begin{{abstract}}\n{abstract}\n\\end{{abstract}}\n"
        f"\\begin{{IEEEkeywords}}\n{keywords}\n\\end{{IEEEkeywords}}\n"
    )


def _split_front_matter(md: str) -> tuple[dict, str]:
    assert md.startswith("---\n")
    _, fm, body = md.split("---\n", 2)
    return yaml.safe_load(fm), body


def _spec_end(text: str, start: int) -> int:
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("unbalanced longtable column spec")


def _breakable_texttt(tex: str) -> str:
    """Let long monospace tokens (trace filenames, model IDs) wrap at their punctuation.

    pandoc renders inline code as unbreakable ``\\texttt{...}`` and turns internal spaces
    into hard spaces, so a name like ``nvidia/nemotron-3-ultra-550b-a55b:free`` overflows a
    narrow column. Inserting ``\\allowbreak`` after ``/ _ . - :`` gives TeX legal break
    points without changing what is printed.
    """

    def fix(match: re.Match[str]) -> str:
        s = match.group(1).replace("\\ ", " ").replace("\\_", "\\_\\allowbreak{}")
        for ch in "/.-:":
            s = s.replace(ch, ch + "\\allowbreak{}")
        return "\\texttt{" + s + "}"

    return re.sub(r"\\texttt\{([^{}]*)\}", fix, tex)


def _tables_to_floats(tex: str) -> str:
    """Rewrite every pandoc ``longtable`` as an unbreakable IEEE float with its caption.

    A table wide enough to need both columns (more than three columns, or any proportional
    ``p{}`` column spec) becomes a ``table*``; a narrow one becomes a single-column
    ``table``. The italic ``\\emph{Table N. ...}`` caption paragraph pandoc produced just
    above the table is pulled inside the float, centred and in a small font.
    """
    out: list[str] = []
    pos = 0
    opener = "\\begin{longtable}[]"
    while (start := tex.find(opener, pos)) != -1:
        spec_start = start + len(opener)
        spec_stop = _spec_end(tex, spec_start)
        spec = tex[spec_start:spec_stop]
        stop = tex.index("\\end{longtable}", spec_stop)
        body = tex[spec_stop:stop]
        skip = {"\\endhead", "\\endfirsthead", "\\endlastfoot", "\\endfoot"}
        body = "\n".join(line for line in body.splitlines() if line.strip() not in skip)

        before = tex[pos:start]
        caption = ""
        match = re.search(r"\\emph\{Table \d+\.(?:[^{}]|\{[^{}]*\})*\}\s*$", before)
        if match:
            caption = (
                "\\begin{center}\\footnotesize\n"
                + match.group(0).rstrip()
                + "\\end{center}\n\\vspace{-0.4em}\n"
            )
            before = before[: match.start()]

        wide = spec.count(">{") >= 1 or spec.count("p{") >= 1 or body.count("&") // max(
            body.count("\\\\"), 1
        ) >= 3
        env = "table*" if wide else "table"
        size = "\\scriptsize" if spec.count("p{") >= 5 else "\\footnotesize"
        out.append(before)
        out.append(
            f"\\begin{{{env}}}[!tb]\n{caption}\\centering\n{size}\n"
            f"\\begin{{tabular}}{spec}{body}\\end{{tabular}}\n\\end{{{env}}}\n"
        )
        pos = stop + len("\\end{longtable}")
    out.append(tex[pos:])
    return "".join(out)


def _figures_to_starred(tex: str) -> str:
    tex = re.sub(r"\\begin\{figure\}(\[[^\]]*\])?", r"\\begin{figure*}[!tb]", tex)
    return tex.replace("\\end{figure}", "\\end{figure*}")


def _references_to_bibliography(tex: str) -> str:
    """Turn the marked reference paragraphs into a ``thebibliography`` environment."""
    match = re.search(r"%%BIBSTART%%(.*?)%%BIBEND%%", tex, re.DOTALL)
    if not match:
        return tex
    block = match.group(1)
    items = re.split(r"\n\s*\n", block.strip())
    rendered = []
    for item in items:
        item = re.sub(r"^\s*\{\[\}(\d+)\{\]\}\s*", lambda m: f"\\bibitem{{ref{m.group(1)}}} ", item)
        rendered.append(item.strip())
    bib = (
        "\\begin{thebibliography}{99}\n\\itemsep=0pt\n"
        + "\n\n".join(rendered)
        + "\n\\end{thebibliography}\n"
    )
    return tex[: match.start()] + bib + tex[match.end() :]


def build_tex(md: str) -> str:
    meta, body = _split_front_matter(md)
    # Mark the reference block so it can be found precisely after conversion.
    body = body.replace("\n# References\n", "\n```{=latex}\n%%BIBSTART%%\n```\n", 1)
    body = body.replace(
        "```{=latex}\n\\appendix\n\\clearpage\n```",
        "```{=latex}\n%%BIBEND%%\n\\appendices\n```",
        1,
    )
    # The IEEE front matter already prints the keywords; drop the body's duplicate line
    # and the now-redundant standalone "Index Terms" paragraph.
    body = re.sub(r"(?m)^\*\*Index Terms\*\* --- .*\n", "", body)
    with tempfile.TemporaryDirectory() as tmp:
        body_md = Path(tmp) / "body.md"
        body_md.write_text(body)
        frag = subprocess.run(
            ["pandoc", str(body_md), "-t", "latex", "--wrap=preserve"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    frag = _breakable_texttt(frag)
    frag = _tables_to_floats(frag)
    frag = _figures_to_starred(frag)
    frag = _references_to_bibliography(frag)
    return (
        PREAMBLE
        + "\\begin{document}\n"
        + _front_matter(meta)
        + frag
        + "\n\\end{document}\n"
    )


def main() -> None:
    tex = build_tex(SOURCE.read_text())
    with tempfile.TemporaryDirectory() as tmp:
        tex_path = Path(tmp) / "paper.tex"
        tex_path.write_text(tex)
        vendor = Path(__file__).resolve().parent / "vendor"
        env = {**os.environ, "TEXINPUTS": f"{vendor}:{os.environ.get('TEXINPUTS', '')}"}
        for _ in range(2):
            subprocess.run(
                ["xelatex", "-interaction=nonstopmode", f"-output-directory={tmp}", str(tex_path)],
                check=True,
                cwd=DOCS,
                stdout=subprocess.DEVNULL,
                env=env,
            )
        shutil.copy(Path(tmp) / "paper.pdf", OUTPUT)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
