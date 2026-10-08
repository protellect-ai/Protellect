"""One analysis per run, shared by every tab so they all see the same facts."""
from __future__ import annotations

from dataclasses import dataclass, field

import streamlit as st
from typing import List, Optional

from ..adapters import Bundle, build_bundle
from ..analysis import body_systems, defect_claims, possibility, rank_diseases, strategy_options
from ..context import Context
from ..engine import InputError, parse_experiment
from ..evidence import Claim
from ..routing import Priority, priorities
from .common import get_engine
from .hypotheses import hypothesis_claims, is_orphan, run_hypotheses


@dataclass
class Analysis:
    b: Bundle
    ctx: Context
    engine: object
    summary: Optional[object] = None
    source: str = ""
    orphan: bool = False
    poss: Optional[dict] = None
    defects: List[Claim] = field(default_factory=list)
    diseases: List[Claim] = field(default_factory=list)
    systems: List[Claim] = field(default_factory=list)
    strategies: List[Claim] = field(default_factory=list)
    hyp_claims: List[Claim] = field(default_factory=list)
    priorities: List[Priority] = field(default_factory=list)
    csv_top: list = field(default_factory=list)
    couplings: dict = field(default_factory=dict)


def build_analysis(ss, *, diseases=None, is_gpcr=None, gpcr_class: str = "", couplings=None) -> Analysis:
    st.session_state["_audit_n"] = 0          # widget keys inside the data audit must be the same on every rerun
    b = build_bundle(ss, diseases=diseases, is_gpcr=is_gpcr, gpcr_class=gpcr_class)
    ctx = Context.from_session(ss)
    eng = get_engine()
    summary, source = run_hypotheses(ss, b, ctx, eng)
    a = Analysis(b=b, ctx=ctx, engine=eng, summary=summary, source=source, orphan=b.loaded and is_orphan(eng, b.gene))
    a.couplings = couplings if isinstance(couplings, dict) else {}
    a.diseases = rank_diseases(b, ctx)
    a.defects = defect_claims(b)
    a.poss = possibility(b) if b.loaded else None
    a.systems = body_systems(b, a.diseases)
    a.strategies = strategy_options(b, a.defects, a.orphan) if b.loaded else []
    a.hyp_claims = hypothesis_claims(eng, summary, b.gene if source == "the protein you searched" else None)
    df = ss.get("csv_df")
    if df is not None and ss.get("csv_triage_active"):
        try:
            parsed = parse_experiment(df)
            top = parsed.reindex(parsed["effect"].abs().sort_values(ascending=False).index).head(5)
            a.csv_top = [(r.gene, float(r.effect)) for r in top.itertuples()]
        except InputError:
            a.csv_top = []
    n_orph = sum(v["status"] == "orphan" for v in eng.registry.values())
    a.priorities = priorities(b, a.poss, a.defects, summary if source == "your experiment" else None, a.csv_top or None, n_orph)
    return a
