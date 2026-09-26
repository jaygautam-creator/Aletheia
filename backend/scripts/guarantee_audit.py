"""Re-check the evidence gate's guarantee directly from committed run traces.

For every asserted (Supported / Contradicted) verdict in a trace, confirm that its quoted
span is contained in one of the retrieved evidence blocks, using the pipeline's own
normalisation (:func:`aletheia.agents.contracts.normalise_for_match`). The runtime gate
already enforces this before a trace is written, so the audit does not test the gate's
logic; it tests that no asserted verdict reached the record without passing it, using
only the trace file — no model, no database. It also reports how many spans match under
whitespace-only normalisation, i.e. without the V4 punctuation fold.

    uv --directory backend run python scripts/guarantee_audit.py \
        runs/fever_n100_8b_clean.jsonl runs/scifact_revalidation.jsonl \
        runs/scifact_gemini.jsonl
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

from aletheia.agents.contracts import GROUNDED_VERDICTS, normalise_for_match


def _whitespace_only(text: str) -> str:
    return " ".join(text.split())


def _found(span: str, blocks: list[str], normalise: Callable[[str], str]) -> bool:
    needle = normalise(span)
    return bool(needle) and any(needle in normalise(block) for block in blocks)


def audit(path: Path) -> tuple[int, int, int]:
    """Return (asserted, backed under the pipeline's normalisation, backed whitespace-only)."""
    asserted = backed = backed_ws = 0
    grounded = {verdict.value for verdict in GROUNDED_VERDICTS}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        # Each evidence block is the title plus the chunk text, as the Verifier saw it.
        blocks = [f"{e.get('title') or ''}\n{e['text']}" for e in record["evidence"]]
        for verdict in record["verdicts"]:
            if verdict["verdict"] not in grounded:
                continue
            asserted += 1
            span = verdict.get("quoted_span") or ""
            backed += _found(span, blocks, normalise_for_match)
            backed_ws += _found(span, blocks, _whitespace_only)
    return asserted, backed, backed_ws


def main(paths: list[str]) -> int:
    failed = False
    for name in paths:
        asserted, backed, backed_ws = audit(Path(name))
        print(
            f"{name}: {backed}/{asserted} asserted verdicts verbatim-backed "
            f"({backed_ws}/{asserted} under whitespace-only normalisation)"
        )
        failed |= backed != asserted
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
