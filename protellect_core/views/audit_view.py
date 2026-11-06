"""Evidence audit: how far to trust each receptor-disease link before committing bench time. See protellect_core/audit.py for the rules."""
from __future__ import annotations

import streamlit as st

from ..audit import EXAMPLE_A7_CSV, TEMPLATE_CSV, audit_markdown, audit_target, lines_from_csv, your_experiment_line
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


def _card(au) -> None:
    with st.container(border=True):
        st.markdown(f"**{au.gene}** <span style='color:{_COLOR[au.tier]};font-weight:700'> {au.tier}</span>", unsafe_allow_html=True)
        st.caption(" ".join(au.reasons))
        for f in au.flags:
            st.markdown(f"- **{f['flag'].replace('_', ' ')}.** {f['why']} *Cheapest check:* {f['test']}")
        if au.to_raise:
            st.markdown("**What would raise confidence:** " + " ".join(au.to_raise))
        st.markdown(f"**Cheapest experiment to separate real from false:** {au.cheapest_test}")


def _fill_example() -> None:
    st.session_state["any_gene"] = "CHRNA7"
    st.session_state["any_disease"] = "chronic neuropathic pain"
    st.session_state["any_csv_text"] = EXAMPLE_A7_CSV


def render_any_target(expanded: bool = False) -> None:
    """Audit any target, GPCR or not. The tool looks nothing up: you paste evidence lines, each with a named source, and it applies the written rules."""
    with st.expander("Check any target: is its link to a disease well supported? (works for non-GPCRs too)", expanded=expanded):
        st.caption("You supply the evidence lines (one per finding, each with a named source). The audit counts the studies, kinds of evidence and anything arguing against, "
                   "and shows the tier, red flags and the cheapest check. It does not search the literature, cannot tell whether two studies come from the same group, and the tier is "
                   "not a chance of success. The tier depends on how you label each line's strength and the tags you give it.")
        st.button("Load a worked example (alpha7 nicotinic receptor and chronic neuropathic pain)", on_click=_fill_example, key="any_example")
        c1, c2 = st.columns(2)
        gene = c1.text_input("Gene symbol", key="any_gene", placeholder="e.g. CHRNA7")
        disease = c2.text_input("Disease or condition", key="any_disease", placeholder="e.g. chronic neuropathic pain")
        up = st.file_uploader("Evidence lines (CSV)", type=["csv"], key="any_csv_up")
        if up is not None:
            st.session_state["any_csv_text"] = up.getvalue().decode("utf-8", errors="replace")
        text = st.text_area("Evidence lines (CSV text)", key="any_csv_text", height=160,
                            help="Columns: gene, disease, kind, direction, strength, summary, source, url, study_id, tags")
        st.download_button("Download the evidence template", TEMPLATE_CSV, "protellect_evidence_template.csv", "text/csv", key="any_tpl")
        if not (gene or "").strip():
            return
        try:
            lines = lines_from_csv(text) if (text or "").strip() else []
        except ValueError as e:
            st.error(f"Could not read the evidence lines: {e}")
            return
        au = audit_target(gene.strip(), (disease or "").strip(), lines)
        _card(au)
        if au.lines:
            st.dataframe([{"Kind": l.kind, "Direction": l.direction, "Strength": l.strength, "What it shows": l.summary, "Source": l.source} for l in au.lines],
                         hide_index=True, use_container_width=True)
        st.download_button("Download this audit (markdown)", audit_markdown(au), f"protellect_audit_{au.gene}.md", key="any_dl")
