"""Display: 'present in your experiment' then 'might mean' (ranked, with justification), and the experiment plan with 'if you see X, it suggests Y'."""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from ..assays import ASSAYS, render_assay, render_assay_inline
from ..dossier import Dossier, Hyp, Pattern, build_all, build_dossier, experiment_patterns, experiment_plan
from .shell import Analysis


def _hyp_block(h: Hyp, rank: int, key: str) -> None:
    comp = " · ".join(f"{k} {v}" for k, v in h.components.items())
    st.markdown(f"**{rank}. {h.statement}**  \n<span style='color:#7dd3fc;font-size:.8rem'>relative support {h.score:.2f}</span>" + (f" <span style='color:#6b8aa3;font-size:.75rem'>({comp})</span>" if comp else ""), unsafe_allow_html=True)
    for w in h.why:
        st.markdown(f"<div style='margin-left:1rem;color:#b7c9db;font-size:.84rem'>+ {html.escape(w)}</div>", unsafe_allow_html=True)
    for x in h.against:
        st.markdown(f"<div style='margin-left:1rem;color:#fbbf24;font-size:.84rem'>- {html.escape(x)}</div>", unsafe_allow_html=True)


def _pack(d: Dossier, prefix: str, expanded: bool) -> None:
    with st.container(border=True):
        st.markdown(f"### {d.gene} <span style='color:#fbbf24;font-size:.8rem'>orphan GPCR</span>", unsafe_allow_html=True)
        st.markdown("**Present in your experiment**")
        for e in d.present[:6]:
            st.markdown(f"<div style='margin-left:.5rem;font-size:.86rem'>• <b>{html.escape(e.label)}:</b> {html.escape(e.detail)} <span style='color:#6b8aa3'>({html.escape(e.source)})</span></div>", unsafe_allow_html=True)
        if len(d.present) > 6:
            st.caption(f"{len(d.present) - 6} more observations are in the full evidence below.")
        st.markdown("**It might mean** (best-supported answer to each question)")
        for q in d.questions:
            top = q.hyps[0] if q.hyps else None
            if top is None:
                st.markdown(f"<div style='margin-left:.5rem;font-size:.86rem'><b>{html.escape(q.title)}</b> {html.escape(q.note)}</div>", unsafe_allow_html=True)
                continue
            because = html.escape(top.why[0]) if top.why else ""
            st.markdown(f"<div style='margin-left:.5rem;font-size:.86rem'><b>{html.escape(q.title)}</b> {html.escape(top.statement)} <span style='color:#7dd3fc'>(support {top.score:.2f})</span><br>"
                        f"<span style='color:#9fb6cc'>because {because}</span></div>", unsafe_allow_html=True)
            if q.note:
                st.caption(q.note[:240])
        with st.expander(f"Full ranking, counter-evidence and how to test it: {d.gene}", expanded=expanded):
            for qi, q in enumerate(d.questions):
                st.markdown(f"##### {q.title}")
                for i, h in enumerate(q.hyps[:3], 1):
                    _hyp_block(h, i, f"{prefix}{d.gene}{qi}{i}")
                top = q.hyps[0] if q.hyps else None
                if top is not None and top.assays and top.assays[0] in ASSAYS:
                    render_assay_inline(st, top.assays[0], top.expect.get(top.assays[0]))
                    st.divider()


def render_dossiers(a: Analysis, prefix: str = "dos", full: int = 4, limit: int = 12) -> None:
    alt = st.session_state.get("alterations")
    ds = build_all(a, alt, limit)
    if a.gpcrome is None and a.summary is None:
        return
    if not ds:
        if a.summary is not None and a.summary.n_orphan:
            st.info("Your table has orphan receptors. Add an expression matrix (cell types or conditions as columns) to see where each is expressed, what it tracks and what it probably couples to. The precedent hypotheses are listed below.")
        return
    pats = experiment_patterns(a, ds, alt)
    if pats:
        st.markdown("#### What the experiment says as a whole")
        for i, p in enumerate(pats[:3]):
            with st.container(border=True):
                st.markdown(f"**{p.title}**")
                for e in p.present:
                    st.markdown(f"<div style='margin-left:.5rem;font-size:.86rem'>• <b>Present in your experiment:</b> {html.escape(e.detail)} <span style='color:#6b8aa3'>({html.escape(e.source)})</span></div>", unsafe_allow_html=True)
                ranked = sorted(p.hyps, key=lambda x: -x.score)
                st.markdown("**It might mean** (ranked): " + " &nbsp;|&nbsp; ".join(f"{j}. {html.escape(h.statement)}" for j, h in enumerate(ranked, 1)), unsafe_allow_html=True)
                with st.expander("Justification, counter-evidence and how to test it"):
                    for j, h in enumerate(ranked, 1):
                        _hyp_block(h, j, f"{prefix}p{i}{j}")
                    top = ranked[0]
                    if top.assays and top.assays[0] in ASSAYS:
                        st.divider()
                        render_assay_inline(st, top.assays[0], None)
        if len(pats) > 3:
            with st.expander(f"{len(pats) - 3} more pattern(s)"):
                for p in pats[3:]:
                    st.markdown(f"**{p.title}**: " + "; ".join(e.detail for e in p.present))
                    st.markdown(" | ".join(f"{j}. {h.statement}" for j, h in enumerate(sorted(p.hyps, key=lambda x: -x.score), 1)))
    st.markdown(f"#### Orphan GPCRs in your experiment ({len(ds)})")
    st.caption("Ranked by effect size, significance and context specificity from your own data. Details are shown for one protein at a time: search it in the sidebar or pick it below.")
    sig = {}
    if a.summary is not None:
        try:
            from ..engine.report import results_table
            sig = {r["Receptor"]: r["Your signal"] for _, r in results_table(a.summary).iterrows()}
        except Exception:
            sig = {}
    st.dataframe(pd.DataFrame([{"Rank": i, "Protein": d.gene, "Your signal": sig.get(d.gene, ""), "Expressed in": ", ".join(d.contexts[:2])} for i, d in enumerate(ds, 1)]), hide_index=True)
    if a.focus:
        dd = next((d for d in ds if d.gene == a.focus), None) or build_dossier(a, a.focus, alt)
        if dd:
            _pack(dd, prefix, True)
        else:
            st.info(f"Your data has too little on {a.focus} to build an evidence summary.")
    else:
        st.info("Pick a protein (Show details for, above) or search one in the sidebar to see what your data says about it, what it might mean, and the experiment that tests it.")


def render_plan(a: Analysis, prefix: str = "plan", only: str = "") -> bool:
    """The experiment plan, straight from the uploaded experiment. Returns False when there is nothing to plan from."""
    alt = st.session_state.get("alterations")
    ds = build_all(a, alt, 12)
    pats = experiment_patterns(a, ds, alt) if ds else []
    plan = experiment_plan(a, ds, pats)
    if not plan:
        return False
    if only:
        plan = [it for it in plan if only in (it.targets or [])]
        if not plan:
            st.info(f"None of the planned experiments from your table is specific to {only}.")
            return True
    st.markdown("#### Next experiments, in the order to run them" + (f" ({only})" if only else ""))
    st.caption("Built from your own experiment" + (f", for {only} only." if only else ".") + " Each step says which receptors it covers, why, and how to read the result.")
    for n, it in enumerate(plan, 1):
        with st.container(border=True):
            st.markdown(f"**{n}. {it.title}**")
            if it.targets:
                st.caption("Receptors: " + ", ".join(it.targets))
            for w in it.why[:5]:
                st.markdown(f"<div style='margin-left:.5rem;font-size:.85rem;color:#b7c9db'>• {html.escape(w)}</div>", unsafe_allow_html=True)
            ex = {g: v for g, v in it.expect.items() if (not only or g == only)} if it.expect else {}
            if ex:
                st.markdown("<div style='margin-left:.5rem;font-size:.85rem;color:#7dd3fc'>If the prediction is right you expect: " + html.escape("; ".join(f"{g}: {v}" for g, v in ex.items())) + "</div>", unsafe_allow_html=True)
            first = next(iter(ex.values()), None) if ex else None
            render_assay(st, it.assay, first)
    return True
