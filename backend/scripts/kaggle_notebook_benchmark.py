"""Paste this into a Kaggle notebook cell (after uploading kaggle_export.jsonl as a
Dataset and attaching it) to run Aletheia's grounded-vs-baseline comparison against
a model available through kaggle_benchmarks, using the SAME prompts,
grounding-downgrade logic, and scoring as backend/src/aletheia/evaluation/phase3.py.

Only the verifying model changes; the claims, gold labels, and retrieved evidence are
frozen (exported from the live corpus), so this is a fair comparison against the
Groq-based headline runs in EVALUATION.md.

IMPORTANT: bare `llm.prompt()` / `kbench.chats.new(...)` calls made OUTSIDE an
`@kbench.task`-decorated function invoked via `.run()` do not execute synchronously —
they silently no-op with no error (confirmed empirically: verified against a live
Kaggle kernel, 2026-08-03). Every model call MUST go through `<task>.run(...)`, as
below. This only runs inside an actual Kaggle Notebook session on kaggle.com — a
plain API-pushed kernel gets zero authorized models (`kbench.llms` is empty), even
with a valid Kaggle API token; the AI quota is scoped to the interactive session.

Set MODEL to whatever `sorted(kbench.llms.keys())` prints in your notebook — the
authorized model set depends on your account/environment, not just the target model
name (`google/gemini-3.1-flash-lite-preview` was NOT authorized for the plain API
token this script was validated against).
"""

import json
from dataclasses import dataclass

import kaggle_benchmarks as kbench

MODEL = "google/gemini-3.1-flash-lite-preview"  # confirm this is in kbench.llms.keys() first
# Adjust to wherever the exported dataset is mounted in the notebook.
DATA_PATH = "/kaggle/input/aletheia-scifact-kaggle-export/kaggle_export.jsonl"

_VERIFY_INSTRUCTIONS = (
    "You are a strict verification critic. Judge a single CLAIM using ONLY the "
    "provided EVIDENCE — never your own knowledge. Choose exactly one verdict:\n"
    '- "Supported": the evidence explicitly supports the claim. You MUST quote the '
    "exact span of evidence that supports it.\n"
    '- "Contradicted": the evidence explicitly contradicts the claim. You MUST quote '
    "the exact span of evidence that contradicts it.\n"
    '- "Unverifiable": the evidence neither supports nor contradicts the claim. Do '
    "NOT quote a span.\n"
    "Apply this sufficiency test to your span before committing to Supported or "
    "Contradicted. Read the span on its own and ask whether it settles THIS exact "
    "claim:\n"
    "  - If it directly states the claim, answer Supported; if it directly states the "
    "opposite, answer Contradicted — do not retreat to Unverifiable when a span plainly "
    "decides the claim.\n"
    "  - If the span is only on the same topic, gives background, or bears on a related "
    "but different statement, it does NOT settle the claim — answer Unverifiable. Judge "
    "only what the span literally says; never close the gap with inference or outside "
    "knowledge.\n"
    "  - Judge meaning, not wording: the claim does not need the same words as the span, "
    "only the same fact. Paraphrase, synonyms, and reordering are fine as long as the "
    "span's stated meaning settles the claim — only the quote itself must be verbatim, "
    "never the claim.\n"
    "The quoted span must be copied verbatim, character for character, from the "
    "EVIDENCE. It must be ONE continuous passage: never stitch together separate "
    "sentences or fragments with an ellipsis (...) and never drop words from the "
    "middle of the span. If no single continuous passage settles the claim, you must "
    "answer Unverifiable."
)

_BASELINE_INSTRUCTIONS = (
    "You judge whether evidence supports a single scientific claim. Use "
    '"Supported" if the evidence supports the claim, "Contradicted" if it refutes '
    'the claim, and "Unverifiable" if the evidence is insufficient. Judge only '
    "against the evidence; do not use outside knowledge."
)

_PUNCTUATION_FOLDS = {
    "\N{MIDDLE DOT}": ".",
    "\N{BULLET}": ".",
    "\N{EN DASH}": "-",
    "\N{EM DASH}": "-",
    "\N{MINUS SIGN}": "-",
    "\N{NON-BREAKING HYPHEN}": "-",
    "\N{LEFT SINGLE QUOTATION MARK}": "'",
    "\N{RIGHT SINGLE QUOTATION MARK}": "'",
    "\N{LEFT DOUBLE QUOTATION MARK}": '"',
    "\N{RIGHT DOUBLE QUOTATION MARK}": '"',
    "\N{NO-BREAK SPACE}": " ",
}
_FOLD_TABLE = str.maketrans(_PUNCTUATION_FOLDS)


def normalise_for_match(text: str) -> str:
    return " ".join(text.translate(_FOLD_TABLE).split())


VERDICTS = {"supported", "contradicted", "unverifiable"}


@dataclass
class GroundedReply:
    """Structured reply for the grounded verifier arm."""

    verdict: str  # "Supported" | "Contradicted" | "Unverifiable"
    quoted_span: str | None
    reasoning: str


@dataclass
class BaselineReply:
    """Structured reply for the single-LLM baseline arm."""

    verdict: str  # "Supported" | "Contradicted" | "Unverifiable"


def grounded_verdict(llm, claim: str, evidence: str) -> str:
    """Mirrors aletheia.agents.verifier: forced span, then grounded_against downgrade."""
    prompt = f"{_VERIFY_INSTRUCTIONS}\n\nEVIDENCE:\n{evidence}\n\nCLAIM:\n{claim}"
    reply = llm.prompt(prompt, schema=GroundedReply)
    verdict = (reply.verdict or "").strip().lower()
    span = (
        reply.quoted_span.strip()
        if isinstance(reply.quoted_span, str) and reply.quoted_span.strip()
        else None
    )

    if verdict not in VERDICTS:
        return "unverifiable"
    if verdict in ("supported", "contradicted") and span is None:
        return "unverifiable"  # Defence 1: no span, no grounded verdict.
    if verdict in ("supported", "contradicted") and normalise_for_match(
        span
    ) not in normalise_for_match(evidence):
        return "unverifiable"  # Defence 2: quote not found verbatim.
    return verdict


def baseline_verdict(llm, claim: str, evidence: str) -> str:
    prompt = f"{_BASELINE_INSTRUCTIONS}\n\nEVIDENCE:\n{evidence}\n\nCLAIM:\n{claim}"
    reply = llm.prompt(prompt, schema=BaselineReply)
    verdict = (reply.verdict or "").strip().lower()
    return verdict if verdict in VERDICTS else "unverifiable"


def score(name: str, predicted: list[str], gold: list[str]) -> None:
    correct = sum(p == g for p, g in zip(predicted, gold, strict=True))
    should_flag = [g for g in gold if g != "supported"]
    flagged = sum(
        1 for p, g in zip(predicted, gold, strict=True) if g != "supported" and p != "supported"
    )
    pred_supported = [p for p in predicted if p == "supported"]
    false_supported = sum(
        1 for p, g in zip(predicted, gold, strict=True) if p == "supported" and g != "supported"
    )
    n = len(gold)
    catch_rate = flagged / len(should_flag) if should_flag else 1.0
    false_agreement = false_supported / len(pred_supported) if pred_supported else 0.0
    print(
        f"{name:<28} accuracy {correct}/{n} ({correct / n * 100:.1f}%)  "
        f"catch {flagged}/{len(should_flag)} ({catch_rate * 100:.1f}%)  "
        f"false-agreement {false_supported}/{len(pred_supported)} ({false_agreement * 100:.1f}%)"
    )


@kbench.task(name="verify_claim", store_task=False)
def verify_claim_task(llm, claim: str, evidence: str) -> dict:
    with kbench.chats.new("grounded"):
        g = grounded_verdict(llm, claim, evidence)
    with kbench.chats.new("baseline"):
        b = baseline_verdict(llm, claim, evidence)
    return {"grounded": g, "baseline": b}


def main():
    print("available models:", sorted(kbench.llms.keys()))

    items = []
    with open(DATA_PATH) as f:
        for line in f:
            items.append(json.loads(line))

    gold: list[str] = []
    grounded_pred: list[str] = []
    baseline_pred: list[str] = []
    failures: list[tuple[str, str]] = []

    for i, item in enumerate(items, 1):
        try:
            run = verify_claim_task.run(
                llm=kbench.llms[MODEL], claim=item["claim"], evidence=item["evidence"]
            )
            g, b = run.result["grounded"], run.result["baseline"]
        except Exception as exc:
            failures.append((item["id"], str(exc)))
            print(f"[{i}/{len(items)}] FAILED {item['id']}: {type(exc).__name__}: {exc}")
            continue
        gold.append(item["gold"].lower())
        grounded_pred.append(g)
        baseline_pred.append(b)
        print(f"[{i}/{len(items)}] {item['id']}: gold={item['gold']} grounded={g} baseline={b}")

    print(f"\n{len(failures)} failures: {failures}\n")
    score("Aletheia (grounded verifier)", grounded_pred, gold)
    score("Single-LLM baseline", baseline_pred, gold)


if __name__ == "__main__":
    main()
