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
from ..explain import plot_note
from ..player import narration, render_player
from .common import data_audit, experiment_protein_list, focus_picker, render_claims, secret, svg
from .dossier_view import render_dossiers
from .mission import render_mission
from .patterns import render_patterns, own_claims
from .gpcrome import example_block, render_gpcrome
from .shell import Analysis, coupling_info

def _guide(a: Analysis) -> None:
    with st.expander("Input formats, templates and what you get back", expanded=False):
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
        st.markdown("**Simulation: what is computed here and what is not**")
        st.dataframe([
            {"Capability": "Collective motion of the fold", "Status": "Computed", "How": "Elastic network on the AlphaFold C-alpha atoms (Triage, 3D viewer, Motion). Resting model only; not an active state."},
            {"Capability": "Inactive-to-active comparison", "Status": "From your structures", "How": "Upload two structures of the receptor (Triage): superposed, per-helix movement measured, straight-line morph. Not a simulated pathway."},
            {"Capability": "Candidate pockets, variants in pockets", "Status": "Computed (geometry)", "How": "LIGSITE-style buriedness on the AlphaFold model plus an enrichment test of ClinVar variants (Hotspots). Not a binding prediction; validated on synthetic shapes only."},
            {"Capability": "Binding kinetics", "Status": "Fit / calculator", "How": "kon, koff, Kd from YOUR SPR/BLI curves or from rates you enter (Experiments). It does not predict them."},
            {"Capability": "Dose-response shifts (co-expression, heterodimer, allosteric)", "Status": "Fit from your data", "How": "EC50 per curve and an F-test for a shift between two conditions (Experiments). Measures a shift; does not predict one."},
            {"Capability": "Docking, binding free energy, interaction maps", "Status": "Run elsewhere, calibrated here", "How": "Run docking, AlphaFold-Multimer or Boltz externally; bring scores into Experiments and see whether they separate known binders from decoys before trusting any ranking."},
            {"Capability": "G-protein coupling from sequence", "Status": "Self-tested", "How": "Loop and motif features, tested on held-out receptor subfamilies; shown only if it beats baseline and shuffled labels (Patterns). Declines on the small built-in table."},
            {"Capability": "Mouse knockout phenotypes", "Status": "From Open Targets", "How": "Phenotype systems affected when the gene is knocked out (Genetics). Not verified against the live API in testing."},
            {"Capability": "Assay protocol with controls; learning from your results", "Status": "Computed", "How": "Experiments; Overview outcomes re-weight the precedent model."},
            {"Capability": "Lipid-raft or membrane simulation, kon/koff prediction, active-state prediction", "Status": "Needs external tools", "How": "Molecular dynamics in an explicit membrane; use a computational partner and bring the summary back."},
        ], hide_index=True)


def _lens_box(p: dict, title: str) -> None:
    col = {"HIGH": "#22c55e", "MODERATE": "#38bdf8", "LOW": "#94a3b8", "INSUFFICIENT DATA": "#f59e0b"}[p["level"]]
    st.markdown(f"<div style='border:1px solid {col}66;border-radius:10px;padding:.8rem 1rem;background:#050d1e;margin-bottom:.4rem'><div style='color:#9ab;font-size:.72rem'>{title}</div>"
                f"<div style='color:{col};font-weight:800;letter-spacing:.06em'>{p['level']}</div>"
                f"<div style='color:#e6edf7;font-size:1.6rem;font-weight:800'>{p['pct']}<span style='font-size:.9rem;color:#6b8aa3'> / 100</span></div><div style='color:#6b8aa3;font-size:.8rem'>{p['coverage']}</div></div>", unsafe_allow_html=True)
    with st.expander(f"How this score is built ({title.split(' (')[0].lower()})"):
        st.dataframe([{"Evidence": c["name"], "Value": c["value"], "Points": f"{c['points']}/{c['max']}" if c["available"] else "not available", "Rule": c["rule"]} for c in p["components"]], hide_index=True)
        st.caption(p["note"])


def _status_orphan(a: Analysis) -> bool:
    return bool(a.b.loaded and a.orphan)


def render_overview(a: Analysis) -> None:
    b, ctx = a.b, a.ctx
    render_mission(a)
    example_block(a)
    _guide(a)
    if ctx.tailored:
        st.caption(f"Tailored to your microenvironment: {ctx.summary()}")
    if not b.loaded and a.summary is None and a.gpcrome is None:
        st.info("Search a protein in the sidebar, upload an experiment, or load the example case above to begin.")
        return
    if b.loaded:
        st.markdown(f"### {b.gene} · {b.name}")
        st.caption(f"UniProt {b.uid} · {b.length} residues" + (" · G-protein-coupled receptor" if b.is_gpcr else "") + (" · orphan (no confirmed ligand on record)" if a.orphan else ""))

    _alias_notice(a)
    focus_picker(a)
    render_dossiers(a)
    render_patterns(a)
    if b.loaded:
        st.markdown("#### Watch what may be happening")
        _animation(a)

    if b.loaded:
        st.markdown("#### Pursue this target?")
        if a.bio:
            st.caption("Two different questions, scored separately: how important is it in the experiment you brought, and does it look like a drug target. A gene can be high on one and low on the other.")
        if a.modality:
            st.info(a.modality)
        left, right = st.columns([2, 3])
        with left:
            _lens_box(a.poss, "As a drug target (small molecule or antibody)")
            if a.bio:
                _lens_box(a.bio, "Role in your experiment (biomarker or mechanism)")
            elif a.user_sig is None and st.session_state.get("csv_df") is not None and st.session_state.get("csv_triage_active"):
                st.caption(f"{b.gene} is not in the table you uploaded, so there is no experiment-based score for it.")
        with right:
            st.markdown("**Strategy options**")
            render_claims(a.strategies, b, "strat", empty="No strategy rule is triggered by the data retrieved.")

        mine = disease_context_claims(ctx, a.diseases)
        if mine:
            st.markdown("#### Relevance to your setup")
            render_claims(mine, b, "mine")

        st.markdown("#### Associated diseases (ranked)")
        render_claims(a.diseases, b, "dis", limit=8, empty="No disease association was found in UniProt or ClinVar for this protein.")
        st.markdown("#### Defects it may cause")
        render_claims(a.defects, b, "def", empty="No pathogenic or likely-pathogenic germline variants were retrieved, so no defect pattern can be stated.")

    render_gpcrome(a)
    st.markdown("#### What may happen (ranked hypotheses)")
    _own = {id(c) for c in own_claims(a)} if _status_orphan(a) else set()
    _rest = [c for c in a.hyp_claims if id(c) not in _own]
    if _own and _rest != a.hyp_claims:
        st.caption(f"The {len(_own)} precedent hypotheses for {b.gene} itself are in the Pattern-learned panel above; they are not repeated here.")
    if _rest:
        st.caption("Ranked by support from documented historical precedents. Each is a hypothesis to test, not a result.")
        shown = render_claims(_rest, b, "hyp", limit=5)
        _crosscheck(shown[:1], b)
    elif _own:
        _crosscheck([c for c in a.hyp_claims if id(c) in _own][:1], b)
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
        experiment_protein_list(a)
        if a.focus:
            from ..engine.report import results_table
            t = results_table(s)
            row = t[t["Receptor"] == a.focus]
            if len(row):
                st.markdown(f"**{a.focus}**")
                st.dataframe(row.drop(columns=["Receptor"]), hide_index=True)
        elif a.focus_options:
            st.caption("Hypotheses, critic verdicts and the first experiment are shown for one protein at a time: pick one under Show details for, or search it in the sidebar.")
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
        st.info(f"{b.gene} is not a GPCR, so there is no receptor-activation video for it. The signalling video, orphan analysis and deorphanisation hypotheses apply to GPCRs. "
                f"Showing its protein architecture and interaction partners instead. To see the GPCR analysis, search a receptor (for example FFAR1) or load the example case.")
        plot_note("architecture")
        svg(architecture_svg(b))
        if b.partners:
            plot_note("network")
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
    mots = tm_motifs(b, segs)
    plot_note("signalling")
    markup = signalling_svg(b, segs, mots, segment_stats(b, segs), coupling=cls, coupling_source=src, status=status, ligand_lines=lines, hypothesis=hyp, signal=sig,
                            context=(ctx.tissue or ctx.disease), first_assay=fa)
    caps = narration(b.gene, status=status, coupling=cls, coupling_source=src, hypothesis=hyp, ligand_lines=lines, motifs=mots, signal=sig, context=(ctx.tissue or ctx.disease), first_assay=fa)
    render_player(markup, caps)
