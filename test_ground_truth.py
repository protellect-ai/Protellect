"""
Ground-truth regression harness for Protellect.

STATUS: scaffold only. This cannot run end-to-end yet because it depends on
the real fetch_uniprot / fetch_clinvar / fetch_gnomad / etc. functions that
live in protellect_data.py, which has not been provided to me. Do not treat
any pass/fail output from this file as real until that dependency is real
and this has actually been executed against live data.

What this DOES do right now:
  - Loads ground_truth_test_set.csv
  - Defines the per-row check logic in a way a human can read and verify
  - Is ready to call the real pipeline the moment protellect_data.py exists

What you need to do to make this real:
  1. Ensure protellect_data.py and app.py are both importable from this
     directory (or adjust the import path below).
  2. Fill in `run_pipeline_for_gene()` to call your actual fetch + scoring
     + ai_synthesize chain for a single gene symbol.
  3. Run: python3 test_ground_truth.py
"""

import csv
import sys
from pathlib import Path

CSV_PATH = Path(__file__).parent / "ground_truth_test_set.csv"


def load_ground_truth(path: Path = CSV_PATH) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_pipeline_for_gene(gene_symbol: str) -> dict:
    """
    THIS IS A STUB. Replace with a real call into the app's pipeline.

    Expected real implementation (once protellect_data.py is available):

        from protellect_data import fetch_uniprot, fetch_clinvar, fetch_gnomad, ...
        from app import ai_synthesize, verify_ai_claims, g_gpcr_full, ...

        pdata = fetch_uniprot(gene_symbol)
        cv = fetch_clinvar(gene_symbol)
        gnomad = fetch_gnomad(gene_symbol)
        ... etc, then run scoring + ai_synthesize, and return the combined
        result so check_row() below can inspect it.
    """
    raise NotImplementedError(
        "run_pipeline_for_gene() is a stub — wire it to the real fetch + "
        "synthesize pipeline once protellect_data.py is available. Until "
        "then this harness cannot produce real pass/fail results."
    )


def check_row(row: dict, pipeline_output: dict) -> tuple[bool, str]:
    """
    Human-readable pass/fail check for one ground-truth row.

    This is intentionally NOT a fully automated semantic check — the
    expected_pipeline_behavior column is written in prose because the real
    check ("does the output avoid stating galanin is GPR151's ligand")
    needs either human review or an LLM-as-judge pass, not a string match.
    This function does what CAN be checked mechanically, and flags the rest
    for human review.
    """
    gene = row["gene_symbol"]
    category = row["category"]
    reasons = []

    # Mechanical checks that don't need human judgment:
    exec_summary = (pipeline_output.get("executive_summary") or "").lower()

    if category == "Currently orphan (negative control)":
        # The known-refuted or unconfirmed ligand should NOT be asserted as fact.
        ligand = (row.get("known_ligand") or "").split("(")[0].strip().lower()
        if ligand and ligand != "none" and ligand in exec_summary:
            # Presence alone isn't necessarily wrong (could be mentioned as
            # "proposed but not confirmed") — this needs a human read, not
            # an automatic fail. Flag for review rather than auto-failing.
            reasons.append(
                f"MANUAL REVIEW NEEDED: output mentions '{ligand}' for {gene} — "
                f"confirm it's framed as unconfirmed/refuted, not stated as fact."
            )

    verification = pipeline_output.get("_verification", {})
    flagged = verification.get("flagged_claims", [])
    if category.startswith("Deorphanized — contested"):
        if not flagged:
            reasons.append(
                f"WARNING: {gene} is a contested case but the verification layer "
                f"raised zero flags — check whether the output is presenting "
                f"disputed evidence with false confidence."
            )

    passed = len([r for r in reasons if r.startswith("MANUAL REVIEW")]) == len(reasons) and not any(
        r.startswith("WARNING") for r in reasons
    )
    # "Passed" here really means "no mechanical red flag was raised" —
    # rows needing manual review should be read by a human regardless of
    # this boolean.
    return passed, "; ".join(reasons) if reasons else "no mechanical issues detected"


def main():
    rows = load_ground_truth()
    print(f"Loaded {len(rows)} ground-truth rows from {CSV_PATH.name}\n")

    results = []
    for row in rows:
        gene = row["gene_symbol"]
        try:
            output = run_pipeline_for_gene(gene)
        except NotImplementedError as e:
            print(f"[SKIPPED] {gene}: {e}")
            continue
        passed, detail = check_row(row, output)
        results.append((gene, row["category"], passed, detail))

    if not results:
        print(
            "\nNo rows were actually run — run_pipeline_for_gene() is still a "
            "stub. Wire it to the real pipeline (see docstring) before trusting "
            "any pass/fail output from this script."
        )
        sys.exit(1)

    print(f"{'GENE':<12} {'CATEGORY':<45} {'RESULT':<8} DETAIL")
    for gene, category, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        print(f"{gene:<12} {category:<45} {status:<8} {detail}")

    # Per-row reporting only — deliberately no aggregate pass rate printed,
    # since an aggregate number can hide a failure on the two adversarial
    # rows (GPR151, GPR35) that matter most.
    adversarial = {"GPR151", "GPR35"}
    adversarial_results = [r for r in results if r[0] in adversarial]
    print("\n--- Adversarial rows (must be checked explicitly, never inferred from an aggregate) ---")
    for gene, category, passed, detail in adversarial_results:
        print(f"{gene}: {'PASS' if passed else 'FAIL'} — {detail}")


if __name__ == "__main__":
    main()
