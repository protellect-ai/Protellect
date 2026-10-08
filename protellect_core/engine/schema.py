"""Shared data structures and vocabularies for the Protellect hypothesis engine."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

# Coarse vocabularies. Expand these as the case library grows.
LIGAND_CLASSES = ("fatty acid", "lipid mediator", "organic acid", "peptide", "nucleotide", "ion / proton", "amine")
COUPLINGS = ("Gq", "Gi", "Gs")
TISSUE_VOCAB = (
    "pancreas", "adipose", "gut", "immune", "brain", "kidney", "liver",
    "heart", "vasculature", "placenta", "muscle", "lung", "endocrine",
)


@dataclass
class Case:
    """One historical deorphanization case.

    IMPORTANT: `tissues`, `neighbors` and `cluster` must contain ONLY what was
    known BEFORE `resolution_year`. That is what keeps the benchmark honest.
    """
    id: str
    gene: str
    resolution_year: int
    ligand: str
    ligand_class: str
    coupling: str
    cluster: str
    neighbors: List[str]
    tissues: List[str]
    later_outcome: str
    citations: List[str]
    verified: bool = False
    contested: bool = False
    notes: str = ""


@dataclass
class QueryProfile:
    """What we know about a receptor we are generating hypotheses for."""
    id: str
    names: List[str] = field(default_factory=list)
    tissues: List[str] = field(default_factory=list)
    neighbors: List[str] = field(default_factory=list)
    cluster: str = ""
    tissue_sources: Dict[str, str] = field(default_factory=dict)


@dataclass
class Hypothesis:
    category: str            # "ligand-class" | "signaling" | "disease-association"
    statement: str
    value: str
    support: float           # relative support among this receptor's candidates (0-1). NOT a probability of being correct.
    precedent_strength: float  # strongest single precedent match (0-1)
    rationale: List[str]
    precedents: List[dict]
    evidence_axes: Dict[str, str]
    test_experiment: str
    flags: Dict[str, str]
    caveats: List[str]
    counterarguments: List[dict] = field(default_factory=list)
    verdict: str = "unchecked"          # "holds up" | "weakened" | "contested" | "unchecked"
    adjusted_support: float = 0.0       # support after critic penalties (display/optional re-rank)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReceptorResult:
    gene: str
    status: str              # "hypotheses" | "insufficient_evidence"
    effect: Optional[float]
    effect_type: str
    significance: Optional[float]
    hypotheses: List[Hypothesis]
    message: str = ""
