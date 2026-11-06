"""Evidence audit: how far to trust each receptor-disease link before committing bench time. See protellect_core/audit.py for the rules."""
from __future__ import annotations

import streamlit as st

from ..audit_auto import lines_from_bundle, report_markdown
from ..literature import LEVELS, best_ot_row, build_query, comparison, gap_statement, lines_from_literature
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


def render_any_target(expanded: bool = False, bundle=None) -> None:
    """Audit any target, GPCR or not. Lines come from two places, always labelled: data the app already retrieved for a searched protein, and lines you paste or upload.
    The tool does not search the literature for pharmacology papers: you supply those, each with a named source."""
    loaded = bool(bundle is not None and getattr(bundle, "loaded", False))
    if loaded and st.session_state.get("_any_gene_for") != bundle.gene:          # a new protein was searched: follow it
        st.session_state["any_gene"] = bundle.gene
        st.session_state["_any_gene_for"] = bundle.gene
    with st.expander("Check any target: is its link to a disease well supported? (works for non-GPCRs too)", expanded=expanded or loaded):
        st.caption("Two kinds of evidence lines go in. (1) Lines the app builds from data it already retrieved for the protein you searched (ClinVar, UniProt, mouse knockouts, gnomAD), "
                   "each marked as retrieved. A retrieved line only counts as support if its text mentions your disease (a keyword match). (2) Lines you paste, each with a named source. "
                   "The audit does not search the literature, cannot tell whether two studies come from the same group, and the tier is not a chance of success.")
        st.button("Load a worked example (alpha7 nicotinic receptor and chronic neuropathic pain)", on_click=_fill_example, key="any_example")
        c1, c2 = st.columns(2)
        gene = c1.text_input("Gene symbol", key="any_gene", placeholder="e.g. CHRNA7")
        disease = c2.text_input("Disease or condition", key="any_disease", placeholder="e.g. chronic neuropathic pain")
        up = st.file_uploader("Evidence lines (CSV)", type=["csv"], key="any_csv_up")
        if up is not None:
            st.session_state["any_csv_text"] = up.getvalue().decode("utf-8", errors="replace")
        text = st.text_area("Evidence lines you add (CSV text)", key="any_csv_text", height=140,
                            help="Columns: gene, disease, kind, direction, strength, summary, source, url, study_id, tags")
        st.download_button("Download the evidence template", TEMPLATE_CSV, "protellect_evidence_template.csv", "text/csv", key="any_tpl")
        if not (gene or "").strip():
            st.info("Enter a gene symbol, or search a protein in the sidebar.")
            return
        names_in = st.text_input("Other names the literature uses for this target (comma-separated, optional)", key="any_names",
                                 placeholder="e.g. alpha7 nicotinic receptor, a7 nAChR")
        lit_key = (gene.strip().upper(), (disease or "").strip().lower(), (names_in or "").strip().lower())
        if st.button("Search the literature and compare with human genetics", key="any_lit_btn", disabled=not (disease or "").strip()):
            _run_lit_search(gene.strip(), (disease or "").strip(), [n.strip() for n in (names_in or "").split(",") if n.strip()], lit_key)
        lit = st.session_state.get("lit_res")
        lit = lit if lit and lit.get("key") == lit_key else None
        try:
            mine = lines_from_csv(text) if (text or "").strip() else []
        except ValueError as e:
            st.error(f"Could not read the evidence lines: {e}")
            return
        auto = lines_from_bundle(bundle, (disease or "").strip()) if loaded and bundle.gene.upper() == gene.strip().upper() else []
        lit_lines = []
        if lit:
            comp = comparison(lit["records"])
            lit_lines = lines_from_literature(gene.strip(), (disease or "").strip(), comp, lit["ot"], len(lit["records"]))
        auto = auto + lit_lines
        au = audit_target(gene.strip(), (disease or "").strip(), auto + mine)
        _card(au)
        if lit:
            _render_comparison(lit, comp)
        elif (disease or "").strip():
            st.caption("Click the search button to compare mouse and cell evidence with human genetic evidence. It queries Europe PMC and Open Targets when you click.")
        if au.lines:
            origin = {id(l): "retrieved by the app" for l in auto}
            st.dataframe([{"Origin": origin.get(id(l), "you entered"), "Kind": l.kind, "Direction": l.direction, "Strength": l.strength, "What it shows": l.summary, "Source": l.source}
                          for l in au.lines], hide_index=True, use_container_width=True)
        if auto and not mine:
            st.caption("Only retrieved database lines are in this audit. Add pharmacology or literature findings above, each with a named source, to see how they change the tier.")
        st.download_button("Download the report (markdown)", report_markdown(au, auto, bundle if loaded else None, lit=lit), f"protellect_report_{au.gene}.md", key="any_dl")


def _run_lit_search(gene: str, disease: str, names: list, key: tuple) -> None:
    errs, records, ot = [], [], []
    try:
        import protellect_data as _pd
    except Exception:   # noqa: BLE001
        st.session_state["lit_res"] = {"key": key, "records": [], "ot": [], "errors": ["The data module is not available in this environment."], "query": ""}
        return
    q = build_query(gene, names, disease)
    with st.spinner("Searching Europe PMC and Open Targets…"):
        try:
            records = _pd.fetch_europepmc_records(q, 100) or []
        except Exception as e:   # noqa: BLE001
            errs.append(f"Europe PMC: {str(e)[:160]}")
        try:
            ot = _pd.fetch_ot_disease_scores(gene, disease) or []
        except Exception as e:   # noqa: BLE001
            errs.append(f"Open Targets: {str(e)[:160]}")
    st.session_state["lit_res"] = {"key": key, "records": records, "ot": ot, "errors": errs, "query": q}


def _render_comparison(lit: dict, comp: dict) -> None:
    st.markdown("**Cross-comparison: cell and animal evidence against human evidence**")
    for e in lit.get("errors", []):
        st.warning(f"{e}. That part is missing from this comparison.")
    st.caption(f"Query used: {lit.get('query', '')}  ·  {len(lit['records'])} record(s) retrieved. Records are put in levels by keywords in the title and abstract, so one record can sit in several levels. A mention is not a finding.")
    rows = []
    for k, label in LEVELS:
        rows.append({"Level": label, "Records": comp[k]["n"], "Newest": "; ".join(f"{p.get('year', '')} {p['title'][:70]} ({p['url']})" for p in comp[k]["papers"])})
    st.dataframe(rows, hide_index=True, use_container_width=True)
    row = best_ot_row(lit["ot"], lit["key"][1])
    if lit["ot"]:
        st.markdown("**Open Targets: how strongly this gene is linked to matching diseases, by type of evidence** (scores run from 0 to 1 and aggregate several sources)")
        st.dataframe([{"Disease": r["disease"], "Overall": round(r["score"], 2), "Genetic association": round(r["datatypes"].get("genetic_association", 0), 2),
                       "Animal model": round(r["datatypes"].get("animal_model", 0), 2), "Literature": round(r["datatypes"].get("literature", 0), 2),
                       "Known drug": round(r["datatypes"].get("known_drug", 0), 2)} for r in lit["ot"][:6]], hide_index=True, use_container_width=True)
    elif not lit.get("errors"):
        st.caption("Open Targets returned no matching disease for this gene and term.")
    st.info(gap_statement(comp, row, len(lit["records"])))
