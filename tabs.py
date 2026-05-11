"""tabs.py — All tab + page functions. Proper module, imported as T in app.py."""
import streamlit as st
import streamlit.components.v1 as components
import numpy as np, pandas as pd, plotly.graph_objects as go
import math, re
import ui

# ── 3D viewer ──────────────────────────────────────────────────────────────
def viewer_3d(pdb_text, style="plddt", height=380, spin=False):
    if not pdb_text:
        st.markdown('<div class="dim" style="padding:8px">AlphaFold structure not available.</div>', unsafe_allow_html=True)
        return
    esc = pdb_text.replace("\\","\\\\").replace("`","\\`")
    sp = "viewer.spin(true);" if spin else ""
    smap = {
        "plddt": "viewer.setStyle({},{cartoon:{colorfunc:function(a){var b=a.b;if(b>=90)return'#00b4d8';if(b>=70)return'#4ab8a7';if(b>=50)return'#f5b942';return'#e05c5c';}}});",
        "spectrum": "viewer.setStyle({},{cartoon:{color:'spectrum'}});",
        "surface":  "viewer.setStyle({},{surface:{opacity:0.85,color:'spectrum'}});",
        "stick":    "viewer.setStyle({},{stick:{colorscheme:'element'}});",
    }
    sj = smap.get(style, smap["plddt"])
    html = f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.4/3Dmol-min.js"></script>
<style>body{{margin:0;background:#010306;overflow:hidden}}#v{{width:100%;height:{height}px;position:relative}}
#info{{position:absolute;bottom:6px;left:6px;background:rgba(2,6,9,.95);color:#d0e8ff;border:1px solid rgba(0,229,255,0.15);border-radius:5px;padding:5px 10px;font:11px/1.5 monospace;display:none;z-index:100;max-width:280px;pointer-events:none}}
#leg{{position:absolute;top:6px;right:6px;background:rgba(2,6,9,.9);color:#d0e8ff;border:1px solid #0a1520;border-radius:5px;padding:7px 10px;font:11px monospace}}
.lr{{display:flex;align-items:center;gap:5px;margin:2px 0}}.lc{{width:10px;height:10px;border-radius:2px}}</style>
</head><body><div id="v"></div><div id="info"></div>
<div id="leg"><b style="color:#00e5ff;font-size:10px">pLDDT</b>
<div class="lr"><div class="lc" style="background:#00b4d8"></div>&gt;90</div>
<div class="lr"><div class="lc" style="background:#4ab8a7"></div>70-90</div>
<div class="lr"><div class="lc" style="background:#f5b942"></div>50-70</div>
<div class="lr"><div class="lc" style="background:#e05c5c"></div>&lt;50</div></div>
<script>try{{
var viewer=$3Dmol.createViewer(document.getElementById('v'),{{backgroundColor:'#010306'}});
viewer.addModel(`{esc}`,'pdb');{sj}
viewer.setClickable({{}},true,function(a,v){{
  var b=document.getElementById('info');b.style.display='block';
  b.innerHTML='<b style="color:#00e5ff">'+a.resn+' '+a.resi+'</b> Chain '+a.chain+'<br>pLDDT: '+(a.b?a.b.toFixed(1):'?');
  v.addStyle({{resi:a.resi}},{{sphere:{{color:'#00e5ff',radius:0.8,opacity:0.7}}}});v.render();
}});viewer.zoomTo();{sp}viewer.render();
}}catch(e){{document.getElementById('v').innerHTML='<p style="color:#ff8c42;padding:12px;font:12px monospace">'+e.message+'</p>';}}</script>
</body></html>"""
    components.html(html, height=height, scrolling=False)


# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
def tab_summary(gene,pdata,gi,cv,gnomad,ot,dgidb,trials,papers,is_gpcr,is_filamin,is_cardiac,exps):
    verdict=gi["verdict"]; vcolor=gi["color"]
    pursue_map={True:"PURSUE",False:"DEPRIORITISE",None:"SELECTIVE"}
    pursue_label=pursue_map.get(gi.get("pursue"),"PROCEED")
    st.markdown(f"""<div style="background:{vcolor}0d;border:1px solid {vcolor}30;border-radius:5px;padding:8px 14px;display:flex;align-items:center;gap:12px;margin-bottom:8px">
      <div><span style="font-size:.95rem;font-weight:800;color:{vcolor}">{pursue_label}</span>
      <span style="background:{vcolor}18;color:{vcolor};border-radius:3px;padding:1px 6px;font-size:.65rem;font-weight:700;margin-left:5px">{verdict}</span></div>
      <div style="color:{vcolor}88;font-size:.72rem;flex:1">{' · '.join(gi.get('reasons',[])[:3])}</div>
    </div>""", unsafe_allow_html=True)

    # Metrics
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Diseases",     len(pdata.get("diseases",[])))
    c2.metric("P/LP Variants",gi.get("n_pathogenic",0))
    c3.metric("CRITICAL ML",  gi.get("n_critical",0))
    c4.metric("pLI",          f"{gnomad.get('pLI'):.2f}" if gnomad.get("pLI") else "N/A")
    c5.metric("Known Drugs",  ot.get("known_drugs_count",0))
    c6.metric("Active Trials",len(trials))

    cl,cr = st.columns([1.2,.8], gap="large")
    with cl:
        ui.section("Disease Associations")
        for d in pdata.get("diseases",[])[:6]:
            n=d.get("name","?"); desc=d.get("desc","")[:110]
            ct=("Somatic" if any(t in n.lower() for t in ["cancer","carcinoma","tumor","sarcoma"])
                else "Germline" if any(t in n.lower() for t in ["hereditary","congenital","familial"]) else "Unknown")
            cc="#ff8c42" if ct=="Somatic" else "#818cf8" if ct=="Germline" else "#4a7090"
            st.markdown(f'<div class="row {("crit" if ct=="Somatic" else "hi" if ct=="Germline" else "")}"><span style="color:{cc};font-size:.62rem;font-weight:600;min-width:52px">{ct}</span><div><b style="color:#d0e8ff;font-size:.73rem">{n}</b><br><span class="dim">{desc}</span></div></div>', unsafe_allow_html=True)
        if not pdata.get("diseases"):
            st.markdown('<div class="dim" style="padding:6px">No disease annotations — complete null mutant with no phenotype = deprioritise.</div>', unsafe_allow_html=True)
        st.markdown(ui.src("UniProt","https://www.uniprot.org"), unsafe_allow_html=True)

        ui.section("Top 5 Experiments")
        shown=0
        for exp in exps:
            if shown>=5 or exp.get("avoid"): continue
            dof=exp.get("do_first",False); color="#00e5ff" if dof else "#4a7090"
            st.markdown(f"""<div style="background:#020609;border:1px solid {"rgba(0,229,255,0.2)" if dof else "#0a1520"};border-radius:4px;padding:5px 9px;margin:3px 0">
              <div style="display:flex;justify-content:space-between">
                <span style="color:{color};font-size:.73rem;font-weight:600">{"🚀 " if dof else ""}{exp['name'][:58]}</span>
                <span style="color:#2a5070;font-size:.63rem;font-family:monospace">${exp['cost_usd']:,} · {exp['time_weeks']}w · P={int(exp['p_success']*100)}%</span>
              </div>
              <div class="dim">{exp['rationale'][:110]}…</div>
            </div>""", unsafe_allow_html=True)
            shown+=1

        ui.section("Pursue vs Avoid")
        pa1,pa2 = st.columns(2)
        pursue_items=[e for e in exps if e.get("do_first") and not e.get("avoid")][:3]
        avoid_items=[e for e in exps if e.get("avoid")][:3]
        with pa1:
            st.markdown('<div style="color:#4ade80;font-size:.67rem;font-weight:600;margin-bottom:3px">✅ PURSUE</div>', unsafe_allow_html=True)
            for e in pursue_items: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #060d14">{e["name"][:48]}</div>', unsafe_allow_html=True)
        with pa2:
            st.markdown('<div style="color:#ef4444;font-size:.67rem;font-weight:600;margin-bottom:3px">🛑 AVOID</div>', unsafe_allow_html=True)
            for e in avoid_items: st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #060d14">{e["name"][:48]}</div>', unsafe_allow_html=True)
            if not avoid_items: st.markdown('<div class="dim">None flagged.</div>', unsafe_allow_html=True)

    with cr:
        ui.section("gnomAD Constraint")
        for lbl,val,thresh,dir_h in [("pLI",gnomad.get("pLI"),0.9,"high"),
                                      ("o/e LoF",gnomad.get("lof_oe"),0.35,"low"),
                                      ("o/e Missense",gnomad.get("missense_oe"),0.6,"low")]:
            if val is None: continue
            good=(val>thresh if dir_h=="high" else val<thresh)
            col="#00e5ff" if good else "#4a7090"
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #060d14;font-size:.72rem"><span class="dim">{lbl}</span><span style="color:{col};font-family:monospace">{val:.3f}{"  ✓" if good else ""}</span></div>', unsafe_allow_html=True)
        st.markdown(ui.src("gnomAD","https://gnomad.broadinstitute.org"), unsafe_allow_html=True)

        if is_gpcr:
            with st.expander("★ H8-Filamin Assay (IP)", expanded=True):
                st.markdown('<div style="font-size:.71rem;color:#d0e8ff;line-height:1.6">GPCR agonist → H8 dislodges → binds FLNA Ig21 → PKA phosphorylates Ser2152. More receptor-proximal than cAMP, IP3, or arrestin. Only FLNA (not B/C). ~300/800 Class A GPCRs carry H8 FBM.</div>', unsafe_allow_html=True)
                st.markdown('<a class="pill" href="https://pubmed.ncbi.nlm.nih.gov/26124276/" target="_blank">Nakamura 2015 PMID:26124276</a>', unsafe_allow_html=True)
        if is_filamin:
            with st.expander("PhosphoSite Ser2152 — Signal vs Noise"):
                st.markdown('<div style="font-size:.71rem;color:#d0e8ff;line-height:1.6">Ser2152 = dominant phospho peak on FLNA. All others = background kinase noise (EGFR, activated kinases). Validated signal requires: specific mutation causes human disease. R2149 variants (heterometropia) confirm this site.</div>', unsafe_allow_html=True)
        if is_cardiac:
            with st.expander("TMAO Rattling Receptor — Arrhythmia"):
                st.markdown('<div style="font-size:.71rem;color:#d0e8ff;line-height:1.6">TMAO causes receptor conformational rattling → disrupts H8-Filamin coupling → Filamin-actin-cytoskeleton decoupling → cardiac conduction defects. Patent-unoccupied axis.</div>', unsafe_allow_html=True)

        wl = st.session_state.wet_lab_text
        if wl:
            ui.section("Wet-Lab Assay Interpretation")
            interp = ("pSer2152 readout — Filamin Ser2152-P correlates with GPCR activation. Cross-ref Step 3 protocol." if "phospho" in wl.lower() and is_gpcr
                      else "Interaction disruption detected — Co-IP with STRING top partners to validate specificity." if any(x in wl.lower() for x in ["co-ip","pull","interaction"])
                      else "Reporter signal — Cross-reference ClinVar P/LP variants at active-site residues for causality."  if any(x in wl.lower() for x in ["reporter","luciferase"])
                      else f"Functional alteration in {gene}. Map to ClinVar pathogenic variants at the affected position.")
            st.markdown(f'<div class="card"><div class="dim">{wl[:140]}</div><div style="color:#00e5ff;font-size:.71rem;margin-top:5px">{interp}</div></div>', unsafe_allow_html=True)

        drugs = ot.get("known_drugs",[]) or [d["drug"] for d in dgidb[:5]]
        if drugs:
            ui.section("Known Drugs")
            st.markdown(" ".join(f'<span class="pill">💊 {d}</span>' for d in drugs[:8]), unsafe_allow_html=True)
            st.markdown(ui.src("OpenTargets","https://platform.opentargets.org")+ui.src("DGIdb","https://dgidb.org"), unsafe_allow_html=True)
        if trials:
            ui.section("Active Trials")
            for t in trials[:3]:
                st.markdown(f'<div class="dim"><a href="{t["url"]}" target="_blank" style="color:#00e5ff">{t["nct_id"]}</a> · Ph{t["phase"]} · {t["title"][:55]}</div>', unsafe_allow_html=True)

    if papers:
        ui.section("Literature")
        for p in papers[:8]:
            st.markdown(f'<div style="display:flex;align-items:baseline;gap:5px;padding:3px 0;border-bottom:1px solid #060d14"><span class="bdc" style="background:{p["tier_color"]}18;color:{p["tier_color"]};border:1px solid {p["tier_color"]}30;min-width:50px;text-align:center;font-size:.6rem">{p["tier_label"]}</span><a href="{p["url"]}" target="_blank" style="color:#8baabf;font-size:.72rem;flex:1">{p["title"][:100]}</a><span class="dim" style="white-space:nowrap">{p["authors"][:18]} {p["year"]} PMID:{p["pmid"]}</span></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# TRIAGE
# ═══════════════════════════════════════════════════════════════════════════
def tab_triage(gene,pdata,pdb,plddt,cv,gnomad,ot,am,sensitivity=0.70):
    cl,cr = st.columns([1.1,.9], gap="large")
    with cl:
        ui.section("AlphaFold Structure (pLDDT)")
        vw=st.radio("view",["pLDDT","Spectrum","Surface","Stick"],horizontal=True,key="t1_view",label_visibility="collapsed")
        viewer_3d(pdb, style={"pLDDT":"plddt","Spectrum":"spectrum","Surface":"surface","Stick":"stick"}[vw], height=380)
        if plddt:
            vals=list(plddt.values())
            fig=go.Figure(go.Histogram(x=vals,nbinsx=25,
                marker_color=["#00b4d8" if v>=90 else "#4ab8a7" if v>=70 else "#f5b942" if v>=50 else "#e05c5c" for v in vals]))
            fig.update_layout(height=130,plot_bgcolor="#010306",paper_bgcolor="#010306",
                xaxis=dict(title="pLDDT",gridcolor="#060d14",color="#2a5070"),
                yaxis=dict(title="n",gridcolor="#060d14",color="#2a5070"),
                font=dict(color="#d0e8ff",size=10),margin=dict(t=5,b=25,l=30,r=5))
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
            avg=np.mean(vals); hc=sum(1 for v in vals if v>=70)/len(vals)*100
            st.markdown(f'<span class="dim">avg pLDDT <b style="color:#00e5ff">{avg:.1f}</b> · >70: <b style="color:#4ab8a7">{hc:.0f}%</b></span> {ui.src("AlphaFold","https://alphafold.ebi.ac.uk")}', unsafe_allow_html=True)

    with cr:
        ui.section(f"Variant Map (sensitivity {sensitivity:.2f})")
        if cv:
            seq_len=pdata.get("seq_len",500)
            fig_l=go.Figure()
            fig_l.add_trace(go.Scatter(x=[0,seq_len],y=[0,0],mode="lines",line=dict(color="#0d1a2a",width=4),hoverinfo="none",showlegend=False))
            for cls,col in {"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MODERATE":"#ffd60a","LOW":"#2a5070"}.items():
                grp=[v for v in cv if v.get("ml_class")==cls and v.get("position",0)>0]
                if grp:
                    fig_l.add_trace(go.Scatter(x=[v["position"] for v in grp],y=[1]*len(grp),mode="markers",
                        marker=dict(size=8,color=col,line=dict(color="#010306",width=1)),
                        text=[f'{v.get("protein_change","?")} — {v.get("significance","")[:25]}' for v in grp],
                        hoverinfo="text",name=cls))
            if am:
                am_p=[a for a in am if a["score"]>=sensitivity]
                if am_p:
                    fig_l.add_trace(go.Scatter(x=[a["position"] for a in am_p[::max(1,len(am_p)//200)]],y=[-0.6]*min(200,len(am_p)),
                        mode="markers",marker=dict(size=3,color="#7c3aed",opacity=0.4),name=f"AM≥{sensitivity:.2f}",hoverinfo="none"))
            fig_l.update_layout(height=200,plot_bgcolor="#010306",paper_bgcolor="#010306",
                xaxis=dict(title="Position",gridcolor="#060d14",color="#2a5070"),
                yaxis=dict(visible=False,range=[-1.5,2]),font=dict(color="#d0e8ff",size=10),
                legend=dict(bgcolor="#020609",bordercolor="#0a1520",font=dict(size=9)),
                margin=dict(t=5,b=30,l=5,r=5))
            st.plotly_chart(fig_l,use_container_width=True,config={"displayModeBar":False})
            st.markdown(ui.src("ClinVar","https://www.ncbi.nlm.nih.gov/clinvar/")+ui.src("AlphaMissense","https://alphafold.ebi.ac.uk"), unsafe_allow_html=True)

        ui.section("Variant Deep Dive")
        for v in [v for v in cv if v.get("ml_class") in ("CRITICAL","HIGH")][:8]:
            cls=v.get("ml_class","?")
            am_here=next((a for a in (am or []) if a.get("position")==v.get("position")),None)
            am_tag=(" 🟢 AM-concordant" if am_here and am_here["score"]>=sensitivity else " 🟡 AM-discordant" if am_here else "")
            conds=", ".join(v.get("conditions",[])[:2]) or "?"
            with st.expander(f'{ui.badge(cls,cls)} {v.get("protein_change","?") or v.get("title","?")[:38]}{am_tag}'):
                st.markdown(f'<div style="font-size:.71rem;line-height:1.7"><b>Significance:</b> {v.get("significance","")}<br><b>Review:</b> {v.get("review_status","")} {"⭐"*v.get("stars",0)}<br><b>Conditions:</b> {conds}<br><a href="{v.get("url","")}" target="_blank" style="color:#00e5ff;font-size:.68rem">View in ClinVar ↗</a></div>', unsafe_allow_html=True)

        ui.section("Tractability")
        t1c,t2c,t3c = st.columns(3)
        t1c.metric("Small Mol","✓" if ot.get("sm_tractable") else "—")
        t2c.metric("Antibody","✓" if ot.get("ab_tractable") else "—")
        t3c.metric("Drugs",ot.get("known_drugs_count",0))
        st.markdown(ui.src("OpenTargets","https://platform.opentargets.org"), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# CASE STUDY
# ═══════════════════════════════════════════════════════════════════════════
def tab_case_study(gene,pdata,cv,gtex,papers,is_gpcr,is_cardiac,is_filamin,string):
    cl,cr = st.columns(2, gap="large")
    with cl:
        ui.section("Function")
        for fn in pdata.get("functions",[])[:2]:
            st.markdown(f'<div class="card" style="font-size:.72rem;color:#d0e8ff;line-height:1.6">{fn[:300]}</div>', unsafe_allow_html=True)
        ui.section("Subcellular Localisation")
        locs=pdata.get("subcellular",[])
        if locs: st.markdown(" ".join(f'<span class="pill">{l}</span>' for l in locs[:8]), unsafe_allow_html=True)
        else:     st.markdown('<div class="dim">Not annotated</div>', unsafe_allow_html=True)
        st.markdown(ui.src("UniProt","https://www.uniprot.org"), unsafe_allow_html=True)
        ui.section("Tissue Expression (GTEx v8)")
        if gtex:
            items=sorted(gtex.items(),key=lambda x:x[1],reverse=True)[:20]
            fig_t=go.Figure(go.Bar(x=[i[1] for i in items],y=[i[0] for i in items],orientation="h",
                marker_color=["#00e5ff" if i[1]==max(gtex.values()) else "#1e3a5f" for i in items]))
            fig_t.update_layout(height=max(260,len(items)*19),plot_bgcolor="#010306",paper_bgcolor="#010306",
                xaxis=dict(title="Median TPM",gridcolor="#060d14",color="#2a5070"),
                yaxis=dict(color="#8baabf",autorange="reversed",tickfont=dict(size=8)),
                font=dict(color="#d0e8ff",size=10),margin=dict(l=130,r=5,t=5,b=25))
            st.plotly_chart(fig_t,use_container_width=True,config={"displayModeBar":False})
            st.markdown(ui.src("GTEx v8","https://gtexportal.org"), unsafe_allow_html=True)
        else:
            st.markdown('<div class="dim">GTEx data not available.</div>', unsafe_allow_html=True)

    with cr:
        ui.section("Structural Domains (UniProt)")
        domains=pdata.get("domains",[])
        if domains:
            df_d=pd.DataFrame(domains[:15])
            st.dataframe(df_d.rename(columns={"type":"Type","name":"Name","start":"Start","end":"End"}),
                         use_container_width=True,hide_index=True,height=min(310,len(domains)*34+36))
        if is_gpcr:
            ui.section("GPCR Study Protocol (7-Step)")
            from databases import GPCR_STUDY_PROTOCOL
            for step in GPCR_STUDY_PROTOCOL:
                if step.get("cardiac_only") and not is_cardiac: continue
                ip=step.get("ip_flag",False)
                with st.expander(f"{'★ ' if ip else ''}Step {step['step']}: {step['name']}",expanded=ip):
                    st.markdown(f'<div style="font-size:.71rem;color:#d0e8ff;line-height:1.6">{step["description"]}</div>', unsafe_allow_html=True)
                    if step.get("warning"): st.warning(step["warning"])
                    st.markdown(f'<span class="dim">{step["cost"]} · {step["time"]}</span>', unsafe_allow_html=True)
                    if ip: st.markdown('<a class="pill" href="https://doi.org/10.1074/jbc.M115.671826" target="_blank">Nakamura 2015 ↗</a>', unsafe_allow_html=True)
        if string:
            ui.section("STRING Network (score>0.7)")
            n=len(string); angles=[2*math.pi*i/n for i in range(n)]; r=3
            nx=[0]+[r*math.cos(a) for a in angles]; ny=[0]+[r*math.sin(a) for a in angles]
            nt=[gene]+[p["partner"] for p in string]; nc=["#00e5ff"]+[f"rgba(0,229,255,{min(1,p['score'])})" for p in string]
            ns=[16]+[max(5,int(p["score"]*14)) for p in string]
            ex_,ey_=[],[]
            for i in range(n): ex_+=[0,r*math.cos(angles[i]),None]; ey_+=[0,r*math.sin(angles[i]),None]
            fig_n=go.Figure()
            fig_n.add_trace(go.Scatter(x=ex_,y=ey_,mode="lines",line=dict(color="#0d1a2a",width=1),hoverinfo="none",showlegend=False))
            fig_n.add_trace(go.Scatter(x=nx,y=ny,mode="markers+text",text=nt,textposition="top center",
                textfont=dict(color="#8baabf",size=9),marker=dict(size=ns,color=nc,line=dict(color="#010306",width=1)),
                hovertext=["Query"]+[f"{p['partner']} ({p['score']:.2f})" for p in string],hoverinfo="text",showlegend=False))
            fig_n.update_layout(height=280,showlegend=False,plot_bgcolor="#010306",paper_bgcolor="#010306",
                xaxis=dict(visible=False),yaxis=dict(visible=False),margin=dict(l=5,r=5,t=5,b=5))
            st.plotly_chart(fig_n,use_container_width=True,config={"displayModeBar":False})
            st.markdown(ui.src("STRING","https://string-db.org"), unsafe_allow_html=True)

    if papers:
        ui.section("Evidence-Tiered Literature")
        for p in papers[:10]:
            st.markdown(f'<div style="display:flex;gap:5px;padding:3px 0;border-bottom:1px solid #060d14;align-items:baseline"><span class="bdc" style="background:{p["tier_color"]}18;color:{p["tier_color"]};border:1px solid {p["tier_color"]}30;min-width:48px;text-align:center;font-size:.6rem">{p["tier_label"]}</span><a href="{p["url"]}" target="_blank" style="color:#8baabf;font-size:.71rem;flex:1">{p["title"][:100]}</a><span class="dim" style="white-space:nowrap">{p["authors"][:18]} {p["year"]} PMID:{p["pmid"]}</span></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# EXPLORER
# ═══════════════════════════════════════════════════════════════════════════
def tab_explorer(gene,pdata,pdb,plddt,cv,am,string):
    cl,cr = st.columns([2,1], gap="large")
    AA = {"A":("Ala",1.8,0),"R":("Arg",-4.5,1),"N":("Asn",-3.5,0),"D":("Asp",-3.5,-1),
          "C":("Cys",2.5,0),"Q":("Gln",-3.5,0),"E":("Glu",-3.5,-1),"G":("Gly",-0.4,0),
          "H":("His",-3.2,0),"I":("Ile",4.5,0),"L":("Leu",3.8,0),"K":("Lys",-3.9,1),
          "M":("Met",1.9,0),"F":("Phe",2.8,0),"P":("Pro",-1.6,0),"S":("Ser",-0.8,0),
          "T":("Thr",-0.7,0),"W":("Trp",-0.9,0),"Y":("Tyr",-1.3,0),"V":("Val",4.2,0)}
    with cl:
        ui.section("3D Explorer — Click Any Residue")
        vw=st.radio("view",["pLDDT","Spectrum","Surface","Stick"],horizontal=True,key="ex_view",label_visibility="collapsed")
        spin=st.checkbox("Auto-spin",key="ex_spin")
        viewer_3d(pdb,style={"pLDDT":"plddt","Spectrum":"spectrum","Surface":"surface","Stick":"stick"}[vw],height=440,spin=spin)
    with cr:
        seq=pdata.get("sequence",""); seq_len=pdata.get("seq_len",0)
        ui.section("Residue Inspector")
        if seq and seq_len:
            pos=st.number_input("Position",1,max(1,seq_len),min(50,seq_len),key="res_pos_ex")
            if 1<=pos<=seq_len:
                aa=seq[pos-1].upper(); pr=AA.get(aa,("?",0,0))
                pv=plddt.get(pos,0)
                pc=("#00b4d8" if pv>=90 else "#4ab8a7" if pv>=70 else "#f5b942" if pv>=50 else "#e05c5c")
                pl=("Very High" if pv>=90 else "Confident" if pv>=70 else "Low" if pv>=50 else "Very Low")
                st.markdown(f"""<div class="card">
                  <span class="mono" style="color:#00e5ff;font-size:.9rem">{aa}{pos}</span> <span class="dim">{pr[0]}</span>
                  <table style="width:100%;font-size:.71rem;margin-top:5px">
                  <tr><td class="dim">Hydrophobicity</td><td style="color:#d0e8ff;font-family:monospace">{pr[1]}</td></tr>
                  <tr><td class="dim">Charge</td><td style="color:#d0e8ff;font-family:monospace">{pr[2]:+}</td></tr>
                  <tr><td class="dim">pLDDT</td><td style="color:{pc};font-family:monospace">{pv:.1f} ({pl})</td></tr>
                  </table></div>""", unsafe_allow_html=True)
                for v in [v for v in cv if v.get("position")==pos][:2]:
                    cl2="#ff2d55" if v.get("ml_class")=="CRITICAL" else "#ff8c42"
                    st.markdown(f'<div style="background:{cl2}0d;border-left:2px solid {cl2};padding:4px 7px;margin:3px 0;border-radius:3px;font-size:.71rem;color:#d0e8ff">{v.get("significance","")} · {", ".join(v.get("conditions",[])[:1])}</div>', unsafe_allow_html=True)
                new_aa=st.selectbox("Mutate to:",sorted([k for k in AA if k!=aa]),key="mut_aa_ex")
                if new_aa:
                    npr=AA.get(new_aa,("?",0,0))
                    dh=abs(npr[1]-pr[1]); dc=abs(npr[2]-pr[2])
                    score=min(100,int(dh*8+dc*25))
                    ic="#ff2d55" if score>=70 else "#ff8c42" if score>=40 else "#ffd60a" if score>=15 else "#4a7090"
                    il="Likely Damaging" if score>=70 else "Possibly Damaging" if score>=40 else "Moderate" if score>=15 else "Benign"
                    st.markdown(f'<div class="card"><span class="mono" style="color:{ic}">{aa}{pos}{new_aa}</span> <span class="dim">{il} · score {score}/100</span><br><span class="dim">Δhyd: {dh:.1f} · Δcharge: {dc:.0f}{"  ⚠️ Pro breaks secondary structure" if new_aa=="P" else ""}</span></div>', unsafe_allow_html=True)

    if am:
        ui.section("AlphaMissense Per-Residue Pathogenicity")
        sample=am[::max(1,len(am)//600)]
        fig_am=go.Figure()
        fig_am.add_trace(go.Scatter(x=[a["position"] for a in sample],y=[a["score"] for a in sample],
            mode="markers",marker=dict(size=3,color=["#ff2d55" if a["score"]>=0.564 else "#1e3a5f" for a in sample],opacity=0.6),
            hovertemplate="Pos %{x} — %{y:.3f}<extra></extra>"))
        path_cv=[v for v in cv if v.get("position") and v.get("ml_class") in ("CRITICAL","HIGH")]
        if path_cv:
            fig_am.add_trace(go.Scatter(x=[v["position"] for v in path_cv],y=[0.564]*len(path_cv),
                mode="markers",marker=dict(size=10,symbol="star",color="#ff8c42"),
                hovertext=[v.get("protein_change","?") for v in path_cv],hoverinfo="text",name="ClinVar P/LP"))
        fig_am.add_hline(y=0.564,line_dash="dash",line_color="#ffd60a",annotation_text="0.564 threshold")
        fig_am.update_layout(height=240,plot_bgcolor="#010306",paper_bgcolor="#010306",
            xaxis=dict(title="Position",gridcolor="#060d14",color="#2a5070"),
            yaxis=dict(title="AM Score",gridcolor="#060d14",color="#2a5070",range=[0,1]),
            font=dict(color="#d0e8ff",size=10),legend=dict(bgcolor="#020609",bordercolor="#0a1520"),
            margin=dict(t=10,b=30,l=45,r=10))
        st.plotly_chart(fig_am,use_container_width=True,config={"displayModeBar":False})
        np_=sum(1 for a in am if a["score"]>=0.564)
        st.markdown(f'<span class="dim">Pathogenic (≥0.564): <b style="color:#ff2d55">{np_}</b> of {len(am)}</span> {ui.src("AlphaMissense","https://alphafold.ebi.ac.uk")}', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# EXPERIMENTS
# ═══════════════════════════════════════════════════════════════════════════
def tab_experiments(gene,exps,cv,gi,is_gpcr,is_arrb,kegg=[]):
    if is_arrb: show_arrb_analysis(gene,cv,{}); return
    ui.section("Protein-Specific Experiment Triage")
    do_f=[e for e in exps if e.get("do_first") and not e.get("avoid")]
    av_=[e for e in exps if e.get("avoid")]
    ot_=[e for e in exps if not e.get("do_first") and not e.get("avoid")]
    c1,c2,c3,c4=st.columns(4)
    c1.metric("DO FIRST",len(do_f),f"${sum(e['cost_usd'] for e in do_f):,}")
    c2.metric("Consider",len(ot_))
    c3.metric("AVOID",len(av_),f"${sum(e['cost_usd'] for e in av_):,}")
    c4.metric("Total",len(exps))

    for exp in exps:
        av=exp.get("avoid",False); dof=exp.get("do_first",False) and not av
        cost_str=f"${exp['cost_usd']:,}" if exp['cost_usd']>0 else "Free"
        hd=f"{'🚀 ' if dof else '🛑 AVOID — ' if av else ''}{exp['name'][:60]} — {cost_str} · {exp['time_weeks']}w · P={int(exp['p_success']*100)}%"
        with st.expander(hd, expanded=dof and not av):
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Cost",cost_str); c2.metric("Timeline",f"{exp['time_weeks']}w")
            c3.metric("P(success)",f"{int(exp['p_success']*100)}%"); c4.metric("Value",f"{exp['value_score']}/10")
            st.markdown(f'<div style="font-size:.72rem;color:#d0e8ff;line-height:1.7;margin-top:6px">{exp["rationale"]}</div>', unsafe_allow_html=True)
            if dof: st.success("Run first — highest expected value for this protein's specific variant profile")
            if av:  st.error("Do not run — insufficient genetic evidence to justify expenditure")

    if kegg:
        ui.section("KEGG Pathways")
        for p in kegg[:6]:
            st.markdown(f'<div class="dim"><a href="{p["url"]}" target="_blank" style="color:#00e5ff">{p["name"]}</a> <span class="src">{p["id"]}</span></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# CSV ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
def tab_csv_analysis(gene,pdata,gi):
    ui.section("CSV / VCF Dataset Analysis")
    df=st.session_state.get("csv_data")
    if df is None:
        st.markdown('<div class="dim">Upload a file in the sidebar (Wet-lab Data section).<br><b style="color:#d0e8ff">Accepted:</b> ClinVar VCF export, proteomics CSV, AlphaMissense TSV, variant tables.</div>', unsafe_allow_html=True)
        return
    c1,c2,c3=st.columns(3)
    c1.metric("Rows",f"{len(df):,}"); c2.metric("Columns",len(df.columns))
    c3.metric("Type","VCF Variants" if "Condition(s)" in df.columns else "Dataset")
    st.dataframe(df.head(20),use_container_width=True,height=260)
    sig_col=next((c for c in df.columns if any(t in c.lower() for t in ["ignif","pathogen"])),"")
    if sig_col:
        ui.section("Variant Classification")
        counts=df[sig_col].value_counts()
        pathogenic=sum(v for k,v in counts.items() if "pathogenic" in str(k).lower() and "benign" not in str(k).lower())
        vus=sum(v for k,v in counts.items() if "uncertain" in str(k).lower())
        benign=sum(v for k,v in counts.items() if "benign" in str(k).lower())
        c1,c2,c3=st.columns(3)
        c1.metric("Pathogenic/LP",f"{pathogenic:,}"); c2.metric("VUS",f"{vus:,}"); c3.metric("Benign/LB",f"{benign:,}")
        for k,v in counts.head(8).items():
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:2px 0;border-bottom:1px solid #060d14;font-size:.71rem"><span class="dim">{k}</span><span class="mono">{v:,}</span></div>', unsafe_allow_html=True)
    ui.section("Recommended Next Experiments")
    sens=st.session_state.sensitivity
    st.markdown(f'<div class="dim"><b>1. ClinVar submission</b> — pathogenic variants absent from ClinVar should be submitted.<br><b>2. Functional validation</b> — P/LP variants lacking functional evidence: DMS or CRISPR knock-in.<br><b>3. VUS resolution</b> — AlphaMissense threshold {sens:.2f} + DMS data.<br><b>4. Segregation analysis</b> — confirm P/LP variants segregate with disease in families.</div>', unsafe_allow_html=True)
    ui.section("Prioritisation Rule")
    st.markdown('<div class="dim">Intersection rule: mutations scoring HIGH in this assay AND carrying ClinVar pathogenic variants = credible drug targets. Single-assay evidence insufficient. Require: functional effect + ClinVar genetics + structural druggability.</div>', unsafe_allow_html=True)
    gene_col=next((c for c in df.columns if any(t in c.lower() for t in ["gene","symbol","hugo"])),"")
    if gene_col:
        ui.section(f"Quick Analyse — {gene_col}")
        top=df[gene_col].dropna().unique()[:10]
        gc=st.columns(min(10,len(top)))
        for i,g in enumerate(top):
            with gc[i]:
                if st.button(str(g)[:8],key=f"csv_g_{g}"): st.session_state._qval=str(g); st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# AI REPORT
# ═══════════════════════════════════════════════════════════════════════════
def tab_ai_report(gene,pdata,cv,gnomad,string,ot,papers):
    ui.section("Evidence-Tiered Literature")
    tg={}
    for p in papers: tg.setdefault(p["tier_label"],[]).append(p)
    for tlbl,tp in sorted(tg.items(),key=lambda x:x[1][0]["tier"]):
        tc=tp[0]["tier_color"]
        with st.expander(f"{tlbl} ({len(tp)})",expanded=tlbl in ("RCT","Cohort","Functional")):
            for p in tp:
                st.markdown(f'<div class="dim" style="padding:2px 0;border-bottom:1px solid #060d14"><a href="{p["url"]}" target="_blank" style="color:#8baabf;font-size:.71rem">{p["title"][:100]}</a> · {p["authors"][:18]} · {p["journal"]} · {p["year"]} · PMID:{p["pmid"]}</div>', unsafe_allow_html=True)
    ui.section("AI Synthesis")
    ak=st.session_state.get("anthropic_key","")
    if not ak:
        st.markdown('<div class="dim">Add Anthropic API key in sidebar to enable AI synthesis with live web search.</div>', unsafe_allow_html=True)
        return
    if st.button("▶ Generate AI Report",type="primary",key="ai_run"):
        with st.spinner("Claude searching literature…"):
            from fetchers import fetch_ai_report
            report=fetch_ai_report(gene,pdata,cv,gnomad,string,ak)
            st.session_state[f"ai_{gene}"]=report
    if f"ai_{gene}" in st.session_state:
        st.markdown(f'<div class="card" style="line-height:1.8;font-size:.76rem">{st.session_state[f"ai_{gene}"]}</div>', unsafe_allow_html=True)
        if st.button("🔄 Regenerate"):
            del st.session_state[f"ai_{gene}"]; st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# WORKSPACE
# ═══════════════════════════════════════════════════════════════════════════
def tab_workspace():
    from auth import current_user,get_searches_used,get_quota
    user=current_user(); ws=st.session_state.get("workspace",[])
    ui.section(f"Workspace — {user.get('name','')}")
    c1,c2,c3=st.columns(3)
    c1.metric("Searches Used",get_searches_used())
    c2.metric("Quota",get_quota() if get_quota()<99999 else "∞")
    c3.metric("Proteins",len(ws))
    if not ws: st.markdown('<div class="dim">No proteins analysed yet.</div>', unsafe_allow_html=True); return
    ui.section("Search History")
    for item in ws:
        col=item.get("color","#4a7090")
        ca,cb=st.columns([5,1])
        with ca:
            st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:4px 0;border-bottom:1px solid #060d14"><span class="mono" style="color:#d0e8ff">{item["gene"]}</span><span class="bdc" style="background:{col}18;color:{col};border-color:{col}30;font-size:.61rem">{item["verdict"]}</span><span class="dim">{item.get("domain","")} · {item["accession"]} · {item["protein"][:38]}</span></div>', unsafe_allow_html=True)
        with cb:
            if st.button("↗",key=f"ws_{item['gene']}"): st.session_state._qval=item["gene"]; st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# DISEASE LINK
# ═══════════════════════════════════════════════════════════════════════════
def tab_disease_link():
    ui.section("Disease → Protein Mapping")
    dq=st.text_input("Disease / pathogen",value=st.session_state._dval,
                     placeholder="Alzheimer · Hantavirus · breast cancer · arrhythmia",
                     label_visibility="collapsed",key="_dl_input")
    if dq: ui.show_disease_link_inline(dq)
    else:  st.markdown('<div class="dim">Enter a disease or pathogen name to map to associated proteins.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# ARRB ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
def show_arrb_analysis(gene,cv,pdata):
    from databases import ARRB_COST_BREAKDOWN,ARRB_LANDMARK_PAPERS,ARRB_EXPERIMENTS_TO_AVOID,ARRB_REDIRECT_ALTERNATIVES
    total=sum(ARRB_COST_BREAKDOWN.values())
    st.markdown(f"""<div style="background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.3);border-radius:6px;padding:14px;text-align:center;margin-bottom:10px">
      <span class="bdc bdc-dep" style="font-size:.8rem">DEPRIORITISE — {gene}</span>
      <div style="font-size:1.4rem;font-weight:800;color:#ef4444;margin:6px 0">${total:,}</div>
      <div class="dim">Avoidable spend · Beta-arrestin &lt;5 confirmed Mendelian disease variants · DKO mice viable/fertile</div>
    </div>""", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        ui.section("Avoidable Cost Breakdown")
        for name,cost in ARRB_COST_BREAKDOWN.items():
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #060d14;font-size:.72rem"><span class="dim">{name}</span><span style="color:#ef4444;font-family:monospace">${cost:,}</span></div>', unsafe_allow_html=True)
        ui.section("Redirect Alternatives")
        for alt in ARRB_REDIRECT_ALTERNATIVES:
            ca,cb=st.columns([3,1])
            with ca: st.markdown(f'<span class="mono" style="color:#00e5ff">{alt["gene"]}</span> <span class="dim">{alt["reason"][:50]}</span>', unsafe_allow_html=True)
            with cb:
                if st.button(f"↗{alt['gene']}",key=f"arrb_{alt['gene']}"): st.session_state._qval=alt["gene"]; st.rerun()
    with c2:
        ui.section("6 Landmark Papers — No Disease Evidence")
        for p in ARRB_LANDMARK_PAPERS:
            st.markdown(f'<div class="dim" style="border-bottom:1px solid #060d14;padding:4px 0"><a href="https://pubmed.ncbi.nlm.nih.gov/{p["pmid"]}/" target="_blank" style="color:#8baabf;font-size:.71rem">{p["title"]}</a><br>{p["journal"]} {p["year"]} · PMID:{p["pmid"]}<br><i style="color:#2a5070">{p["finding"]}</i></div>', unsafe_allow_html=True)
        ui.section("5 Experiments to AVOID")
        for exp in ARRB_EXPERIMENTS_TO_AVOID:
            st.markdown(f'<div class="dim" style="border-left:2px solid rgba(239,68,68,0.3);padding:3px 7px;margin:3px 0"><b style="color:#ef4444">{exp["name"]}</b> — ${exp["cost"]:,}<br>{exp["reason"]}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# MICROBIOME
# ═══════════════════════════════════════════════════════════════════════════
def show_microbiome():
    ui.section("🦠 Microbiome Intelligence")
    st.markdown('<div class="dim" style="margin-bottom:8px">LLM-enhanced gene annotation · Taxonomy · Pathway re-annotation · BGC detection</div>', unsafe_allow_html=True)
    t1,t2,t3,t4=st.tabs(["Gene Annotation","Taxonomy","Pathway Re-annotation","BGC"])
    with t1:
        ui.section("Vague → Specific Annotation")
        c1,c2=st.columns(2)
        with c1:
            gid=st.text_input("Gene ID / KO",placeholder="K01810, WP_001234",key="mg_gid")
            vague=st.text_input("Current annotation",placeholder="biosynthesis",key="mg_vague")
            org_ctx=st.text_input("Organism context",placeholder="gut microbiome, Lactobacillus",key="mg_org")
        with c2:
            st.markdown('<div class="dim" style="margin-top:8px">Rule-based expansion works without API key. Add Anthropic key for AI-powered annotation with EC numbers, pathway specificity, and ecological context.</div>', unsafe_allow_html=True)
        if st.button("Generate",type="primary",key="mg_go") and vague:
            EXPANSIONS={"biosynthesis":"Anabolic enzyme — specify via KO: amino acid (e.g. lysine via DAP pathway), lipid (FASII/membrane), or B-vitamin. Run eggNOG-mapper for reaction specificity.",
                        "chemosynthesis":"Chemolithotrophy — energy from inorganic oxidation (NH₃/S²⁻/Fe²⁺). Check AMO/NXR/Sox gene families. Nitrifier, sulfur oxidiser, or iron oxidiser.",
                        "protein aggregation":"Regulated polymerisation: curli (CsgA/B — biofilm), functional amyloid, or spore coat. Curli activate TLR2/TLR1 → innate immune response.",
                        "hypothetical protein":"No homology. Pipeline: (1) AlphaFold2 + Foldseek, (2) eggNOG-mapper DIAMOND, (3) InterProScan, (4) Phyre2.",
                        "transporter":"TC database classification: ABC (ATP-driven), MFS (proton gradient), RND (multidrug efflux). Check antibiotic resistance relevance.",
                        "metabolism":"Use KEGG GHOSTX or eggNOG-mapper for specific reaction. Cross-reference SEED/RAST reconstruction."}
            ak=st.session_state.get("anthropic_key",""); result=None
            if ak:
                try:
                    import anthropic
                    client=anthropic.Anthropic(api_key=ak)
                    msg=client.messages.create(model="claude-sonnet-4-20250514",max_tokens=600,
                        messages=[{"role":"user","content":f"Gene:{gid}\nCurrent:{vague}\nOrganism:{org_ctx}\nGive specific: molecular function, EC number, pathway, ecological role, validation tools. No vague terms."}])
                    result=msg.content[0].text
                except: pass
            if not result:
                al=vague.lower(); result=next((v for k,v in EXPANSIONS.items() if k in al),f"'{vague}' not in rule base. Run eggNOG-mapper v2 or InterProScan.")
            ca,cb=st.columns(2)
            with ca: st.markdown(f'<div class="card" style="border-color:rgba(239,68,68,0.2)"><span class="dim" style="color:#ef4444">❌ Before</span><br><i style="color:#fca5a5">{vague}</i></div>', unsafe_allow_html=True)
            with cb: st.markdown(f'<div class="card" style="border-color:rgba(74,222,128,0.2)"><span class="dim" style="color:#4ade80">✅ After</span><div style="font-size:.71rem;color:#d0e8ff;margin-top:5px;line-height:1.7">{result}</div></div>', unsafe_allow_html=True)
    with t2:
        ui.section("Taxonomy")
        taxon=st.text_input("Organism",placeholder="Akkermansia muciniphila",key="mg_tax")
        ROLES={"Lactobacillus":"Lactic acid producer; pH-mediated pathogen competition; gut barrier reinforcement; SCFA; probiotic",
               "Bifidobacterium":"Probiotic; SCFA; immune modulation; infant microbiome; B-vitamin synthesis",
               "Bacteroides":"Major fermenter; polysaccharide utilisation loci (PULs); keystone symbiont",
               "Akkermansia":"Mucin-layer coloniser; gut barrier integrity; depleted in obesity/T2D/IBD; next-gen probiotic",
               "Faecalibacterium":"Butyrate producer; anti-inflammatory; depleted in IBD",
               "Helicobacter":"CagA/VacA virulence; peptic ulcer; gastric cancer; MALT lymphoma",
               "Fusobacterium":"FadA adhesin; CRC invasion; Wnt/β-catenin activation"}
        if taxon:
            genus=taxon.split()[0]
            role=ROLES.get(genus,"Ecological role not curated — search NCBI taxonomy and primary literature")
            st.markdown(f'<div class="card"><span class="mono" style="color:#4ade80">{taxon}</span><br><span style="font-size:.72rem;color:#d0e8ff;line-height:1.6">{role}</span></div>', unsafe_allow_html=True)
    with t3:
        ui.section("Batch Re-annotation")
        raw=st.text_area("Annotations (one per line)",placeholder="biosynthesis\nchemosynthesis\nhypothetical protein",height=90,key="mg_batch")
        VAGUE={"biosynthesis","chemosynthesis","protein aggregation","hypothetical protein","metabolism","transport","regulation","unknown","uncharacterized"}
        if st.button("Analyse",type="primary",key="mg_batch_go") and raw:
            lines=[l.strip() for l in raw.splitlines() if l.strip()]
            vn=sum(1 for l in lines if any(v in l.lower() for v in VAGUE))
            c1,c2,c3=st.columns(3)
            c1.metric("Total",len(lines)); c2.metric("Vague",vn); c3.metric("Informative",len(lines)-vn)
            for l in lines:
                iv=any(v in l.lower() for v in VAGUE); col="#ef4444" if iv else "#4ade80"
                st.markdown(f'<div style="font-size:.71rem;padding:2px 0;border-bottom:1px solid #060d14"><span style="color:{col}">{"❌" if iv else "✅"}</span> <span style="color:#d0e8ff">{l}</span></div>', unsafe_allow_html=True)
    with t4:
        ui.section("BGC Prediction")
        bgc=st.text_area("BGC annotations",placeholder="adenylation domain\ncondensation domain",height=80,key="mg_bgc")
        BGC_SIGS={"NRPS":["nrps","adenylation","thiolation","condensation"],"PKS":["pks","polyketide","ketosynthase"],
                  "Terpene":["terpene cyclase","geranylgeranyl"],"RiPP":["lanthipeptide","bacteriocin"],"Siderophore":["siderophore","enterobactin"]}
        if st.button("Predict",type="primary",key="mg_bgc_go") and bgc:
            c2=bgc.lower(); scores={t:sum(1 for k in kws if k in c2) for t,kws in BGC_SIGS.items()}
            best=max(scores,key=scores.get); conf="High" if scores[best]>=3 else "Medium" if scores[best]>=2 else "Low"
            cc={"High":"#4ade80","Medium":"#ffd60a","Low":"#ef4444"}[conf]
            st.markdown(f'<div class="card" style="text-align:center;border-color:{cc}40"><span class="mono" style="color:{cc};font-size:.95rem">{best}</span> <span class="bdc bdc-lo">{conf} confidence · score {scores[best]}</span></div>', unsafe_allow_html=True)
