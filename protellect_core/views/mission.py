"""The top of the Overview: the goal, where you are, and the one next step. Plus what this tool does that a standard pipeline does not."""
from __future__ import annotations

import html

import streamlit as st

from ..dossier import build_all, experiment_plan
from .shell import Analysis

GOAL = "Goal: work out what the orphan GPCRs in your experiment do and what they bind, and decide which one to test first."

NICHE = [
    ("Finds the orphans for you.", "It reads the receptor list (IUPHAR) against your results and pulls out the GPCRs nobody has characterised, instead of treating them as ordinary rows."),
    ("Reads each orphan in its own context.", "Each orphan is matched to documented deorphanisations using the cell types where it is actually expressed in your matrix, not one tissue label for the whole experiment."),
    ("Combines three independent lines of evidence.", "Documented precedent, co-expression with characterised receptors (tested on your own data first), and what receptor families its neighbours belong to. Where they disagree it says so."),
    ("Ends in an experiment with a decoding table.", "Every hypothesis names the assay, and every assay lists what you might see, what it would suggest and what to do next."),
    ("Tests itself and says how well.", "A blind test hides a known receptor's ligand and checks whether the model would have found it. The current leave-one-out result is shown, and it is modest."),
]
NOT = "It will not confirm a ligand or function (only a wet-lab experiment does), give a probability of success, or show a statement without a source."


def _chip(n: int, title: str, body: str, state: str) -> str:
    col = {"done": "#22c55e", "now": "#38bdf8", "wait": "#475569"}[state]
    mark = {"done": "DONE", "now": "NEXT", "wait": ""}[state]
    return (f"<div style='border:1px solid {col}88;border-radius:12px;padding:.7rem .85rem;background:#06142a;height:100%'>"
            f"<div style='color:{col};font-weight:800;font-size:.72rem;letter-spacing:.08em'>STEP {n} {mark}</div>"
            f"<div style='color:#e6edf7;font-weight:700;margin:2px 0'>{html.escape(title)}</div><div style='color:#9fb6cc;font-size:.82rem;line-height:1.45'>{body}</div></div>")


def render_mission(a: Analysis) -> None:
    b = a.b
    have = bool(a.summary is not None or a.gpcrome is not None or b.loaded)
    n_orph = (a.summary.n_orphan if a.summary is not None else 0) or (len(a.gpcrome.orphans) if a.gpcrome is not None else 0)
    ds = build_all(a, st.session_state.get("alterations"), 12) if have else []
    plan = experiment_plan(a, ds, []) if (ds or a.summary is not None) else []
    first = plan[0].title if plan else ""
    s1 = "done" if have else "now"
    s2 = ("done" if (ds or n_orph) else "now") if have else "wait"
    s3 = "now" if (have and plan) else "wait"
    st.markdown(f"<div style='color:#e6edf7;font-size:1rem;margin:.2rem 0 .5rem'>{html.escape(GOAL)}</div>", unsafe_allow_html=True)
    c = st.columns(4)
    c[0].markdown(_chip(1, "Give it your experiment", "A differential table (and optionally an expression matrix) in the sidebar, or <b>load the example</b>." if not have else f"Loaded. {n_orph} orphan GPCR(s) found." if n_orph else "Loaded.", s1), unsafe_allow_html=True)
    c[1].markdown(_chip(2, "Read what it says", "Below: what the experiment says as a whole, then each orphan: <b>present in your data</b>, then <b>what it might mean</b>, ranked." if have else "Appears here once an experiment is loaded.", s2), unsafe_allow_html=True)
    c[2].markdown(_chip(3, "Run the first experiment", (f"Experiments tab, step 1: {html.escape(first)}." if first else "The Experiments tab lists them in order, each with how to read the result.") if have else "Comes from your data.", s3), unsafe_allow_html=True)
    c[3].markdown(_chip(4, "Record what happened", "Record the outcome at the bottom of this page. A confirmed result with a citation becomes a new precedent and the model retrains.", "wait"), unsafe_allow_html=True)
    with st.expander("What this does that a standard bioinformatics pipeline does not", expanded=not have):
        st.markdown("A differential-expression and pathway pipeline ends at a ranked gene list. For an uncharacterised receptor that is where the interesting question starts. This tool continues from there:")
        for t, d in NICHE:
            st.markdown(f"- **{t}** {d}")
        st.caption(NOT)
