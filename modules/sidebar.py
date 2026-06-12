# modules/sidebar.py
from __future__ import annotations
import streamlit as st
import pandas as pd
from modules.config import GOAL_OPTIONS, CSV_GUIDE, STRIPE_LINKS, RESEARCH_DOMAINS, DOMAIN_STYLES, _logo_src
from modules.utils import sh, mc
from modules.data_processing import g_gene, g_name, g_seq, g_diseases, g_func, g_ptype, classify_entity
from modules.api import fetch_disease_proteins, detect_csv_type, summarise_assay
from modules.auth import check_search_limit

def render_sidebar():
    with st.sidebar:
        _rd_sb = st.session_state.get("research_domain", "")
        _rd_meta_sb = RESEARCH_DOMAINS.get(_rd_sb, {})
        _rd_clr_sb = _rd_meta_sb.get("color", "#00e5ff")
        _rd_icon_sb = _rd_meta_sb.get("icon", "🔬")
        st.markdown(
            f"<div style='text-align:center;padding:.3rem 0 .5rem;'>"
            f"<div style='font-size:1.4rem;'>{_rd_icon_sb}</div>"
            f"<div style='color:#00e5ff;font-size:1.05rem;font-weight:800;'>Protellect</div>"
            f"<div style='background:{_rd_clr_sb}15;border:1px solid {_rd_clr_sb}33;"
            f"color:{_rd_clr_sb};font-size:.72rem;font-weight:700;padding:2px 10px;"
            f"border-radius:8px;display:inline-block;margin:.3rem 0;'>{_rd_sb}</div>"
            f"</div><div style='border-top:1px solid #0c2040;margin-bottom:.5rem;'></div>",
            unsafe_allow_html=True,
        )
        if st.button("← Change Domain", use_container_width=True, key="change_domain_btn"):
            st.session_state["research_domain"] = None
            st.session_state["domain_expanded"] = None
            st.rerun()
        st.markdown("<div style='margin-bottom:.3rem;'></div>", unsafe_allow_html=True)

        st.markdown("<div class='sb-t'>🎯 Research Goal</div>", unsafe_allow_html=True)
        goal_label = st.selectbox("Goal", GOAL_OPTIONS, label_visibility="collapsed", key="sidebar_goal")
        goal_custom = ""
        if "Custom" in goal_label:
            goal_custom = st.text_input("Describe your goal", placeholder="e.g. Find splice variants affecting exon 4…", label_visibility="collapsed")
        active_goal = goal_custom if "Custom" in goal_label else goal_label
        st.session_state["goal_label"] = active_goal

        st.markdown("<div class='sb-t'>🔍 Protein Search</div>", unsafe_allow_html=True)
        query = st.text_input("Gene / UniProt ID", placeholder="TP53 · BRCA1 · P04637 · FLNC · ACM2", label_visibility="collapsed", value=st.session_state.get("protein_query_val", ""), key="protein_query_box")
        search = st.button("🔬 Analyse Protein", use_container_width=True, key="search_btn")
        if search:
            st.session_state["_search_clicked"] = True

        st.markdown("<div class='sb-t'>🏥 Disease → Proteins</div>", unsafe_allow_html=True)
        disease_q = st.text_input("Search by disease name", placeholder="e.g. dilated cardiomyopathy · Glanzmann", label_visibility="collapsed", key="dis_q_inp")
        dis_search = st.button("🔎 Find Disease Proteins", use_container_width=True, key="dis_btn")
        if dis_search:
            if disease_q and disease_q.strip():
                with st.spinner(f"Searching ClinVar for proteins linked to '{disease_q}'..."):
                    dp = fetch_disease_proteins(disease_q.strip(), max_genes=20)
                    st.session_state["disease_search"] = disease_q.strip()
                    st.session_state["disease_proteins"] = dp
                    if not dp:
                        st.session_state["disease_proteins"] = []
                        st.warning(f"No ClinVar results for '{disease_q}'. Try a broader term like 'cardiomyopathy' or 'Glanzmann'.")
            else:
                st.warning("Enter a disease name first.")

        st.markdown("<div class='sb-t'>📂 Wet-Lab Data (CSV)</div>", unsafe_allow_html=True)
        with st.expander("📋 What CSVs work best?", expanded=False):
            for ctype, cinfo in CSV_GUIDE.items():
                st.markdown(
                    f"<div style='margin:.4rem 0;'><span style='color:#00e5ff;font-weight:700;font-size:.8rem;'>{cinfo['icon']} {cinfo['name']}</span>"
                    f"<div style='color:#3a6080;font-size:.73rem;'>Needs: {', '.join(cinfo['required_cols'][:2])}</div>"
                    f"<div style='color:#2a5060;font-size:.71rem;'>{cinfo['tip'][:70]}</div></div>",
                    unsafe_allow_html=True,
                )
        uploaded_csv = st.file_uploader("Upload CSV (any format)", type=["csv", "tsv", "txt"], label_visibility="collapsed")
        if uploaded_csv:
            try:
                sep = "\t" if uploaded_csv.name.endswith((".tsv", ".txt")) else ","
                df = pd.read_csv(uploaded_csv, sep=sep, on_bad_lines="skip")
                csv_type = detect_csv_type(df)
                st.session_state["csv_df"] = df
                st.session_state["csv_type"] = csv_type
                summary_text = summarise_assay(df, csv_type)
                st.markdown(
                    f"<div style='background:#040d18;border:1px solid #0c3050;border-radius:8px;padding:8px 10px;margin-top:4px;'>"
                    f"<div style='color:#4adaff;font-size:.94rem;font-weight:700;margin-bottom:3px;'>{uploaded_csv.name}</div>"
                    f"<div style='color:#1a4060;font-size:.80rem;'>{csv_type.replace('_', ' ').title()} · {len(df):,} rows</div>"
                    f"<div style='color:#0d2840;font-size:.96rem;margin-top:3px;line-height:1.4;'>{summary_text[:200]}</div></div>",
                    unsafe_allow_html=True,
                )
            except Exception as e:
                st.error(f"CSV error: {e}")

        if st.session_state.get("csv_df") is not None:
            run_csv_triage = st.button("🔬 Run Wet-Lab Triage", use_container_width=True, key="csv_triage_btn")
            if run_csv_triage:
                st.session_state["csv_triage_active"] = True

        st.markdown("<div class='sb-t'>🧫 Assay Notes</div>", unsafe_allow_html=True)
        assay_txt = st.text_area("Assay description", height=70, placeholder="e.g. Western blot shows 3× expression increase…", label_visibility="collapsed")
        st.session_state["assay"] = assay_txt

        st.markdown(
            "<div class='sb-t'>Variant Triage Threshold</div>"
            "<div style='color:#3a6080;font-size:.75rem;margin-bottom:4px;'>Disease variants / total variants per 100 residues</div>",
            unsafe_allow_html=True,
        )
        sensitivity = st.slider("", 0, 100, st.session_state.get("sensitivity", 50), 5, label_visibility="collapsed")
        st.session_state["sensitivity"] = sensitivity

        _gi_now = st.session_state.get("gi", {})
        _density_now = _gi_now.get("density", 0) * 100 if _gi_now else 0
        _plen_now = st.session_state.get("pdata", {}).get("sequence", {}).get("length", 1) if st.session_state.get("pdata") else 1
        _path_now = _gi_now.get("n_pathogenic", 0) if _gi_now else 0
        _total_now = _gi_now.get("n_total", 1) if _gi_now else 1
        if _gi_now and _path_now > 0:
            _density_per100 = round(_path_now / max(_plen_now, 1) * 100, 2)
            sens_lbl = f"{_path_now} disease / {_total_now} total = {_density_per100}/100 residues"
            sens_clr = "#ff2d55" if _density_per100 > 5 else "#ff8c42" if _density_per100 > 1 else "#ffd60a"
        else:
            sens_lbl = "Strict  <————>  Sensitive"
            sens_clr = "#3a6080"
        st.markdown(f"<div style='color:{sens_clr};font-size:.78rem;margin-top:2px;font-weight:600;'>{sens_lbl}</div>", unsafe_allow_html=True)

        st.markdown("<div class='sb-t'>🔗 Compare Interaction Partner</div>", unsafe_allow_html=True)
        partner_q = st.text_input("Partner gene / UniProt ID", placeholder="e.g. ITGAL · FLNC · ARRB2", label_visibility="collapsed", key="partner_inp")
        fetch_partner = st.button("Compare Partner", use_container_width=True, key="partner_btn")
        if fetch_partner and partner_q:
            with st.spinner("Fetching partner data..."):
                try:
                    from modules.api import fetch_uniprot, fetch_clinvar
                    from modules.data_processing import g_gene, compute_gi
                    p2 = fetch_uniprot(partner_q)
                    g2 = g_gene(p2)
                    uid2 = p2.get("primaryAccession", "")
                    cv2 = fetch_clinvar(g2, 100)
                    ln2 = p2.get("sequence", {}).get("length", 1)
                    gi2 = compute_gi(cv2, ln2)
                    st.session_state["partner_query"] = partner_q
                    st.session_state["partner_cv"] = cv2
                    st.session_state["partner_gi"] = {"gi": gi2, "gene": g2, "uid": uid2}
                except Exception as e:
                    st.error(f"Partner: {e}")

        st.markdown("<div class='sb-t'>⚙️ Data Depth</div>", unsafe_allow_html=True)
        depth = st.selectbox("Depth", ["Standard (150 variants)", "Deep (400 variants)"], label_visibility="collapsed")
        max_v = 150 if "Standard" in depth else 400
        st.session_state["max_variants"] = max_v

        # Sidebar protein summary when loaded
        if st.session_state.get("pdata"):
            p3 = st.session_state["pdata"]
            gene3 = st.session_state["gene"]
            uid3 = st.session_state["uid"]
            scored3 = st.session_state["scored"]
            cv3 = st.session_state["cv"]
            st.markdown(f"<div style='border-top:1px solid #0c2040;margin:.6rem 0 .3rem;'></div><div style='background:#040d18;border:1px solid #0c2040;border-radius:8px;padding:7px 9px;'><div style='color:#00e5ff;font-weight:700;font-size:.98rem;'>{gene3}</div><div style='color:#5a8090;font-size:.96rem;'>{uid3}</div></div>", unsafe_allow_html=True)

            gi3 = st.session_state.get("gi")
            ds_scores = {}
            for sv in scored3:
                for c2 in sv.get("condition", "").split(";"):
                    c2 = c2.strip()
                    if c2:
                        ds_scores[c2] = max(ds_scores.get(c2, 0), sv.get("ml", 0))
            diseases3 = g_diseases(p3)
            all_names = list(dict.fromkeys([d["name"] for d in diseases3] + [c2 for sv in cv3.get("variants", []) for c2 in sv.get("condition", "").split(";") if c2.strip() and c2.strip() != "Not specified"]))
            if all_names:
                st.markdown("<div class='sb-t'>🏥 Disease Affiliations</div>", unsafe_allow_html=True)
                for name3 in all_names[:8]:
                    score3 = ds_scores.get(name3, .4)
                    rk3 = "CRITICAL" if score3 >= .85 else "HIGH" if score3 >= .65 else "MEDIUM" if score3 >= .40 else "NEUTRAL"
                    css3 = {"CRITICAL": "bC", "HIGH": "bH", "MEDIUM": "bM", "NEUTRAL": "bN"}.get(rk3, "bN")
                    st.markdown(f"<div style='display:flex;align-items:center;gap:6px;margin:3px 0;'><span class='badge {css3}'>{rk3}</span><span style='color:#5a8090;font-size:.81rem;'>{name3[:32]}</span></div>", unsafe_allow_html=True)

            _ent3 = classify_entity(p3)
            _gi3 = st.session_state.get("gi", {})
            _n_crit3 = sum(1 for v in scored3 if v.get("ml_rank") == "CRITICAL")
            _n_lof3 = sum(1 for v in scored3 if any(k in v.get("variant_name", "").lower() for k in ["del", "ter", "fs", "stop", "nonsense"]) and v.get("score", 0) >= 3)
            _pli3 = st.session_state.get("gnomad", {}).get("pLI", 0)
            _goal3 = get_goal_config(st.session_state.get("goal_label", ""))

            _exps3 = []
            if _ent3["ptype"] == "kinase":
                _exps3 = [f"ADP-Glo kinase assay — test {min(3, _n_crit3)} CRITICAL variants vs WT", f"pERK/pAKT western — downstream signalling loss", f"{'HTS inhibitor screen' if st.session_state.get('ot', {}).get('tractability', {}).get('Small molecule') else 'Allosteric site mapping by HDX-MS'}"]
            elif _ent3["ptype"] == "gpcr":
                _exps3 = ["cAMP HTRF (Gs coupling) + beta-arrestin BRET (bias)", "Radioligand competition binding assay", "BRET2 proximity assay for G-protein selectivity"]
            elif _ent3["ptype"] == "transcription_factor":
                _exps3 = ["EMSA — test DNA binding affinity", "ChIP-seq — identify lost target gene occupancy", "Luciferase reporter — quantify transactivation defect"]
            else:
                _exps3 = [f"Variant activity assay — {_n_crit3} CRITICAL variants vs WT", f"{'CRISPR knock-in' if _pli3 > 0.8 else 'Cell viability panel — confirm loss-of-function phenotype first'}", _goal3.get('experiment_priority', ['Variant biochemical activity assay'])[0]]

            st.markdown("<div class='sb-t'>Prioritised Experiments</div>", unsafe_allow_html=True)
            for s3 in _exps3:
                st.markdown(f"<div style='color:#7ab0c4;font-size:.82rem;margin:2px 0;'>▸ {s3}</div>", unsafe_allow_html=True)

            if _goal3.get("sidebar_tip"):
                st.markdown(f"<div style='background:#020d18;border:1px solid #00e5ff22;border-radius:7px;padding:6px 9px;margin-top:5px;'><div style='color:#3a7090;font-size:.74rem;'><b style='color:#4a8090;'>Goal tip:</b> {_goal3['sidebar_tip']}</div></div>", unsafe_allow_html=True)

            # Excel download button
            st.markdown("<div class='sb-t'>📥 Export All Data</div>", unsafe_allow_html=True)
            if st.button('📊 Download Excel Report', use_container_width=True, key='xl_btn'):
                with st.spinner('Building Excel workbook (9 sheets)...'):
                    from modules.excel_export import generate_excel
                    from modules.data_processing import compute_experiment_roi, g_ptype
                    xl_bytes = generate_excel(
                        gene3, p3, cv3, scored3,
                        st.session_state.get('gi', {}),
                        st.session_state.get('gnomad', {}),
                        st.session_state.get('string', []),
                        st.session_state.get('drugs', []),
                        st.session_state.get('trials', []),
                        st.session_state.get('ot', {}),
                        g_diseases(p3),
                        st.session_state.get('papers', []),
                        st.session_state.get('patients', {}),
                        compute_experiment_roi(scored3, st.session_state.get('gi', {}), g_ptype(p3), st.session_state.get('gnomad', {}), st.session_state.get('ot', {})),
                        st.session_state.get('am', {}),
                        st.session_state.get('hotspots', []),
                    )
                    if xl_bytes:
                        st.session_state['excel_bytes'] = xl_bytes
            if st.session_state.get('excel_bytes'):
                st.download_button('⬇️ Save Excel', st.session_state['excel_bytes'],
                    file_name=f'Protellect_{gene3}_report.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    use_container_width=True, key='xl_dl')


def get_goal_config(gl):
    GOAL_CONFIG = {
        "Identify therapeutic targets": {
            "emphasis": ["druggability", "tractability", "hotspots", "patient_population", "clinical_trials"],
            "experiment_priority": ["Variant biochemical activity assay (WT vs P/LP)", "CRISPR isogenic knock-in", "AP-MS interactome mapping"],
            "banner": "Therapeutic target mode: OpenTargets tractability + drug landscape + FDA pathways prioritised.",
            "sidebar_tip": "Cross-reference with OpenTargets tractability — only proceed to HTS if small molecule tractable.",
        },
        "Understand disease mechanism": {
            "emphasis": ["variant_cascade", "pathway", "somatic_germline", "interactions"],
            "experiment_priority": ["CRISPR isogenic knock-in (PS3 evidence)", "AP-MS unbiased interactome mapping", "Bulk RNA-seq transcriptional response"],
            "banner": "Mechanism mode: variant cascade, pathway disruption, and somatic vs germline split emphasised.",
            "sidebar_tip": "CRISPR knock-in of the top pathogenic variant is the gold-standard PS3 mechanistic evidence.",
        },
        "Drug discovery & development": {
            "emphasis": ["binding", "ic50", "ADMET", "selectivity", "SAR"],
            "experiment_priority": ["SPR binding kinetics (kon/koff)", "HTS biochemical primary assay", "ADMET panel (CYP3A4, hERG, plasma binding)"],
            "banner": "Drug development mode: binding kinetics, ChEMBL scaffolds, and selectivity panel emphasised.",
            "sidebar_tip": "Sequence: AlphaFold binding pocket → fpocket druggability → SPR primary screen → ITC for thermodynamics.",
        },
    }
    for k in GOAL_CONFIG:
        if k.lower() in gl.lower() or gl.lower() in k.lower():
            return GOAL_CONFIG[k]
    return GOAL_CONFIG.get("Identify therapeutic targets", {})
