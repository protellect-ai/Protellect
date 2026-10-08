"""ML validation: every ranked claim is cross-examined before it is shown.

Three layers, stated honestly:
  1. a learned precedent model (the engine's logistic ranker) scores orphan-GPCR hypotheses against documented cases;
  2. evidence rules (this module) test each claim for independent sources, review quality, thin evidence, and
     contradiction with gene-level constraint;
  3. an optional language-model cross-check (engine.llm_debate) that may only cite the evidence shown and can only
     make a verdict more cautious.
The verdict is holds up / weakened / contested, with the specific counter-arguments listed.
"""
from __future__ import annotations

from typing import List

from .adapters import Bundle
from .engine.critic import verdict_from
from .evidence import Claim, has_proof


def _c(check: str, severity: str, text: str, evidence: str) -> dict:
    return {"check": check, "severity": severity, "text": text, "evidence": evidence}


def validate(claim: Claim, b: Bundle) -> Claim:
    """Attach counter-arguments and a verdict. Never raises; never upgrades a claim."""
    counters: List[dict] = []
    if not has_proof(claim):
        counters.append(_c("no_proof", "major", "No proof attached, so this should not be shown.", "evidence policy"))
    else:
        indep = {p.source.split(" (")[0] for p in claim.proofs if p.kind in ("data", "literature")}
        if len(indep) <= 1 and claim.kind == "data":
            counters.append(_c("single_source", "minor", f"Rests on one source only ({', '.join(sorted(indep)) or 'none'}); nothing independent corroborates it.", "proof list"))
        if claim.kind in ("rule", "inference"):
            counters.append(_c("not_measured", "minor", "This follows from a rule applied to data; it was not directly measured for this protein.", claim.basis[:140]))
        n = claim.tags.get("n_supporting")
        if isinstance(n, int) and n < 3:
            counters.append(_c("thin_evidence", "minor", f"Only {n} supporting record(s).", "tags"))
        stars = claim.tags.get("max_stars")
        if isinstance(stars, int) and stars <= 1 and claim.tags.get("domain") == "clinvar":
            counters.append(_c("low_review", "minor", f"Best ClinVar review status is {stars} star(s): single submitter or conflicting, not expert-reviewed.", "ClinVar review status"))
        if claim.tags.get("mechanism") == "loss-of-function":
            pli, loeuf = b.constraint.get("pLI"), b.constraint.get("oe_lof_upper")
            if pli is not None and loeuf is not None and pli < 0.1 and loeuf > 0.6:
                counters.append(_c("constraint_mismatch", "major", f"Claims loss of function, but gnomAD shows the gene tolerates LoF (pLI {pli:.2f}, LOEUF {loeuf:.2f}).", "gnomAD constraint"))
        conf = sum(v.significance == "conflicting" for v in b.variants)
        if claim.tags.get("domain") == "clinvar" and b.variants and conf / len(b.variants) > 0.2:
            counters.append(_c("conflicting_interpretations", "minor", f"{conf} of {len(b.variants)} ClinVar entries have conflicting interpretations.", "ClinVar"))
    claim.counters = (claim.counters or []) + counters
    # a missing proof or a contradiction with gene-level constraint is disqualifying on its own
    hard = any(c["check"] in ("no_proof", "constraint_mismatch") for c in claim.counters)
    claim.verdict = "contested" if hard else verdict_from(claim.counters)
    return claim


def validate_all(claims: List[Claim], b: Bundle) -> List[Claim]:
    return [validate(c, b) for c in claims]
