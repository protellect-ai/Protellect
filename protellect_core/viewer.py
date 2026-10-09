"""AlphaFold structure viewer (3Dmol) with focus-on-variant and a scroll guard.

Scroll guard: 3Dmol captures the mouse wheel for zooming, which stops the page scrolling whenever the cursor is over the
viewer. A transparent overlay sits on top until you click; it hands the wheel back to the page, and returns when the mouse
leaves or you press Escape.
"""
from __future__ import annotations

import html
import json
from typing import Iterable, Optional

from .adapters import Variant

RANK_COLOR = {"CRITICAL": "#ff2d55", "HIGH": "#ff8c42", "MEDIUM": "#ffd60a", "NEUTRAL": "#3a5a7a"}
SIG_RANK = {"pathogenic": "CRITICAL", "likely pathogenic": "HIGH", "uncertain": "MEDIUM", "conflicting": "MEDIUM"}


def _points(variants: Iterable[Variant], limit: int = 150) -> dict:
    pts = {}
    for v in variants:
        if v.pos is None or len(pts) >= limit:
            continue
        rank = v.ml_rank if v.ml_rank in RANK_COLOR else SIG_RANK.get(v.significance, "NEUTRAL")
        cur = pts.get(str(v.pos))
        if cur and list(RANK_COLOR).index(cur["rank"]) <= list(RANK_COLOR).index(rank):
            continue
        pts[str(v.pos)] = {"rank": rank, "var": v.name[-40:], "sig": v.significance, "cond": v.condition[:60], "url": v.url,
                           "am": None if v.am_score is None else round(v.am_score, 2)}
    return pts


def structure_viewer_html(pdb_text: str, variants: Iterable[Variant], height: int = 520, focus: Optional[int] = None, segments: Optional[list] = None,
                          am_by_res: Optional[dict] = None, burden: Optional[dict] = None, motion: Optional[dict] = None) -> str:
    variants = list(variants)
    pp = json.dumps(_points(variants))
    seg_js = json.dumps([{"name": x.name, "kind": x.kind, "start": x.start, "end": x.end} for x in (segments or [])])
    am_js = json.dumps({str(k): round(float(v), 3) for k, v in (am_by_res or {}).items()})
    bur_js = json.dumps({str(k): int(v) for k, v in (burden or {}).items()})
    pdb_js = json.dumps(pdb_text or "")
    focus_js = json.dumps(int(focus) if focus else None)
    colors = json.dumps(RANK_COLOR)
    mot_js = json.dumps(motion if motion else None)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
<style>*{{margin:0;padding:0;box-sizing:border-box}}html,body{{height:100%;background:#020617;font-family:Inter,system-ui,sans-serif;overflow:hidden}}
body{{display:flex;flex-direction:column}}
#ctrl{{display:flex;gap:4px;padding:6px 8px;background:#050f1e;border-bottom:1px solid #0c2040;flex-wrap:wrap}}
.btn{{background:#05101e;color:#7da3c0;border:1px solid #0c2040;padding:3px 10px;border-radius:14px;cursor:pointer;font-size:11px}}
.btn.on,.btn:hover{{background:#38bdf8;color:#001;font-weight:700;border-color:#38bdf8}}
#wrap{{position:relative;flex:1;min-height:0}}#v{{position:absolute;inset:0}}
#guard{{position:absolute;inset:0;z-index:5;cursor:pointer;display:flex;align-items:flex-end;justify-content:center;padding-bottom:8px;color:#9ccbe6;font-size:11px}}
#guard span{{background:rgba(2,6,23,.85);border:1px solid #0c2040;border-radius:10px;padding:3px 10px}}
#panel{{position:absolute;top:8px;right:8px;width:230px;z-index:6;background:rgba(4,8,15,.95);border:1px solid #0c2040;border-radius:10px;padding:10px;display:none;color:#c8dcea;font-size:11px}}
#panel h3{{color:#38bdf8;font-size:12px;margin-bottom:6px}}#panel .r{{display:flex;justify-content:space-between;margin:3px 0}}#panel a{{color:#5cc3ec}}
#mnote{{position:absolute;top:8px;left:8px;z-index:4;max-width:290px;background:rgba(4,8,15,.92);border:1px solid #0c2040;border-radius:8px;padding:6px 9px;font-size:10px;color:#9ab;display:none}}
#leg{{position:absolute;bottom:34px;left:7px;z-index:4;background:rgba(4,8,15,.9);border:1px solid #0c2040;border-radius:8px;padding:6px 9px;font-size:10px;color:#9ab}}
.ld{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}}</style></head><body>
<div id="ctrl"><button class="btn on" data-s="cartoon">Ribbon</button><button class="btn" data-s="surface">Surface</button>
<span style="color:#6b8aa3;font-size:11px;align-self:center;margin-left:6px">colour by</span><button class="btn on" data-c="plddt">Confidence</button><button class="btn" data-c="topo" id="c_topo">Topology</button><button class="btn" data-c="am" id="c_am">AlphaMissense</button><button class="btn" data-c="bur" id="c_bur">Variant burden</button><button class="btn" data-c="mob" id="c_mob">Mobility</button><button class="btn" id="spin">Spin</button><button class="btn" id="mot">&#9654; Motion</button><select id="mode" class="btn" style="display:none"></select><button class="btn" id="reset">Reset</button><button class="btn on" id="tv">Variants</button></div>
<div id="wrap"><div id="v"></div><div id="guard"><span>Click to interact. Until then the page scrolls normally.</span></div>
<div id="panel"><h3 id="pt"></h3><div id="pc"></div></div>
<div id="mnote">Low-frequency motion of the resting AlphaFold model (elastic network). It shows what is mechanically free to move. It is NOT an active state and has no ligand, lipid or G protein in it.</div>
<div id="leg"><div id="legtxt"></div><div style="margin-top:4px"><i class="ld" style="background:#ff2d55"></i>pathogenic &nbsp;<i class="ld" style="background:#ff8c42"></i>likely &nbsp;<i class="ld" style="background:#ffd60a"></i>VUS (spheres)</div></div></div>
<script>
const PP={pp},PDB={pdb_js},FOCUS={focus_js},COL={colors},SEG={seg_js},AMR={am_js},BUR={bur_js},MOT={mot_js};
const wrap=document.getElementById('wrap'),guard=document.getElementById('guard'),box=document.getElementById('v');
function showGuard(){{guard.style.display='flex'}} function hideGuard(){{guard.style.display='none'}}
guard.addEventListener('click',hideGuard);wrap.addEventListener('mouseleave',showGuard);
document.addEventListener('keydown',function(e){{if(e.key==='Escape')showGuard()}});
function fail(m){{box.innerHTML='<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#8da8bf;font-size:12px;text-align:center;padding:20px">'+m+'</div>';guard.style.display='none'}}
if(typeof $3Dmol==='undefined'){{fail('3D viewer library could not load (network or content blocker).')}}
else if(!PDB||PDB.length<100){{fail('No AlphaFold structure is loaded for this protein.')}}
else{{
const v=$3Dmol.createViewer(box,{{backgroundColor:'#020617'}});v.addModel(PDB,'pdb');
let style='cartoon',showV=true,spinning=false;
let cmode='plddt';
const TMC=['#38bdf8','#818cf8','#2dd4bf','#c084fc','#60a5fa','#f59e0b','#34d399'];
const segOf=r=>{{for(const s of SEG){{if(r>=s.start&&r<=s.end)return s}}return null}};
const mixc=(a,b,t)=>{{t=Math.max(0,Math.min(1,t));const p=x=>[1,3,5].map(i=>parseInt(x.substr(i,2),16));const A=p(a),B=p(b);return '#'+A.map((v,i)=>Math.round(v+(B[i]-v)*t).toString(16).padStart(2,'0')).join('')}};
const CF={{plddt:a=>a.b>=90?'#1565C0':a.b>=70?'#29B6F6':a.b>=50?'#FDD835':'#FF7043',
 topo:a=>{{const s=segOf(a.resi);if(!s)return '#475569';return s.kind==='TM'?TMC[(parseInt(s.name.slice(2))-1)%7]:s.kind==='ECL'?'#cbd5e1':s.kind==='ICL'?'#64748b':'#475569'}},
 am:a=>{{const v=AMR[String(a.resi)];return v===undefined?'#334155':mixc('#1d4e89','#ff2d55',(v-0.2)/0.7)}},
 mob:a=>{{const m=MOBI[String(a.resi)];return m===undefined?'#334155':mixc('#1d4e89','#ff8c42',m)}},
 bur:a=>{{const n=BUR[String(a.resi)]||0;return n===0?'#16365c':mixc('#fbbf24','#ff2d55',Math.min(1,(n-1)/4))}}}};
const MOBI={{}};if(MOT)MOT.resi.forEach((r,i)=>{{MOBI[String(r)]=MOT.mobility[i]}});
const cf=a=>CF[cmode](a);
const LEG={{plddt:'pLDDT: &ge;90 dark blue, 70-90 light blue, 50-70 yellow, &lt;50 orange',topo:'TM1-TM7 each a colour; loops grey; termini dark',am:'mean-of-max AlphaMissense per residue: blue (benign) to red (pathogenic)',bur:'ClinVar variants per residue: dark = none, yellow to red = more',mob:'Mechanical mobility from the elastic network: blue = rigid core, orange = free to move'}};
function legend(){{document.getElementById('legtxt').innerHTML=LEG[cmode]}}
function paint(){{v.removeAllSurfaces();v.removeAllLabels();
 if(style==='surface'){{v.setStyle({{}},{{cartoon:{{colorfunc:cf,opacity:.5}}}});v.addSurface($3Dmol.SurfaceType.VDW,{{colorfunc:cf,opacity:.7}})}}
 else v.setStyle({{}},{{cartoon:{{colorfunc:cf,thickness:.42}}}});
 if(showV)Object.keys(PP).forEach(p=>{{const i=PP[p];v.addStyle({{resi:+p}},{{sphere:{{color:COL[i.rank]||'#fff',radius:.9}}}})}});
 if(cmode==='topo')SEG.filter(s=>s.kind==='TM').forEach(s=>v.addLabel(s.name,{{fontSize:12,backgroundColor:'#000',backgroundOpacity:.7,fontColor:'#fff'}},{{resi:Math.round((s.start+s.end)/2),atom:'CA'}}));
 if(FOCUS){{v.addStyle({{resi:FOCUS}},{{stick:{{color:'#ffffff',radius:.35}},sphere:{{color:'#ffffff',radius:1.5,opacity:.55}}}});
  v.addLabel('residue '+FOCUS,{{fontSize:12,backgroundColor:'#000',backgroundOpacity:.75,fontColor:'#fff'}},{{resi:FOCUS,atom:'CA'}})}}
 legend();v.render()}}
paint();if(FOCUS)v.zoomTo({{resi:FOCUS}},600);else v.zoomTo();v.render();
v.setClickable({{}},true,function(atom){{const i=PP[String(atom.resi)];let h='<div class="r"><span>Residue</span><b>'+(atom.resn||'')+' '+atom.resi+'</b></div><div class="r"><span>pLDDT</span><b>'+(atom.b||0).toFixed(0)+'</b></div>';
 if(i){{h+='<div class="r"><span>Class</span><b>'+i.sig+'</b></div>';if(i.am!==null)h+='<div class="r"><span>AlphaMissense</span><b>'+i.am+'</b></div>';
  if(i.cond)h+='<div style="margin-top:4px;color:#9ab">'+i.cond+'</div>';if(i.url)h+='<a href="'+i.url+'" target="_blank">ClinVar record</a>'}}
 document.getElementById('pt').textContent=(atom.resn||'')+atom.resi;document.getElementById('pc').innerHTML=h;document.getElementById('panel').style.display='block'}});
document.querySelectorAll('.btn[data-s]').forEach(b=>b.addEventListener('click',()=>{{document.querySelectorAll('.btn[data-s]').forEach(x=>x.classList.remove('on'));b.classList.add('on');style=b.dataset.s;paint()}}));
document.querySelectorAll('.btn[data-c]').forEach(b=>b.addEventListener('click',()=>{{document.querySelectorAll('.btn[data-c]').forEach(x=>x.classList.remove('on'));b.classList.add('on');cmode=b.dataset.c;paint()}}));
if(!SEG.length)document.getElementById('c_topo').style.display='none';if(!Object.keys(AMR).length)document.getElementById('c_am').style.display='none';if(!Object.keys(BUR).length)document.getElementById('c_bur').style.display='none';
document.getElementById('spin').addEventListener('click',()=>{{spinning=!spinning;v.spin(spinning?'y':false,.6)}});
document.getElementById('reset').addEventListener('click',()=>{{v.zoomTo();v.render()}});

let moving=false,curMode=0;
const NF=24,AMP=3.5;
function frameModel(k){{const f=Math.sin(2*Math.PI*k/NF)*AMP,vec=MOT.modes[curMode].vec,ix={{}};MOT.resi.forEach((r,i)=>ix[r]=i);
 return PDB.split('\\n').filter(l=>l.startsWith('ATOM')).map(l=>{{const r=parseInt(l.substr(22,4)),i=ix[r];if(i===undefined)return l;const d=vec[i];
  const x=(parseFloat(l.substr(30,8))+f*d[0]).toFixed(3).padStart(8),y=(parseFloat(l.substr(38,8))+f*d[1]).toFixed(3).padStart(8),z=(parseFloat(l.substr(46,8))+f*d[2]).toFixed(3).padStart(8);
  return l.substr(0,30)+x+y+z+l.substr(54)}}).join('\\n')+'\\nENDMDL'}}
function startMotion(){{v.removeAllModels();let all='';for(let k=0;k<NF;k++)all+='MODEL '+(k+1)+'\\n'+frameModel(k)+'\\n';
 v.addModelsAsFrames(all,'pdb');paint();v.animate({{interval:70,loop:'forward',reps:0}})}}
function stopMotion(){{v.stopAnimate();v.removeAllModels();v.addModel(PDB,'pdb');paint()}}
if(!MOT){{document.getElementById('mot').style.display='none';document.getElementById('c_mob').style.display='none'}}
else{{const sel=document.getElementById('mode');MOT.modes.forEach((m,i)=>{{const o=document.createElement('option');o.value=i;o.textContent='mode '+m.mode;sel.appendChild(o)}});
 document.getElementById('mot').addEventListener('click',e=>{{moving=!moving;e.target.classList.toggle('on',moving);sel.style.display=moving?'inline-block':'none';document.getElementById('mnote').style.display=moving?'block':'none';
  if(moving){{if(spinning){{spinning=false;v.spin(false)}};startMotion()}}else stopMotion()}});
 sel.addEventListener('change',()=>{{curMode=+sel.value;if(moving){{v.stopAnimate();startMotion()}}}})}}

document.getElementById('tv').addEventListener('click',e=>{{showV=!showV;e.target.classList.toggle('on',showV);paint()}});
}}
</script></body></html>"""
