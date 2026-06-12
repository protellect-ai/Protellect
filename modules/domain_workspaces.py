# modules/domain_workspaces.py
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
from modules.config import DOMAIN_STYLES, STRIPE_LINKS, LOGO_B64, _logo_src
from modules.utils import sh, mc
from modules.data_processing import g_gene, g_name, g_gpcr, g_diseases, g_func, g_ptype
from modules.visualization import kyte_doolittle, calc_pI

def render_oncology_workspace():
    CDATA = {
        "Lung adenocarcinoma":{"icon":"🫁","clr":"#00aaff","surv":[85,60,30,6],"met":["Brain 40%","Bone","Adrenal","Liver"],"screen":"LDCT annually: 50–80y smokers ≥20 pack-years (USPSTF A)","causes":["Smoking (SBS4)","Radon gas","Asbestos","PM2.5","Passive smoke"],"drivers":{"EGFR ex19/L858R":"Osimertinib","KRAS G12C":"Sotorasib","ALK fusion":"Alectinib","ROS1 fusion":"Entrectinib","BRAF V600E":"Dabrafenib+Trametinib","MET ex14":"Capmatinib","RET fusion":"Selpercatinib","NTRK":"Larotrectinib"}},
        "Colorectal cancer":{"icon":"🔴","clr":"#ff8c42","surv":[90,80,60,16],"met":["Liver 60%","Lung","Peritoneum"],"screen":"FIT annually + colonoscopy every 10y from age 45","causes":["Processed meat","Obesity","Alcohol","Lynch syndrome","UC >30y"],"drivers":{"APC (85%)":"Wnt driver — FAP germline","KRAS (40%)":"RAS WT → cetuximab eligible","BRAF V600E (10%)":"BEACON-CRC triple combo","MSI-H (15%)":"Pembrolizumab 1st line","HER2 amp (5%)":"Tucatinib+trastuzumab"}},
        "Breast (HR+)":{"icon":"🎗","clr":"#f43f5e","surv":[99,86,57,31],"met":["Bone 70%","Lung","Liver","Brain"],"screen":"Mammography ± MRI annually. BRCA: MRI from age 25","causes":["BRCA1/2 germline","Oestrogen exposure","Combined HRT","Alcohol","Obesity"],"drivers":{"PIK3CA (30%)":"Alpelisib+fulvestrant","ESR1 mutation":"Elacestrant (EMERALD)","BRCA germline":"Olaparib","HER2-low":"T-DXd (DESTINY-Breast04)"}},
        "Pancreatic (PDAC)":{"icon":"🟡","clr":"#ffd60a","surv":[20,10,5,3],"met":["Liver 80%","Peritoneum","Lung"],"screen":"EUS+MRI for BRCA2/PALB2 carriers from 50y","causes":["Smoking 2×","Obesity","T2D","Chronic pancreatitis","BRCA2/PALB2"],"drivers":{"KRAS (>90%)":"No approved targeted Tx yet","BRCA2/PALB2 germ":"Olaparib maintenance","MSI-H (<1%)":"Pembrolizumab","ATM (5%)":"DNA repair trials"}},
        "Melanoma":{"icon":"🟤","clr":"#a855f7","surv":[97,75,50,25],"met":["Lung","Brain 30%","Liver","Bone"],"screen":"Annual skin exam + dermoscopy","causes":["UV exposure (SBS7)","Tanning beds","CDKN2A germline","Fair skin"],"drivers":{"BRAF V600E/K (45%)":"Dabrafenib+Trametinib","NRAS (20%)":"Binimetinib (modest)","NF1 (15%)":"Immunotherapy preferred","PD-L1/MSI":"Pembrolizumab/Nivolumab"}},
        "Glioblastoma":{"icon":"🧠","clr":"#ff2d55","surv":[50,20,10,6],"met":["Local infiltration only"],"screen":"MRI+gad for symptoms (headache/seizure/focal deficit)","causes":["Prior radiotherapy (only confirmed)","Rare germline (Li-Fraumeni)","Sporadic >90%"],"drivers":{"EGFR amp/vIII (57%)":"No approved targeted Tx","IDH1 R132H (<5% GBM)":"Vorasidenib (grade 2/3 only)","MGMT methylation":"Predicts TMZ response","TERT promoter (72%)":"Prognostic only"}},
    }

    st.markdown("<div style='color:#f43f5e;font-size:1.1rem;font-weight:800;margin-bottom:.6rem;'>🎗 Oncology — Patient Clinical Decision Tool</div>", unsafe_allow_html=True)

    card_cols = st.columns(len(CDATA))
    sel = st.session_state.get("onc_sel_cancer", "Lung adenocarcinoma")
    for ci, (cname, cd) in enumerate(CDATA.items()):
        with card_cols[ci]:
            is_sel = sel == cname
            border = f"2px solid {cd['clr']}" if is_sel else f"1px solid {cd['clr']}22"
            bg = f"{cd['clr']}12" if is_sel else "#010810"
            st.markdown(f"<div style='background:{bg};border:{border};border-radius:9px;padding:.6rem;text-align:center;'>"
                f"<div style='font-size:1.4rem;'>{cd['icon']}</div>"
                f"<div style='color:{cd['clr']};font-weight:700;font-size:.68rem;margin-top:2px;'>{cname}</div></div>", unsafe_allow_html=True)
            if st.button("Select" if not is_sel else "✓ Selected", key=f"onc_card_{ci}", use_container_width=True):
                st.session_state["onc_sel_cancer"] = cname
                st.rerun()

    cd = CDATA[sel]
    clr = cd["clr"]
    st.markdown("<hr class='dv'>", unsafe_allow_html=True)

    form_col, output_col = st.columns([1, 1.4])

    with form_col:
        st.markdown(f"<div style='color:{clr};font-size:.8rem;font-weight:700;margin-bottom:.5rem;'>👤 Patient Profile</div>", unsafe_allow_html=True)
        stage = st.selectbox("Stage", ["Stage I","Stage II","Stage III","Stage IV (met)","Recurrent"], key="onc_f_stage")
        variant = st.text_input("Key mutation", placeholder="e.g. KRAS G12C · EGFR L858R · BRCA2 p.Trp31*", key="onc_f_var")
        origin = st.radio("Origin", ["Somatic","Germline","Unknown"], horizontal=True, key="onc_f_ori")
        msi = st.selectbox("MSI/MMR", ["Unknown","MSS","MSI-H"], key="onc_f_msi")
        pdl1 = st.selectbox("PD-L1 TPS", ["Unknown","<1%","1–49%","≥50%"], key="onc_f_pdl1")
        tmb = st.number_input("TMB (mut/Mb)", 0, 500, 0, key="onc_f_tmb")
        gene_btn = variant.split()[0].upper() if variant else ""
        if gene_btn and st.button(f"→ Deep-analyse {gene_btn}", key="onc_f_analyse", use_container_width=True, type="primary"):
            st.session_state["_trigger_search"] = gene_btn
            st.rerun()

    with output_col:
        v = variant.lower()
        tx = None
        for drv_key, drv_tx in cd["drivers"].items():
            drv_genes = drv_key.lower().split()[0].replace("(","").split("/")
            if any(dg.strip() in v for dg in drv_genes if len(dg.strip()) > 2):
                tx = (drv_key, drv_tx)
                break
        if "msi-h" in msi or tmb >= 10:
            tx = ("MSI-H / High TMB", "Pembrolizumab (tumour-agnostic FDA) — KEYNOTE-177 mPFS 16.5mo MSI-H CRC")
        if "≥50%" in pdl1 and "Lung" in sel:
            tx = ("PD-L1 ≥50% NSCLC", "Pembrolizumab monotherapy — KEYNOTE-024. Exclude EGFR/ALK first.")
        if "germline" in origin.lower() and any(x in v for x in ["brca","palb2","atm"]):
            tx = ("Germline HRD", "Olaparib — OlympiAD/POLO. Confirm HRD score ≥42 (Myriad myChoice).")

        if tx:
            st.markdown(f"<div style='background:#000a03;border:2px solid #22c55e;border-left:5px solid #22c55e;border-radius:0 10px 10px 0;padding:10px 14px;margin-bottom:.6rem;'>"
                f"<div style='color:#22c55e;font-weight:700;font-size:.82rem;'>✅ Actionable: {tx[0]}</div>"
                f"<div style='color:#3a6080;font-size:.76rem;line-height:1.6;margin-top:3px;'>{tx[1]}</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='background:#0a0800;border:1px solid #ffd60a22;border-left:4px solid #ffd60a;border-radius:0 9px 9px 0;padding:8px 12px;color:#ffd60a;font-size:.76rem;'>⚠ Enter variant above for personalised recommendation. Fallback: FoundationOne NGS + ClinicalTrials.gov basket trial.</div>", unsafe_allow_html=True)

        stages_s = ["I","II","III","IV"]
        surv_bars = "".join(f"<div style='flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;'>"
            f"<div style='font-size:.68rem;color:{clr};font-weight:700;'>{s}%</div>"
            f"<div style='background:{clr};border-radius:3px;width:22px;height:{int(s*0.7)}px;'></div>"
            f"<div style='font-size:.62rem;color:#1e4060;'>St.{st_}</div></div>"
            for st_, s in zip(stages_s, cd["surv"]))
        st.markdown(f"<div style='color:#3a6080;font-size:.67rem;margin-bottom:3px;'>5-yr OS by stage</div>"
            f"<div style='display:flex;align-items:flex-end;height:80px;gap:4px;'>{surv_bars}</div>", unsafe_allow_html=True)

        st.markdown(f"<div style='margin-top:.5rem;display:flex;gap:8px;'>"
            f"<div style='flex:1;background:#010810;border:1px solid #ff8c4222;border-radius:7px;padding:6px 9px;'>"
            f"<div style='color:#ff8c42;font-size:.66rem;font-weight:700;margin-bottom:3px;'>CAUSES</div>"
            + "".join(f"<div style='color:#3a6080;font-size:.68rem;padding:1px 0;'>• {c}</div>" for c in cd["causes"])
            + f"</div><div style='flex:1;background:#010810;border:1px solid #22c55e22;border-radius:7px;padding:6px 9px;'>"
            f"<div style='color:#22c55e;font-size:.66rem;font-weight:700;margin-bottom:3px;'>SCREENING</div>"
            f"<div style='color:#3a6080;font-size:.69rem;line-height:1.5;'>{cd['screen']}</div>"
            f"<div style='color:#ff2d55;font-size:.66rem;font-weight:700;margin:.4rem 0 2px;'>METASTASIS</div>"
            + "".join(f"<span style='background:#ff2d5514;color:#ff2d55;border:1px solid #ff2d5530;border-radius:5px;padding:1px 6px;font-size:.64rem;margin:1px;display:inline-block;'>{m}</span>" for m in cd["met"])
            + "</div></div>", unsafe_allow_html=True)

        st.markdown(f"<div style='color:{clr};font-size:.67rem;font-weight:700;margin:.6rem 0 .2rem;text-transform:uppercase;'>All drivers — {sel}</div>", unsafe_allow_html=True)
        for drv, drv_tx in cd["drivers"].items():
            st.markdown(f"<div style='display:flex;gap:6px;padding:2px 0;border-bottom:1px solid #050e18;'>"
                f"<span style='color:{clr};font-size:.68rem;min-width:140px;font-weight:600;'>{drv}</span>"
                f"<span style='color:#3a6080;font-size:.68rem;'>{drv_tx}</span></div>", unsafe_allow_html=True)


def render_neuroscience_workspace():
    st.markdown("<div style='color:#818cf8;font-size:1.1rem;font-weight:800;margin-bottom:.4rem;'>🧠 Neuroscience Workspace</div>", unsafe_allow_html=True)

    mode = st.radio("", ["⚡ Synapse Explorer", "🏥 Disease → Proteins", "🔌 Channel Pharmacology", "💊 BBB Calculator"], horizontal=True, key="neuro_mode")

    if mode == "⚡ Synapse Explorer":
        components.html("""<!DOCTYPE html><html><head>
<style>body{margin:0;background:#000205;overflow:hidden;font-family:Inter,sans-serif;}
canvas{display:block;}
#tip{position:absolute;background:rgba(0,2,10,.97);border:1px solid #6366f133;
  border-radius:9px;padding:8px 12px;color:#b0d8f0;font-size:11px;display:none;
  pointer-events:none;z-index:10;max-width:260px;line-height:1.6;}
#hint{position:absolute;bottom:6px;left:50%;transform:translateX(-50%);
  color:#1e4060;font-size:9px;font-family:JetBrains Mono,monospace;}
</style></head><body>
<canvas id="cv"></canvas>
<div id="tip"></div>
<div id="hint">Click any protein node → search in Protellect sidebar</div>
<script>
const cv=document.getElementById('cv'),x=cv.getContext('2d');
cv.width=window.innerWidth||860;cv.height=(window.innerHeight||430)-10;
const W=cv.width,H=cv.height;

const P={
 SYT1:{x:.24,y:.34,r:13,c:"#6366f1",label:"Synaptotagmin-1",fn:"Ca²⁺ sensor → vesicle fusion",dis:"Mutations → severe ID, epilepsy"},
 VAMP2:{x:.30,y:.43,r:11,c:"#6366f1",label:"Synaptobrevin-2",fn:"v-SNARE — core fusion",dis:"Cleaved by BoNT/B → botulism"},
 STX1A:{x:.37,y:.36,r:11,c:"#8b8cf4",label:"Syntaxin-1A",fn:"t-SNARE — membrane",dis:"Mutations → West syndrome"},
 SNAP25:{x:.34,y:.27,r:10,c:"#8b8cf4",label:"SNAP-25",fn:"t-SNARE — 2 SNARE motifs",dis:"BoNT/A substrate. ADHD risk."},
 STXBP1:{x:.18,y:.26,r:12,c:"#a855f7",label:"Munc18-1",fn:"Chaperone for STX1A",dis:"Haploinsufficiency → Ohtahara EIEE"},
 SYN1:{x:.17,y:.40,r:10,c:"#6366f1",label:"Synapsin-1",fn:"Vesicle-actin tether",dis:"Mutations → X-linked epilepsy + ASD"},
 GRIN2B:{x:.52,y:.38,r:14,c:"#ff2d55",label:"GluN2B — NMDAR",fn:"NMDA receptor — plasticity",dis:"GoF → West; LoF → ID+ASD"},
 GRIA1:{x:.57,y:.27,r:12,c:"#ff4465",label:"GluA1 — AMPAR",fn:"AMPA receptor — LTP",dis:"Ser831 phospho = LTP marker"},
 GABRA1:{x:.47,y:.52,r:11,c:"#22c55e",label:"GABAα1",fn:"Cl⁻ influx — inhibition",dis:"Mutations → absence, Dravet-spectrum"},
 DLG4:{x:.69,y:.30,r:13,c:"#ffd60a",label:"PSD-95",fn:"Master scaffold — PDZ",dis:"Haploinsufficiency → ASD"},
 SHANK3:{x:.74,y:.41,r:12,c:"#ffd60a",label:"SHANK3",fn:"Spine architecture",dis:"Deletion → Phelan-McDermid"},
 SYNGAP1:{x:.78,y:.27,r:11,c:"#ffd60a",label:"SynGAP1",fn:"Ras-GAP — LTP gate",dis:"Haploinsufficiency → monogenic ID #2"},
 HOMER1:{x:.82,y:.42,r:10,c:"#ff8c42",label:"Homer1",fn:"mGluR5 scaffold",dis:"Homer1a = dominant neg → LTP tag"},
 SCN1A:{x:.10,y:.57,r:11,c:"#00e5ff",label:"Nav1.1",fn:"Na⁺ channel — interneurons",dis:"Dravet (LoF) · GEFS+ (GoF)"},
 KCNQ2:{x:.16,y:.65,r:10,c:"#00e5ff",label:"Kv7.2 M-channel",fn:"AIS repolarisation",dis:"GoF: neonatal epilepsy; LoF: encephalopathy"},
 LRRK2:{x:.88,y:.60,r:11,c:"#ff8c42",label:"LRRK2",fn:"Kinase — Rab phosphorylation",dis:"G2019S → most common AD Parkinson"},
};
const names=Object.keys(P);
let t=0,hov=null;
const px=(r)=>r*W,py=(r)=>r*H;

function draw(){
 x.clearRect(0,0,W,H);
 const bg=x.createLinearGradient(0,0,W,H);
 bg.addColorStop(0,'#000205');bg.addColorStop(1,'#020b1a');
 x.fillStyle=bg;x.fillRect(0,0,W,H);
 x.beginPath();x.roundRect(px(.07),py(.18),px(.42),py(.32),12);
 x.fillStyle='rgba(99,102,241,.05)';x.fill();
 x.strokeStyle='rgba(99,102,241,.18)';x.lineWidth=1.2;x.stroke();
 x.fillStyle='#6366f144';x.font='bold 10px Inter';x.textAlign='center';
 x.fillText('PRE-SYNAPTIC TERMINAL',px(.28),py(.215));
 x.beginPath();x.roundRect(px(.43),py(.20),px(.50),py(.32),12);
 x.fillStyle='rgba(255,214,10,.04)';x.fill();
 x.strokeStyle='rgba(255,214,10,.15)';x.lineWidth=1.2;x.stroke();
 x.fillStyle='#ffd60a44';x.font='bold 10px Inter';x.textAlign='center';
 x.fillText('POST-SYNAPTIC DENSITY (PSD)',px(.68),py(.225));
 x.fillStyle='rgba(255,255,255,.015)';x.fillRect(px(.09),py(.48),px(.82),py(.055));
 x.fillStyle='#1e4060';x.font='9px Inter';x.textAlign='center';
 x.fillText('SYNAPTIC CLEFT',px(.5),py(.512));
 x.beginPath();x.roundRect(px(.03),py(.50),px(.23),py(.22),8);
 x.fillStyle='rgba(0,229,255,.025)';x.fill();
 x.strokeStyle='rgba(0,229,255,.10)';x.lineWidth=1;x.stroke();
 x.fillStyle='#00e5ff33';x.font='8px Inter';x.textAlign='center';
 x.fillText('AXON INITIAL SEGMENT',px(.15),py(.665));
 for(let i=0;i<6;i++){
  const vx2=px(.25)+Math.cos(t*.7+i)*px(.055);
  const vy2=py(.38)+Math.sin(t*.5+i*1.1)*py(.04);
  x.beginPath();x.arc(vx2,vy2,6.5,0,Math.PI*2);
  x.fillStyle='rgba(99,102,241,.14)';x.fill();
  x.strokeStyle='rgba(99,102,241,.4)';x.lineWidth=1;x.stroke();
 }
 const sig=Math.sin(t*1.1);
 if(sig>0) for(let i=0;i<5;i++){
  const ax=px(.37)+i*px(.025);
  const ay=py(.47)-sig*py(.055);
  x.beginPath();x.arc(ax,ay,2.5,0,Math.PI*2);
  x.fillStyle=`rgba(255,45,85,${sig*.75})`;x.fill();
 }
 names.forEach(n=>{
  const p=P[n],cx2=px(p.x),cy2=py(p.y),pr=p.r,ih=hov===n;
  if(ih){const g=x.createRadialGradient(cx2,cy2,0,cx2,cy2,pr*2.5);g.addColorStop(0,p.c+'44');g.addColorStop(1,'transparent');x.beginPath();x.arc(cx2,cy2,pr*2.5,0,Math.PI*2);x.fillStyle=g;x.fill();}
  x.beginPath();x.arc(cx2,cy2,pr+1.5,0,Math.PI*2);x.strokeStyle=p.c+(ih?'bb':'28');x.lineWidth=ih?2:1;x.stroke();
  x.beginPath();x.arc(cx2,cy2,pr,0,Math.PI*2);x.fillStyle=ih?p.c+'55':p.c+'1a';x.fill();x.strokeStyle=p.c+(ih?'ff':'77');x.lineWidth=ih?1.8:1.2;x.stroke();
  x.fillStyle=ih?'#fff':p.c+'cc';x.font=`bold ${Math.max(6.5,Math.min(8.5,pr*.62))}px JetBrains Mono`;x.textAlign='center';x.textBaseline='middle';
  x.fillText(n,cx2,cy2);
 });
 t+=0.032;requestAnimationFrame(draw);
}

cv.addEventListener('mousemove',e=>{
 const r=cv.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
 hov=null;
 names.forEach(n=>{const p=P[n];if(Math.hypot(mx-px(p.x),my-py(p.y))<p.r+4)hov=n;});
 const tt=document.getElementById('tip');
 if(hov){
  const p=P[hov];tt.style.display='block';
  tt.style.left=Math.min(e.clientX-r.left+12,W-270)+'px';
  tt.style.top=Math.max(e.clientY-r.top-65,5)+'px';
  tt.innerHTML=`<b style="color:${p.c}">${hov} — ${p.label}</b><br><span style="color:#3a6080">${p.fn}</span><br><span style="color:#ff8c42">🏥 ${p.dis}</span>`;
 } else tt.style.display='none';
});
cv.addEventListener('click',()=>{
 if(hov){window.parent.postMessage({type:'protellect_search',gene:hov},'*');}
});
draw();
</script></body></html>""", height=420, scrolling=False)

        st.markdown("<div style='color:#6366f1;font-size:.7rem;font-weight:700;margin:.4rem 0 .2rem;'>Click to analyse:</div>", unsafe_allow_html=True)
        qc = st.columns(9)
        for qi, g in enumerate(["SYT1","GRIN2B","SHANK3","SCN1A","KCNQ2","LRRK2","MAPT","SNCA","DLG4"]):
            with qc[qi]:
                if st.button(g, key=f"nq_{g}", use_container_width=True):
                    st.session_state["_trigger_search"] = g
                    st.rerun()

    elif mode == "🏥 Disease → Proteins":
        DMAP = {
            "Alzheimer's disease":{"genes":["APP","PSEN1","PSEN2","APOE","TREM2","SORL1"],"tx":"Lecanemab (anti-Aβ, FDA 2023) · Donanemab (anti-Aβ, FDA 2024) · Donepezil/rivastigmine (AChEI)","clr":"#a855f7"},
            "Parkinson's disease":{"genes":["SNCA","LRRK2","PINK1","PARKIN","GBA","VPS35"],"tx":"Levodopa+carbidopa · Pramipexole · DBS for advanced · DNL201 (LRRK2i, Phase II)","clr":"#ff8c42"},
            "ALS":{"genes":["SOD1","TARDBP","FUS","C9orf72","TBK1","OPTN"],"tx":"Tofersen (SOD1-ASO, FDA 2023) · Riluzole · Edaravone · AMX0035","clr":"#ff2d55"},
            "Dravet syndrome":{"genes":["SCN1A"],"tx":"Stiripentol+VPA+clobazam · Fenfluramine (FDA 2020) · AVOID: carbamazepine, lamotrigine, phenytoin","clr":"#ffd60a"},
            "KCNQ2 encephalopathy":{"genes":["KCNQ2"],"tx":"Carbamazepine/phenobarb (LoF) · XEN496 Kv7 opener (Phase III) · Avoid Na-blockers in GoF","clr":"#00e5ff"},
            "Autism (ASD)":{"genes":["SHANK3","SYNGAP1","NRXN1","ADNP","TSC1","TSC2"],"tx":"Everolimus (TSC mTOR) · No approved DMTX otherwise · ABA therapy gold standard","clr":"#22c55e"},
            "Huntington's disease":{"genes":["HTT"],"tx":"Tetrabenazine/deutetrabenazine (chorea) · Tominersen (ASO, Phase III) · Branaplam (Phase II)","clr":"#6366f1"},
        }
        for dis, dd in DMAP.items():
            with st.expander(f"🔴  {dis}"):
                st.markdown(f"<div style='background:{dd['clr']}08;border-left:3px solid {dd['clr']};padding:6px 10px;border-radius:0 7px 7px 0;margin-bottom:6px;color:#3a6080;font-size:.74rem;line-height:1.5;'><b style='color:{dd['clr']};'>Therapy:</b> {dd['tx']}</div>", unsafe_allow_html=True)
                gc = st.columns(min(len(dd["genes"]), 6))
                for gi, g in enumerate(dd["genes"]):
                    with gc[gi % len(gc)]:
                        if st.button(g, key=f"dmap_{dis[:5]}_{g}", use_container_width=True):
                            st.session_state["_trigger_search"] = g
                            st.rerun()

    elif mode == "🔌 Channel Pharmacology":
        st.markdown("<div style='background:#0a0002;border:1px solid #ff2d5522;border-radius:8px;padding:7px 12px;margin-bottom:.6rem;color:#ff2d55;font-size:.76rem;'>"
            "⚠ <b>Critical precision medicine</b>: the correct drug class depends on GoF vs LoF. Wrong class = worse seizure outcome.</div>", unsafe_allow_html=True)
        CHANS = [
            ("SCN1A","Nav1.1","#ff2d55","LoF → Dravet: interneuron failure → disinhibition. Stiripentol+VPA+CLB. Fenfluramine. AVOID carbamazepine/phenytoin/lamotrigine — block interneurons → worse.\nGoF → GEFS+: valproate first-line. Avoid heat triggers."),
            ("SCN2A","Nav1.2","#ff8c42","GoF onset <3 months → epilepsy: Na-blockers EFFECTIVE (carbamazepine, oxcarbazepine, phenytoin).\nLoF onset >3 months → ASD/ID: Na-blockers CONTRAINDICATED — reduce already low excitatory drive."),
            ("KCNQ2","Kv7.2","#22c55e","GoF: self-limited neonatal epilepsy — often resolves by 6 months. Carbamazepine short-term.\nLoF: KCNQ2 encephalopathy — carbamazepine/phenobarb. XEN496 (Kv7 opener, Phase III ongoing)."),
            ("GRIN2B","GluN2B","#6366f1","GoF → hyperexcitability, West syndrome: memantine (NMDA blocker) — small Phase II data.\nLoF → ID+ASD: increase NMDA tone. D-cycloserine (glycine site) investigational."),
            ("HCN1","Ih","#4a90d9","GoF → Dravet-like febrile seizures: ivermectin (HCN1 blocker), investigational only.\nLoF → generalised epilepsy: standard AEDs. Ketogenic diet reduces HCN1 expression indirectly."),
            ("CACNA1A","Cav2.1","#a855f7","Missense → FHM1: avoid triptans (vasoconstrictors). Verapamil acute attacks.\nCAG repeat → SCA6: no approved therapy. Riluzole slows cerebellar loss in small RCT."),
        ]
        for ch, protein, cclr, detail in CHANS:
            cols_ch = st.columns([0.22, 0.78])
            with cols_ch[0]:
                st.markdown(f"<div style='background:#010810;border:2px solid {cclr};border-radius:9px;padding:.6rem;text-align:center;'>"
                    f"<div style='color:{cclr};font-weight:800;font-size:.85rem;'>{ch}</div>"
                    f"<div style='color:#1e4060;font-size:.62rem;'>{protein}</div></div>", unsafe_allow_html=True)
                if st.button(f"Analyse", key=f"ch_b_{ch}", use_container_width=True):
                    st.session_state["_trigger_search"] = ch
                    st.rerun()
            with cols_ch[1]:
                st.markdown(f"<div style='background:#010810;border-left:3px solid {cclr};padding:8px 12px;border-radius:0 8px 8px 0;font-size:.73rem;color:#4a7090;line-height:1.7;white-space:pre-line;'>{detail}</div>", unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom:.3rem;'></div>", unsafe_allow_html=True)

    else:
        sh("💊", "CNS MPO Score — Blood-Brain Barrier Penetrance Calculator")
        st.markdown("<div style='color:#3a6080;font-size:.77rem;margin-bottom:.5rem;'>Pfizer CNS MPO framework (1128 CNS vs 1000 non-CNS drugs). Score ≥4/6 = CNS penetrant. Enter compound properties:</div>", unsafe_allow_html=True)
        b1, b2, b3 = st.columns(3)
        with b1:
            mw_c = st.number_input("MW (Da)", 100, 1000, 360, key="bbb_mw2")
            logp_c = st.number_input("cLogP", -5.0, 10.0, 2.2, 0.1, key="bbb_lp2")
        with b2:
            hbd_c = st.number_input("HBD (donors)", 0, 10, 1, key="bbb_hbd2")
            psa_c = st.number_input("PSA (Ų)", 0, 300, 58, key="bbb_psa2")
        with b3:
            pka_c = st.number_input("pKa (basic)", 0.0, 14.0, 7.5, 0.1, key="bbb_pka2")
            logd_c = st.number_input("cLogD pH7.4", -5.0, 8.0, 1.8, 0.1, key="bbb_ld2")

        sc = {"MW < 400":mw_c<400,"cLogP 1–3":1<=logp_c<=3,"HBD ≤ 1":hbd_c<=1,"PSA < 60":psa_c<60,"pKa < 8":pka_c<8,"cLogD -1 to 2":-1<=logd_c<=2}
        tot = sum(sc.values())
        tclr = "#22c55e" if tot>=4 else "#ffd60a" if tot>=3 else "#ff2d55"
        st.markdown(f"<div style='background:{tclr}10;border:2px solid {tclr}44;border-radius:10px;padding:.7rem;text-align:center;margin:.4rem 0;'>"
            f"<div style='font-size:2.2rem;font-weight:800;color:{tclr};'>{tot}/6</div>"
            f"<div style='color:{tclr};font-size:.82rem;font-weight:700;'>{'✅ CNS PENETRANT' if tot>=4 else '⚠ BORDERLINE' if tot>=3 else '❌ POOR CNS'}</div></div>", unsafe_allow_html=True)
        for pname, ok in sc.items():
            sc2 = "#22c55e" if ok else "#ff2d55"
            st.markdown(f"<div style='display:flex;align-items:center;gap:8px;padding:3px 0;border-bottom:1px solid #050e18;'>"
                f"<span style='color:{sc2};font-size:.9rem;'>{'✓' if ok else '✗'}</span>"
                f"<span style='color:#5a8090;font-size:.73rem;'>{pname}</span></div>", unsafe_allow_html=True)


def render_microbiome_workspace():
    st.markdown("<div style='color:#22c55e;font-size:1.1rem;font-weight:800;margin-bottom:.4rem;'>🦠 Microbiome Intelligence Platform</div>", unsafe_allow_html=True)
    st.info("Microbiome workspace with annotation engine, taxonomy intelligence, host-microbe interactions, and BGC analysis. Search a protein in the sidebar for full analysis or use the Annotation Engine below.")

    mode = st.radio("", ["🔬 Annotation Engine", "🌳 Taxonomy Intelligence", "🔗 Host-Microbe Interactions", "🧪 BGC Analysis"], horizontal=True, key="mic_mode")

    if mode == "🔬 Annotation Engine":
        sh("⚡", "Vague → Specific Annotation Engine")
        st.text_input("Paste vague annotation", placeholder="e.g. biosynthesis · chemosynthesis · hypothetical protein · metabolism", key="mic_vague")
        st.caption("Enter a vague functional annotation to get specific EC-numbered pathways and mechanisms.")

    elif mode == "🌳 Taxonomy Intelligence":
        sh("🌳", "Microbial Taxonomy Intelligence")
        st.text_input("Search microbe genus/species", placeholder="e.g. Akkermansia · Fusobacterium · Helicobacter", key="mic_tax_search")
        st.caption("Curated knowledge base: ecological role, clinical significance, and host interactions.")

    elif mode == "🔗 Host-Microbe Interactions":
        sh("🔗", "Host-Microbe Interaction Atlas")
        st.caption("Known host receptor interactions for microbial surface proteins and metabolites.")

    else:
        sh("🧪", "Biosynthetic Gene Cluster (BGC) Analysis")
        st.caption("BGC types, detection tools, and predicted products. Cross-reference with MiBIG database.")


def render_pharma_workspace():
    st.markdown("<div style='color:#00d4ff;font-size:1.1rem;font-weight:800;margin-bottom:.4rem;'>💊 Drug Discovery Workspace</div>", unsafe_allow_html=True)
    st.info("GPCR Filamin piggyback assay, druggability scoring, ADMET rules, HTS pipeline, and clinical development timeline. Search a protein in the sidebar for full tractability + variant analysis.")


def render_molbio_workspace():
    st.markdown("<div style='color:#fb923c;font-size:1.1rem;font-weight:800;margin-bottom:.4rem;'>⚛️ Molecular Biology Workspace</div>", unsafe_allow_html=True)
    st.info("Kinase-substrate networks, PTM landscape, structural biology tools, and mechanism dissection. Search a protein via the sidebar for full phosphorylation map and structural domain cards.")


def render_rare_disease_workspace():
    st.markdown("<div style='color:#c084fc;font-size:1.1rem;font-weight:800;margin-bottom:.4rem;'>🧬 Rare Disease Workspace</div>", unsafe_allow_html=True)
    st.info("VUS prioritisation engine, HPO → candidate genes, ACMG/AMP classifier, functional validation roadmap, and inheritance analyser. Search a protein in the sidebar for full genetic analysis.")


def render_oncology_panel(gene, pdata, cv, scored, gi, gnomad, ot_data, am_scores, string_data, patient_data):
    from modules.data_processing import g_diseases, g_ptype, g_ptype as _gp
    from modules.utils import sh

    diseases = g_diseases(pdata)
    cancer_diseases = [d for d in diseases if any(k in d.get("name","").lower() for k in
                       ["cancer","carcinoma","tumor","tumour","sarcoma","glioma","lymphoma","leukemia","leukaemia","melanoma","myeloma","adenocarcinoma"])]
    somatic_variants = [v for v in scored if v.get("somatic",False) and v.get("score",0)>=3]
    n_crit = sum(1 for v in scored if v.get("ml_rank")=="CRITICAL")
    pLI = gnomad.get("pLI",0) or 0
    _is_gpcr9 = g_gpcr(pdata) if pdata else False
    _is_kin9 = _gp(pdata) == "kinase"

    sh("🎗", f"Oncology Intelligence — {gene}")

    with st.expander("👤 Patient/Cancer Context (optional — personalise analysis)", expanded=True):
        cols_p = st.columns(3)
        with cols_p[0]:
            cancer_type = st.selectbox("Cancer type", ["Not specified","Lung adenocarcinoma","Breast cancer (HR+)","Breast cancer (TNBC)","Colorectal cancer","Glioblastoma","Pancreatic ductal adenocarcinoma","Ovarian cancer","Melanoma","Hepatocellular carcinoma","Prostate cancer","AML","CLL","Other"], key="onc_type")
            stage = st.selectbox("Stage", ["Unknown","Stage 0 (CIS)","Stage I","Stage II","Stage III","Stage IV (Metastatic)"], key="onc_stage")
        with cols_p[1]:
            variant_input = st.text_input("Patient variant (p.notation)", placeholder="p.Arg175His · p.Gly12Asp", key="onc_variant")
            germline_som = st.radio("Variant origin", ["Somatic","Germline","Unknown"], horizontal=True, key="onc_origin")
        with cols_p[2]:
            msi_status = st.selectbox("MSI status", ["Unknown","MSS (microsatellite stable)","MSI-H (high)","MSI-L (low)"], key="onc_msi")
            tmb = st.number_input("TMB (mut/Mb)", 0, 500, 0, key="onc_tmb")

    is_metastatic = "IV" in stage
    is_germline = germline_som == "Germline"
    is_msih = "MSI-H" in msi_status
    is_driver = n_crit >= 2

    met_risk_score = 0
    if is_metastatic: met_risk_score += 4
    if is_driver: met_risk_score += 3
    if len(somatic_variants) > 5: met_risk_score += 2
    if "IV" in stage: met_risk_score += 2
    met_risk = "VERY HIGH" if met_risk_score>=8 else "HIGH" if met_risk_score>=5 else "MODERATE" if met_risk_score>=3 else "LOW"
    met_clr = "#ff2d55" if "HIGH" in met_risk else "#ffd60a" if met_risk=="MODERATE" else "#22c55e"

    col_o1, col_o2, col_o3, col_o4 = st.columns(4)
    col_o1.metric("Metastasis Risk", met_risk)
    col_o2.metric("P/LP Variants", gi.get("n_pathogenic",0))
    col_o3.metric("CRITICAL ML variants", n_crit)
    col_o4.metric("Cancer diseases", len(cancer_diseases))

    sh("💊", "Treatment Strategy — Personalised")

    strategies = []
    if any(k in gene for k in ["BRCA1","BRCA2","ATM","PALB2","CHEK2"]):
        strategies.append(("PARP Inhibitor (olaparib/niraparib)", "#22c55e", "Synthetic lethality via HRD. FDA-approved for BRCA1/2 germline carriers."))
    if any(k in gene for k in ["EGFR","ALK","ROS1","MET","BRAF","RET","NTRK"]):
        strategies.append(("Targeted kinase inhibitor", "#00e5ff", f"{gene} = oncogenic kinase driver. Match specific exon/codon variant to approved drug."))
    if is_msih or tmb > 10:
        strategies.append(("Immune checkpoint inhibitor (pembrolizumab)", "#a855f7", f"{'MSI-H' if is_msih else 'High TMB'} = FDA-approved pembrolizumab biomarker."))
    if ot_data.get("tractability",{}).get("Small molecule") and n_crit >= 2:
        strategies.append(("Small molecule inhibitor (HTS candidate)", "#ffd60a", f"OpenTargets confirms small molecule tractability for {gene}."))
    if pLI > 0.9 and is_germline:
        strategies.append(("ASO / RNA-targeted therapy", "#ff8c42", f"pLI={pLI:.2f} — highly constrained gene. ASO skip-exon or gene therapy viable."))
    if not strategies:
        strategies.append(("Standard-of-care ± clinical trial", "#3a6080", f"No specific targeted therapy identified for {gene} variants. Search ClinicalTrials.gov."))

    for sname, sclr, sdesc in strategies:
        st.markdown(
            f"<div style='background:#010810;border:1px solid {sclr}33;border-left:3px solid {sclr};"
            f"border-radius:0 8px 8px 0;padding:9px 12px;margin:.4rem 0;'>"
            f"<div style='color:{sclr};font-size:.78rem;font-weight:700;margin-bottom:3px;'>💊 {sname}</div>"
            f"<div style='color:#3a6080;font-size:.76rem;line-height:1.6;'>{sdesc}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
