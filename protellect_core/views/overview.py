"""Overview: the experiment animated, whether and how to pursue the target, associated diseases and defects, and ranked hypotheses."""
from __future__ import annotations

import streamlit as st

import re

from ..network import interaction_svg
from ..topology import motifs as tm_motifs, segment_stats, topology as tm_topology
from ..viz import architecture_svg, signalling_svg
from ..context import disease_context_claims, factor_claims, medication_claims
from ..engine.llm_debate import PROVIDERS, LLMError, available_providers, debate, fallback_llm
from ..engine.report import hypotheses_table, markdown_report, results_table
from ..engine.templates import GENERAL_RULES, SHAPES, template_csv
from .common import data_audit, render_claims, secret, svg
from .patterns import render_patterns
from .gpcrome import example_block, render_gpcrome
from .shell import Analysis, coupling_info

NICHE = ("**What this does that a standard pipeline does not.** A differential-expression or variant pipeline ends at a ranked gene list and pathway enrichment, "
         "and treats a receptor nobody has characterised like any other row. Protellect picks out the **orphan GPCRs** inside your own results, ranks what each one "
         "might bind and couple to by **documented deorphanisation precedent**, ties every claim to its source, **cross-examines it (ML validation)** so you can see "
         "why it might be wrong, and joins that to the clinical genetics, structure and druggability evidence for the same receptor, ending in a confirmatory assay you can run.")


def _guide(a: Analysis) -> None:
    with st.expander("What to give, what to expect, and what only this app does", expanded=not a.b.loaded and a.summary is None):
        st.markdown(NICHE)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**What you give it**")
            st.markdown("- **Your experiment:** a processed table (one of the three shapes below), or a gene symbol in the sidebar.\n- **The microenvironment:** disease, tissue, model, and any patient context.\n- **Optional:** a multi-context expression matrix (cell types or conditions) for the GPCRome analysis.")
            for key, s in SHAPES.items():
                st.download_button(f"Template: {s['label']}", template_csv(key), file_name=f"protellect_template_{key}.csv", key=f"ov_tpl_{key}")
            st.caption(" ".join(GENERAL_RULES[:3]))
        with c2:
            st.markdown("**What you get back**")
            st.markdown("- The orphan GPCRs in your data, each with ranked hypotheses (ligand class, signalling, disease analogy) and the assay that would test them.\n- With a matrix: which cell types each GPCR belongs to and what unknown ones probably couple to, after the method has tested itself on your own data.\n"
                        "- Whether to pursue the target and how, from genetics and ClinVar, with the components of the score shown.\n"
                        "- Associated diseases, the defects they involve, and what may happen, all with proof.\n"
                        "- A banner saying what to prioritise or deprioritise and which tab to open next.")
            st.markdown("**What it will not do:** confirm a ligand or function (only a wet-lab experiment does), give a probability of success, or show a statement that has no source.")


def render_overview(a: Analysis) -> None:
    b, ctx = a.b, a.ctx
    _guide(a)
    example_block(a)
    if ctx.tailored:
        st.caption(f"Tailored to your microenvironment: {ctx.summary()}")
    if not b.loaded and a.summary is None and a.gpcrome is None:
        st.info("Search a protein in the sidebar, upload an experiment, or load the example case above to begin.")
        return
    if b.loaded:
        st.markdown(f"### {b.gene} · {b.name}")
        st.caption(f"UniProt {b.uid} · {b.length} residues" + (" · G-protein-coupled receptor" if b.is_gpcr else "") + (" · orphan (no confirmed ligand on record)" if a.orphan else ""))

    _alias_notice(a)
    render_patterns(a)
    if b.loaded:
        st.markdown("#### What is happening in the experiment")
        _animation(a)

    if b.loaded:
        st.markdown("#### Pursue this target?")
        left, right = st.columns([2, 3])
        with left:
            p = a.poss
            col = {"HIGH": "#22c55e", "MODERATE": "#38bdf8", "LOW": "#94a3b8", "INSUFFICIENT DATA": "#f59e0b"}[p["level"]]
            st.markdown(f"<div style='border:1px solid {col}66;border-radius:10px;padding:.8rem 1rem;background:#050d1e'><div style='color:{col};font-weight:800;letter-spacing:.06em'>POSSIBILITY: {p['level']}</div>"
                        f"<div style='color:#e6edf7;font-size:1.6rem;font-weight:800'>{p['pct']}<span style='font-size:.9rem;color:#6b8aa3'> / 100</span></div><div style='color:#6b8aa3;font-size:.8rem'>{p['coverage']}</div></div>", unsafe_allow_html=True)
            with st.expander("How this score is built"):
                st.dataframe([{"Evidence": c["name"], "Value": c["value"], "Points": f"{c['points']}/{c['max']}" if c["available"] else "not available", "Rule": c["rule"]} for c in p["components"]], hide_index=True)
                st.caption(p["note"])
        with right:
            st.markdown("**Strategy options**")
            render_claims(a.strategies, b, "strat", empty="No strategy rule is triggered by the data retrieved.")

        mine = medication_claims(ctx, b) + factor_claims(ctx, b) + disease_context_claims(ctx, a.diseases)
        if mine:
            st.markdown("#### Relevance to your setup")
            render_claims(mine, b, "mine")

        st.markdown("#### Associated diseases (ranked)")
        render_claims(a.diseases, b, "dis", limit=8, empty="No disease association was found in UniProt or ClinVar for this protein.")
        st.markdown("#### Defects it may cause")
        render_claims(a.defects, b, "def", empty="No pathogenic or likely-pathogenic germline variants were retrieved, so no defect pattern can be stated.")

    render_gpcrome(a)
    st.markdown("#### What may happen (ranked hypotheses)")
    if a.hyp_claims:
        st.caption("Ranked by support from documented historical precedents. Each is a hypothesis to test, not a result.")
        shown = render_claims(a.hyp_claims, b, "hyp", limit=10)
        _crosscheck(shown[:1], b)
    elif b.loaded and not a.orphan:
        st.info("The precedent library covers orphan GPCRs. For other proteins the ranked statements above (diseases and defects) are the evidence-based expectations.")
    if a.summary is not None:
        _experiment_table(a)
    _outcomes(a)
    _registry(a)
    if b.loaded:
        data_audit(b)


def _experiment_table(a: Analysis) -> None:
    s = a.summary
    st.markdown(f"#### Orphan GPCRs found in {a.source}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Genes read", s.n_input_genes); c2.metric("GPCRs found", s.n_gpcr); c3.metric("Orphan GPCRs", s.n_orphan)
    if s.n_orphan:
        st.dataframe(results_table(s), hide_index=True)
        d1, d2 = st.columns(2)
        d1.download_button("Download all hypotheses (CSV)", hypotheses_table(s).to_csv(index=False), "protellect_hypotheses.csv", "text/csv", key="ov_dl_csv")
        d2.download_button("Download report", markdown_report(s, a.ctx.engine_ctx(), a.engine.calibration_note(), a.engine.library_verified), "protellect_report.md", key="ov_dl_md")
    st.caption(a.engine.calibration_note())


def _crosscheck(claims, b) -> None:
    if not claims:
        return
    prov = available_providers(secret)
    if not prov:
        st.caption("Optional language-model cross-check is off: add GEMINI_API_KEY or ANTHROPIC_API_KEY to Streamlit secrets to enable it.")
        return
    pick = st.selectbox("ML validation cross-check provider", prov, format_func=lambda p: PROVIDERS[p]["label"], key="ov_prov")
    if st.button("Cross-check the top hypothesis", key="ov_xcheck"):
        c = claims[0]
        hyp = {"statement": c.text, "support": round(c.score, 3), "verdict": c.verdict, "precedents": [], "evidence_axes": {}, "counterarguments": c.counters,
               "proofs": [f"{p.source}: {p.detail}" for p in c.proofs]}
        try:
            out = debate(c.text.split(":")[0], hyp, {}, fallback_llm([pick] + [p for p in prov if p != pick], secret))
        except LLMError as e:
            st.warning(str(e)); return
        st.markdown(f"**Cross-check verdict:** {out['final_verdict']} (evidence rules: {out['deterministic_verdict']})")
        for r in out["reasons"]:
            st.markdown(f"- {r['text']} _(cites {', '.join(r['cites'])})_")
        for q in out["open_questions"]:
            st.markdown(f"- Open question (unverified): {q}")
        if out["note"]:
            st.caption(out["note"])


def _registry(a: Analysis) -> None:
    from ..engine.registry import convert_iuphar_bytes
    n = sum(v["status"] == "orphan" for v in a.engine.registry.values())
    with st.expander(f"Receptor registry: {len(a.engine.registry)} GPCRs, {n} orphan ({st.session_state.get('_registry_label', '')})"):
        err = st.session_state.get("_registry_error")
        if err:
            st.warning(f"The full list could not be loaded automatically ({err}). Upload the file below, or check the data sources panel.")
        elif len(a.engine.registry) < 100:
            st.warning("Only a small list is loaded. Upload the Guide to Pharmacology file so every orphan GPCR in your data is recognised.")
        st.markdown("Download the Guide to Pharmacology **targets and families** CSV (guidetopharmacology.org, Downloads) and upload it here.")
        up = st.file_uploader("targets-and-families CSV", type=["csv", "txt"], key="ov_reg_up")
        if up is not None:
            try:
                txt = convert_iuphar_bytes(up.getvalue())
            except ValueError as e:
                st.error(str(e)); return
            if st.session_state.get("hyp_registry_csv") != txt:
                st.session_state["hyp_registry_csv"] = txt
                st.rerun()


def _outcomes(a: Analysis) -> None:
    import json
    from ..engine.cases import cases_from_outcomes
    from ..engine.schema import COUPLINGS, LIGAND_CLASSES, TISSUE_VOCAB
    recs = json.loads(st.session_state.get("outcomes_json", "[]") or "[]")
    n_conf = sum(1 for r in recs if r.get("status") == "confirmed")
    with st.expander(f"Record an experimental outcome: the model learns from these ({n_conf} confirmed this session)"):
        st.caption(a.engine.calibration_note())
        st.markdown("When an experiment confirms what a receptor binds, record it here. A **confirmed** outcome with a citation or note becomes a new case and the model retrains immediately. "
                    "Refuted or inconclusive results are saved in the file for the record but never trained on. Download the file and commit it as `protellect_core/engine/data/outcomes.json` to keep it.")
        genes = sorted({r.gene for r in a.summary.results}) if a.summary is not None else ([a.b.gene] if a.b.loaded else [])
        c1, c2 = st.columns(2)
        gene = c1.selectbox("Receptor", genes, key="out_gene") if genes else c1.text_input("Receptor (gene symbol)", key="out_gene_txt")
        status = c2.selectbox("Outcome", ["confirmed", "refuted", "inconclusive"], key="out_status")
        d1, d2, d3 = st.columns(3)
        lclass = d1.selectbox("Ligand class (if confirmed)", list(LIGAND_CLASSES), key="out_class")
        coup = d2.selectbox("G-protein coupling", list(COUPLINGS), key="out_coup")
        year = d3.number_input("Year", 1990, 2100, 2026, key="out_year")
        ligand = st.text_input("Ligand identified", key="out_ligand")
        tissues = st.multiselect("Tissue context at the time", list(TISSUE_VOCAB), key="out_tissues")
        notes = st.text_area("Citation or note (required for a confirmed outcome)", key="out_notes")
        if st.button("Add this outcome", key="out_add") and gene:
            recs.append({"gene": str(gene).upper(), "status": status, "ligand_class": lclass, "coupling": coup, "resolution_year": int(year), "ligand": ligand, "tissues": tissues,
                         "neighbors": [], "cluster": "", "notes": notes, "citations": []})
            _, rejected = cases_from_outcomes([recs[-1]])
            if rejected and status == "confirmed":
                recs.pop()
                st.error("Not added: " + "; ".join(rejected))
            else:
                st.session_state["outcomes_json"] = json.dumps(recs)
                st.rerun()
        if recs:
            st.download_button("Download outcomes.json", json.dumps({"outcomes": recs}, indent=1), "outcomes.json", "application/json", key="out_dl")


def _alias_notice(a: Analysis) -> None:
    b = a.b
    q = (b.query or "").strip()
    norm = lambda s: re.sub(r"[^A-Z0-9]", "", str(s).upper())
    if not b.loaded or not q or norm(q) in (norm(b.gene), norm(b.uid)):
        return
    reg_alias = a.engine.registry.get(b.gene.upper(), {}).get("aliases", [])
    others = [x for x in dict.fromkeys(list(b.aliases) + list(reg_alias)) if norm(x) != norm(q) and len(x) < 40][:6]
    is_alias = any(norm(x) == norm(q) for x in list(b.aliases) + list(reg_alias))
    msg = (f"You searched **{q}**. That is a recorded alias of **{b.gene}** ({b.name}), whose official symbol is **{b.gene}**, so everything below is about {b.gene}." if is_alias else
           f"You searched **{q}**. The closest match is **{b.gene}** ({b.name}). If that is not the receptor you meant, search its exact symbol.")
    st.info(msg + (f" Other names: {', '.join(others)}." if others else ""))


def _animation(a: Analysis) -> None:
    b, ctx = a.b, a.ctx
    segs = tm_topology(b)
    if not (b.is_gpcr or segs):
        svg(architecture_svg(b))
        if b.partners:
            svg(interaction_svg(b.gene, b.partners, registry=a.engine.registry))
        return
    cls, src = coupling_info(a)
    stt = a.engine.registry.get(b.gene.upper(), {}).get("status", "")
    status = {"orphan": "orphan", "characterized": "characterised"}.get(stt, "unknown")
    top = next((c for c in a.hyp_claims if c.tags.get("category") == "ligand-class" and c.text.split(":")[0].upper() == b.gene.upper()), None)
    lines = []
    if b.drugs:
        lines.append(f"Recorded drug-gene interactions: {len(b.drugs)} (e.g. " + ", ".join(f"{d.name}{' · ' + d.kind if d.kind else ''}" for d in b.drugs[:3]) + ").")
    elif status == "characterised":
        lines.append("No drug or ligand records were returned by the sources queried; that does not mean none exist.")
    if status == "orphan" and top is not None:
        lines.append(f"Precedent model: {top.text.split(': ', 1)[-1]} (support {top.tags.get('support', 0):.2f}).")
    sig = ""
    if a.summary is not None:
        r = next((r for r in a.summary.results if r.gene.upper() == b.gene.upper()), None)
        if r is not None and r.effect == r.effect:
            sig = f"{r.effect_type} {r.effect:+.2f}" + (f", p = {r.significance:.3g}" if r.significance is not None else "")
    hyp = {"statement": top.text.split(": ", 1)[-1], "support": float(top.tags.get("support", 0))} if top is not None and status == "orphan" else None
    fa = (top.how[0] if top is not None and top.how else "")[:150]
    svg(signalling_svg(b, segs, tm_motifs(b, segs), segment_stats(b, segs), coupling=cls, coupling_source=src, status=status, ligand_lines=lines, hypothesis=hyp, signal=sig,
                       context=(ctx.tissue or ctx.disease), first_assay=fa))
