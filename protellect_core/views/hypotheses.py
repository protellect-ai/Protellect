"""Bridge: run the orphan-GPCR hypothesis engine on the loaded experiment or protein and express results as Claims."""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

from ..adapters import Bundle
from ..context import Context
from ..evidence import Claim, Proof
from ..engine import InputError, lookup_frame, parse_experiment
from ..engine.registry import normalize_tissues


def is_orphan(engine, gene: str) -> bool:
    return engine.registry.get((gene or "").upper(), {}).get("status") == "orphan"


def run_hypotheses(ss, b: Bundle, ctx: Context, engine) -> Tuple[Optional[object], str]:
    extra = {}
    if b.loaded and b.tissue_text:
        t = normalize_tissues([b.tissue_text])
        if t:
            extra = {b.gene.upper(): {"tissues": t, "source": "UniProt tissue specificity"}}
    df = ss.get("csv_df")
    if df is not None and ss.get("csv_triage_active"):
        try:
            return engine.run(parse_experiment(df, None, 0.05), ctx.engine_ctx(), extra_annotations=extra), "your experiment"
        except InputError:
            pass
    if b.loaded and is_orphan(engine, b.gene):
        return engine.run(lookup_frame(b.gene), ctx.engine_ctx(), extra_annotations=extra), "the protein you searched"
    return None, ""


def hypothesis_claims(engine, summary, gene: Optional[str] = None) -> List[Claim]:
    if summary is None:
        return []
    cases = {c.id: c for c in engine.cases}
    out: List[Claim] = []
    for r in summary.results:
        if gene and r.gene.upper() != gene.upper():
            continue
        for h in r.hypotheses:
            proofs = [Proof("Receptor registry", f"{r.gene} is listed as an orphan GPCR (no confirmed ligand)", "https://www.guidetopharmacology.org/")]
            if not (isinstance(r.effect, float) and math.isnan(r.effect)):
                proofs.append(Proof("Your experiment", f"{r.effect_type} {r.effect:.2f}" + (f", p = {r.significance:.3g}" if r.significance is not None else "")))
            for p in h.precedents:
                c = cases.get(p["case"])
                if c:
                    proofs.append(Proof("Documented deorphanisation (case library, not yet expert-verified)", f"{c.gene}: {c.ligand}; later: {c.later_outcome}; {', '.join(c.citations)}", kind="literature"))
            claim = Claim(text=f"{r.gene}: {h.statement}", proofs=proofs, kind="inference",
                          basis="Analogy to documented deorphanisation precedents that share tissue context, family cluster or neighbours. " + " | ".join(h.rationale),
                          score=h.support, tags={"n_supporting": len(h.precedents), "category": h.category, "support": h.support}, verdict=h.verdict,
                          counters=[{"check": c["check"], "severity": c["severity"], "text": c["text"], "evidence": c.get("evidence", "")} for c in h.counterarguments],
                          how=[h.test_experiment])
            out.append(claim)
    return sorted(out, key=lambda c: -c.score)
