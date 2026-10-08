"""One analysis per run, shared by every tab so they all see the same facts."""
from __future__ import annotations

from dataclasses import dataclass, field

import streamlit as st
from typing import List, Optional

from ..adapters import Bundle, build_bundle
from ..analysis import body_systems, defect_claims, possibility, rank_diseases, strategy_options
from ..context import Context
from ..contexts import matrix_tissue_annotations
from ..engine import InputError, parse_experiment
from ..engine.io_parsers import parse_matrix
from ..gpcrome import GPCRomeResult, load_couplings
from ..workbench import Workbench, build as build_workbench
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
    gpcrome: Optional[GPCRomeResult] = None
    wb: Optional[Workbench] = None
    matrix: Optional[object] = None
    gpcrome_error: str = ""
    matrix_tissues: dict = field(default_factory=dict)


@st.cache_data(show_spinner=False)
def _workbench_cached(matrix, registry, coupling, coupling_source, de_effect, de_sig, fg, rank_source, metric, comparison, extra_programs):
    return build_workbench(matrix, registry, coupling, coupling_source, de_effect=de_effect, de_sig=de_sig, fg=fg, rank_source=rank_source, metric=metric, comparison=comparison, extra_programs=extra_programs)


def get_couplings(ss):
    """The coupling table in use: the user's (uploaded) one if present, else the built-in seed, always with its source stated."""
    t = ss.get("coupling_table")
    if isinstance(t, dict) and t:
        return t, ss.get("coupling_source") or "uploaded table"
    seed = load_couplings()
    return seed, f"built-in seed table, curated from memory and NOT verified ({len(seed)} receptors)"


def _custom_program(ss):
    genes = [x.strip().upper() for x in str(ss.get("gp_custom_genes", "")).replace("\n", ",").replace(";", ",").split(",") if x.strip()]
    return {str(ss.get("gp_custom_name") or "Custom program"): genes} if len(genes) >= 3 else {}


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
    gm = ss.get("gpcrome_matrix")
    if gm is not None:
        try:
            matrix = parse_matrix(gm)
            coupling, csrc = get_couplings(ss)
            de_eff = de_sig = None
            dfx = ss.get("csv_df")
            if dfx is not None and ss.get("csv_triage_active"):
                try:
                    parsed = parse_experiment(dfx)
                    de_eff, de_sig = parsed.set_index("gene")["effect"], parsed.set_index("gene")["significance"]
                except InputError:
                    pass
            fg = [c for c in (ss.get("gp_fg") or []) if c in matrix.columns]
            a.wb = _workbench_cached(matrix, eng.registry, coupling, csrc, de_eff, de_sig, fg, ss.get("gp_rank_source", "auto"), ss.get("gp_metric", "log2fc"), ctx.comparison, _custom_program(ss))
            a.gpcrome, a.matrix = a.wb.gpcrome, matrix
            a.matrix_tissues = matrix_tissue_annotations(a.gpcrome, matrix)
            if a.summary is not None and source == "your experiment" and a.matrix_tissues:
                try:      # re-run the precedent model so each orphan is matched on where IT is expressed, not on the experiment-wide tissue
                    a.summary = eng.run(parse_experiment(dfx), ctx.engine_ctx(), extra_annotations=a.matrix_tissues)
                    a.hyp_claims = hypothesis_claims(eng, a.summary, None)
                except InputError:
                    pass
            mine = [c for c in a.wb.claims if (not b.loaded) or source != "the protein you searched" or b.gene.upper() in (str(c.tags.get("gene", "")).upper(), str(c.tags.get("receptor", "")).upper()) or b.gene.upper() in [x.upper() for x in c.tags.get("lead", [])]]
            a.hyp_claims = sorted(a.hyp_claims + mine, key=lambda c: -c.score)
        except InputError as e:
            a.gpcrome_error = str(e)
    df = ss.get("csv_df")
    if df is not None and ss.get("csv_triage_active"):
        try:
            parsed = parse_experiment(df)
            top = parsed.reindex(parsed["effect"].abs().sort_values(ascending=False).index).head(5)
            a.csv_top = [(r.gene, float(r.effect)) for r in top.itertuples()]
        except InputError:
            a.csv_top = []
    n_orph = sum(v["status"] == "orphan" for v in eng.registry.values())
    a.priorities = priorities(b, a.poss, a.defects, summary if source == "your experiment" else None, a.csv_top or None, n_orph, a.gpcrome, a.wb)
    return a


def coupling_info(a: "Analysis"):
    """(class, source) for the loaded receptor. Recorded data first, then the coupling table (labelled), then co-expression prediction, else unknown."""
    b = a.b
    rec = next((k for k in a.couplings if isinstance(k, str) and k[:1] == "G"), "")
    if rec:
        key = {"Gs": "Gs", "Gi/o": "Gi", "Gi": "Gi", "Gq/11": "Gq", "Gq": "Gq", "G12/13": "G12", "G12": "G12"}.get(rec, "")
        return key or rec, "recorded in GPCRdb"
    coupling, src = get_couplings(st.session_state)
    if b.gene.upper() in coupling:
        return coupling[b.gene.upper()], ("uploaded table" if st.session_state.get("coupling_table") else "curated seed table, unverified")
    if a.gpcrome is not None and len(a.gpcrome.orphans):
        row = a.gpcrome.orphans[a.gpcrome.orphans["GPCR"] == b.gene.upper()]
        if len(row) and row.iloc[0]["Predicted coupling"] not in ("no supported call", ""):
            return row.iloc[0]["Predicted coupling"], "predicted by co-expression in your matrix"
    return "", ""
