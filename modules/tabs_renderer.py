# modules/tabs_renderer.py
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from modules.config import RANK_CLR, RANK_CSS, _logo_src, LOGO_B64
from modules.utils import sh, mc, badge, src_link, render_citations, classify_experiment_type
from modules.data_processing import g_gene, g_name, g_seq, g_diseases, g_func, g_sub, g_tissue, g_xref, g_gpcr, g_gpcr_class, g_ptype, classify_entity
from modules.visualization import viewer_html, variant_landscape_fig, mutation_cascade_html, build_mutation_dynamics_html, build_disease_timeline_html, build_druggability_map_html, render_domain_expansion_cards, render_chemical_backbone
from modules.ai_synthesis import ai_synthesize
from modules.excel_export import generate_excel

def render_all_tabs():
    pdata = st.session_state.get("pdata") or {}
    cv = st.session_state.get("cv") or {}
    pdb = st.session_state["pdb"]
    papers = st.session_state["papers"]
    scored = st.session_state["scored"]
    gene = st.session_state["gene"]
    assay = st.session_state["assay"]
    uid = st.session_state["uid"]
    variants = cv.get("variants", [])
    diseases = g_diseases(pdata)
    protein_length = pdata.get("sequence", {}).get("length", 1)
    gi = st.session_state.get("gi") or {}
    is_gpcr = g_gpcr(pdata)
    gpcr_assessment = st.session_state.get("gpcr_assessment", {})
    entity = classify_entity(pdata)
    active_goal = st.session_state.get("goal_label", "")
    gnomad_data = st.session_state.get("gnomad", {})
    string_data = st.session_state.get("string", [])
    trials_data = st.session_state.get("trials", [])
    drugs_data = st.session_state.get("drugs", [])
    abstracts = st.session_state.get("abstracts", [])
    ot_data = st.session_state.get("ot", {})
    am_scores = st.session_state.get("am", {})
    hotspots = st.session_state.get("hotspots", [])
    patient_data = st.session_state.get("patients", {})
    roi_data = st.session_state.get("roi_data", [])
    reg_paths = st.session_state.get("reg_paths", {})
    analogs = st.session_state.get("analogs", [])

    tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(["📋  Summary", "🔴  Triage", "📋  Case Study", "🔬  Explorer", "🧪  Experiments", "🤖  AI Report", "🗂️  Workspace", "🔗  Disease Link", "⚗️  Chemistry", "💊  Pharma"])

    # Tab 0 - Summary
    with tab0:
        render_summary_tab(pdata, gene, uid, protein_length, gi, scored, diseases, variants, gnomad_data, drugs_data, patient_data, papers, roi_data, reg_paths, ot_data, is_gpcr, gpcr_assessment, entity, active_goal, string_data, scored, hotspots)

    # Tab 1 - Triage
    with tab1:
        render_triage_tab(pdata, gene, uid, protein_length, gi, scored, diseases, variants, gnomad_data, drugs_data, patient_data, papers, roi_data, reg_paths, ot_data, is_gpcr, gpcr_assessment, entity, active_goal, string_data, hotspots, am_scores, pdb)

    # Tab 2 - Case Study
    with tab2:
        render_case_study_tab(pdata, gene, uid, protein_length, gi, scored, diseases, variants, gnomad_data, papers, is_gpcr, gpcr_assessment, entity)

    # Tab 3 - Explorer
    with tab3:
        render_explorer_tab(pdata, gene, uid, protein_length, scored, variants, diseases, pdb, am_scores, string_data, is_gpcr, papers)

    # Tab 4 - Experiments
    with tab4:
        render_experiments_tab(pdata, gene, uid, protein_length, gi, scored, variants, diseases, gnomad_data, papers, entity, is_gpcr, gpcr_assessment, active_goal, roi_data, reg_paths, analogs, ot_data, drugs_data, hotspots, string_data)

    # Tab 5 - AI Report
    with tab5:
        render_ai_report_tab(pdata, gene, uid, scored, variants, diseases, papers, abstracts, string_data, gnomad_data, trials_data, drugs_data, is_gpcr, gpcr_assessment, active_goal, assay, am_scores, ot_data, hotspots, patient_data, roi_data)

    # Tab 6 - Workspace
    with tab6:
        render_workspace_tab()

    # Tab 7 - Disease Link
    with tab7:
        render_disease_link_tab(pdata, gene, uid, scored, variants, diseases, is_gpcr, gpcr_assessment, entity)

    # Tab 8 - Chemistry
    with tab8:
        render_chemistry_tab(pdata, gene, uid, protein_length, scored, variants, pdb, am_scores, diseases)

    # Tab 9 - Pharma
    with tab9:
        render_pharma_tab(pdata, gene, uid, protein_length, scored, variants, diseases, gnomad_data, papers, entity, is_gpcr, gpcr_assessment, ot_data, drugs_data, pdb, gi)

def render_summary_tab(pdata, gene, uid, protein_length, gi, scored, diseases, variants, gnomad_data, drugs_data, patient_data, papers, roi_data, reg_paths, ot_data, is_gpcr, gpcr_assessment, entity, active_goal, string_data, scored, hotspots):
    from modules.visualization import build_mutation_dynamics_html, build_disease_timeline_html
    from modules.utils import render_citations

    v_clr_s = {"prioritise":"#ff2d55","proceed":"#ff8c42","selective":"#ffd60a","caution":"#ffd60a","deprioritise":"#3a5a7a","neutral":"#1e6080"}.get(gi.get("pursue","neutral"),"#3a6080")
    pursue_label_s = {"prioritise":"🔴 PURSUE","proceed":"🟠 PROCEED","selective":"🟡 BE SELECTIVE","caution":"⚠️ CAUTION — POSSIBLE PIGGYBACK","deprioritise":"⚪ DEPRIORITISE","neutral":"❓ INSUFFICIENT DATA"}.get(gi.get("pursue","neutral"),"❓")
    
    st.markdown(
        "<div style='background:linear-gradient(135deg,#020810,#030d1a);border:2px solid " + v_clr_s + "55;"
        "border-radius:16px;padding:1.4rem 1.8rem;margin-bottom:1rem;'>"
        "<div style='display:flex;align-items:center;gap:14px;'>"
        f"<img src='data:image/svg+xml;base64,{LOGO_B64}' style='width:54px;height:54px;object-fit:contain;filter:drop-shadow(0 0 16px #00e5ff66);'>"
        "<div>"
        f"<div style='color:{v_clr_s};font-weight:800;font-size:1.3rem;'>{pursue_label_s}: {gene}</div>"
        f"<div style='color:#7ab0c0;font-size:.9rem;margin-top:3px;'>{g_name(pdata)[:80]}</div>"
        f"<div style='color:#4a7090;font-size:.82rem;'>{uid} · {protein_length} aa · "
        f"{gi.get('n_pathogenic',0)} confirmed pathogenic / {gi.get('n_total',0)} total ClinVar variants · "
        f"Density {gi.get('density',0)*100:.2f}%</div>"
        "</div></div></div>",
        unsafe_allow_html=True,
    )

    sm1, sm2, sm3, sm4, sm5, sm6 = st.columns(6)
    n_crit_s = sum(1 for v in scored if v.get("ml_rank")=="CRITICAL")
    with sm1: st.markdown(mc(len(diseases),"Diseases","#00e5ff"), unsafe_allow_html=True)
    with sm2: st.markdown(mc(gi.get("n_pathogenic",0),"Pathogenic","#ff2d55"), unsafe_allow_html=True)
    with sm3: st.markdown(mc(n_crit_s,"CRITICAL ML","#ff8c42"), unsafe_allow_html=True)
    with sm4: st.markdown(mc(f"{gnomad_data.get('pLI','?')}","pLI (essential.)","#a855f7") if gnomad_data else mc("N/A","pLI","#3a6080"), unsafe_allow_html=True)
    with sm5: st.markdown(mc(len(drugs_data),"Known drugs","#00c896"), unsafe_allow_html=True)
    with sm6: st.markdown(mc(f"{patient_data.get('estimated_global_patients',0)//1000}K" if patient_data.get('estimated_global_patients',0)>0 else "?","Est. patients","#4a90d9"), unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    # Disease summary table
    sa, sb = st.columns([3, 2], gap="large")
    with sa:
        sh("🏥", "All Associated Diseases")
        if diseases:
            dis_rows = ""
            for d_s in diseases[:20]:
                nm = d_s.get("name", "")
                inh = d_s.get("inheritance", "Unknown")
                d_vars = [v for v in variants if nm.lower()[:20] in v.get("condition", "").lower() and v.get("score", 0) >= 2]
                n_d_vars = len(d_vars)
                _n_p_s = sum(1 for v in d_vars if v.get("score", 0) >= 4)
                sev = min(97, max(5, _n_p_s * 7 + n_d_vars * 3 + (8 if "dominant" in inh.lower() else 0)))
                s_clr = "#ff2d55" if sev > 70 else "#ff8c42" if sev > 40 else "#ffd60a"
                dis_rows += f"<tr><td style='color:#c0d8f0;font-weight:600;font-size:.84rem;'>{nm[:40]}</td><td style='color:#5a8090;font-size:.78rem;'>{inh}</td><td style='text-align:center;'><span style='color:{s_clr};font-weight:700;font-size:.84rem;'>{n_d_vars}</span></td><td><div style='display:flex;align-items:center;gap:5px;'><div style='width:60px;height:6px;background:#0a1828;border-radius:3px;'><div style='width:{sev}%;height:100%;background:{s_clr};border-radius:3px;'></div></div><span style='color:{s_clr};font-size:.76rem;'>{sev}</span></div></td></tr>"
            st.markdown("<div style='overflow-x:auto;border-radius:10px;border:1px solid #0c2040;max-height:380px;overflow-y:auto;'><table class='pt2'><thead><tr><th>Disease</th><th>Inheritance</th><th>Variants</th><th>Severity</th></tr></thead><tbody>" + dis_rows + "</tbody></table></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#3a6080;font-size:.9rem;'>No disease associations found in UniProt or ClinVar.</div>", unsafe_allow_html=True)

    with sb:
        sh("🧬", "Germline vs Somatic")
        somatic_s = set()
        germline_s = set()
        for v2 in variants:
            cond4 = v2.get("condition", "")
            if not cond4 or cond4.strip().lower() in ("not specified", "not provided", "", "none", "-", "n/a", "unknown"): continue
            if v2.get("somatic"): somatic_s.add(cond4)
            elif v2.get("germline") or v2.get("score", 0) >= 3: germline_s.add(cond4)
        total_s = max(len(germline_s) + len(somatic_s), 1)
        g_pct = int(len(germline_s) / total_s * 100)
        s_pct = 100 - g_pct
        st.markdown(f"<div style='background:#020810;border:1px solid #0d2545;border-radius:10px;padding:.9rem;margin-bottom:.6rem;'><div style='display:flex;gap:4px;height:24px;border-radius:6px;overflow:hidden;margin-bottom:.6rem;'><div style='width:{g_pct}%;background:#00c896;display:flex;align-items:center;justify-content:center;color:#000;font-size:.72rem;font-weight:700;'>Germline {g_pct}%</div><div style='width:{s_pct}%;background:#ff2d55;display:flex;align-items:center;justify-content:center;color:#fff;font-size:.72rem;font-weight:700;'>Somatic {s_pct}%</div></div><div style='color:#4a9070;font-size:.82rem;margin-bottom:3px;'><b style='color:#00c896;'>🧬 Germline ({len(germline_s)}):</b></div>" + "".join(f"<div style='color:#2a6040;font-size:.78rem;margin:1px 0;'>◆ {c[:50]}</div>" for c in sorted(germline_s)[:5]) + (f"<div style='color:#1a4030;font-size:.74rem;'>+{len(germline_s)-5} more</div>" if len(germline_s) > 5 else "") + f"<div style='color:#804050;font-size:.82rem;margin:.5rem 0 3px;'><b style='color:#ff2d55;'>🔴 Somatic ({len(somatic_s)}):</b></div>" + "".join(f"<div style='color:#602030;font-size:.78rem;margin:1px 0;'>◆ {c[:50]}</div>" for c in sorted(somatic_s)[:5]) + (f"<div style='color:#401020;font-size:.74rem;'>+{len(somatic_s)-5} more</div>" if len(somatic_s) > 5 else "") + "</div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    # Mutation dynamics
    sh("🎬", "Mutation Dynamics — Germline vs Somatic Visualiser")
    mut_html = build_mutation_dynamics_html(gene=gene, protein_length=protein_length, scored=scored, variants=variants, hotspots=hotspots, diseases=diseases, ptype=g_ptype(pdata), is_gpcr=is_gpcr)
    components.html(mut_html, height=560, scrolling=False)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    # Disease timeline
    sh("📅", "Disease Timeline — Per-Disease Onset & Progression")
    if diseases:
        timeline_html = build_disease_timeline_html(gene=gene, diseases=diseases, variants=variants, scored=scored)
        components.html(timeline_html, height=440, scrolling=False)

    render_citations(papers, 4)


def render_triage_tab(pdata, gene, uid, protein_length, gi, scored, diseases, variants, gnomad_data, drugs_data, patient_data, papers, roi_data, reg_paths, ot_data, is_gpcr, gpcr_assessment, entity, active_goal, string_data, hotspots, am_scores, pdb):
    from modules.visualization import variant_landscape_fig, viewer_html, render_domain_expansion_cards

    n_crit = sum(1 for v in scored if v.get("ml_rank") == "CRITICAL")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(mc(len(diseases), "Disease links"), unsafe_allow_html=True)
    with c2: st.markdown(mc(len(variants), "ClinVar variants", "#4a90d9"), unsafe_allow_html=True)
    with c3: st.markdown(mc(gi.get("n_pathogenic", 0), "Disease-causing", "#ff2d55"), unsafe_allow_html=True)
    with c4: st.markdown(mc(n_crit, "CRITICAL (ML-scored)", "#ff8c42"), unsafe_allow_html=True)

    if hotspots:
        top_h = hotspots[0]
        st.markdown(f"<div style='background:#080210;border:1px solid #a855f744;border-radius:10px;padding:.8rem 1.2rem;margin-bottom:.6rem;display:flex;gap:14px;align-items:center;'><div style='font-size:1.6rem;'>🎯</div><div><div style='color:#a855f7;font-weight:800;font-size:.95rem;margin-bottom:3px;'>{len(hotspots)} Pathogenic Variant Hotspot{'s' if len(hotspots) > 1 else ''} Detected</div><div style='color:#7a60a0;font-size:.84rem;'>Top cluster: residues {top_h['start']}–{top_h['end']} · {top_h['count']} pathogenic variants · {top_h['fold_enrichment']}× above background density.</div></div></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    cs, cd = st.columns([3, 2], gap="large")
    with cs:
        sh("🏗️", f"AlphaFold Structure — {gene}")
        if pdb:
            components.html(viewer_html(pdb, scored, 445), height=450, scrolling=False)
        else:
            st.markdown("<div style='background:#040d18;border:1px dashed #0c2040;border-radius:12px;height:340px;display:flex;align-items:center;justify-content:center;'><div style='text-align:center;color:#0e2840;'><div style='font-size:2rem;'>🧬</div><div style='font-size:1rem;margin-top:5px;'>AlphaFold structure unavailable</div></div></div>", unsafe_allow_html=True)

    with cd:
        sh("🔴", "Disease Triage")
        ds_scores = {}
        for sv in scored:
            for c2 in sv.get("condition", "").split(";"):
                c2 = c2.strip()
                if c2: ds_scores[c2] = max(ds_scores.get(c2, 0), sv.get("ml", 0))
        all_d = []
        for d in diseases:
            sc2 = ds_scores.get(d["name"], .5)
            rk2 = "CRITICAL" if sc2 >= .85 else "HIGH" if sc2 >= .65 else "MEDIUM" if sc2 >= .40 else "NEUTRAL"
            all_d.append({"name": d["name"], "desc": d.get("desc", ""), "rk": rk2, "sc": sc2})
        for d2 in all_d[:10]:
            bw = int(d2["sc"] * 100)
            clr2 = RANK_CLR[d2["rk"]]
            css2 = RANK_CSS[d2["rk"]]
            st.markdown(f"<div class='dis-row'><div style='flex-shrink:0;'><span class='badge {css2}'>{d2['rk']}</span></div><div style='flex:1;min-width:0;'><div class='dis-name'>{d2['name']}</div><div class='dis-desc'>{d2['desc'][:90]}</div><div style='height:3px;background:#07152a;border-radius:3px;overflow:hidden;margin-top:3px;'><div style='width:{bw}%;height:100%;background:{clr2};'></div></div></div></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("📊", "Variant Landscape — Where on the protein do disease-causing mutations cluster?")
    landscape = variant_landscape_fig(variants, protein_length, scored)
    if landscape: st.plotly_chart(landscape, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🔮", "Residue Hotspot Triage — Which specific mutations matter most?")
    if scored:
        rows = ""
        for v2 in scored[:50]:
            rk = v2.get("ml_rank", "NEUTRAL")
            ml2 = v2.get("ml", 0)
            clr3 = RANK_CLR.get(rk, "#3a5a7a")
            css3 = RANK_CSS.get(rk, "bN")
            bw = int(ml2 * 100)
            url = v2.get("url", "")
            nm = (v2.get("variant_name") or v2.get("title", "—"))[:55]
            sig2 = v2.get("sig", "—")[:35]
            _rc = v2.get("condition", "")
            cond2 = (_rc if _rc and _rc not in ("Not specified", "not provided", "") else f"{gene} variant — condition pending ClinVar curation")[:55]
            pos2 = str(v2.get("start", "—"))
            lnk = f"<a href='{url}' target='_blank' style='color:#2a6a8a;font-size:.80rem;'>ClinVar ↗</a>" if url else "—"
            row_bg = RANK_CLR.get(rk, "#3a5a7a") + "08"
            rows += f"<tr style='background:{row_bg};'><td><span class='badge {css3}'>{rk}</span></td><td style='color:#8ab0c8;font-size:.96rem;'>{nm}</td><td style='color:#8abccc;text-align:center;'>{pos2}</td><td style='color:#3a6080;font-size:.94rem;'>{sig2}</td><td style='color:#2a5070;font-size:1.02rem;'>{cond2}</td><td><div style='display:flex;align-items:center;gap:4px;'><div style='width:32px;height:4px;background:#07152a;border-radius:3px;overflow:hidden;'><div style='width:{bw}%;height:100%;background:{clr3};'></div></div><span style='color:{clr3};font-size:.77rem;font-weight:700;'>{ml2:.2f}</span></div></td><td style='text-align:center;'>{lnk}</td></tr>"
        st.markdown(f"<div style='overflow-x:auto;border-radius:10px;border:1px solid #0c2040;'><table class='pt2'><thead><tr><th>Rank</th><th>Variant (DNA change)</th><th>Position</th><th>ClinVar Classification</th><th>Disease</th><th>ML Score</th><th>Source</th></tr></thead><tbody>{rows}</tbody></table></div>", unsafe_allow_html=True)

    render_citations(papers, 4)


def render_case_study_tab(pdata, gene, uid, protein_length, gi, scored, diseases, variants, gnomad_data, papers, is_gpcr, gpcr_assessment, entity):
    from modules.data_processing import fetch_ncbi_gene

    TKWS = {"Brain": ["brain", "neuron", "cerebral", "cortex"], "Liver": ["liver", "hepatic"], "Heart": ["heart", "cardiac", "myocardium"], "Kidney": ["kidney", "renal"], "Lung": ["lung", "pulmonary"], "Blood": ["blood", "erythrocyte", "platelet"], "Breast": ["breast", "mammary"], "Colon": ["colon", "colorectal", "intestine"], "Prostate": ["prostate"], "Skin": ["skin", "keratinocyte"], "Muscle": ["muscle", "skeletal"], "Pancreas": ["pancreas", "islet"]}

    c_t, c_s = st.columns([1, 1], gap="large")
    with c_t:
        sh("🫀", "Tissue Associations (where in the body is this protein active?)")
        tt = g_tissue(pdata)
        if tt: st.markdown(f"<div class='card'><p>{tt[:500]}</p><div style='margin-top:5px;'>{src_link('UniProt', f'https://www.uniprot.org/uniprotkb/{uid}#expression')}</div></div>", unsafe_allow_html=True)
        blob = (tt + " " + g_func(pdata) + " " + " ".join(k.get("value", "") for k in pdata.get("keywords", []))).lower()
        tsc = {t: sum(1 for k in ks if k in blob) for t, ks in TKWS.items()}
        tsc = {t: s for t, s in tsc.items() if s > 0}
        if tsc:
            tsc = dict(sorted(tsc.items(), key=lambda x: -x[1])[:10])
            fig3 = go.Figure(go.Bar(y=list(tsc.keys()), x=list(tsc.values()), orientation="h", marker=dict(color=list(tsc.values()), colorscale=[[0, "#0c2040"], [.5, "#0d4080"], [1, "#00e5ff"]], cmin=0, cmax=max(tsc.values()))))
            fig3.update_layout(paper_bgcolor="#04080f", plot_bgcolor="#04080f", font_color="#1e4060", xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(tickfont=dict(size=11, color="#3a6080")), margin=dict(l=0, r=0, t=5, b=0), height=160 + len(tsc) * 17)
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
    with c_s:
        sh("📍", "Where in the cell? (Subcellular location)")
        locs = g_sub(pdata)
        for loc in locs: st.markdown(f"<div style='display:flex;align-items:center;gap:7px;margin:4px 0;'><span style='color:#00e5ff;font-size:.80rem;'>◆</span><span style='color:#3a6080;font-size:1.02rem;'>{loc}</span></div>", unsafe_allow_html=True)
        ptm = next((c5.get("texts", [{}])[0].get("value", "") for c5 in pdata.get("comments", []) if c5.get("commentType") == "PTM"), "")
        if ptm: st.markdown(f"<div class='card' style='margin-top:.7rem;'><h4>Chemical tags on the protein (PTMs — post-translational modifications)</h4><p>{ptm[:350]}</p></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🧬", f"Genomic Framework — where in the genome does {gene} live?")
    omim = g_xref(pdata, "MIM")
    hgnc = g_xref(pdata, "HGNC")
    ens = g_xref(pdata, "Ensembl")
    gd = fetch_ncbi_gene(gene) if gene else {}
    c1g, c2g, c3g = st.columns(3)
    with c1g: st.markdown(f"<div class='card'><h4>Protein identity</h4><p>UniProt: <b style='color:#00e5ff;'>{uid}</b><br>Length: <b>{protein_length} amino acids (building blocks)</b><br>HGNC: {hgnc or '—'}</p><div style='margin-top:5px;'>{src_link('UniProt', f'https://www.uniprot.org/uniprotkb/{uid}')}</div></div>", unsafe_allow_html=True)
    with c2g:
        chrom = gd.get("chr", "?")
        cyto = gd.get("map", "?")
        exons = gd.get("exons", "?")
        start_g = gd.get("start", "?")
        stop_g = gd.get("stop", "?")
        st.markdown(f"<div class='card'><h4>Location in genome (DNA blueprint)</h4><p>Chromosome: <b style='color:#00e5ff;'>{chrom}</b><br>Cytoband (address): <b>{cyto}</b><br>Exons (coding sections): <b>{exons}</b><br>Genomic span: {start_g}–{stop_g}</p><div style='margin-top:5px;'>{src_link('NCBI Gene', gd.get('link', 'https://www.ncbi.nlm.nih.gov/gene')) if gd.get('link') else ''}</div></div>", unsafe_allow_html=True)
    with c3g:
        omim_link = f"<a href='https://omim.org/entry/{omim}' target='_blank' style='color:#3a90c4;'>{omim} ↗</a>" if omim else "—"
        ens_link = f"<a href='https://www.ensembl.org/id/{ens}' target='_blank' style='color:#3a90c4;'>{ens[:18]} ↗</a>" if ens else "—"
        st.markdown(f"<div class='card'><h4>Cross-references (databases)</h4><p>OMIM (disease DB): {omim_link}<br>Ensembl (genome DB): {ens_link}<br>{src_link('UniProt', f'https://www.uniprot.org/uniprotkb/{uid}')} {src_link('ClinVar', f'https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]') if gene else ''}</p></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    # GPCR / Piggyback section
    sh("📡", "GPCR Association & Piggyback Analysis")
    ga = gpcr_assessment
    ga_clr = ga.get("colour", "#3a6080")
    st.markdown(f"<div style='background:#020810;border:2px solid {ga_clr}44;border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:.8rem;'><div style='color:{ga_clr};font-weight:800;font-size:1rem;margin-bottom:5px;'>{ga.get('label', '')}</div><div style='color:#6a9ab0;font-size:.87rem;line-height:1.6;margin-bottom:6px;'>{ga.get('reasoning', '')}</div><div style='color:{ga_clr};font-weight:700;font-size:.85rem;margin-bottom:5px;'>Investment verdict: {ga.get('investment', '')}</div><div style='color:#3a6080;font-size:.78rem;'>Confidence: {ga.get('confidence', '')} | Type: {ga.get('type', '')}</div></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🔬", "Disease Classification — Inherited (germline) vs Acquired (somatic)")
    somatic = set()
    germline = set()
    for v2 in variants:
        cond4 = v2.get("condition", "")
        if not cond4 or cond4.strip().lower() in ("not specified", "not provided", "", "none", "-", "n/a", "unknown"): continue
        if v2.get("somatic") or "somatic" in v2.get("origin", "").lower():
            somatic.add(cond4)
        elif v2.get("germline") or any(x in v2.get("origin", "").lower() for x in ["germline", "inherited", "de novo"]):
            germline.add(cond4)
        elif v2.get("score", 0) >= 4:
            germline.add(cond4)
    cg2, cs3 = st.columns(2)
    with cg2:
        st.markdown(f"<div style='background:#03100a;border:1px solid #00c89628;border-radius:11px;padding:1rem;'><p style='color:#00c896;font-weight:700;font-size:.98rem;margin:0 0 2px;'>🧬 Inherited / born-with (Germline) ({len(germline)})</p><p style='color:#1a4030;font-size:.80rem;margin:0 0 6px;'>Variant present in DNA from birth — heritable, runs in families</p>" + "".join(f"<div style='color:#2a6040;font-size:.96rem;margin:2px 0;'>◆ {c[:65]}</div>" for c in sorted(germline)[:7]) + ("<div style='color:#1a3020;font-size:.82rem;'>No confirmed germline disease associations found in ClinVar.</div>" if not germline else "") + "</div>", unsafe_allow_html=True)
    with cs3:
        st.markdown(f"<div style='background:#100308;border:1px solid #ff2d5528;border-radius:11px;padding:1rem;'><p style='color:#ff2d55;font-weight:700;font-size:.98rem;margin:0 0 2px;'>🔴 Acquired / developed (Somatic) ({len(somatic)})</p><p style='color:#3a1020;font-size:.80rem;margin:0 0 6px;'>Variant acquired after birth in specific cells — not heritable (e.g. cancer mutations)</p>" + "".join(f"<div style='color:#602030;font-size:.96rem;margin:2px 0;'>◆ {c[:65]}</div>" for c in sorted(somatic)[:7]) + ("<div style='color:#1a1020;font-size:.82rem;'>No confirmed somatic disease associations found in ClinVar.</div>" if not somatic else "") + "</div>", unsafe_allow_html=True)


def render_explorer_tab(pdata, gene, uid, protein_length, scored, variants, diseases, pdb, am_scores, string_data, is_gpcr, papers):
    from modules.visualization import viewer_html, render_domain_expansion_cards

    sh("🔬", "Protein Explorer — click any residue to inspect")
    if pdb:
        components.html(viewer_html(pdb, scored, 570), height=575, scrolling=False)
    else:
        st.info("No AlphaFold structure — try searching by UniProt accession (e.g. P04637).")

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    _research_domain_ctx = st.session_state.get("goal_label", "")
    render_domain_expansion_cards(pdata, variants, scored, am_scores, _research_domain_ctx, gene, uid, pdb)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🧫", "Mutation Analysis — what happens when you change one building block?")
    seq = g_seq(pdata)
    if seq:
        from modules.visualization import parse_bfactors
        bf = parse_bfactors(pdb) if pdb else {}
        pos_to_v = {int(v.get("start", 0) or 0): v2 for v2 in scored if int(v.get("start", 0) or 0) and str(v2.get("start", "0")).replace("-", "").isdigit()}
        cs4, cm = st.columns([1, 2], gap="large")
        with cs4:
            position = int(st.number_input("Amino acid (building block) position", 1, max(len(seq), 1), 1, 1, key="rpos"))
            aa = seq[position - 1] if position <= len(seq) else "?"
            pl = bf.get(position)
            conf = ("Very High" if pl and pl >= 90 else "Confident" if pl and pl >= 70 else "Low" if pl and pl >= 50 else "Very Low") if pl else "—"
            st.markdown(f"<div class='card'><h4>Position {position} — {aa} ({AA_NAMES.get(aa, 'Unknown')})</h4><p>Model confidence (pLDDT): <b style='color:#00e5ff;'>{f'{pl:.1f}' if pl else '—'}</b> ({conf})<br>Water affinity (hydropathy): <b>{AA_HYDRO.get(aa, 0):+.1f}</b><br>Electric charge: <b>{AA_CHG.get(aa, 0):+.1f}</b></p></div>", unsafe_allow_html=True)
            vd = pos_to_v.get(position)
            if vd:
                rk2 = vd.get("ml_rank", "NEUTRAL")
                clr2 = RANK_CLR[rk2]
                css2 = RANK_CSS[rk2]
                url_vd = vd.get("url", "")
                st.markdown(f"<div class='card' style='border-color:{clr2}33;'><h4 style='color:{clr2};'>⚠️ ClinVar Disease Variant Here</h4><p>{'pathogenic' if vd.get('score', 0) >= 4 else vd.get('sig', '—')}<br><small style='color:#5a8090;'>{vd.get('condition', '')[:80]}</small></p>{'<a href=\"' + url_vd + '\" target=\"_blank\" style=\"color:#2a6a8a;font-size:1.02rem;\">View in ClinVar ↗</a>' if url_vd else ''}</div>", unsafe_allow_html=True)
            else:
                st.success("No ClinVar disease variant at this position", icon="✅")
        with cm:
            tb1, tb2 = st.tabs(["Building-block properties", "What if it mutates? →"])
            with tb1:
                SPECIAL = {"C": "Disulfide bonds · metal binding", "G": "Most flexible · helix-breaker", "P": "Rigid ring · helix-breaker", "H": "pH-sensitive (pKa≈6)", "W": "Largest · UV-absorbing", "Y": "Phosphorylation (chemical tagging) target", "R": "DNA/RNA binding · +1 charge", "K": "Ubiquitination target · +1", "D": "Catalytic acid · −1", "E": "Catalytic acid · −1"}
                for lbl, val in [("Building block (amino acid)", f"{aa} — {AA_NAMES.get(aa, '?')}"), ("Water affinity (hydropathy)", f"{AA_HYDRO.get(aa, 0):+.1f} (positive=water-hating, negative=water-loving)"), ("Electric charge", f"{AA_CHG.get(aa, 0):+.1f}"), ("Special role", SPECIAL.get(aa, "No special designation"))]:
                    st.markdown(f"<div style='display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #040c18;'><span style='color:#5a8090;font-size:.79rem;'>{lbl}</span><span style='color:#5a8090;font-size:.79rem;font-weight:600;'>{val}</span></div>", unsafe_allow_html=True)
            with tb2:
                alts = [a for a in AA_NAMES.keys() if a != aa]
                alt = st.selectbox("Replace with:", alts, key="alt_aa")
                sev = st.slider("Structural disruption magnitude (how severe?)", 0.0, 1.0, .5, .05, key="sev")
                if bf:
                    pos_list = sorted(bf.keys())
                    window = 32
                    center = min(max(position, window + 1), max(pos_list) - window)
                    dp = [p4 for p4 in pos_list if abs(p4 - center) <= window]
                    wt2 = [bf.get(p4, 70) for p4 in dp]
                    mt2 = [max(0, wt2[i] - sev * 28 * math.exp(-.5 * ((p4 - position) / 6) ** 2)) for i, p4 in enumerate(dp)]
                    fig5 = go.Figure()
                    fig5.add_trace(go.Scatter(x=dp, y=wt2, mode="lines", name="Normal protein", line=dict(color="#00e5ff", width=2)))
                    fig5.add_trace(go.Scatter(x=dp, y=mt2, mode="lines", name=f"Mutant {aa}{position}{alt}", line=dict(color="#ff2d55", width=2, dash="dash")))
                    fig5.add_trace(go.Scatter(x=dp + dp[::-1], y=mt2 + wt2[::-1], fill="toself", fillcolor="rgba(255,45,85,.07)", line=dict(color="rgba(0,0,0,0)"), showlegend=False))
                    fig5.add_vline(x=position, line_color="#ffd60a", line_dash="dot", annotation_text=f"p.{aa}{position}{alt}", annotation_font_color="#ffd60a", annotation_font_size=10)
                    fig5.update_layout(paper_bgcolor="#04080f", plot_bgcolor="#04080f", font_color="#1e4060", xaxis=dict(title="Position in protein", gridcolor="#060f1c"), yaxis=dict(title="Model confidence (pLDDT)", range=[0, 100], gridcolor="#060f1c"), legend=dict(bgcolor="#04080f", font_size=10), margin=dict(t=8, b=28, l=28, r=8), height=220)
                    st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})
                hd = abs(AA_HYDRO.get(aa, 0) - AA_HYDRO.get(alt, 0))
                cd = abs(AA_CHG.get(aa, 0) - AA_CHG.get(alt, 0))
                imps = []
                if alt == "*": imps.append(("🔴", f"Early-stop mutation ({p('nonsense')})", "Protein production halts early → half-sized, non-functional protein → likely destroyed by cell (NMD)"))
                if hd > 3: imps.append(("🟠", f"Large water-affinity shift", f"Δ{hd:.1f} — buried building block changes polarity → protein core destabilised"))
                if cd >= 1: imps.append(("⚡", f"Electric charge change", f"Δ{cd:+.0f} — disrupts molecular attraction/repulsion in protein core"))
                if aa == "C": imps.append(("🔗", "Cysteine lost", "Molecular bridge (disulfide bond) broken → protein shape collapses"))
                if alt == "P": imps.append(("🔀", "Proline introduced", "Rigid kink inserted → helix or sheet structure likely disrupted"))
                if not imps: imps.append(("🟡", "Conservative substitution", "Small physicochemical change — likely low structural impact"))
                for icon2, title2, body2 in imps:
                    st.markdown(f"<div style='display:flex;gap:8px;background:#05101e;border:1px solid #0c2040;border-radius:8px;padding:8px 10px;margin:4px 0;'><span style='font-size:1.05rem;flex-shrink:0;'>{icon2}</span><div><div style='color:#5a8090;font-size:.96rem;font-weight:700;'>{title2}</div><div style='color:#5a8090;font-size:1.02rem;margin-top:1px;'>{body2}</div></div></div>", unsafe_allow_html=True)

    render_citations(papers, 4)


def render_experiments_tab(pdata, gene, uid, protein_length, gi, scored, variants, diseases, gnomad_data, papers, entity, is_gpcr, gpcr_assessment, active_goal, roi_data, reg_paths, analogs, ot_data, drugs_data, hotspots, string_data):
    from modules.visualization import mutation_cascade_html, build_druggability_map_html

    ptype = g_ptype(pdata)
    drugg = {"kinase": .9, "gpcr": .95, "transcription_factor": .35, "receptor": .8, "general": .5}.get(ptype, .5)
    n_crit2 = sum(1 for v2 in scored if v2.get("ml_rank") == "CRITICAL")
    n_high2 = sum(1 for v2 in scored if v2.get("ml_rank") == "HIGH")
    priority = min(100, n_crit2 * 15 + n_high2 * 8 + len(scored) * .5 + drugg * 20)
    c1e, c2e, c3e, c4e = st.columns(4)
    with c1e: st.markdown(mc(n_crit2, "CRITICAL (ML)", "#ff2d55"), unsafe_allow_html=True)
    with c2e: st.markdown(mc(n_high2, "HIGH (ML)", "#ff8c42"), unsafe_allow_html=True)
    with c3e: st.markdown(mc(f"{drugg:.0%}", "Druggability est.", "#00c896"), unsafe_allow_html=True)
    with c4e: st.markdown(mc(int(priority), "Priority score / 100", "#00e5ff"), unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    sh("🎬", "Mutation Cascade — How does a DNA change lead to disease?")
    top_p_vars = gi.get("pathogenic_list", []) or scored[:3]
    components.html(mutation_cascade_html(gene, is_gpcr, gi["pursue"], top_p_vars), height=480, scrolling=False)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    # Genomic verdict
    sh("🧬", "Genomic Verdict — Should you invest in this protein?")
    gi_clr4 = gi.get("color", "#3a6080")
    pursue_recs = {"prioritise": "✅ INVEST — genetics confirms this is a real, important target. Proceed to CRISPR knock-in + biochemical validation immediately.",
                   "proceed": "🟠 PROCEED — meaningful evidence. Focus only on confirmed disease-causing variants.",
                   "selective": "🟡 BE SELECTIVE — work only on confirmed P/LP variants. Do not extrapolate.",
                   "caution": "⚠️ CAUTION — very low disease burden. Verify partner proteins carry the actual risk first.",
                   "deprioritise": "🛑 DO NOT INVEST — zero Mendelian disease variants. Risk of wasted resources is high.",
                   "neutral": "❓ HOLD — insufficient data. Need more ClinVar submissions before a genetics-based decision."}
    st.markdown(f"<div class='{gi.get('css', '')}'><div style='color:{gi_clr4};font-weight:800;font-size:1.05rem;margin-bottom:5px;'>{gi.get('icon', '')} {gi.get('verdict', '')}: {gi.get('label', '')}</div><div style='color:{gi_clr4}88;font-size:1.02rem;margin-bottom:.6rem;'>{gi.get('explanation', '')}</div><div style='color:{gi_clr4};font-weight:700;font-size:.94rem;margin-bottom:.5rem;'>{pursue_recs.get(gi.get('pursue', ''), '—')}</div><div style='color:#5a8090;font-size:.81rem;font-style:italic;border-top:1px solid {gi_clr4}22;padding-top:.5rem;'>Principle: <em>Protein structures by themselves are not a validation of biology. DNA sequences are. Genetics must be the starting point of any biology.</em><br>Sources: {src_link('ClinVar', f'https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]')} · {src_link('UniProt', f'https://www.uniprot.org/uniprotkb/{uid}')}</div></div>", unsafe_allow_html=True)

    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("🎯", "Druggability Targeting Map — Where and How to Drug This Protein")
    drug_map_html = build_druggability_map_html(gene=gene, protein_length=protein_length, hotspots=hotspots, scored=scored, ot_data=ot_data, gnomad=gnomad_data, ptype=g_ptype(pdata), is_gpcr=is_gpcr, drugs_data=drugs_data)
    components.html(drug_map_html, height=600, scrolling=True)

    # Experiment ROI Calculator
    st.markdown("<hr class='dv'>", unsafe_allow_html=True)
    sh("📈", "Experiment ROI Calculator — Ranked by Expected Value")
    for rank, exp in enumerate(roi_data, 1):
        roi_clr = {"🟢 Excellent": "#00c896", "🟡 Good": "#ffd60a", "🟠 Fair": "#ff8c42", "🔴 Low": "#ff2d55"}.get(exp["roi_label"], "#3a6080")
        cost_str = "FREE" if exp["cost_usd"] == 0 else f"${exp['cost_usd']//1000}K" if exp["cost_usd"] >= 1000 else f"${exp['cost_usd']}"
        time_str = f"{exp['time_weeks']}w" if exp["time_weeks"] >= 1 else f"{int(exp['time_weeks'] * 7)}d"
        st.markdown(f"<div style='background:#020810;border:1px solid #0d2545;border-radius:10px;padding:.8rem 1.1rem;margin:.4rem 0;display:flex;gap:12px;align-items:flex-start;'><div style='min-width:28px;color:{roi_clr};font-weight:800;font-size:1.1rem;text-align:center;'>#{rank}</div><div style='flex:1;'><div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap;'><span style='color:#d0e8ff;font-weight:700;font-size:.9rem;'>{exp['name']}</span><span style='background:{roi_clr}22;color:{roi_clr};border:1px solid {roi_clr}44;padding:1px 8px;border-radius:6px;font-size:.74rem;font-weight:700;'>{exp['roi_label']}</span><span style='color:#3a6080;font-size:.78rem;'>{exp['category']}</span><span style='color:#5a8090;font-size:.78rem;'>{cost_str}</span><span style='color:#5a8090;font-size:.78rem;'>⏱ {time_str}</span>{'<span style="color:#00c896;font-size:.74rem;font-weight:700;">✓ Do first</span>' if exp.get('do_first') else ''}</div><div style='color:#5a8090;font-size:.82rem;line-height:1.5;'>{exp['rationale']}</div><div style='display:flex;align-items:center;gap:6px;margin-top:4px;'><span style='color:#2a5060;font-size:.74rem;'>ROI score:</span><div style='flex:1;max-width:120px;height:5px;background:#0a1828;border-radius:3px;overflow:hidden;'><div style='width:{min(100, int(exp["roi"] / 8 * 100))}%;height:100%;background:{roi_clr};'></div></div><span style='color:{roi_clr};font-size:.78rem;font-weight:700;'>{exp["roi"]}</span></div></div></div>", unsafe_allow_html=True)


def render_ai_report_tab(pdata, gene, uid, scored, variants, diseases, papers, abstracts, string_data, gnomad_data, trials_data, drugs_data, is_gpcr, gpcr_assessment, active_goal, assay, am_scores, ot_data, hotspots, patient_data, roi_data):
    from modules.utils import classify_experiment_type

    sh("🤖", "AI Intelligence Report")
    st.markdown("<div style='background:#020810;border:1px solid #00e5ff22;border-radius:10px;padding:.9rem 1.2rem;margin-bottom:1rem;'><div style='color:#d0e8ff;font-weight:700;font-size:.95rem;margin-bottom:4px;'>About this report</div><div style='color:#5a8090;font-size:.86rem;line-height:1.6;'>This report is generated by Claude (Anthropic) reasoning over ALL fetched data. <b style='color:#8ab8cc;'>Claude cannot hallucinate here</b> — it only reasons about the data explicitly provided to it.</div></div>", unsafe_allow_html=True)

    col_run, col_status = st.columns([2, 3])
    with col_run:
        run_ai = st.button("🤖 Generate AI Report", use_container_width=True, type="primary")
    with col_status:
        if st.session_state.get("ai_result"):
            st.markdown("<div style='color:#00c896;font-size:.86rem;padding-top:.4rem;'>✅ Report generated — scroll down</div>", unsafe_allow_html=True)

    if run_ai:
        with st.spinner(f"🧠 Claude is analysing all data for {gene}..."):
            am_summary = f"{len(am_scores)} positions with AlphaMissense data" if am_scores else "Not available"
            ot_summary = f"Druggability: {list(ot_data.get('tractability', {}).keys())} | {len(ot_data.get('known_drugs', []))} known drugs" if ot_data else "Not available"
            hotspot_summary = f"{len(hotspots)} hotspot clusters" if hotspots else "None detected"
            patient_summary = f"~{patient_data.get('estimated_global_patients', 0):,} global patients" if patient_data else "Unknown"
            result = ai_synthesize(gene=gene, pdata=pdata, cv=st.session_state.get("cv", {}), gi=st.session_state.get("gi", {}), papers=papers, abstracts=abstracts, string_data=string_data, gnomad=gnomad_data, trials=trials_data, drugs=drugs_data, scored=scored, gpcr_assessment=gpcr_assessment, goal=active_goal, assay_text=assay)
            result["alphamissense_note"] = am_summary
            result["opentargets_note"] = ot_summary
            result["hotspot_note"] = hotspot_summary
            result["patient_note"] = patient_summary
            result["roi_top3"] = [f"#{i+1} {e['name']} (ROI={e['roi']}, {e['roi_label']})" for i, e in enumerate(roi_data[:3])]
            st.session_state["ai_result"] = result
            st.rerun()

    ai = st.session_state.get("ai_result", {})
    if ai:
        verdict = ai.get("one_line_verdict", "")
        exec_sum = ai.get("executive_summary", "")
        confidence = ai.get("confidence", "?")
        conf_clr = {"HIGH": "#00c896", "MEDIUM": "#ffd60a", "LOW": "#ff8c42", "N/A": "#3a6080"}.get(confidence, "#3a6080")
        if verdict:
            st.markdown(f"<div style='background:#03100a;border:1px solid #00c89633;border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:.8rem;'><div style='display:flex;justify-content:space-between;align-items:flex-start;'><div style='color:#00c896;font-weight:800;font-size:1rem;margin-bottom:6px;'>🎯 AI Verdict</div><div style='color:{conf_clr};font-size:.78rem;border:1px solid {conf_clr}44;padding:2px 8px;border-radius:6px;'>Confidence: {confidence}</div></div><div style='color:#d0e8ff;font-size:.95rem;font-weight:600;margin-bottom:8px;'>{verdict}</div><div style='color:#6a9ab0;font-size:.88rem;line-height:1.7;'>{exec_sum}</div></div>", unsafe_allow_html=True)

        exps_done = ai.get("experiments_done", [])
        if exps_done:
            sh("📚", f"What Has Already Been Done on {gene}?")
            for e2 in exps_done:
                st.markdown(f"<div style='background:#020810;border:1px solid #0d2545;border-left:3px solid #4a90d9;border-radius:0 10px 10px 0;padding:.8rem 1.1rem;margin:.4rem 0;'><div style='color:#7ab8d0;font-weight:700;font-size:.88rem;margin-bottom:3px;'>{e2.get('type', '?')}</div><div style='color:#6a9ab0;font-size:.84rem;margin-bottom:3px;'><b style='color:#8ab8cc;'>Finding:</b> {e2.get('finding', '')}</div><div style='color:#4a7080;font-size:.82rem;'><b style='color:#6a9880;'>Gap:</b> {e2.get('gap', '')}</div></div>", unsafe_allow_html=True)


def render_workspace_tab():
    user_plan_ws = st.session_state.get("auth_plan", "free")
    limit_ws = PLAN_LIMITS[user_plan_ws]["history"]
    ws = st.session_state.get("workspace", [])

    plan_clr_ws = {"free": "#3a6080", "pro": "#00e5ff", "enterprise": "#a855f7"}.get(user_plan_ws, "#3a6080")
    st.markdown(f"<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:.8rem;'><div style='color:#5a8090;font-size:.86rem;'>{len(ws)} / {limit_ws} saved analyses · Plan: <b style='color:{plan_clr_ws};'>{user_plan_ws.upper()}</b></div></div>", unsafe_allow_html=True)

    if not ws:
        st.markdown("<div style='background:#020810;border:1px solid #0d2545;border-radius:10px;padding:2rem;text-align:center;color:#3a6080;'><div style='font-size:1.2rem;margin-bottom:.5rem;'>No analyses saved yet</div><div style='font-size:.86rem;'>Search a protein in the sidebar to begin.</div></div>", unsafe_allow_html=True)
    else:
        n_pursue = sum(1 for w in ws if w.get("verdict") in ("prioritise", "proceed"))
        n_caution = sum(1 for w in ws if w.get("verdict") in ("selective", "caution"))
        n_depri = sum(1 for w in ws if w.get("verdict") == "deprioritise")
        wsc1, wsc2, wsc3 = st.columns(3)
        with wsc1: st.markdown(f"<div class='mc' style='border-color:#ff2d5533;'><div class='mc-v' style='color:#ff2d55;'>{n_pursue}</div><div class='mc-l'>PURSUE</div></div>", unsafe_allow_html=True)
        with wsc2: st.markdown(f"<div class='mc' style='border-color:#ffd60a33;'><div class='mc-v' style='color:#ffd60a;'>{n_caution}</div><div class='mc-l'>SELECTIVE / CAUTION</div></div>", unsafe_allow_html=True)
        with wsc3: st.markdown(f"<div class='mc' style='border-color:#3a6080;'><div class='mc-v' style='color:#3a6080;'>{n_depri}</div><div class='mc-l'>DEPRIORITISE</div></div>", unsafe_allow_html=True)

        st.markdown("<hr class='dv'>", unsafe_allow_html=True)

        ws_filter = st.text_input("Filter workspace", placeholder="Search gene name or disease...", label_visibility="collapsed", key="ws_filter")
        if st.button("Clear all history", key="ws_clear"):
            st.session_state["workspace"] = []
            st.rerun()

        st.markdown("<hr class='dv'>", unsafe_allow_html=True)

        for w_idx, w in enumerate(ws):
            if ws_filter and ws_filter.lower() not in (w.get("gene", "") + " ".join(w.get("diseases", []))).lower():
                continue
            verdict_w = w.get("verdict", "")
            v_clr_w = {"prioritise": "#ff2d55", "proceed": "#ff8c42", "selective": "#ffd60a", "caution": "#ffd60a", "deprioritise": "#3a5a7a", "neutral": "#1e6080"}.get(verdict_w, "#3a6080")
            v_label_w = {"prioritise": "PURSUE", "proceed": "PROCEED", "selective": "BE SELECTIVE", "caution": "CAUTION", "deprioritise": "DEPRIORITISE", "neutral": "INSUFFICIENT DATA"}.get(verdict_w, verdict_w.upper())
            density_w = w.get("density", 0)

            with st.expander(f"{w.get('gene', '')}  ·  {v_label_w}  ·  {density_w:.2f} disease variants/100 residues  ·  {w.get('timestamp', '')}", expanded=False):
                wca, wcb = st.columns([3, 2], gap="large")
                with wca:
                    st.markdown(f"<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:.6rem;'><span style='background:{v_clr_w}22;color:{v_clr_w};border:1px solid {v_clr_w}44;padding:2px 12px;border-radius:8px;font-size:.8rem;font-weight:700;'>{v_label_w}</span><span style='background:#0d254533;color:#3a6080;padding:2px 10px;border-radius:8px;font-size:.78rem;'>UniProt: {w.get('uid', '')}</span></div><div style='color:#4a7090;font-size:.84rem;margin-bottom:.4rem;'>{w.get('n_pathogenic', 0)} pathogenic / {w.get('n_total', 0)} total ClinVar variants · Density: {density_w}/100 residues</div><div style='color:#3a6080;font-size:.8rem;'><b style='color:#5a8090;'>Diseases:</b> {', '.join(w.get('diseases', [])[:4])}</div>", unsafe_allow_html=True)
                    if w.get("scored_top"):
                        st.markdown(f"<div style='color:#3a6070;font-size:.78rem;margin-top:.4rem;'><b style='color:#4a8090;'>Top variants:</b> {' · '.join(f'{vn} ({vr})' for vn, vr in w['scored_top'][:3])}</div>", unsafe_allow_html=True)
                with wcb:
                    if st.button(f"Reload {w.get('gene', '')}", key=f"ws_reload_{w_idx}"):
                        st.session_state["last"] = ""
                        st.session_state["protein_query_val"] = w.get("gene", "")
                        st.rerun()
                    if st.button(f"Remove", key=f"ws_remove_{w_idx}"):
                        st.session_state["workspace"].pop(w_idx)
                        st.rerun()


def render_disease_link_tab(pdata, gene, uid, scored, variants, diseases, is_gpcr, gpcr_assessment, entity):
    sh("🔗", "Disease ↔ Protein Causal Link Analysis")
    dis_search_ws = st.session_state.get("disease_search", "")

    if not pdata:
        st.info("Search a protein in the sidebar to see its relationship to a disease.")
    elif not dis_search_ws:
        st.markdown(f"<div style='color:#4a7090;font-size:.86rem;margin-bottom:.4rem;'>Enter a disease to link with <b style='color:#00e5ff;'>{gene}</b>:</div>", unsafe_allow_html=True)
        link_disease = st.text_input("Disease name", placeholder="e.g. cardiomyopathy · breast cancer · Fanconi anemia", key="link_disease_inp")
        if st.button("Analyse link", type="primary", key="link_dis_btn") and link_disease:
            st.session_state["disease_search"] = link_disease
            st.rerun()
    else:
        link_dis = dis_search_ws
        dis_variants = [v for v in variants if link_dis.lower()[:15] in v.get("condition", "").lower() and v.get("score", 0) >= 2]
        path_dis_vars = [v for v in dis_variants if v.get("score", 0) >= 4]
        uniprot_match = [d for d in diseases if link_dis.lower()[:12] in d.get("name", "").lower()]
        has_clinvar = len(path_dis_vars) > 0
        has_uniprot = len(uniprot_match) > 0
        has_mendelian = has_clinvar and has_uniprot

        if has_mendelian:
            link_verdict = "DIRECT CAUSAL LINK"
            link_clr = "#ff2d55"
            link_strength = 95
            link_evidence = f"Both ClinVar pathogenic variants AND UniProt disease annotation confirm {gene} as a direct genetic driver of {link_dis}."
        elif has_clinvar:
            link_verdict = "STRONG GENETIC ASSOCIATION"
            link_clr = "#ff8c42"
            link_strength = 70
            link_evidence = f"{len(path_dis_vars)} pathogenic variants in ClinVar link {gene} to {link_dis}."
        elif has_uniprot:
            link_verdict = "ANNOTATED ASSOCIATION"
            link_clr = "#ffd60a"
            link_strength = 50
            link_evidence = f"{gene} is listed in UniProt disease comments for {link_dis}."
        else:
            link_verdict = "NO DIRECT LINK FOUND"
            link_clr = "#3a6080"
            link_strength = 5
            link_evidence = f"No ClinVar pathogenic variants or UniProt annotations linking {gene} to {link_dis}."

        st.markdown(f"<div style='background:#020810;border:2px solid {link_clr}55;border-radius:14px;padding:1.2rem 1.5rem;margin-bottom:1rem;'><div style='display:flex;align-items:center;gap:14px;margin-bottom:.6rem;'><div><div style='color:{link_clr};font-weight:800;font-size:1.1rem;margin-bottom:3px;'>{link_verdict}</div><div style='color:#8ab8cc;font-size:.95rem;'>{gene} ↔ {link_dis}</div></div></div><div style='height:10px;background:#0a1828;border-radius:5px;margin:.6rem 0;overflow:hidden;'><div style='width:{link_strength}%;height:100%;background:linear-gradient(90deg,{link_clr}88,{link_clr});border-radius:5px;'></div></div><div style='color:#6a9ab0;font-size:.86rem;'>{link_evidence}</div></div>", unsafe_allow_html=True)

        if st.button("Clear disease link", key="clear_link_btn"):
            st.session_state["disease_search"] = ""
            st.rerun()


def render_chemistry_tab(pdata, gene, uid, protein_length, scored, variants, pdb, am_scores, diseases):
    from modules.visualization import render_chemical_backbone, kyte_doolittle, calc_pI, aa_composition
    import plotly.graph_objects as go

    seq = g_seq(pdata)
    is_gpcr_c = g_gpcr(pdata)
    is_kin_c = g_ptype(pdata) == "kinase"

    sh("⚗️", "Chemical & Receptor Biology — Full Protein Chemistry")
    if seq:
        mw_kda = round(sum({"A": 89, "R": 174, "N": 132, "D": 133, "C": 121, "Q": 146, "E": 147, "G": 75, "H": 155, "I": 131, "L": 131, "K": 146, "M": 149, "F": 165, "P": 115, "S": 105, "T": 119, "W": 204, "Y": 181, "V": 117}.get(aa, 110) for aa in seq) / 1000, 1)
        pi_est = calc_pI(seq)
        charge_74 = round(sum({"K": 1, "R": 1, "H": 0.1, "D": -1, "E": -1}.get(aa, 0) for aa in seq), 1)
        n_cys = seq.count("C")
        n_ser = seq.count("S") + seq.count("T") + seq.count("Y")

        cols_prop = st.columns(6)
        props = [("Molecular Weight", f"{mw_kda} kDa", "#00e5ff"), ("Length", f"{len(seq):,} aa", "#00e5ff"), ("Est. pI", str(pi_est), "#6478ff" if pi_est < 7 else "#ff8c42"), ("Net charge pH 7.4", f"{charge_74:+.0f}", "#ff2d55" if charge_74 < 0 else "#22c55e"), ("Cys (potential SS)", f"{n_cys} C / {n_cys//2} bonds", "#ffd60a"), ("Phospho targets", f"{n_ser} S/T/Y", "#f97316")]
        for col, (lbl, val, clr) in zip(cols_prop, props):
            with col:
                st.markdown(f"<div class='mc' style='--clr:{clr};--acc:linear-gradient(90deg,{clr},{clr}88);'><div class='mv' style='font-size:1.2rem;'>{val}</div><div class='ml2'>{lbl}</div></div>", unsafe_allow_html=True)

        st.markdown("<hr class='dv'>", unsafe_allow_html=True)

        sh("🌊", "Kyte-Doolittle Hydrophobicity Profile — Membrane Regions & Core")
        hydro_profile = kyte_doolittle(seq, window=9)
        sample_step = max(1, len(hydro_profile) // 800)
        hp_x = [h[0] for h in hydro_profile[::sample_step]]
        hp_y = [h[1] for h in hydro_profile[::sample_step]]
        fig_hydro = go.Figure()
        fig_hydro.add_trace(go.Scatter(x=hp_x, y=[max(0, v) for v in hp_y], mode="lines", fill="tozeroy", line=dict(color="#ff8c42", width=0), fillcolor="rgba(255,140,66,.2)", name="Hydrophobic"))
        fig_hydro.add_trace(go.Scatter(x=hp_x, y=[min(0, v) for v in hp_y], mode="lines", fill="tozeroy", line=dict(color="#4a90d9", width=0), fillcolor="rgba(74,144,217,.2)", name="Hydrophilic"))
        fig_hydro.add_trace(go.Scatter(x=hp_x, y=hp_y, mode="lines", line=dict(color="#00e5ff", width=1.5), name="Profile"))
        fig_hydro.add_hline(y=1.6, line_dash="dot", line_color="rgba(255,140,66,0.4)", annotation_text="TM threshold (1.6)", annotation_font_color="#ff8c42", annotation_font_size=9)
        fig_hydro.update_layout(paper_bgcolor="#010306", plot_bgcolor="#010306", font_color="#3a6080", xaxis=dict(title="Residue position", gridcolor="#040c18"), yaxis=dict(title="KD hydrophobicity score", gridcolor="#040c18"), height=280, margin=dict(t=10, b=36, l=55, r=10))
        st.plotly_chart(fig_hydro, use_container_width=True, config={"displayModeBar": False})

    if pdb:
        st.markdown("<hr class='dv'>", unsafe_allow_html=True)
        sh("⚡", "Electrostatic Surface — Charge Distribution (3D)")
        pdb_esc = pdb.replace("\\", "\\\\").replace("`", "\\`")
        elec_html = f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.4/3Dmol-min.js"></script>
<style>body{{margin:0;background:#010306;overflow:hidden;}}
#v{{width:100%;height:360px;}}
#leg{{position:absolute;top:8px;right:8px;background:rgba(1,3,6,.9);border:1px solid #0d2545;
  border-radius:7px;padding:7px 11px;font:9px Inter,sans-serif;}}
.lr{{display:flex;align-items:center;gap:6px;margin:2px 0;color:#3a6080;}}
.lc{{width:10px;height:10px;border-radius:50%;flex-shrink:0;}}
</style></head><body>
<div id="v"></div>
<div id="leg">
  <b style="color:#00e5ff;font-size:9px;">Electrostatics</b>
  <div class="lr"><div class="lc" style="background:#4a90d9;"></div>Positive (K/R/H)</div>
  <div class="lr"><div class="lc" style="background:#ff2d55;"></div>Negative (D/E)</div>
  <div class="lr"><div class="lc" style="background:#5a8090;"></div>Neutral</div>
</div>
<script>
try{{
  var viewer=$3Dmol.createViewer(document.getElementById('v'),{{backgroundColor:'#010306'}});
  viewer.addModel(`{pdb_esc}`,'pdb');
  viewer.setStyle({{}},{{cartoon:{{color:'spectrum',opacity:0.45}}}});
  viewer.addSurface($3Dmol.SurfaceType.VDW,{{opacity:0.80,colorfunc:function(a){{
    var pos=['LYS','ARG','HIS'];
    var neg=['ASP','GLU'];
    if(pos.indexOf(a.resn)>=0) return '#00aaff';
    if(neg.indexOf(a.resn)>=0) return '#ff3355';
    return '#00cc77';
  }}}});
  viewer.zoomTo();viewer.render();
}}catch(e){{document.getElementById('v').innerHTML='<p style="color:#ff8c42;padding:14px;">'+e.message+'</p>';}}
</script></body></html>"""
        components.html(elec_html, height=365, scrolling=False)


def render_pharma_tab(pdata, gene, uid, protein_length, scored, variants, diseases, gnomad_data, papers, entity, is_gpcr, gpcr_assessment, ot_data, drugs_data, pdb, gi):
    sh("💊", f"Pharmaceutical Atlas — {gene} Drug Development Landscape")

    _sm_tract = ot_data.get("tractability", {}).get("Small molecule", False) if ot_data else False
    _n_drugs = len(drugs_data)
    _n_crit9 = sum(1 for v in scored if v.get("ml_rank") == "CRITICAL")
    _pLI9 = gnomad_data.get("pLI", 0) or 0

    _score_gen = min(10, _n_crit9 * 1.2 + (gi.get("n_pathogenic", 0) or 0) * 0.3)
    _score_tract = min(10, (_sm_tract * 4) + min(3, _n_drugs * 0.5))
    _score_ess = min(10, _pLI9 * 8 + (2 if is_gpcr else 0))
    _score_str = min(10, 7 if pdb else 3)
    _score_disc = min(10, len(diseases) * 1.5)
    _total_drug = round((_score_gen + _score_tract + _score_ess + _score_str + _score_disc) / 5, 1)

    d_col = "#22c55e" if _total_drug >= 7 else "#ffd60a" if _total_drug >= 4 else "#ff2d55"
    st.markdown(f"<div style='background:linear-gradient(135deg,#000308,#010810);border:2px solid {d_col}44;border-radius:14px;padding:1.1rem 1.4rem;margin-bottom:.8rem;'><div style='display:flex;align-items:center;gap:16px;'><div style='text-align:center;min-width:90px;'><div style='font-size:3rem;font-weight:800;color:{d_col};line-height:1;'>{_total_drug}</div><div style='color:#1e4060;font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;'>/ 10 Druggability</div></div><div style='flex:1;'>" + "".join(f"<div style='display:flex;align-items:center;gap:8px;margin:4px 0;'><span style='color:#3a6080;font-size:.72rem;min-width:120px;'>{name}</span><div style='flex:1;max-width:200px;height:6px;background:#071828;border-radius:3px;overflow:hidden;'><div style='width:{int(score / 10 * 100)}%;height:100%;background:{clr};border-radius:3px;'></div></div><span style='color:{clr};font-size:.72rem;font-weight:700;min-width:24px;text-align:right;'>{score:.1f}</span></div>" for name, score, clr in [("Genetic evidence", _score_gen, "#ff2d55"), ("Tractability", _score_tract, "#00e5ff"), ("Essentiality (pLI)", _score_ess, "#a855f7"), ("Structure available", _score_str, "#22c55e"), ("Disease burden", _score_disc, "#ffd60a")]) + "</div></div></div>", unsafe_allow_html=True)

    all_drugs9 = list({d.get("drug") for d in drugs_data if d.get("drug")})[:12]
    if all_drugs9:
        sh("💊", "Known Drug Interactions & Approved Compounds")
        drug_cols9 = st.columns(4)
        for di2, drg in enumerate(all_drugs9):
            with drug_cols9[di2 % 4]:
                _dtype9 = next((d.get("type", "?") for d in drugs_data if d.get("drug") == drg), "?")
                st.markdown(f"<div style='background:#010810;border:1px solid #071828;border-radius:8px;padding:7px 9px;margin:3px 0;text-align:center;'><div style='color:#00e5ff;font-size:.78rem;font-weight:700;'>💊 {drg}</div><div style='color:#1e4060;font-size:.64rem;'>{_dtype9[:20] if _dtype9 != '?' else 'interaction'}</div></div>", unsafe_allow_html=True)
