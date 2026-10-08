"""Claims, proofs, and the truth gate.

Policy: nothing is displayed as a finding unless it carries at least one Proof naming a real source. Statements that come
from a rule or an inference must say so (kind) and state their basis. Anything without proof is WITHHELD and counted, never
shown. This is the structural answer to hallucinated text: the UI cannot render an unsupported claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Proof:
    source: str            # e.g. "ClinVar", "UniProt", "gnomAD", "AlphaMissense (Cheng 2023)"
    detail: str            # the specific record / number / citation
    url: str = ""
    kind: str = "data"     # data | literature | rule


@dataclass
class Claim:
    text: str
    proofs: List[Proof] = field(default_factory=list)
    kind: str = "data"                 # data (from fetched records) | rule (a stated rule applied to data) | inference
    basis: str = ""                    # required for rule/inference: why this follows from the proofs
    score: float = 0.0                 # used only for ranking within a list
    tags: Dict[str, object] = field(default_factory=dict)
    verdict: str = "unchecked"         # ML validation: holds up | weakened | contested | unchecked
    counters: List[dict] = field(default_factory=list)
    how: List[str] = field(default_factory=list)   # "how to go about it" steps (themselves rules, with the basis above)

    @property
    def sources(self) -> List[str]:
        return sorted({p.source for p in self.proofs if p.kind != "rule"})


def has_proof(c: Claim) -> bool:
    if not c.proofs or any(not p.source or not p.detail for p in c.proofs):
        return False
    if c.kind in ("rule", "inference") and not c.basis:
        return False
    if c.kind in ("rule", "inference") and not any(p.kind != "rule" for p in c.proofs):
        return False                   # a rule must be triggered by at least one real data point
    return True


def truth_gate(claims: List[Claim]) -> Tuple[List[Claim], List[Claim]]:
    shown = [c for c in claims if has_proof(c)]
    withheld = [c for c in claims if not has_proof(c)]
    return shown, withheld
