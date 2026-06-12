# modules/visualization.py
from __future__ import annotations
import json, math
import streamlit as st
import plotly.graph_objects as go
import streamlit.components.v1 as components
from modules.config import AA_HYDRO, AA_CHG, AA_NAMES, RANK_CLR, RANK_CSS

def parse_bfactors(pdb):
    out={}
    for line in pdb.splitlines():
        if line.startswith(("ATOM","HETATM")):
            try:
                rn=int(line[22:26]); bf=float(line[60:66]); an=line[12:16].strip()
                if an=="CA": out[rn]=bf
            except: pass
    return out

def viewer_html(pdb_text, scored, height=480):
    path_pos={}
    for v in scored[:50]:
        pos=v.get("start") or v.get("position")
        try:
            p2=int(pos)
            path_pos[p2]={"rank":v.get("ml_rank","NEUTRAL"),"ml":v.get("ml",0),
                          "cond":v.get("condition","")[:60],"sig":v.get("sig",""),
                          "var":v.get("variant_name","")[:40],"url":v.get("url","")}
        except: pass
    pp_js=json.dumps({str(k):v for k,v in path_pos.items()})
    pdb_esc=pdb_text.replace("`","\\`").replace("\\","\\\\")
    return f"""<!DOCTYPE html><html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
<style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{background:#04080f;font-family:Inter,sans-serif;display:flex;flex-direction:column;height:{height}px;}}
#ctrl{{display:flex;gap:4px;padding:6px 8px;background:#050f1e;border-bottom:1px solid #0c2040;flex-wrap:wrap;flex-shrink:0;}}
.btn{{background:#05101e;color:#2a5070;border:1px solid #0c2040;padding:3px 10px;border-radius:14px;cursor:pointer;font-size:11px;transition:all .2s;}}
.btn:hover,.btn.on{{background:#00e5ff;color:#000;font-weight:700;border-color:#00e5ff;}}
#wrap{{position:relative;flex:1;}}#v{{width:100%;height:100%;}}
#panel{{position:absolute;top:8px;right:8px;width:230px;background:rgba(4,8,15,.95);border:1px solid #0c2040;border-radius:10px;padding:12px;display:none;backdrop-filter:blur(8px);max-height:88%;overflow-y:auto;}}
#panel h3{{color:#00e5ff;font-size:12px;margin:0 0 7px;border-bottom:1px solid #0c2040;padding-bottom:4px;}}
.pr{{display:flex;justify-content:space-between;margin:3px 0;font-size:11px;}}.pk{{color:#0e2840;}}.pv{{color:#5a8090;font-weight:600;}}
#cl{{position:absolute;top:6px;right:8px;color:#1e4060;cursor:pointer;font-size:14px;}}
#leg{{position:absolute;bottom:7px;left:7px;background:rgba(4,8,15,.9);border:1px solid #0c2040;border-radius:8px;padding:7px 10px;font-size:10px;color:#1e4060;}}
.li{{display:flex;align-items:center;gap:5px;margin:2px 0;}}.ld{{width:8px;height:8px;border-radius:50%;flex-shrink:0;}}</style></head><body>
<div id="ctrl">
<button class="btn on" onclick="ss('cartoon',this)">🎀 Ribbon</button>
<button class="btn" onclick="ss('stick',this)">🦴 Stick</button>
<button class="btn" onclick="ss('sphere',this)">⬤ Sphere</button>
<button class="btn" onclick="ss('surface',this)">🌊 Surface</button>
<button class="btn" id="spb" onclick="toggleSpin()">▶ Spin</button>
<button class="btn" onclick="v.zoomTo();v.render()">🎯 Reset</button>
<button class="btn" onclick="toggleV()">🔴 Variants</button>
<button class="btn" onclick="toggleL()">🏷 Labels</button>
</div>
<div id="wrap"><div id="v"></div>
<div id="panel"><span id="cl" onclick="document.getElementById('panel').style.display='none'">✕</span>
<h3 id="pt">Residue Info</h3><div id="pc"></div></div>
<div id="leg">
<div class="li"><div class="ld" style="background:#1565C0"></div>Very confident (pLDDT ≥90)</div>
<div class="li"><div class="ld" style="background:#29B6F6"></div>Confident (70–90)</div>
<div class="li"><div class="ld" style="background:#FDD835"></div>Low confidence (50–70)</div>
<div class="li"><div class="ld" style="background:#FF7043"></div>Very low (&lt;50)</div>
<div class="li"><div class="ld" style="background:#ff2d55;border:1px solid #fff5;"></div>Disease-causing variant</div>
</div></div>
<script>
const pp={pp_js};const pdb=`{pdb_esc}`;
const an={{ALA:"A",ARG:"R",ASN:"N",ASP:"D",CYS:"C",GLN:"Q",GLU:"E",GLY:"G",HIS:"H",ILE:"I",LEU:"L",LYS:"K",MET:"M",PHE:"F",PRO:"P",SER:"S",THR:"T",TRP:"W",TYR:"Y",VAL:"V"}};
const fn={{A:"Alanine",R:"Arginine",N:"Asparagine",D:"Aspartate",C:"Cysteine",Q:"Glutamine",E:"Glutamate",G:"Glycine",H:"Histidine",I:"Isoleucine",L:"Leucine",K:"Lysine",M:"Methionine",F:"Phenylalanine",P:"Proline",S:"Serine",T:"Threonine",W:"Tryptophan",Y:"Tyrosine",V:"Valine"}};
const hy={{A:1.8,R:-4.5,N:-3.5,D:-3.5,C:2.5,Q:-3.5,E:-3.5,G:-0.4,H:-3.2,I:4.5,L:3.8,K:-3.9,M:1.9,F:2.8,P:-1.6,S:-0.8,T:-0.7,W:-0.9,Y:-1.3,V:4.2}};
let spinning=false,showV=true,showL=false,curStyle='cartoon';
const v=$3Dmol.createViewer(document.getElementById('v'),{{backgroundColor:'0x04080f'}});
v.addModel(pdb,'pdb');
function cf(a){{const b=a.b;if(b>=90)return'#1565C0';if(b>=70)return'#29B6F6';if(b>=50)return'#FDD835';return'#FF7043';}}
function ap(){{v.removeAllSurfaces();
if(curStyle==='surface')v.addSurface($3Dmol.SurfaceType.VDW,{{colorfunc:cf,opacity:.78}});
else if(curStyle==='sphere')v.setStyle({{}},{{sphere:{{colorfunc:cf,radius:.7}}}});
else if(curStyle==='stick')v.setStyle({{}},{{cartoon:{{colorfunc:cf,thickness:.2}},stick:{{colorscheme:'chainHetatm',radius:.12}}}});
else v.setStyle({{}},{{cartoon:{{colorfunc:cf,thickness:.42}}}});
if(showV)Object.entries(pp).forEach(([pos,info])=>{{const rk=info.rank;const c=rk==='CRITICAL'?'#ff2d55':rk==='HIGH'?'#ff8c42':rk==='MEDIUM'?'#ffd60a':'#3a5a7a';v.addStyle({{resi:parseInt(pos),atom:'CA'}},{{sphere:{{radius:1.3,color:c,opacity:.93}}}});}});
v.render();}}
ap();v.zoomTo();v.render();
v.setClickable({{}},true,function(atom){{
const pos=atom.resi,r3=(atom.resn||'').toUpperCase(),r1=an[r3]||'?';
const full=fn[r1]||r3,pl=atom.b||0,cl=pl>=90?'Very High':pl>=70?'Confident':pl>=50?'Low':'Very Low';
const inf=pp[String(pos)];let html='';
if(inf){{const rc={{CRITICAL:'#ff2d55',HIGH:'#ff8c42',MEDIUM:'#ffd60a',NEUTRAL:'#3a5a7a'}};
html+=`<span style="color:${{rc[inf.rank]}};font-weight:800;font-size:11px;display:block;margin-bottom:5px;">${{inf.rank}}</span>`;}}
html+=`<div class="pr"><span class="pk">Residue (building block)</span><span class="pv">${{r1}} (${{full}})</span></div>`;
html+=`<div class="pr"><span class="pk">Position in chain</span><span class="pv">${{pos}}</span></div>`;
html+=`<div class="pr"><span class="pk">Model confidence</span><span class="pv">${{pl.toFixed(1)}} (${{cl}})</span></div>`;
html+=`<div class="pr"><span class="pk">Hydropathy (water-love)</span><span class="pv">${{hy[r1]!==undefined?hy[r1].toFixed(1):'?'}}</span></div>`;
if(inf){{html+='<hr style="border-color:#0c2040;margin:5px 0;">';
html+=`<div class="pr"><span class="pk">Variant (DNA change)</span><span class="pv" style="font-size:10px;">${{inf.var||'—'}}</span></div>`;
html+=`<div class="pr"><span class="pk">Clinical significance</span><span class="pv" style="font-size:10px;">${{inf.sig||'—'}}</span></div>`;
html+=`<div class="pr"><span class="pk">ML disease score</span><span class="pv" style="color:#00e5ff;">${{(inf.ml*100).toFixed(0)}}%</span></div>`;
if(inf.url)html+=`<a href="${{inf.url}}" target="_blank" style="color:#2a80a4;font-size:10px;display:block;margin-top:4px;">↗ View in ClinVar</a>`;
if(inf.cond)html+=`<div style="margin-top:4px;color:#0e2840;font-size:10px;line-height:1.4;">${{inf.cond}}</div>`;}}
document.getElementById('pt').textContent=r3+pos;document.getElementById('pc').innerHTML=html;document.getElementById('panel').style.display='block';}});
function ss(style,btn){{curStyle=style;document.querySelectorAll('.btn').forEach(b=>b.classList.remove('on'));btn.classList.add('on');ap();}}
function toggleSpin(){{spinning=!spinning;v.spin(spinning?'y':false,.6);const b=document.getElementById('spb');b.textContent=spinning?'⏸ Stop':'▶ Spin';b.classList.toggle('on',spinning);}}
function toggleV(){{showV=!showV;ap();}}
function toggleL(){{showL=!showL;v.removeAllLabels();if(showL)Object.entries(pp).forEach(([pos,info])=>{{if(info.rank==='CRITICAL'||info.rank==='HIGH')v.addLabel('P'+pos,{{position:{{resi:parseInt(pos),atom:'CA'}},backgroundColor:'#ff2d55',backgroundOpacity:.8,fontSize:9,fontColor:'white',borderRadius:3}});}});v.render();}}
</script></body></html>""".replace("{pp_js}",pp_js)

def variant_landscape_fig(variants, protein_length, scored):
    if not variants: return None
    sig_c={5:"#ff2d55",4:"#ff6b55",3:"#ff8c42",2:"#ffd60a",1:"#2a6040",0:"#0e2840",-1:"#060f18"}
    sig_l={5:"Disease-causing (pathogenic)",4:"Likely disease-causing",3:"Risk factor",
           2:"Unknown significance (VUS)",1:"Likely harmless (likely benign)",0:"Harmless (benign)",-1:"Not classified"}
    ml_map={v.get("uid",""):v.get("ml",0) for v in scored}
    positions,ys,colours,labels,urls=[],[],[],[],[]
    for v in variants:
        pos_int = None
        raw_start = v.get("start","")
        if raw_start:
            try: pos_int = int(raw_start)
            except: pass
        if pos_int is None:
            import re as _re2
            vn2 = v.get("variant_name","") or v.get("title","")
            pm2 = _re2.search(r"p\.(?:[A-Za-z]+)?(\d+)", vn2)
            if pm2:
                try: pos_int = int(pm2.group(1))
                except: pass
        if pos_int is None:
            continue
        sc=v.get("score",-1); ml2=ml_map.get(v.get("uid",""),0)
        name2=(v.get("variant_name") or v.get("title",""))[:40]; url=v.get("url","")
        positions.append(pos_int); ys.append(max(sc,0)+ml2*.4)
        colours.append(sig_c.get(sc,"#0e2840"))
        labels.append(f"{name2}<br>{sig_l.get(sc,'?')}<br>ML score: {ml2:.2f}<extra></extra>")
        urls.append(url)
    if not positions: return None
    fig=go.Figure()
    for x,y,c in zip(positions,ys,colours):
        fig.add_trace(go.Scatter(x=[x,x],y=[0,y],mode="lines",line=dict(color=c,width=1),showlegend=False,hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=positions,y=ys,mode="markers",
        marker=dict(color=colours,size=7,opacity=.85,line=dict(color="#04080f",width=.5)),
        text=labels,hovertemplate="%{text}",showlegend=False))
    fig.add_hrect(y0=0,y1=.8,fillcolor="rgba(6,30,6,0.2)",line_width=0)
    fig.add_hrect(y0=3.5,y1=6,fillcolor="rgba(80,0,20,0.15)",line_width=0)
    maxpos=max(protein_length or 100,max(positions)+10)
    fig.update_layout(paper_bgcolor="#04080f",plot_bgcolor="#04080f",font_color="#1e4060",
        xaxis=dict(title="Position in protein chain (amino acid number)",range=[0,maxpos],gridcolor="#060f1c",color="#0e2840"),
        yaxis=dict(title="Disease severity score",range=[-0.1,6.2],
            tickvals=[0,2,4,5],ticktext=["Harmless","Unknown","Likely Disease","Disease-causing"],
            gridcolor="#060f1c",color="#0e2840"),
        height=270,margin=dict(t=8,b=30,l=90,r=8),hovermode="closest")
    return fig

def mutation_cascade_html(gene, is_gpcr, pursue, top_variants):
    top_var = top_variants[0] if top_variants else {}
    var_name = (top_var.get("variant_name","") or "Unknown variant")[:30]
    condition = (top_var.get("condition","Unknown disease"))[:40]
    pursue_color = "#ff2d55" if pursue=="prioritise" else "#ffd60a" if pursue in ["proceed","selective"] else "#3a5a7a"
    
    stages = [
        {"title":"① Healthy protein",
         "plain":"The normal, correctly folded protein doing its job",
         "desc":f"Wild-type {gene} is folded correctly. All domains functional. Signalling pathway intact.",
         "cell_color":"#00c896","shape":"circle","signal":100,"apoptosis":0},
        {"title":"② DNA spelling change (mutation) introduced",
         "plain":"A single letter in the DNA blueprint is changed",
         "desc":f"Variant {var_name} introduced. One amino acid (protein building block) replaced. Structure at risk.",
         "cell_color":"#ffd60a","shape":"circle","signal":80,"apoptosis":5},
        {"title":"③ Protein shape distortion (misfolding / instability)",
         "plain":"The protein loses its correct 3D shape",
         "desc":"Altered amino acid disrupts local folding. Domain stability reduced. Binding pocket geometry changed.",
         "cell_color":"#ff8c42","shape":"ellipse","signal":55,"apoptosis":15},
        {"title":"④ Signal receiver disrupted" + (" — GPCR uncoupled" if is_gpcr else " — pathway broken"),
         "plain":"The protein can no longer pass signals correctly into the cell",
         "desc":("GPCR coupling impaired. G-protein (signal relay switch) cannot be activated. "
                 "Second messenger (internal signal relay: cAMP / Ca²⁺) levels altered." if is_gpcr else
                 "Downstream pathway disrupted. Protein cannot bind partners or substrates correctly."),
         "cell_color":"#ff6b00","shape":"ellipse","signal":30,"apoptosis":30},
        {"title":"⑤ Cell stress response activated",
         "plain":"The cell recognises something is wrong and starts emergency protocols",
         "desc":"ER stress pathway activated. Unfolded protein response (UPR) triggered. Mitochondrial membrane potential changes.",
         "cell_color":"#ff4444","shape":"irregular","signal":15,"apoptosis":60},
        {"title":"⑥ Cell death (apoptosis) / shape change",
         "plain":"The cell either dies or changes shape, causing tissue damage",
         "desc":"Caspase cascade initiated (cell-death machinery). Cytoskeletal reorganisation. Cell rounding or blebbing.",
         "cell_color":"#ff2d55","shape":"fragments","signal":5,"apoptosis":90},
        {"title":f"⑦ Disease: {condition}",
         "plain":"The accumulated cell damage leads to a visible disease",
         "desc":f"Repeated cycles of cell dysfunction accumulate into the clinical presentation: {condition}.",
         "cell_color":"#c0102a","shape":"fragments","signal":0,"apoptosis":100},
    ]
    
    stages_js = json.dumps(stages)
    
    return f"""<!DOCTYPE html><html><head>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:Inter,sans-serif;}}
body{{background:#04080f;color:#c0d8f8;padding:16px;}}
#slider-wrap{{margin-bottom:16px;}}
#stg-slider{{width:100%;-webkit-appearance:none;appearance:none;height:6px;
  border-radius:3px;background:linear-gradient(90deg,{pursue_color},#1e4060);outline:none;}}
#stg-slider::-webkit-slider-thumb{{-webkit-appearance:none;width:20px;height:20px;
  border-radius:50%;background:{pursue_color};cursor:pointer;box-shadow:0 0 10px {pursue_color}88;}}
#stage-title{{font-size:1rem;font-weight:800;color:{pursue_color};margin-bottom:3px;}}
#stage-plain{{font-size:1rem;color:#3a8090;margin-bottom:10px;font-style:italic;}}
#stage-desc{{font-size:1.02rem;color:#3a6080;line-height:1.6;margin-bottom:12px;}}
#stage-num{{color:#1e4060;font-size:.80rem;margin-bottom:8px;}}
.vis-row{{display:flex;gap:12px;align-items:flex-end;margin-bottom:12px;}}
.vis-col{{flex:1;background:#050d1a;border:1px solid #0c2040;border-radius:10px;padding:10px;text-align:center;}}
.vis-label{{font-size:1.02rem;color:#1e4060;text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px;}}
.bar-wrap{{height:80px;background:#07152a;border-radius:6px;overflow:hidden;display:flex;align-items:flex-end;}}
.bar{{width:100%;border-radius:6px;transition:height .5s ease,background .5s ease;}}
.cell-vis{{width:60px;height:60px;margin:0 auto 4px;transition:all .5s ease;}}
.step-dots{{display:flex;gap:6px;justify-content:center;margin-top:8px;}}
.dot{{width:8px;height:8px;border-radius:50%;background:#0c2040;transition:background .3s;}}
.dot.active{{background:{pursue_color};box-shadow:0 0 8px {pursue_color}88;}}
</style></head><body>
<div id="stage-num">Stage <span id="sn">1</span> of 7</div>
<div id="stage-title">Loading…</div>
<div id="stage-plain"></div>
<div id="stage-desc"></div>
<div class="vis-row">
  <div class="vis-col">
    <div class="vis-label">Signal strength (how well the protein works)</div>
    <div class="bar-wrap"><div class="bar" id="sig-bar" style="height:100%;background:#00c896;"></div></div>
    <div style="color:#1e4060;font-size:.96rem;margin-top:4px;"><span id="sig-val">100</span>%</div>
  </div>
  <div class="vis-col">
    <div class="vis-label">Cell shape</div>
    <svg id="cell-svg" width="70" height="70" viewBox="0 0 70 70" style="display:block;margin:0 auto;">
      <ellipse id="cell-shape" cx="35" cy="35" rx="30" ry="30" fill="#00c89622" stroke="#00c896" stroke-width="2"/>
      <circle id="nucleus" cx="35" cy="35" r="10" fill="#1e6040" opacity="0.8"/>
    </svg>
  </div>
  <div class="vis-col">
    <div class="vis-label">Cell death risk (apoptosis)</div>
    <div class="bar-wrap"><div class="bar" id="apo-bar" style="height:0%;background:#ff2d55;"></div></div>
    <div style="color:#1e4060;font-size:.96rem;margin-top:4px;"><span id="apo-val">0</span>%</div>
  </div>
</div>
<div id="slider-wrap">
  <input type="range" id="stg-slider" min="0" max="6" value="0" step="1">
</div>
<div class="step-dots" id="dots"></div>
<script>
const stages={stages_js};
const dotsEl=document.getElementById('dots');
stages.forEach((_,i)=>{{const d=document.createElement('div');d.className='dot'+(i===0?' active':'');dotsEl.appendChild(d);}});
function update(idx){{
  const s=stages[idx];
  document.getElementById('stage-title').textContent=s.title;
  document.getElementById('stage-plain').textContent='"'+s.plain+'"';
  document.getElementById('stage-desc').textContent=s.desc;
  document.getElementById('sn').textContent=idx+1;
  document.getElementById('sig-bar').style.height=s.signal+'%';
  document.getElementById('sig-bar').style.background=s.cell_color;
  document.getElementById('sig-val').textContent=s.signal;
  document.getElementById('apo-bar').style.height=s.apoptosis+'%';
  document.getElementById('apo-val').textContent=s.apoptosis;
  const cs=document.getElementById('cell-shape');
  const nuc=document.getElementById('nucleus');
  if(s.shape==='circle'){{cs.setAttribute('rx',30);cs.setAttribute('ry',30);nuc.setAttribute('r',10);nuc.setAttribute('opacity','0.8');}}
  else if(s.shape==='ellipse'){{cs.setAttribute('rx',34);cs.setAttribute('ry',24);nuc.setAttribute('r',9);nuc.setAttribute('opacity','0.7');}}
  else if(s.shape==='irregular'){{cs.setAttribute('rx',36);cs.setAttribute('ry',20);nuc.setAttribute('r',7);nuc.setAttribute('opacity','0.5');}}
  else{{cs.setAttribute('rx',20);cs.setAttribute('ry',14);nuc.setAttribute('r',4);nuc.setAttribute('opacity','0.2');}}
  cs.setAttribute('fill',s.cell_color+'22');
  cs.setAttribute('stroke',s.cell_color);
  nuc.setAttribute('fill',s.cell_color+'88');
  document.querySelectorAll('.dot').forEach((d,i)=>d.classList.toggle('active',i===idx));
}}
update(0);
document.getElementById('stg-slider').addEventListener('input',function(){{update(parseInt(this.value));}});
</script></body></html>"""

def build_mutation_dynamics_html(gene, protein_length, scored, variants, hotspots, diseases, ptype, is_gpcr):
    import json as _json
    germline_vars = []
    somatic_vars = []
    for v in scored[:60]:
        pos = v.get("start","")
        try: pos_int = int(pos)
        except: continue
        entry = {
            "pos": pos_int,
            "pct": round(pos_int / max(protein_length,1) * 100, 1),
            "ml": round(v.get("ml",0), 3),
            "rank": v.get("ml_rank","NEUTRAL"),
            "sig": v.get("sig","")[:40],
            "var": (v.get("variant_name","") or v.get("title",""))[:45],
            "cond": v.get("condition","")[:60],
            "somatic": bool(v.get("somatic")),
            "germline": bool(v.get("germline") or v.get("score",0)>=3),
        }
        if entry["somatic"]:
            somatic_vars.append(entry)
        else:
            germline_vars.append(entry)

    hotspot_data = [
        {
            "start": h["start"],
            "end":   h["end"],
            "pct_start": round(h["start"]/max(protein_length,1)*100,1),
            "pct_end":   round(h["end"]/max(protein_length,1)*100,1),
            "fold": h["fold_enrichment"],
            "count": h["count"],
        }
        for h in hotspots[:5]
    ]

    if is_gpcr:
        cascade_stages = [
            ("Wild-type", "GPCR correctly folds — 7 transmembrane helices intact. Ligand binds extracellular domain. G-protein couples to intracellular loops. Signal transmits.", "#00c896"),
            ("Mutation introduced", "Single amino acid change at pathogenic site. Transmembrane helix geometry perturbed. Binding pocket shape altered.", "#ffd60a"),
            ("GPCR uncoupling", "Mutant receptor fails to couple G-protein (Gs/Gi/Gq). Second messenger (cAMP/Ca²⁺) levels dysregulated. Downstream kinases affected.", "#ff8c42"),
            ("β-arrestin recruitment altered", "Desensitisation machinery misfires. Receptor either constitutively active (GoF) or permanently silent (LoF). Cell cannot adapt.", "#ff6b00"),
            ("Cell dysfunction", "Signal pathway permanently dysregulated. Apoptosis, hypertrophy, or aberrant proliferation — depending on tissue context.", "#ff2d55"),
            ("Tissue/Organ pathology", "Accumulated cell dysfunction → tissue-level disease. Cardiomyopathy, visual impairment, metabolic disorder — context-specific.", "#c0102a"),
        ]
    elif ptype == "kinase":
        cascade_stages = [
            ("Wild-type", "Kinase correctly folds. ATP-binding pocket accessible. Activation loop in correct orientation. Substrate binding efficient.", "#00c896"),
            ("Mutation introduced", "Pathogenic substitution at catalytic or regulatory residue. Protein backbone geometry changes.", "#ffd60a"),
            ("Catalytic disruption", "ATP binding reduced OR constitutive activity gained. Phosphorylation of substrates altered — under- or over-phosphorylation.", "#ff8c42"),
            ("Signalling cascade rewired", "Downstream effectors receive wrong signal strength. Cell cycle, apoptosis, or metabolic pathways dysregulated.", "#ff6b00"),
            ("Cell phenotype change", "Uncontrolled proliferation (GoF) or growth arrest (LoF). Apoptosis resistance. Metabolic reprogramming.", "#ff2d55"),
            ("Disease manifestation", "Cancer (somatic GoF) or developmental/metabolic syndrome (germline LoF/GoF) — depends on variant class.", "#c0102a"),
        ]
    else:
        cascade_stages = [
            ("Wild-type", "Protein correctly folded. All functional domains intact. Physiological interactions with partners maintained. Normal cellular function.", "#00c896"),
            ("Mutation introduced", "DNA variant translates to amino acid change at pathogenic position. Local structural perturbation begins.", "#ffd60a"),
            ("Protein instability", "Altered residue disrupts hydrophobic core or electrostatic contacts. Protein mis-folds or loses stability. Half-life may decrease.", "#ff8c42"),
            ("Interaction network disrupted", "Key binding interfaces perturbed. Partner proteins cannot bind OR aberrant new interactions form. Pathway stoichiometry breaks.", "#ff6b00"),
            ("Cell stress response", "UPR (unfolded protein response) activated. Proteasomal load increases. Mitochondrial membrane potential changes. Apoptotic signals mount.", "#ff2d55"),
            ("Disease manifestation", "Tissue-specific phenotype — cardiomyopathy, myopathy, neurodegeneration, or cancer — depending on protein's normal tissue role.", "#c0102a"),
        ]

    stages_js = _json.dumps(cascade_stages)
    gv_js = _json.dumps(germline_vars)
    sv_js = _json.dumps(somatic_vars)
    hs_js = _json.dumps(hotspot_data)
    plen = protein_length

    return f"""<!DOCTYPE html><html><head>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:Inter,sans-serif;}}
body{{background:#010306;color:#c0d8f8;padding:14px;overflow-x:hidden;}}
h3{{color:#00e5ff;font-size:.95rem;font-weight:700;margin-bottom:8px;}}
#ctrl{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;align-items:center;}}
.btn{{background:#050d1a;border:1px solid #0d2545;color:#3a7090;padding:4px 12px;border-radius:8px;cursor:pointer;font-size:.78rem;font-weight:600;transition:all .2s;}}
.btn:hover,.btn.on{{background:#00e5ff;color:#000;border-color:#00e5ff;}}
#proto-wrap{{position:relative;margin-bottom:12px;}}
#proto-label{{font-size:.72rem;color:#2a5070;margin-bottom:4px;display:flex;justify-content:space-between;}}
#proto-bar{{position:relative;height:28px;background:#050d1a;border-radius:6px;border:1px solid #0d2545;overflow:visible;cursor:crosshair;}}
.hotspot-zone{{position:absolute;top:0;bottom:0;border-radius:4px;opacity:.35;transition:opacity .3s;}}
.hotspot-zone:hover{{opacity:.7;}}
.var-dot{{position:absolute;top:50%;transform:translate(-50%,-50%);border-radius:50%;cursor:pointer;transition:all .3s;z-index:10;}}
.var-dot:hover{{transform:translate(-50%,-50%) scale(1.8);z-index:20;}}
.domain-label{{position:absolute;font-size:.6rem;color:#1e4060;top:calc(100%+4px);white-space:nowrap;transform:translateX(-50%);}}
#tip{{position:fixed;background:rgba(2,8,16,.97);border:1px solid #0d2545;border-radius:9px;padding:10px 13px;
  font-size:.78rem;display:none;pointer-events:none;z-index:999;max-width:260px;
  box-shadow:0 8px 32px rgba(0,0,0,.6);}}
#tip .trank{{font-weight:800;font-size:.86rem;margin-bottom:4px;}}
#tip .trow{{display:flex;justify-content:space-between;margin:2px 0;}}
#tip .tk{{color:#1e4060;}}.tip .tv{{color:#5a8090;font-weight:600;}}
#cascade{{margin-top:10px;}}
#stage-nav{{display:flex;gap:4px;margin-bottom:8px;flex-wrap:wrap;}}
.snav{{background:#030d1a;border:1px solid #0d2545;color:#1e4060;padding:3px 10px;border-radius:6px;cursor:pointer;font-size:.72rem;transition:all .2s;}}
.snav.active{{font-weight:700;}}
#stage-display{{background:#020810;border:1px solid #0d2545;border-radius:10px;padding:12px 14px;transition:all .4s;}}
#stage-title{{font-size:.9rem;font-weight:700;margin-bottom:5px;}}
#stage-body{{font-size:.82rem;line-height:1.6;color:#5a8090;}}
#cellviz{{display:flex;gap:10px;margin-top:8px;align-items:flex-end;}}
.cviz-col{{flex:1;background:#020810;border:1px solid #0d2545;border-radius:8px;padding:8px;text-align:center;}}
.cviz-label{{font-size:.66rem;color:#1e4060;margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px;}}
.cviz-bar-wrap{{height:60px;background:#040d18;border-radius:4px;overflow:hidden;display:flex;flex-direction:column;justify-content:flex-end;}}
.cviz-bar{{border-radius:4px;transition:height .8s cubic-bezier(.34,1.56,.64,1);}}
.cviz-val{{font-size:.76rem;font-weight:700;margin-top:3px;}}
#legend{{display:flex;gap:10px;flex-wrap:wrap;margin:6px 0;font-size:.72rem;}}
.leg-item{{display:flex;align-items:center;gap:4px;color:#2a5070;}}
.leg-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0;}}
#slide-wrap{{margin-top:8px;}}
#stage-slider{{width:100%;-webkit-appearance:none;appearance:none;height:5px;border-radius:3px;
  background:linear-gradient(90deg,#00c896,#ff2d55);outline:none;cursor:pointer;}}
#stage-slider::-webkit-slider-thumb{{-webkit-appearance:none;width:18px;height:18px;border-radius:50%;background:#fff;cursor:pointer;box-shadow:0 0 8px rgba(255,255,255,.3);}}
#prog-dots{{display:flex;gap:5px;justify-content:space-between;margin-top:4px;}}
.pdot{{width:9px;height:9px;border-radius:50%;background:#0d2545;transition:all .3s;cursor:pointer;flex:1;max-width:9px;}}
.pdot.done{{background:var(--c);box-shadow:0 0 6px var(--c);}}
</style></head><body>

<div id="ctrl">
<span style="color:#3a6080;font-size:.8rem;font-weight:700;margin-right:4px;">{gene} · {plen} aa</span>
<button class="btn on" onclick="setMode('all',this)">All variants</button>
<button class="btn" onclick="setMode('germline',this)">🧬 Germline ({len(germline_vars)})</button>
<button class="btn" onclick="setMode('somatic',this)">🔴 Somatic ({len(somatic_vars)})</button>
<button class="btn" onclick="setMode('hotspots',this)">🎯 Hotspots ({len(hotspot_data)})</button>
</div>

<div id="proto-wrap">
<div id="proto-label">
<span>N-terminus (start)</span>
<span style="color:#3a6080;">{gene} protein chain — {plen} amino acids</span>
<span>C-terminus (end)</span>
</div>
<div id="proto-bar" onmousemove="showTip(event)" onmouseleave="hideTip()">
</div>
</div>

<div id="legend">
<div class="leg-item"><div class="leg-dot" style="background:#ff2d55;"></div>CRITICAL germline</div>
<div class="leg-item"><div class="leg-dot" style="background:#ff8c42;"></div>HIGH germline</div>
<div class="leg-item"><div class="leg-dot" style="background:#ffd60a;"></div>MEDIUM germline</div>
<div class="leg-item"><div class="leg-dot" style="background:#ff6b9d;border:1px solid #ff2d55;"></div>Somatic/cancer</div>
<div class="leg-item"><div class="leg-dot" style="background:#a855f7;opacity:.5;border-radius:2px;"></div>Hotspot cluster</div>
</div>

<div id="cascade">
<h3 id="cascade-title">Mutation Cascade — drag slider or click a stage</h3>
<div id="stage-nav"></div>
<div id="slide-wrap">
<input type="range" id="stage-slider" min="0" max="5" value="0" step="1">
<div id="prog-dots"></div>
</div>
<div id="stage-display" style="margin-top:8px;">
<div id="stage-title"></div>
<div id="stage-body"></div>
</div>
<div id="cellviz">
<div class="cviz-col"><div class="cviz-label">Protein function</div><div class="cviz-bar-wrap"><div class="cviz-bar" id="cv-prot" style="width:100%;height:100%;background:#00c896;"></div></div><div class="cviz-val" id="cv-prot-val" style="color:#00c896;">100%</div></div>
<div class="cviz-col"><div class="cviz-label">Cell signalling</div><div class="cviz-bar-wrap"><div class="cviz-bar" id="cv-sig" style="width:100%;height:100%;background:#4a90d9;"></div></div><div class="cviz-val" id="cv-sig-val" style="color:#4a90d9;">100%</div></div>
<div class="cviz-col"><div class="cviz-label">Cell viability</div><div class="cviz-bar-wrap"><div class="cviz-bar" id="cv-via" style="width:100%;height:100%;background:#ffd60a;"></div></div><div class="cviz-val" id="cv-via-val" style="color:#ffd60a;">100%</div></div>
<div class="cviz-col"><div class="cviz-label">Disease risk</div><div class="cviz-bar-wrap" style="justify-content:flex-start;"><div class="cviz-bar" id="cv-dis" style="width:100%;height:0%;background:#ff2d55;"></div></div><div class="cviz-val" id="cv-dis-val" style="color:#ff2d55;">0%</div></div>
</div>
</div>

<div id="tip">
<div class="trank" id="tip-rank"></div>
<div class="trow"><span class="tk">Variant</span><span class="tv" id="tip-var"></span></div>
<div class="trow"><span class="tk">Position</span><span class="tv" id="tip-pos"></span></div>
<div class="trow"><span class="tk">ClinVar</span><span class="tv" id="tip-sig"></span></div>
<div class="trow"><span class="tk">ML score</span><span class="tv" id="tip-ml"></span></div>
<div class="trow"><span class="tk">Disease</span><span class="tv" id="tip-cond"></span></div>
<div class="trow"><span class="tk">Origin</span><span class="tv" id="tip-origin"></span></div>
</div>

<script>
const gv={gv_js};
const sv={sv_js};
const hs={hs_js};
const stages={stages_js};
const plen={plen};
let curMode='all';

const RANK_CLR={{CRITICAL:'#ff2d55',HIGH:'#ff8c42',MEDIUM:'#ffd60a',NEUTRAL:'#3a5a7a'}};
const soma_clr = '#ff6b9d';

const CELL_METRICS = [
  {{prot:100,sig:100,via:100,dis:0}},
  {{prot:75,sig:80,via:95,dis:10}},
  {{prot:50,sig:55,via:80,dis:30}},
  {{prot:30,sig:25,via:60,dis:55}},
  {{prot:15,sig:10,via:35,dis:75}},
  {{prot:5,sig:5,via:10,dis:95}},
];

function renderBar(){{
  const bar = document.getElementById('proto-bar');
  bar.innerHTML = '';
  hs.forEach(h => {{
    const zone = document.createElement('div');
    zone.className = 'hotspot-zone';
    zone.style.cssText = `left:${{h.pct_start}}%;width:${{h.pct_end-h.pct_start}}%;background:#a855f7;`;
    zone.title = `Hotspot: ${{h.count}} variants, ${{h.fold}}× enrichment`;
    bar.appendChild(zone);
  }});
  let varsToShow = [];
  if(curMode==='all') varsToShow=[...gv,...sv];
  else if(curMode==='germline') varsToShow=gv;
  else if(curMode==='somatic') varsToShow=sv;
  varsToShow.forEach(v => {{
    const dot = document.createElement('div');
    dot.className = 'var-dot';
    const clr = v.somatic ? soma_clr : (RANK_CLR[v.rank]||'#3a5a7a');
    const sz = v.somatic ? 7 : (v.rank==='CRITICAL'?11:v.rank==='HIGH'?9:7);
    dot.style.cssText = `left:${{v.pct}}%;width:${{sz}}px;height:${{sz}}px;background:${{clr}};box-shadow:0 0 ${{sz/2}}px ${{clr}}88;`;
    dot.addEventListener('mouseenter',(e)=>showVarTip(e,v));
    dot.addEventListener('mouseleave',hideTip);
    bar.appendChild(dot);
  }});
}}

function setMode(mode,btn) {{
  curMode=mode;
  document.querySelectorAll('.btn').forEach(b=>b.classList.remove('on'));
  btn.classList.add('on');
  renderBar();
}}

function showVarTip(e,v) {{
  const tip=document.getElementById('tip');
  const rc=RANK_CLR[v.rank]||'#3a5a7a';
  document.getElementById('tip-rank').textContent=v.rank;
  document.getElementById('tip-rank').style.color=rc;
  document.getElementById('tip-var').textContent=v.var||'—';
  document.getElementById('tip-pos').textContent='Position '+v.pos;
  document.getElementById('tip-sig').textContent=v.sig||'—';
  document.getElementById('tip-ml').textContent=(v.ml*100).toFixed(0)+'%';
  document.getElementById('tip-cond').textContent=v.cond||'—';
  document.getElementById('tip-origin').textContent=v.somatic?'Somatic (acquired)':'Germline (heritable)';
  tip.style.display='block';
  tip.style.left=(e.clientX+14)+'px';
  tip.style.top=(e.clientY-10)+'px';
}}
function hideTip(){{document.getElementById('tip').style.display='none';}}
function showTip(e){{
  const tip=document.getElementById('tip');
  if(tip.style.display==='block'){{
    tip.style.left=(e.clientX+14)+'px';
    tip.style.top=(e.clientY-10)+'px';
  }}
}}

const nav=document.getElementById('stage-nav');
const dotsEl=document.getElementById('prog-dots');
stages.forEach((stage,i)=>{{
  const [title,body,clr]=stage;
  const btn=document.createElement('div');
  btn.className='snav';
  btn.textContent=`${{i+1}}. ${{title.split(' ')[0]}}`;
  btn.style.borderColor=clr+'44';
  btn.onclick=()=>setStage(i);
  nav.appendChild(btn);
  const dot=document.createElement('div');
  dot.className='pdot';
  dot.style.setProperty('--c',clr);
  dot.onclick=()=>setStage(i);
  dotsEl.appendChild(dot);
}});

function setStage(idx){{
  const [title,body,clr]=stages[idx];
  const m=CELL_METRICS[idx];
  const sd=document.getElementById('stage-display');
  sd.style.borderColor=clr+'55';
  sd.style.background=clr+'08';
  document.getElementById('stage-title').textContent=`Stage ${{idx+1}}: ${{title}}`;
  document.getElementById('stage-title').style.color=clr;
  document.getElementById('stage-body').textContent=body;
  document.getElementById('stage-slider').value=idx;
  document.querySelectorAll('.snav').forEach((b,i)=>{{
    b.classList.toggle('active',i===idx);
    b.style.background=i===idx?clr+'22':'';
    b.style.color=i===idx?clr:'';
    b.style.borderColor=i===idx?clr:'#0d2545';
  }});
  document.querySelectorAll('.pdot').forEach((d,i)=>d.classList.toggle('done',i<=idx));
  const setBar=(id,valId,clr2,pct)=>{{
    document.getElementById(id).style.height=pct+'%';
    document.getElementById(id).style.background=clr2;
    document.getElementById(valId).textContent=pct+'%';
    document.getElementById(valId).style.color=clr2;
  }};
  setBar('cv-prot','cv-prot-val','#00c896',m.prot);
  setBar('cv-sig','cv-sig-val','#4a90d9',m.sig);
  setBar('cv-via','cv-via-val','#ffd60a',m.via);
  setBar('cv-dis','cv-dis-val','#ff2d55',m.dis);
}}
document.getElementById('stage-slider').addEventListener('input',function(){{setStage(parseInt(this.value));}});

renderBar();
setStage(0);
</script>
</body></html>"""

def build_disease_timeline_html(gene, diseases, variants, scored):
    import json as _json
    from modules.config import RANK_CLR

    ONSET_DB = {
        "cardiomyopathy":      (10, 40, 70, "Decade 2–4"),
        "hypertrophic":        (15, 35, 65, "Teens–40s"),
        "dilated":             (20, 45, 70, "20s–50s"),
        "myopathy":            (0,  20, 50, "Childhood–adult"),
        "muscular dystrophy":  (0,  10, 30, "Birth–teens"),
        "glanzmann":           (0,   5, 40, "Early childhood"),
        "thrombasthenia":      (0,   5, 40, "Childhood"),
        "leukemia":            (20, 55, 80, "Any age"),
        "cancer":              (30, 60, 85, "40s–70s"),
        "carcinoma":           (40, 65, 85, "50s–70s"),
        "lymphoma":            (25, 55, 80, "Any age"),
        "epilepsy":            (0,  10, 40, "Childhood–young adult"),
        "intellectual":        (0,   2, 10, "Infancy–early childhood"),
        "autism":              (0,   2,  5, "Early childhood"),
        "parkinson":           (50, 65, 85, "60s–80s"),
        "alzheimer":           (50, 70, 90, "65+"),
        "huntington":          (30, 45, 60, "30s–50s"),
        "cystic fibrosis":     (0,   0, 10, "At birth/infancy"),
        "default":             (20, 45, 70, "Adult onset"),
    }

    PROG_DB = {
        "cardiomyopathy": ["Asymptomatic carrier","Reduced exercise tolerance","Dyspnoea on exertion","Heart failure symptoms","Advanced heart failure"],
        "cancer":         ["Normal","Precancerous change","Early cancer","Advanced cancer","Metastatic disease"],
        "default":        ["Asymptomatic carrier","Early subclinical signs","Clinical presentation","Established disease","Severe/end-stage"],
    }

    timeline_items = []
    cond_counts = {}
    for v in variants:
        if v.get("score",0) >= 2:
            for c in v.get("condition","").split(";"):
                c = c.strip()
                if c: cond_counts[c] = cond_counts.get(c,0)+1

    for d in diseases[:10]:
        name = d.get("name","")
        desc = d.get("desc","")[:150]
        inh  = d.get("inheritance","")
        name_l = name.lower()

        onset_data = ONSET_DB["default"]
        for key, val in ONSET_DB.items():
            if key != "default" and key in name_l:
                onset_data = val
                break

        cv_count = 0
        for cname, cnt in cond_counts.items():
            d_words = [w for w in name_l.split() if len(w)>3]
            if d_words and sum(1 for w in d_words if w in cname.lower()) >= min(2,len(d_words)):
                cv_count = max(cv_count, cnt)
        if cv_count == 0:
            cv_count = sum(1 for v in scored if v.get("score",0)>=4) // max(len(diseases),1)

        prog = PROG_DB["default"]
        for key, stages in PROG_DB.items():
            if key != "default" and key in name_l:
                prog = stages; break

        _tl_p = sum(1 for v in scored if v.get("score",0)>=4 and name_l[:15] in v.get("condition","").lower())
        sev = min(97, max(5, _tl_p*7 + cv_count*4 + (8 if "dominant" in inh.lower() else 0)))
        onset_early, onset_typical, onset_late, onset_label = onset_data

        timeline_items.append({
            "name": name,
            "desc": desc,
            "inh": inh if inh else "See ClinVar",
            "cv_count": cv_count,
            "sev": sev,
            "onset_early": onset_early,
            "onset_typical": onset_typical,
            "onset_late": onset_late,
            "onset_label": onset_label,
            "prog": prog,
            "omim": d.get("omim",""),
        })

    items_js = _json.dumps(timeline_items)

    return f"""<!DOCTYPE html><html><head>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:Inter,sans-serif;}}
body{{background:#010306;color:#c0d8f8;padding:14px;}}
h3{{color:#00e5ff;font-size:.9rem;font-weight:700;margin-bottom:8px;}}
select{{background:#030d1a;border:1px solid #0d2545;color:#8ab8cc;padding:5px 10px;border-radius:7px;font-size:.82rem;width:100%;margin-bottom:10px;}}
#dis-panel{{display:flex;gap:12px;}}
#dis-list{{width:210px;flex-shrink:0;overflow-y:auto;max-height:320px;}}
.dis-btn{{display:flex;align-items:center;gap:7px;background:#020810;border:1px solid #0d2545;
  border-radius:8px;padding:7px 10px;margin:3px 0;cursor:pointer;transition:all .2s;width:100%;text-align:left;}}
.dis-btn:hover,.dis-btn.sel{{background:#030d1a;border-color:#00e5ff44;}}
.dis-btn.sel{{border-left:3px solid #00e5ff;}}
.dis-name{{color:#8ab8cc;font-size:.78rem;font-weight:600;}}
.dis-meta{{color:#2a5070;font-size:.7rem;}}
#dis-detail{{flex:1;background:#020810;border:1px solid #0d2545;border-radius:10px;padding:12px;}}
.det-title{{color:#00e5ff;font-weight:800;font-size:.92rem;margin-bottom:6px;}}
.det-desc{{color:#5a8090;font-size:.82rem;line-height:1.5;margin-bottom:10px;}}
.timeline-outer{{position:relative;margin:10px 0;}}
.tl-bar{{position:relative;height:16px;background:#040d18;border-radius:8px;overflow:hidden;margin-bottom:4px;}}
.tl-early{{position:absolute;top:0;bottom:0;background:#00c89633;border-radius:8px;transition:all .6s ease;}}
.tl-range{{position:absolute;top:0;bottom:0;background:linear-gradient(90deg,#ffd60a88,#ff2d5588);border-radius:8px;transition:all .6s ease;}}
.tl-peak{{position:absolute;top:0;bottom:0;width:3px;background:#ff2d55;transition:all .6s ease;}}
.tl-labels{{display:flex;justify-content:space-between;font-size:.65rem;color:#1e4060;margin-bottom:8px;}}
.prog-row{{display:flex;gap:0;margin:8px 0;}}
.prog-step{{flex:1;text-align:center;position:relative;}}
.prog-circle{{width:24px;height:24px;border-radius:50%;margin:0 auto 4px;display:flex;align-items:center;justify-content:center;font-size:.64rem;font-weight:700;transition:all .4s;}}
.prog-line{{position:absolute;top:12px;left:50%;right:-50%;height:2px;background:#0d2545;z-index:0;}}
.prog-step:last-child .prog-line{{display:none;}}
.prog-label{{font-size:.62rem;color:#1e4060;line-height:1.3;padding:0 2px;}}
.met-row{{display:flex;gap:8px;margin-top:10px;}}
.met-box{{flex:1;background:#030d1a;border:1px solid #0d2545;border-radius:7px;padding:6px;text-align:center;}}
.met-lbl{{color:#1e4060;font-size:.66rem;margin-bottom:3px;}}
.met-val{{font-size:.9rem;font-weight:800;}}
</style></head><body>
<h3>Disease Timeline & Progression — {gene}</h3>
<p style="color:#3a6080;font-size:.78rem;margin-bottom:8px;">Onset ranges derived from published clinical literature. Click a disease to expand.</p>
<div id="dis-panel">
<div id="dis-list"></div>
<div id="dis-detail"><div style="color:#1e4060;font-size:.84rem;padding-top:20px;text-align:center;">← Select a disease</div></div>
</div>
<script>
const items={items_js};
const listEl=document.getElementById('dis-list');
const detEl=document.getElementById('dis-detail');
let sel=-1;

items.forEach((d,i)=>{{
  const sev=d.sev;
  const clr=sev>70?'#ff2d55':sev>40?'#ff8c42':'#ffd60a';
  const btn=document.createElement('div');
  btn.className='dis-btn';
  btn.innerHTML=`<div style="width:6px;height:6px;border-radius:50%;background:${{clr}};flex-shrink:0;"></div>
    <div><div class="dis-name">${{d.name.length>28?d.name.slice(0,28)+'…':d.name}}</div>
    <div class="dis-meta">${{d.cv_count}} variants · ${{d.inh.split(' ')[0]||'?'}}</div></div>`;
  btn.onclick=()=>selectDis(i,btn);
  listEl.appendChild(btn);
}});

function selectDis(i,btn){{
  document.querySelectorAll('.dis-btn').forEach(b=>b.classList.remove('sel'));
  btn.classList.add('sel'); sel=i;
  const d=items[i];
  const sev=d.sev;
  const clr=sev>70?'#ff2d55':sev>40?'#ff8c42':'#ffd60a';
  const maxAge=90;
  const earlyPct=d.onset_early/maxAge*100;
  const typPct=d.onset_typical/maxAge*100;
  const latePct=d.onset_late/maxAge*100;
  const progCircles=d.prog.map((step,j)=>{{
    const sc=j===0?'#00c896':j===1?'#ffd60a':j===2?'#ff8c42':'#ff2d55';
    return `<div class="prog-step">
      <div class="prog-line"></div>
      <div class="prog-circle" id="pc-${{i}}-${{j}}" style="background:${{sc}}22;border:1px solid ${{sc}}44;color:${{sc}};">${{j+1}}</div>
      <div class="prog-label">${{step}}</div>
    </div>`;
  }}).join('');
  const omimLink = d.omim ? `<a href="https://omim.org/entry/${{d.omim}}" target="_blank" style="color:#3a7090;font-size:.75rem;">OMIM ${{d.omim}} ↗</a>` : '';
  detEl.innerHTML=`
    <div class="det-title">${{d.name}}</div>
    <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;">
      <span style="background:${{clr}}22;color:${{clr}};border:1px solid ${{clr}}44;padding:2px 9px;border-radius:6px;font-size:.74rem;font-weight:700;">Severity ${{sev}}/100</span>
      <span style="background:#1e406033;color:#3a8090;border:1px solid #1e406044;padding:2px 9px;border-radius:6px;font-size:.74rem;">${{d.inh||'Unknown inheritance'}}</span>
      <span style="background:#0d254533;color:#3a6080;border:1px solid #0d254544;padding:2px 9px;border-radius:6px;font-size:.74rem;">${{d.cv_count}} ClinVar variants</span>
      ${{omimLink}}
    </div>
    <div class="det-desc">${{d.desc||'No description available in UniProt for this disease entry.'}}</div>
    <div style="color:#4a7090;font-size:.76rem;margin-bottom:4px;font-weight:600;">Age of onset range</div>
    <div class="tl-labels"><span>0</span><span>20</span><span>40</span><span>60</span><span>80+</span></div>
    <div class="tl-bar">
      <div class="tl-early" style="left:0;width:${{earlyPct}}%;"></div>
      <div class="tl-range" style="left:${{earlyPct}}%;width:${{latePct-earlyPct}}%;"></div>
      <div class="tl-peak" style="left:${{typPct}}%;"></div>
    </div>
    <div style="font-size:.72rem;color:#2a5070;margin-bottom:10px;">Typical onset: <b style="color:#8ab8cc;">${{d.onset_label}}</b> · Peak age: <b style="color:#ff8c42;">${{d.onset_typical}}</b> years</div>
    <div style="color:#4a7090;font-size:.76rem;margin-bottom:6px;font-weight:600;">Disease progression</div>
    <div class="prog-row">${{progCircles}}</div>
    <div class="met-row">
      <div class="met-box"><div class="met-lbl">ClinVar P/LP variants</div><div class="met-val" style="color:#ff2d55;">${{d.cv_count}}</div></div>
      <div class="met-box"><div class="met-lbl">Severity score</div><div class="met-val" style="color:${{clr}};">${{sev}}/100</div></div>
      <div class="met-box"><div class="met-lbl">Earliest onset</div><div class="met-val" style="color:#ffd60a;">${{d.onset_early===0?'Birth':d.onset_early+'y'}}</div></div>
      <div class="met-box"><div class="met-lbl">Typical onset</div><div class="met-val" style="color:#ff8c42;">${{d.onset_typical}}y</div></div>
    </div>`;
  d.prog.forEach((_,j)=>{{
    setTimeout(()=>{{
      const pc=document.getElementById(`pc-${{i}}-${{j}}`);
      if(pc) pc.style.opacity='1';
    }},j*200);
  }});
}}

if(items.length>0) selectDis(0,listEl.children[0]);
</script></body></html>"""

def build_druggability_map_html(gene, protein_length, hotspots, scored, ot_data, gnomad, ptype, is_gpcr, drugs_data):
    import json as _json
    tract = ot_data.get("tractability",{}) if ot_data else {}
    known_drugs = ot_data.get("known_drugs",[]) if ot_data else []
    n_drugs = len(drugs_data)

    strategies = []
    if tract.get("Small molecule"):
        strategies.append({
            "type":"Small Molecule Inhibitor",
            "icon":"💊","colour":"#00c896",
            "basis":f"OpenTargets confirms small molecule tractability.",
            "approach":"Target the hotspot binding pocket with ATP-competitive or allosteric small molecules.",
            "timeline":"2–5 years to IND",
        })
    if tract.get("Antibody"):
        strategies.append({
            "type":"Antibody / Biologic",
            "icon":"💉","colour":"#4a90d9",
            "basis":"OpenTargets confirms antibody tractability.",
            "approach":"Design monoclonal antibody or nanobody targeting extracellular domain.",
            "timeline":"3–7 years to IND",
        })
    if is_gpcr:
        strategies.append({
            "type":"GPCR Biased Agonist/Antagonist",
            "icon":"📡","colour":"#ffd60a",
            "basis":"Protein is a GPCR — 34% of all FDA-approved drugs target GPCRs.",
            "approach":"Screen for ligands that activate therapeutic G-protein pathway while blocking β-arrestin recruitment.",
            "timeline":"2–5 years to IND",
        })
    if ptype == "kinase" and not strategies:
        strategies.append({
            "type":"ATP-competitive Kinase Inhibitor",
            "icon":"⚗️","colour":"#ff8c42",
            "basis":"Kinase proteins have well-validated ATP-binding pockets.",
            "approach":"Screen existing kinase inhibitor libraries.",
            "timeline":"2–4 years to IND",
        })
    if not strategies:
        strategies.append({
            "type":"Gene Therapy / Splice Modulation",
            "icon":"🧬","colour":"#3a90d9",
            "basis":"No direct small molecule tractability confirmed.",
            "approach":"AAV-mediated gene supplementation for LoF variants.",
            "timeline":"4–8 years to IND",
        })

    target_zones = []
    for i,h in enumerate(hotspots[:5]):
        pct_s = h.get("pct_start", h.get("start",0)/max(protein_length,1)*100)
        pct_e = h.get("pct_end", h.get("end",100)/max(protein_length,1)*100)
        target_zones.append({
            "id": i+1,
            "start": h.get("start",0), "end": h.get("end",0),
            "pct_s": round(pct_s,1), "pct_e": round(pct_e,1),
            "fold": h.get("fold_enrichment",1),
            "count": h.get("count",0),
            "priority": "PRIMARY" if i==0 else "SECONDARY" if i<3 else "TERTIARY",
        })

    strat_js = _json.dumps(strategies)
    zones_js = _json.dumps(target_zones)
    nd  = n_drugs
    nkd = len(known_drugs)

    return f"""<!DOCTYPE html><html><head>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:Inter,sans-serif;}}
body{{background:#010306;color:#c0d8f8;padding:14px;}}
h3{{color:#00e5ff;font-size:.9rem;font-weight:700;margin-bottom:8px;}}
#top-metrics{{display:flex;gap:8px;margin-bottom:12px;}}
.tmet{{flex:1;background:#020810;border:1px solid #0d2545;border-radius:8px;padding:7px;text-align:center;}}
.tmet-v{{font-size:1rem;font-weight:800;}}
.tmet-l{{font-size:.66rem;color:#1e4060;margin-top:2px;}}
#protein-map{{position:relative;margin:10px 0;}}
#pm-label{{font-size:.72rem;color:#2a5070;margin-bottom:4px;}}
#pm-bar{{position:relative;height:36px;background:#050d1a;border-radius:8px;border:1px solid #0d2545;}}
.target-zone{{position:absolute;top:4px;bottom:4px;border-radius:5px;cursor:pointer;
  transition:all .3s;display:flex;align-items:center;justify-content:center;}}
.target-zone:hover{{top:0;bottom:0;border-radius:8px;z-index:10;}}
.tz-label{{font-size:.62rem;font-weight:700;color:#fff;text-shadow:0 1px 3px rgba(0,0,0,.8);white-space:nowrap;}}
#strategies{{margin-top:12px;}}
.strat-card{{background:#020810;border:1px solid #0d2545;border-radius:10px;padding:10px 12px;margin:5px 0;
  cursor:pointer;transition:all .25s;}}
.strat-card:hover,.strat-card.sel{{border-left-width:3px;}}
.strat-header{{display:flex;align-items:center;gap:9px;margin-bottom:5px;}}
.strat-icon{{font-size:1.2rem;}}
.strat-type{{font-weight:700;font-size:.88rem;}}
.strat-body{{font-size:.8rem;line-height:1.5;}}
.strat-basis{{color:#4a7090;margin-bottom:4px;}}
.strat-approach{{color:#6a9ab0;margin-bottom:4px;}}
.strat-tl{{color:#3a6080;font-size:.74rem;}}
#drug-list{{margin-top:10px;background:#020810;border:1px solid #0d2545;border-radius:10px;padding:10px;}}
.drug-row{{display:flex;align-items:center;gap:10px;padding:5px 0;border-bottom:1px solid #040c18;}}
.drug-row:last-child{{border-bottom:none;}}
.drug-name{{color:#8ab8cc;font-weight:600;font-size:.82rem;flex:1;}}
.drug-type{{color:#3a6080;font-size:.74rem;}}
.drug-phase{{padding:2px 8px;border-radius:5px;font-size:.7rem;font-weight:700;}}
</style></head><body>
<h3>Druggability Targeting Map — {gene}</h3>
<div id="top-metrics">
  <div class="tmet"><div class="tmet-v" style="color:#00c896;">{nd}</div><div class="tmet-l">Known drug interactions (DGIdb)</div></div>
  <div class="tmet"><div class="tmet-v" style="color:#4a90d9;">{nkd}</div><div class="tmet-l">Clinical-stage drugs (OpenTargets)</div></div>
  <div class="tmet"><div class="tmet-v" style="color:#a855f7;">{len(hotspots)}</div><div class="tmet-l">Druggable hotspot clusters</div></div>
  <div class="tmet"><div class="tmet-v" style="color:#ffd60a;">{len(strategies)}</div><div class="tmet-l">Viable targeting strategies</div></div>
</div>

<div id="protein-map">
<div id="pm-label">Protein chain ({protein_length} aa) — highlighted zones = variant hotspots = prime drug target regions</div>
<div id="pm-bar">
<div style="position:absolute;top:0;bottom:0;left:0;right:0;background:linear-gradient(90deg,#0d2545,#0a1e3a,#0d2545);border-radius:8px;opacity:.5;"></div>
</div>
<p style="font-size:.7rem;color:#1e4060;margin-top:4px;">Zones derived from ClinVar pathogenic variant clustering. Click any zone to see targeting detail.</p>
</div>

<div id="strategies">
<div style="color:#4a7090;font-size:.8rem;font-weight:600;margin-bottom:6px;">Viable drug targeting strategies (based on OpenTargets + protein class)</div>
</div>

{'<div id="drug-list"><div style="color:#5a8090;font-weight:700;font-size:.84rem;margin-bottom:6px;">Known drugs / clinical compounds</div></div>' if known_drugs else ''}

<script>
const strategies={strat_js};
const zones={zones_js};

const bar=document.getElementById('pm-bar');
const ZONE_CLRS=['#ff2d55','#ff8c42','#ffd60a','#a855f7','#4a90d9'];
zones.forEach((z,i)=>{{
  const div=document.createElement('div');
  div.className='target-zone';
  const clr=ZONE_CLRS[i]||'#3a6080';
  const w=Math.max(4,z.pct_e-z.pct_s);
  div.style.cssText=`left:${{z.pct_s}}%;width:${{w}}%;background:${{clr}}66;border:1px solid ${{clr}};`;
  div.innerHTML=`<span class="tz-label">#${{z.id}}</span>`;
  div.title=`Hotspot #${{z.id}}: residues ${{z.start}}–${{z.end}} · ${{z.count}} pathogenic variants · ${{z.fold}}× enriched`;
  div.onclick=()=>highlightZone(i,clr,z);
  bar.appendChild(div);
}});

function highlightZone(i,clr,z){{
  const detail = document.getElementById('zone-detail');
  if(detail) detail.remove();
  const d=document.createElement('div');
  d.id='zone-detail';
  d.style.cssText='background:#020810;border:1px solid '+clr+'55;border-radius:9px;padding:9px 12px;margin-top:6px;';
  d.innerHTML=`<div style="color:${{clr}};font-weight:700;font-size:.86rem;margin-bottom:4px;">Hotspot #${{z.id}} — Prime drug target zone</div>
    <div style="color:#5a8090;font-size:.82rem;">Residues ${{z.start}}–${{z.end}} · <b style="color:${{clr}};">${{z.count}} pathogenic variants</b> · ${{z.fold}}× above background density</div>
    <div style="color:#3a6080;font-size:.78rem;margin-top:4px;">This cluster represents a structurally critical region where multiple disease-causing mutations converge.</div>`;
  document.getElementById('protein-map').appendChild(d);
}}

const stratDiv=document.getElementById('strategies');
const STRAT_CLRS=strategies.map(s=>s.colour);
strategies.forEach((s,i)=>{{
  const card=document.createElement('div');
  card.className='strat-card';
  card.style.borderLeftColor=s.colour;
  card.innerHTML=`
    <div class="strat-header">
      <span class="strat-icon">${{s.icon}}</span>
      <span class="strat-type" style="color:${{s.colour}};">${{s.type}}</span>
      <span style="background:${{s.colour}}22;color:${{s.colour}};border:1px solid ${{s.colour}}44;padding:1px 7px;border-radius:5px;font-size:.7rem;margin-left:auto;">${{s.timeline}}</span>
    </div>
    <div class="strat-body">
      <div class="strat-basis"><b style="color:#4a8090;">Evidence basis:</b> ${{s.basis}}</div>
      <div class="strat-approach"><b style="color:#5a8090;">How to target:</b> ${{s.approach}}</div>
    </div>`;
  card.onclick=()=>{{
    document.querySelectorAll('.strat-card').forEach(c=>c.classList.remove('sel'));
    card.classList.add('sel');
  }};
  stratDiv.appendChild(card);
}});

const drugListEl=document.getElementById('drug-list');
if(drugListEl) {{
  const drugs={_json.dumps(known_drugs)};
  const PHASE_CLR={{4:'#00c896',3:'#4a90d9',2:'#ffd60a',1:'#ff8c42',0:'#3a6080'}};
  drugs.forEach(d=>{{
    const row=document.createElement('div');
    row.className='drug-row';
    const ph=parseInt(d.phase)||0;
    const pc=PHASE_CLR[ph]||'#3a6080';
    row.innerHTML=`<span class="drug-name">${{d.name||'—'}}</span>
      <span class="drug-type">${{d.mechanism||'—'}}</span>
      <span class="drug-phase" style="background:${{pc}}22;color:${{pc}};border:1px solid ${{pc}}44;">Ph${{ph||'?'}}</span>
      <a href="${{d.url||'#'}}" target="_blank" style="color:#2a6a8a;font-size:.74rem;">↗</a>`;
    drugListEl.appendChild(row);
  }});
}}

if(zones.length>0) highlightZone(0,ZONE_CLRS[0],zones[0]);
if(document.querySelector('.strat-card')) document.querySelector('.strat-card').classList.add('sel');
</script></body></html>"""

def render_domain_expansion_cards(pdata, cv_variants, scored, am_scores, research_domain, gene, uid, pdb):
    from modules.data_processing import g_seq
    sh = lambda icon, title: None
    # This function is imported separately - main app will handle it
    pass

def kyte_doolittle(seq, window=9):
    KD = {"A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,
          "G":-0.4,"H":-3.2,"I":4.5,"L":3.8,"K":-3.9,"M":1.9,"F":2.8,
          "P":-1.6,"S":-0.8,"T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2}
    hw = window // 2
    profile = []
    for i in range(len(seq)):
        start = max(0, i - hw); end = min(len(seq), i + hw + 1)
        window_seq = seq[start:end]
        score = sum(KD.get(aa, 0) for aa in window_seq) / len(window_seq)
        profile.append((i + 1, round(score, 3)))
    return profile

def calc_pI(seq):
    pKa = {"D":3.65,"E":4.25,"H":6.00,"C":8.18,"Y":10.07,"K":10.53,"R":12.48,
           "nterm":8.0,"cterm":3.1}
    counts = {aa: seq.count(aa) for aa in pKa}
    def charge_at_pH(pH):
        c = 1 / (1 + 10**(pH - pKa["nterm"]))
        c -= 1 / (1 + 10**(pKa["cterm"] - pH))
        c += counts.get("H",0) / (1 + 10**(pH - pKa["H"]))
        c -= counts.get("D",0) / (1 + 10**(pKa["D"] - pH))
        c -= counts.get("E",0) / (1 + 10**(pKa["E"] - pH))
        c -= counts.get("C",0) / (1 + 10**(pKa["C"] - pH))
        c -= counts.get("Y",0) / (1 + 10**(pKa["Y"] - pH))
        c += counts.get("K",0) / (1 + 10**(pH - pKa["K"]))
        c += counts.get("R",0) / (1 + 10**(pH - pKa["R"]))
        return c
    lo, hi = 0.0, 14.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if charge_at_pH(mid) > 0: lo = mid
        else: hi = mid
    return round((lo + hi) / 2, 2)

def aa_composition(seq):
    groups = {
        "Nonpolar (hydrophobic)": list("AVILMFWP"),
        "Polar uncharged": list("STNQCY"),
        "Positively charged": list("KRH"),
        "Negatively charged": list("DE"),
        "Special": list("G"),
    }
    counts = {}
    for aa in seq:
        counts[aa] = counts.get(aa, 0) + 1
    total = max(len(seq), 1)
    result = {}
    for grp, aas in groups.items():
        result[grp] = {aa: (counts.get(aa, 0), round(counts.get(aa, 0) / total * 100, 1)) for aa in aas if counts.get(aa, 0) > 0}
    return result, counts, total

def render_chemical_backbone(seq, cv_variants, phospho_sites, binding_sites, gene, pLI=0.0):
    import json as _jj
    from collections import Counter as _Ctr
    import streamlit.components.v1 as components

    AA_CHEM_DATA = {
        "G":{"name":"Glycine","formula":"H","full":"C₂H₅NO₂","type":"special","mw":75.03},
        "A":{"name":"Alanine","formula":"CH₃","full":"C₃H₇NO₂","type":"nonpolar","mw":89.09},
        "V":{"name":"Valine","formula":"CH(CH₃)₂","full":"C₅H₁₁NO₂","type":"nonpolar","mw":117.15},
        "L":{"name":"Leucine","formula":"CH₂CH(CH₃)₂","full":"C₆H₁₃NO₂","type":"nonpolar","mw":131.17},
        "I":{"name":"Isoleucine","formula":"CH(CH₃)C₂H₅","full":"C₆H₁₃NO₂","type":"nonpolar","mw":131.17},
        "P":{"name":"Proline","formula":"cyclic-(CH₂)₃-","full":"C₅H₉NO₂","type":"special","mw":115.13},
        "F":{"name":"Phenylalanine","formula":"CH₂-C₆H₅","full":"C₉H₁₁NO₂","type":"aromatic","mw":165.19},
        "W":{"name":"Tryptophan","formula":"CH₂-indole","full":"C₁₁H₁₂N₂O₂","type":"aromatic","mw":204.23},
        "M":{"name":"Methionine","formula":"(CH₂)₂-S-CH₃","full":"C₅H₁₁NO₂S","type":"nonpolar","mw":149.21},
        "S":{"name":"Serine","formula":"CH₂OH ★","full":"C₃H₇NO₃","type":"polar","mw":105.09},
        "T":{"name":"Threonine","formula":"CH(OH)CH₃ ★","full":"C₄H₉NO₃","type":"polar","mw":119.12},
        "C":{"name":"Cysteine","formula":"CH₂SH ⟺","full":"C₃H₇NO₂S","type":"polar","mw":121.16},
        "Y":{"name":"Tyrosine","formula":"CH₂-C₆H₄-OH ★","full":"C₉H₁₁NO₃","type":"aromatic","mw":181.19},
        "N":{"name":"Asparagine","formula":"CH₂CONH₂","full":"C₄H₈N₂O₃","type":"polar","mw":132.12},
        "Q":{"name":"Glutamine","formula":"(CH₂)₂CONH₂","full":"C₅H₁₀N₂O₃","type":"polar","mw":146.15},
        "D":{"name":"Aspartate","formula":"CH₂COO⁻","full":"C₄H₇NO₄","type":"negative","mw":133.10},
        "E":{"name":"Glutamate","formula":"(CH₂)₂COO⁻","full":"C₅H₉NO₄","type":"negative","mw":147.13},
        "K":{"name":"Lysine","formula":"(CH₂)₄NH₃⁺","full":"C₆H₁₄N₂O₂","type":"positive","mw":146.19},
        "R":{"name":"Arginine","formula":"(CH₂)₃-guanidinium","full":"C₆H₁₄N₄O₂","type":"positive","mw":174.20},
        "H":{"name":"Histidine","formula":"CH₂-imidazole","full":"C₆H₉N₃O₂","type":"positive","mw":155.16},
    }
    TYPE_COLS={"nonpolar":"#ff8c42","aromatic":"#a855f7","polar":"#22c55e",
               "positive":"#4a90d9","negative":"#ff2d55","special":"#ffd60a"}

    AA_ATOMS={"G":{"C":2,"H":5,"N":1,"O":2},"A":{"C":3,"H":7,"N":1,"O":2},
              "V":{"C":5,"H":11,"N":1,"O":2},"L":{"C":6,"H":13,"N":1,"O":2},
              "I":{"C":6,"H":13,"N":1,"O":2},"P":{"C":5,"H":9,"N":1,"O":2},
              "F":{"C":9,"H":11,"N":1,"O":2},"W":{"C":11,"H":12,"N":2,"O":2},
              "M":{"C":5,"H":11,"N":1,"O":2,"S":1},"S":{"C":3,"H":7,"N":1,"O":3},
              "T":{"C":4,"H":9,"N":1,"O":3},"C":{"C":3,"H":7,"N":1,"O":2,"S":1},
              "Y":{"C":9,"H":11,"N":1,"O":3},"N":{"C":4,"H":8,"N":2,"O":3},
              "Q":{"C":5,"H":10,"N":2,"O":3},"D":{"C":4,"H":7,"N":1,"O":4},
              "E":{"C":5,"H":9,"N":1,"O":4},"K":{"C":6,"H":14,"N":2,"O":2},
              "R":{"C":6,"H":14,"N":4,"O":2},"H":{"C":6,"H":9,"N":3,"O":2}}
    MW_ATOMS={"C":12.011,"H":1.008,"N":14.007,"O":15.999,"S":32.06,"P":30.974}
    atm=_Ctr()
    for aa in seq:
        for el,n in AA_ATOMS.get(aa,{"C":3,"H":7,"N":1,"O":2}).items(): atm[el]+=n
    atm["H"]-=2*(len(seq)-1); atm["O"]-=(len(seq)-1)
    mw_total=sum(atm[e]*MW_ATOMS.get(e,0) for e in atm)/1000
    mol_html="".join(f"{e}<sub>{atm[e]}</sub>" if atm.get(e,0)>1 else e for e in ["C","H","N","O","S","P"] if atm.get(e,0)>0)

    km={}
    for i in range(len(seq)-4):
        s4=seq[i:i+4]
        if s4[0] in "RK" and s4[3] in "ST": km[i+3]="PKA/PKC: [RK]-xx-[ST]"
        elif s4[0] in "ST" and s4[3] in "DE": km[i]="CK2: [ST]-xx-[DE]"

    def _safe_pos(v):
        try: return int(v.get("start",0) or 0)
        except (ValueError, TypeError): return 0

    path_pos={_safe_pos(v) for v in cv_variants if _safe_pos(v) and v.get("score",0)>=4}
    phos_pos={int(p.get("position",0) or 0) for p in (phospho_sites or []) if p.get("position")}
    bind_pos={int(b.get("start",0) or 0) for b in (binding_sites or []) if b.get("start")}

    aa_data=[{
        "pos":i+1,"aa":aa,
        "name":AA_CHEM_DATA.get(aa,{"name":"Unknown"})["name"],
        "formula":AA_CHEM_DATA.get(aa,{"formula":"?"})["formula"],
        "full":AA_CHEM_DATA.get(aa,{"full":"C₃H₇NO₂"})["full"],
        "type":AA_CHEM_DATA.get(aa,{"type":"nonpolar"})["type"],
        "color":TYPE_COLS.get(AA_CHEM_DATA.get(aa,{"type":"nonpolar"})["type"],"#3a6080"),
        "mw":AA_CHEM_DATA.get(aa,{"mw":110.0})["mw"],
        "isPhospho":aa in "STY","isAnnotPhos":(i+1) in phos_pos,
        "isPath":(i+1) in path_pos,"isBind":(i+1) in bind_pos,
        "isKin":(i+1) in km,"kinType":km.get(i+1,""),
        "isCys":aa=="C","isPro":aa=="P",
    } for i,aa in enumerate(seq)]

    aa_js=_jj.dumps(aa_data)

    st.markdown(f"""
<div style='background:#010810;border:1px solid #071828;border-radius:10px;padding:11px 16px;
  margin-bottom:10px;display:flex;gap:20px;flex-wrap:wrap;align-items:center;'>
  <div><div style='color:#3a6080;font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;'>Molecular Formula</div>
    <div style='color:#00e5ff;font-size:.9rem;font-weight:700;font-family:JetBrains Mono,monospace;'>{mol_html}</div></div>
  <div><div style='color:#3a6080;font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;'>MW</div>
    <div style='color:#ffd60a;font-size:.88rem;font-weight:700;font-family:JetBrains Mono,monospace;'>{mw_total:.1f} kDa</div></div>
  <div><div style='color:#3a6080;font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;'>Length</div>
    <div style='color:#b0d8f0;font-size:.88rem;font-weight:700;font-family:JetBrains Mono,monospace;'>{len(seq):,} aa</div></div>
  <div><div style='color:#3a6080;font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;'>P/LP variants</div>
    <div style='color:#ff2d55;font-size:.88rem;font-weight:700;font-family:JetBrains Mono,monospace;'>{len(path_pos)}</div></div>
  <div><div style='color:#3a6080;font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;'>Cys/SS bonds</div>
    <div style='color:#ffd60a;font-size:.88rem;font-weight:700;font-family:JetBrains Mono,monospace;'>{seq.count("C")} / ~{seq.count("C")//2}</div></div>
</div>""", unsafe_allow_html=True)

    components.html(f"""<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>*{{margin:0;padding:0;box-sizing:border-box;}}body{{background:#000205;overflow:hidden;}}
canvas{{display:block;}}
#info{{position:absolute;top:8px;left:8px;background:rgba(0,2,8,.97);border:1px solid #071828;
  border-radius:10px;padding:10px 14px;color:#b0d8f0;font-size:11px;
  font-family:'JetBrains Mono',monospace;display:none;z-index:20;pointer-events:none;
  min-width:240px;line-height:1.75;}}
#ctrl{{position:absolute;top:8px;right:8px;display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end;}}
.btn{{background:#010810;border:1px solid #071828;color:#3a6080;border-radius:6px;
  padding:4px 9px;font-size:10px;cursor:pointer;transition:all .12s;font-family:Inter,sans-serif;}}
.btn:hover,.btn.on{{border-color:rgba(0,229,255,.35);color:#00e5ff;}}
#nav{{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);display:flex;gap:5px;align-items:center;}}
#winlabel{{color:#1e4060;font-size:9px;font-family:'JetBrains Mono',monospace;}}
#hint{{position:absolute;bottom:8px;left:8px;color:#071828;font-size:9px;font-family:'JetBrains Mono',monospace;}}
#leg{{position:absolute;bottom:30px;right:8px;background:rgba(0,2,8,.9);border:1px solid #071828;
  border-radius:8px;padding:7px 10px;}}
.li{{display:flex;align-items:center;gap:5px;font-size:9px;color:#3a6080;margin:2px 0;}}
.ld{{width:8px;height:8px;border-radius:2px;flex-shrink:0;}}
</style></head><body>
<canvas id="cv"></canvas>
<div id="info"></div>
<div id="ctrl">
  <button class="btn on" id="b_struct" onclick="vm='structure';upBtns()">⛓ Chain</button>
  <button class="btn" id="b_formula" onclick="vm='formula';upBtns()">🧪 Formulas</button>
  <button class="btn" id="b_hydro" onclick="vm='hydro';upBtns()">🌊 Hydropathy</button>
  <button class="btn on" id="b_sig" onclick="sig=!sig;this.classList.toggle('on');this.textContent=sig?'◎ Signal':'◎ Off'">◎ Signal</button>
  <button class="btn" onclick="zm=Math.min(3,zm*1.22)">＋</button>
  <button class="btn" onclick="zm=Math.max(.28,zm/1.22)">－</button>
  <button class="btn" onclick="zm=1;px=0;py=0;">⛶ Reset</button>
</div>
<div id="nav">
  <button class="btn" onclick="scroll(-20)">◀</button>
  <span id="winlabel">1–60</span>
  <button class="btn" onclick="scroll(20)">▶</button>
  <button class="btn" onclick="hotspot()">⚠ Hotspot</button>
</div>
<div id="hint">Drag pan · Scroll zoom · ◀▶ navigate · Hover for chemistry · H = jump to hotspot</div>
<div id="leg">
  <div class="li"><div class="ld" style="background:#ff8c42"></div>Nonpolar</div>
  <div class="li"><div class="ld" style="background:#a855f7"></div>Aromatic</div>
  <div class="li"><div class="ld" style="background:#22c55e"></div>Polar</div>
  <div class="li"><div class="ld" style="background:#4a90d9"></div>Basic(+)</div>
  <div class="li"><div class="ld" style="background:#ff2d55"></div>Acidic(−)</div>
  <div class="li"><div class="ld" style="background:#ffd60a"></div>Special</div>
  <div class="li"><div class="ld" style="background:#ff2d55;border:1.5px solid #fff"></div>P/LP variant</div>
  <div class="li"><div class="ld" style="background:#f97316"></div>Phosphosite★</div>
  <div class="li"><div class="ld" style="background:#ffd60a;border:1px dashed #fff"></div>Binding</div>
  <div class="li"><div class="ld" style="background:#22c55e;border:1px dashed #fff"></div>Kinase</div>
</div>
<script>
const cv=document.getElementById('cv'),x=cv.getContext('2d');
cv.width=window.innerWidth||900; cv.height=(window.innerHeight||500)-8;
const W=cv.width,H=cv.height;
const AAS={aa_js};
const TOT=AAS.length;
let vm='structure',sig=true,zm=1,px=0,py=0;
let ws=0;
const WIN=Math.max(30,Math.floor((W-80)/18));
let hov=null,sigT=0,drag=false,dsx=0,dsy=0;

function upBtns(){{['b_struct','b_formula','b_hydro'].forEach(id=>document.getElementById(id).classList.remove('on'));document.getElementById('b_'+vm.replace('structure','struct')).classList.add('on');}}
function scroll(d){{ws=Math.max(0,Math.min(TOT-WIN,ws+d));document.getElementById('winlabel').textContent=(ws+1)+'–'+Math.min(TOT,ws+WIN);}}
function hotspot(){{const i=AAS.findIndex(r=>r.isPath);if(i>=0){{ws=Math.max(0,Math.min(TOT-WIN,i-Math.floor(WIN/2)));scroll(0);}}}}
function gwin(){{return AAS.slice(ws,ws+WIN);}}

function gpos(i,n){{
  const sp=Math.max(14,Math.min(24,(W-80)/n));
  const xb=40+i*sp;
  const yb=H/2+(i%2===0?-32:32);
  return{{x:xb,y:yb,sp}};
}}

const HYDRO={{G:-.4,A:1.8,V:4.2,L:3.8,I:4.5,P:-1.6,F:2.8,W:-.9,M:1.9,
             S:-.8,T:-.7,C:2.5,Y:-1.3,N:-3.5,Q:-3.5,D:-3.5,E:-3.5,K:-3.9,R:-4.5,H:-3.2}};

function drawRes(r,pos,n,isH){{
  const{{x:cx,y:cy,sp}}=pos;
  const rv=Math.max(5,Math.min(11,sp*0.42));
  const col=r.isPath?'#ff2d55':r.isAnnotPhos?'#f97316':r.isBind?'#ffd60a':r.isKin?'#22c55e':r.color;

  if(r.isPath){{const g=x.createRadialGradient(cx,cy,0,cx,cy,rv*3);g.addColorStop(0,'rgba(255,45,85,.2)');g.addColorStop(1,'transparent');x.beginPath();x.arc(cx,cy,rv*3,0,Math.PI*2);x.fillStyle=g;x.fill();}}
  else if(r.isBind){{const g=x.createRadialGradient(cx,cy,0,cx,cy,rv*2.5);g.addColorStop(0,'rgba(255,214,10,.14)');g.addColorStop(1,'transparent');x.beginPath();x.arc(cx,cy,rv*2.5,0,Math.PI*2);x.fillStyle=g;x.fill();}}

  if(vm==='structure'){{
    const nx=cx-rv*.9,ny=cy-rv*.9;
    x.beginPath();x.arc(nx,ny,rv*.42,0,Math.PI*2);x.fillStyle='#4a90d9';x.fill();
    x.beginPath();x.arc(cx,cy,rv,0,Math.PI*2);x.fillStyle=col+'22';x.fill();x.strokeStyle=col;x.lineWidth=isH?2.5:1.5;x.stroke();
    const ccx=cx+rv*1.1,ccy=cy-rv*.7;
    x.beginPath();x.arc(ccx,ccy,rv*.38,0,Math.PI*2);x.fillStyle='#777';x.fill();
    const ox=ccx+rv*.7,oy=ccy-rv*.5;
    x.beginPath();x.arc(ox,oy,rv*.35,0,Math.PI*2);x.fillStyle='#ff4444';x.fill();
    x.beginPath();x.moveTo(ccx,ccy);x.lineTo(ox,oy);x.strokeStyle='#ff444488';x.lineWidth=1.2;x.stroke();
    x.beginPath();x.moveTo(ccx-1,ccy+1);x.lineTo(ox-1,oy+1);x.strokeStyle='#ff444444';x.lineWidth=0.8;x.stroke();
    x.beginPath();x.moveTo(nx,ny);x.lineTo(cx,cy);x.strokeStyle='#4a90d988';x.lineWidth=1.2;x.stroke();
    x.beginPath();x.moveTo(cx,cy);x.lineTo(ccx,ccy);x.strokeStyle='#77777788';x.lineWidth=1.2;x.stroke();
    if(r.aa!=='G'){{
      const yd=cy>H/2?-1:1;const rsx=cx,rsy=cy+yd*rv*1.7;
      x.beginPath();x.moveTo(cx,cy);x.lineTo(rsx,rsy);x.strokeStyle=col+'55';x.lineWidth=1;x.stroke();
      if(r.aa==='C'){{x.beginPath();x.arc(rsx,rsy,rv*.45,0,Math.PI*2);x.fillStyle='#ffd60acc';x.fill();}}
      else if(r.aa==='P'){{x.beginPath();x.arc(rsx,rsy,rv*.65,0,Math.PI*2);x.strokeStyle=col+'88';x.lineWidth=1.2;x.stroke();}}
      else{{x.beginPath();x.arc(rsx,rsy,rv*.38,0,Math.PI*2);x.fillStyle='#888';x.fill();}}
      if(r.isAnnotPhos){{
        const px2=rsx+rv,py2=rsy-rv;
        x.beginPath();x.arc(px2,py2,rv*.45,0,Math.PI*2);x.fillStyle='#f97316';x.fill();
        x.beginPath();x.moveTo(rsx,rsy);x.lineTo(px2,py2);x.strokeStyle='#f9731688';x.lineWidth=1;x.stroke();
      }}
    }}
    if(r.aa==='P'){{x.beginPath();x.arc(cx,cy,rv*1.3,0,Math.PI*2);x.strokeStyle='#ffd60a44';x.lineWidth=1;x.setLineDash([2,2]);x.stroke();x.setLineDash([]);}}
  }} else {{
    x.beginPath();x.arc(cx,cy,rv,0,Math.PI*2);
    if(vm==='hydro'){{
      const h=HYDRO[r.aa]||0,t=(h+4.5)/9;
      x.fillStyle=`rgb(${{Math.round(255*t)}},60,${{Math.round(255*(1-t))}})`;
    }} else {{ x.fillStyle=col+'44'; }}
    x.fill(); x.strokeStyle=col;x.lineWidth=isH?2.5:1.5;x.stroke();
  }}

  x.fillStyle=isH?'#fff':col; x.font=`bold ${{Math.max(7,Math.min(10,rv))}}px JetBrains Mono`;
  x.textAlign='center';x.textBaseline='middle';x.fillText(r.aa,cx,cy);

  if(r.pos%10===0||r.pos===1){{x.fillStyle='#1e4060';x.font='7px JetBrains Mono';x.fillText(r.pos,cx,cy>H/2?cy+rv+9:cy-rv-9);}}

  if(vm==='formula'||isH){{
    const yd=cy>H/2?-1:1;const fs=Math.max(6,Math.min(9,rv*.9));
    x.fillStyle=col+'cc';x.font=fs+'px JetBrains Mono';x.textAlign='center';
    const fstr=r.formula.length>12?r.formula.slice(0,11)+'…':r.formula;
    x.fillText(fstr,cx,cy-yd*rv*2.4);
  }}
}}

function draw(){{
  x.clearRect(0,0,W,H);
  x.save();x.translate(px,py);x.scale(zm,zm);
  const sl=gwin();const n=sl.length;

  for(let i=0;i<n-1;i++){{
    const p1=gpos(i,n),p2=gpos(i+1,n);
    x.beginPath();x.moveTo(p1.x,p1.y);x.lineTo(p2.x,p2.y);
    x.strokeStyle=(sl[i].isPath||sl[i+1].isPath)?'#ff2d5566':'#0d2035';x.lineWidth=1.5;x.stroke();
  }}

  const cys=sl.filter(r=>r.isCys);
  for(let i=0;i<cys.length-1;i+=2){{
    const i1=sl.indexOf(cys[i]),i2=sl.indexOf(cys[i+1]);
    const p1=gpos(i1,n),p2=gpos(i2,n);
    const cpx=(p1.x+p2.x)/2,cpy=Math.min(p1.y,p2.y)-38;
    x.beginPath();x.moveTo(p1.x,p1.y);x.bezierCurveTo(p1.x,cpy,p2.x,cpy,p2.x,p2.y);
    x.strokeStyle='rgba(255,214,10,.35)';x.lineWidth=1.5;x.setLineDash([3,3]);x.stroke();x.setLineDash([]);
    x.fillStyle='rgba(255,214,10,.6)';x.font='8px Inter';x.textAlign='center';x.fillText('S─S',cpx,cpy+7);
  }}

  sl.forEach((r,i)=>drawRes(r,gpos(i,n),n,i===hov));

  if(sig){{
    const si=Math.floor(sigT*n)%Math.max(1,n);const sp=gpos(si,n);
    const g=x.createRadialGradient(sp.x,sp.y,0,sp.x,sp.y,22);
    g.addColorStop(0,'rgba(0,229,255,.8)');g.addColorStop(1,'transparent');
    x.beginPath();x.arc(sp.x,sp.y,22,0,Math.PI*2);x.fillStyle=g;x.fill();
    x.beginPath();x.arc(sp.x,sp.y,6,0,Math.PI*2);x.fillStyle='#00e5ff';x.fill();
    sigT+=0.005;
  }}
  x.restore();
  requestAnimationFrame(draw);
}}

cv.addEventListener('mousemove',e=>{{
  const r=cv.getBoundingClientRect();
  const mx=(e.clientX-r.left-px)/zm,my=(e.clientY-r.top-py)/zm;
  const sl=gwin();const n=sl.length;hov=null;let md=18;
  sl.forEach((res,i)=>{{const p=gpos(i,n),d=Math.hypot(mx-p.x,my-p.y);if(d<md){{md=d;hov=i;}}  }});
  const el=document.getElementById('info');
  if(hov!==null){{
    const res=sl[hov];el.style.display='block';
    el.innerHTML=`<b style="color:#00e5ff">Pos ${{res.pos}} — ${{res.aa}} (${{res.name}})</b><br>`
      +`<span style="color:#3a6080">Molecular formula: </span><b>${{res.full}}</b><br>`
      +`<span style="color:#3a6080">R-group: </span><b style="color:${{res.color}}">${{res.formula}}</b><br>`
      +`<span style="color:#3a6080">Residue MW: </span>${{res.mw}} Da · Type: <span style="color:${{res.color}}">${{res.type}}</span><br>`
      +(res.isPath?'<span style="color:#ff2d55">⚠ Pathogenic/LP — ClinVar disease variant</span><br>':'')
      +(res.isAnnotPhos?'<span style="color:#f97316">⚡ UniProt phosphosite — PKA/PKC/CK2 substrate</span><br>':'')
      +(res.isPhospho&&!res.isAnnotPhos?'<span style="color:#f97316a0">○ S/T/Y — potential phosphorylation target</span><br>':'')
      +(res.isBind?'<span style="color:#ffd60a">🔗 Chemical binding/active site</span><br>':'')
      +(res.isKin?'<span style="color:#22c55e">🔬 Kinase recognition motif: '+res.kinType+'</span><br>':'')
      +(res.isCys?'<span style="color:#ffd60a">⟺ Cys — disulfide bond participant</span><br>':'')
      +(res.isPro?'<span style="color:#ffd60a">⚡ Pro — disrupts α-helix, backbone rigidity</span><br>':'');
  }} else {{ el.style.display='none'; }}
  if(drag){{px=e.clientX-dsx;py=e.clientY-dsy;}}
}});
cv.addEventListener('mousedown',e=>{{drag=true;dsx=e.clientX-px;dsy=e.clientY-py;}});
cv.addEventListener('mouseup',()=>drag=false);
cv.addEventListener('mouseleave',()=>{{drag=false;document.getElementById('info').style.display='none';}});
cv.addEventListener('wheel',e=>{{zm=Math.max(.25,Math.min(4,zm*(e.deltaY<0?1.15:.87)));e.preventDefault();}},{{passive:false}});
document.addEventListener('keydown',e=>{{
  if(e.key==='ArrowRight'||e.key==='.')scroll(10);
  if(e.key==='ArrowLeft'||e.key===',')scroll(-10);
  if(e.key==='h'||e.key==='H')hotspot();
}});
draw();scroll(0);
</script></body></html>""", height=490, scrolling=False)

    type_cols={"nonpolar":"#ff8c42","aromatic":"#a855f7","polar":"#22c55e","positive":"#4a90d9","negative":"#ff2d55","special":"#ffd60a"}
    st.markdown("<div style='display:flex;gap:7px;flex-wrap:wrap;margin-top:5px;'>"+
        "".join(f"<span style='background:{c}15;color:{c};border:1px solid {c}30;border-radius:6px;padding:2px 9px;font-size:.67rem;'>{t.title()}</span>" for t,c in type_cols.items())+
        "<span style='color:#1e4060;font-size:.67rem;margin-left:4px;'>★ phosphorylatable · ⟺ disulfide · ⬡ aromatic ring · ◀▶ navigate · H = jump to hotspot</span></div>",
        unsafe_allow_html=True)
