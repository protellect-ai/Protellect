"""Evidence audit: how far to trust each receptor-disease link before committing bench time. See protellect_core/audit.py for the rules."""
from __future__ import annotations

import streamlit as st

from ..audit import TEMPLATE_CSV, audit_markdown, audit_target, lines_from_csv, your_experiment_line
from .shell import Analysis

_COLOR = {"Strong": "#34d399", "Mixed": "#fbbf24", "Weak": "#fb923c", "Contradicted": "#f87171", "Unchecked": "#94a3b8"}


def render_audit(a: Analysis) -> None:
    s = a.summary
    if s is None or not s.results:
        return
    st.markdown("#### Evidence audit: should you trust the link?")
    st.caption("Before spending months on a receptor, check how much independent evidence ties it to your disease. Add evidence lines from papers (a named source for each) "
               "and the audit applies written rules: it never looks anything up or invents a source. With only your own experiment, every receptor is Weak by design: one source.")
    disease = st.text_input("Disease or condition", value=st.session_state.get("ctx_disease", "") or "", key="audit_disease")
    c1, c2 = st.columns([3, 2])
    up = c1.file_uploader("Evidence lines (CSV, optional)", type=["csv"], key="audit_csv")
    c2.download_button("Download the evidence template", TEMPLATE_CSV, "protellect_evidence_template.csv", "text/csv", key="audit_tpl")
    lines = []
    if up is not None:
        try:
            lines = lines_from_csv(up.getvalue().decode("utf-8", errors="replace"))
            st.caption(f"Read {len(lines)} evidence line(s).")
        except ValueError as e:
            st.error(f"Could not read the evidence file: {e}")
    md_all = []
    focus = (getattr(a, "focus", None) or "").upper()
    compact = bool(getattr(a, "focus_options", None)) and not focus      # many receptors and none chosen: one line each, details follow the chosen protein
    if compact:
        st.caption("Choose a protein under 'Show details for' to see its red flags and the cheapest check.")
    for r in s.results:
        if focus and r.gene.upper() != focus:
            continue
        own = []
        if r.effect is not None and r.effect == r.effect:
            own = [your_experiment_line(r.gene, disease, r.effect, r.effect_type, r.significance)]
        au = audit_target(r.gene, disease, [l for l in lines if l.gene.upper() == r.gene.upper()] + own)
        md_all.append(audit_markdown(au))
        if compact:
            st.markdown(f"- {r.gene}: <span style='color:{_COLOR[au.tier]};font-weight:700'>{au.tier}</span>", unsafe_allow_html=True)
            continue
        with st.container(border=True):
            st.markdown(f"**{r.gene}** <span style='color:{_COLOR[au.tier]};font-weight:700'> {au.tier}</span>", unsafe_allow_html=True)
            st.caption(" ".join(au.reasons))
            for f in au.flags:
                st.markdown(f"- **{f['flag'].replace('_', ' ')}.** {f['why']} *Cheapest check:* {f['test']}")
            if au.to_raise:
                st.markdown("**What would raise confidence:** " + " ".join(au.to_raise))
            st.markdown(f"**Cheapest experiment to separate real from false:** {au.cheapest_test}")
    st.download_button("Download the audit (markdown)", "# Evidence audit\n\n" + "\n\n".join(md_all), "protellect_evidence_audit.md", key="audit_dl")
