"""Unknowns: variants of uncertain significance and the other 'unknown' items, each with ranked hypotheses and how to test them."""
from __future__ import annotations

import streamlit as st

from ..adapters import Variant
from ..topology import motifs as tm_motifs, topology as tm_topology
from ..unknowns import WEIGHTS, is_unknown, plddt_map, protein_unknowns, variant_hypotheses, vus_board
from .common import get_pockets, render_claims
from .shell import coupling_info

_NOTE = ("These are hypotheses from rules applied to this protein's own data, ranked by an evidence score built from design-choice weights (listed below). "
         "They are not a pathogenicity call and cannot reclassify a variant: under ACMG/AMP only functional and genetic evidence does that (Richards 2015). Each one says what to run, what each result would mean, and the controls.")


def _ctx(a):
    b = a.b
    segs = tm_topology(b)
    try:
        coupling = (coupling_info(a) or ("", ""))[0] or ""
    except Exception:
        coupling = ""
    try:
        pockets = get_pockets(b) or []
    except Exception:
        pockets = []
    return segs, (tm_motifs(b, segs) if segs else []), pockets, bool(a.orphan), coupling


def weights_table() -> None:
    with st.expander("How the evidence score is built (design choices, not fitted)"):
        rows = [{"Hypothesis": k, "Trigger": t, "Weight": w, "Why": why} for k, items in WEIGHTS.items() for t, w, why in items]
        st.dataframe(rows, hide_index=True)
        st.caption("A hypothesis appears only if at least one of its triggers is met by real data. Weights rank hypotheses against each other for one variant; they are not probabilities and are not used anywhere else.")


def render_unknown_variant(a, v: Variant, prefix: str = "uv") -> None:
    b = a.b
    segs, motifs, pockets, orphan, coupling = _ctx(a)
    hs = variant_hypotheses(v, b, segs, motifs, pockets, orphan, coupling, plddt_map(b.pdb))
    st.markdown(f"##### This variant is of unknown significance: what it might be, and how to find out")
    st.caption(_NOTE)
    render_claims(hs, b, f"{prefix}_{v.pos}", limit=6, empty="No hypothesis could be backed by the data retrieved.", how_label="Test it")
    weights_table()


def render_vus_board(a) -> None:
    b = a.b
    unk = [v for v in b.variants if is_unknown(v) and v.pos]
    st.markdown("#### Variants of unknown significance, ranked by what the data can say")
    if not unk:
        st.caption("No variants of uncertain, conflicting or unclassified significance with a position were retrieved for this protein.")
        return
    segs, motifs, pockets, orphan, coupling = _ctx(a)
    rows = vus_board(b, segs, motifs, pockets, orphan, coupling, limit=60)
    st.caption(f"{len(unk)} variants are unknown (uncertain, conflicting or unclassified). Each row shows its leading hypothesis and the first thing to test. The score only ranks hypotheses against each other; a high score means more data points agree, not that the variant is pathogenic.")
    st.dataframe([{"Variant": r["variant"].name[-44:], "Residue": r["variant"].pos, "Region": r["region"], "Class": r["variant"].significance,
                   "AlphaMissense": None if r["variant"].am_score is None else round(r["variant"].am_score, 2),
                   "Leading hypothesis": r["claim"].text, "Evidence score": r["score"], "First test": (r["claim"].how[0] if r["claim"].how else "")} for r in rows], hide_index=True)
    labels = [f"{r['variant'].pos} · {r['variant'].name[-40:]} · {r['variant'].significance}" for r in rows]
    pick = st.selectbox("Show all hypotheses for", labels, key="vb_pick")
    render_unknown_variant(a, rows[labels.index(pick)]["variant"], "vb")


def render_protein_unknowns(a) -> None:
    b = a.b
    segs, motifs, pockets, orphan, coupling = _ctx(a)
    claims = protein_unknowns(b, segs, pockets, orphan, coupling)
    st.markdown("#### What is still unknown about this protein, and how to test it")
    st.caption("Each item is something the loaded data is silent or 'Unknown' about. A hypothesis is offered only when real data from this protein supports it (stated in the proof box), together with the test and what each result would mean.")
    if a.orphan:
        st.caption(f"{b.gene} is an orphan receptor: its unknown ligand is handled on the Overview tab, with ranked ligand-class hypotheses and the assay for each.")
    render_claims(claims, b, "pu", empty="Nothing in the loaded data is flagged unknown with enough evidence to build a hypothesis.", how_label="Test it")
