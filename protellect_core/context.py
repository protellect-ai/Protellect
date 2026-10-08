"""The researcher's microenvironment. One Context object that every view reads, so changing it reshapes the whole workspace.

Honesty rule: tailoring only RE-RANKS and FLAGS where there is a real match between what the researcher entered and
fetched records (a disease name matching an associated disease, a medication matching a recorded drug, a pathway factor
whose canonical genes appear among the protein's interaction partners). It never adds a claim that is not in the data.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Mapping

from .adapters import Bundle
from .analysis import _same_condition
from .evidence import Claim, Proof

FACTORS = {
    "Hypoxia": ["HIF1A", "EPAS1", "VHL", "ARNT", "EGLN1"],
    "Inflammation": ["NFKB1", "RELA", "TNF", "IL6", "IL1B", "STAT3"],
    "Oxidative stress": ["NFE2L2", "KEAP1", "SOD1", "SOD2", "CAT"],
    "DNA damage": ["ATM", "ATR", "CHEK1", "CHEK2", "TP53", "BRCA1"],
    "Angiogenesis": ["VEGFA", "KDR", "FLT1"],
    "Immune checkpoint": ["PDCD1", "CD274", "CTLA4"],
}


def _split(s: str) -> List[str]:
    return [x.strip() for x in re.split(r"[\n,;]", s or "") if x.strip()]


@dataclass
class Context:
    disease: str = ""
    tissue: str = ""
    comparison: str = ""
    model: str = ""
    factors: List[str] = field(default_factory=list)
    age: str = ""
    sex: str = ""
    ancestry: str = ""
    comorbid: List[str] = field(default_factory=list)
    meds: List[str] = field(default_factory=list)
    family: str = ""
    exposures: str = ""

    @classmethod
    def from_session(cls, ss: Mapping) -> "Context":
        g = lambda k, d="": ss.get(k, d) or d
        return cls(disease=str(g("ctx_disease") or g("disease_search")), tissue=str(g("ctx_tissue")), comparison=str(g("ctx_comparison")),
                   model=str(g("ctx_model")), factors=list(g("ctx_factors", [])), age=str(g("pt_age")),
                   sex=str(g("pt_sex")) if g("pt_sex") not in ("?", "—") else "", ancestry=str(g("pt_ethnicity")),
                   comorbid=_split(str(g("pt_comorbid"))), meds=_split(str(g("pt_meds"))), family=str(g("pt_family")), exposures=str(g("pt_envir")))

    @property
    def tailored(self) -> bool:
        return any([self.disease, self.tissue, self.comparison, self.model, self.factors, self.comorbid, self.meds, self.family, self.age, self.ancestry, self.exposures])

    def summary(self) -> str:
        parts = [p for p in (self.disease and f"disease: {self.disease}", self.tissue and f"tissue: {self.tissue}", self.model and f"model: {self.model}",
                             self.factors and "factors: " + ", ".join(self.factors), self.comorbid and "comorbidities: " + ", ".join(self.comorbid),
                             self.meds and "medications: " + ", ".join(self.meds), self.family and "family history given") if p]
        return "; ".join(parts) or "not set"

    def engine_ctx(self) -> dict:
        return {"disease": self.disease, "tissue": self.tissue, "comparison": self.comparison}


def factor_claims(ctx: Context, b: Bundle) -> List[Claim]:
    names = {p.name.upper(): p for p in b.partners} | {b.gene.upper(): None}
    out = []
    for f in ctx.factors:
        hits = [g for g in FACTORS.get(f, []) if g in names]
        if not hits:
            continue
        proofs = [Proof("STRING", f"{b.gene} interacts with {g} (score {names[g].score:.2f})" if names[g] else f"{g} is the protein itself", names[g].url if names[g] else "", "data") for g in hits]
        out.append(Claim(text=f"{f}: {b.gene} connects to canonical {f.lower()} pathway genes ({', '.join(hits)}).", proofs=proofs + [Proof("Pathway marker list", f"canonical {f.lower()} genes", kind="rule")],
                         kind="rule", basis=f"Overlap between a short list of canonical {f.lower()} genes and the protein's STRING interaction partners.", score=len(hits), tags={"n_supporting": len(hits), "factor": f}))
    return out


def medication_claims(ctx: Context, b: Bundle) -> List[Claim]:
    out = []
    for m in ctx.meds:
        for d in b.drugs:
            if m.lower() == d.name.lower() or (len(m) > 4 and m.lower() in d.name.lower()):
                out.append(Claim(text=f"Your listed medication {m} is a recorded {d.kind or 'modulator'} of {b.gene}.", proofs=[Proof(d.source or "DGIdb", f"{d.name} - {d.kind or 'interaction'}", d.url)], kind="data", score=2, tags={"n_supporting": 1}))
                break
    return out


def disease_context_claims(ctx: Context, diseases: List[Claim]) -> List[Claim]:
    """Associated diseases that match the researcher's comorbidities or family history, with inheritance, as flags."""
    out = []
    for d in diseases:
        name = d.tags.get("disease", d.text)
        hit = next((c for c in ctx.comorbid if _same_condition(c, name)), None)
        if hit:
            out.append(Claim(text=f"{name} matches your listed comorbidity '{hit}'.", proofs=d.proofs, kind="data", score=d.score, tags=dict(d.tags)))
        elif ctx.family and d.tags.get("inheritance") and _same_condition(ctx.family, name):
            out.append(Claim(text=f"Your family history mentions {name}, which is {d.tags['inheritance'].lower()} for {name.split()[0]}.", proofs=d.proofs, kind="data", score=d.score, tags=dict(d.tags)))
    return out
