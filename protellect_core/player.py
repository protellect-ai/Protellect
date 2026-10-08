"""A video-style player for the signalling animation: play, pause, drag the timeline, jump between steps, and read what each moment means for THIS receptor.

Why an iframe player instead of an inline SVG: inline SVG animations run forever and repaint the page even when scrolled out of view, which makes long pages stutter.
The player pauses itself when it is off-screen and starts paused if the browser asks for reduced motion.
"""
from __future__ import annotations

import html
import json
from typing import Dict, List, Optional

from .gpcrome import PATHWAYS

CYCLE_MS = 14000
STEP_MS = CYCLE_MS // 5


def narration(gene: str, *, status: str = "unknown", coupling: str = "", coupling_source: str = "", hypothesis: Optional[dict] = None, ligand_lines: Optional[List[str]] = None,
              motifs: Optional[List[dict]] = None, signal: str = "", context: str = "", first_assay: str = "", segments: Optional[Dict[str, tuple]] = None) -> List[Dict[str, str]]:
    """Six captions: the five steps of activation, then what it means for the user's data. General mechanism is stated as mechanism; anything about this receptor is labelled by its source."""
    orphan = status == "orphan"
    mm = {m["motif"].split(" ")[0]: m for m in (motifs or [])}
    ligand_specific = (f"No ligand is confirmed for {gene}. The molecule in the animation stands for the unknown ligand, so this whole step is a hypothesis. " if orphan else "")
    if hypothesis:
        ligand_specific += f"The precedent model's top suggestion: {hypothesis['statement'].lower()} (relative support {hypothesis['support']:.2f}, not a probability). "
    ligand_specific += " ".join(ligand_lines or [])
    toggle = mm.get("CWxP")
    dry = mm.get("D/ERY")
    npxxy = mm.get("NPxxY")
    sp2 = []
    if dry:
        sp2.append(f"In {gene} the ionic-lock motif {dry['seq']} is found at residues {dry['start']}-{dry['end']}")
    if toggle:
        sp2.append(f"the toggle-switch motif {toggle['seq']} at {toggle['start']}-{toggle['end']}")
    if npxxy:
        sp2.append(f"and {npxxy['seq']} at {npxxy['start']}-{npxxy['end']}")
    step2 = (", ".join(sp2) + ". These are pattern matches in the sequence, not proof of function." if sp2 else "No conserved class A motif was found in the expected positions of the sequence, so this receptor may be a divergent class or the annotation is incomplete.")
    if orphan:
        step2 += f" If {gene} signals without a ligand (constitutive activity), this opening happens spontaneously at a low rate and shows up as a basal signal above an empty-vector control."
    cls = coupling.replace("Gi/o", "Gi").replace("Gq/11", "Gq")
    cp = (f"Predicted partner for {gene}: {coupling} ({coupling_source}). " if coupling else f"No coupling is recorded or predicted for {gene} from the data supplied. ")
    cp += "Which G-protein it picks is set mainly by the receptor's intracellular loops and the C-terminal alpha-5 helix of the G protein; a G-protein sensor panel measures exactly this step."
    path = PATHWAYS.get(cls, "")
    eff = (path + " " if path else "") + "Readouts: cAMP for Gs and Gi, calcium or IP1 for Gq, a RhoA or SRF reporter for G12/13, and beta-arrestin recruitment for the arrestin branch."
    mine = []
    if signal:
        mine.append(f"In your experiment {gene} shows {signal}.")
    if context:
        mine.append(f"Experiment context: {context}.")
    if coupling and not orphan:
        mine.append(f"If {gene} acts through {coupling} here, the readout above should change when it is active.")
    if orphan and coupling:
        mine.append(f"If the {coupling} prediction is right, a {coupling}-selective sensor should respond and the others should not; if several respond, over-expression is the first suspect.")
    if first_assay:
        mine.append("Suggested first experiment: " + first_assay)
    return [
        {"title": "1. A ligand binds", "general": "An agonist enters the orthosteric pocket formed by transmembrane helices 3, 5, 6 and 7 (class A receptors) and stabilises the active state.", "specific": ligand_specific or f"For {gene} the ligand is not part of the data supplied."},
        {"title": "2. The helix bundle opens", "general": "Binding rearranges the helices. TM6 swings outward by several angstroms and the cytoplasmic cleft opens; the conserved ionic-lock, toggle-switch and NPxxY motifs mark this switch.", "specific": step2},
        {"title": "3. A G protein engages", "general": "The G protein's alpha-5 helix inserts into the cleft. The receptor pulls on the Galpha nucleotide pocket and GDP is released.", "specific": cp},
        {"title": "4. GTP binds, subunits separate", "general": "GTP enters the empty pocket. Galpha-GTP and the Gbeta-gamma dimer separate, and each is free to act on its own targets.", "specific": f"This step is why a G-protein-activation sensor (a BRET or shedding readout) reports activity for {gene}." if cls else "Whether Galpha or Gbeta-gamma carries the signal depends on the family."},
        {"title": "5. Effectors act, messengers appear", "general": "The released subunits regulate effectors such as adenylyl cyclase, phospholipase C-beta and RhoGEFs, producing second messengers that can be measured. Arrestins then terminate the signal.", "specific": eff},
        {"title": "What this means for your data", "general": "The animation is the general mechanism. This panel is where it meets your experiment.", "specific": " ".join(mine) if mine else "Load an experiment to see how it meets this receptor's data."},
    ]


_JS = r"""
const CH=__CHAPTERS__,CYCLE=__CYCLE__,STEP=__STEP__;
let t=0,playing=true,speed=1,last=null,visible=true,pinned=-1,anims=[];
const $=id=>document.getElementById(id);
function collect(){anims=document.getAnimations();anims.forEach(a=>a.pause());}
function apply(){for(const a of anims)a.currentTime=t;}
function chapterAt(ms){return Math.min(4,Math.floor(ms/STEP));}
function ui(){
  const i=pinned>=0?pinned:chapterAt(t);
  $('sc').value=Math.round(t);$('tm').textContent=(t/1000).toFixed(1)+' / '+(CYCLE/1000).toFixed(0)+' s';
  $('ct').textContent=CH[i].title;$('cg').textContent=CH[i].general;$('cs').textContent=CH[i].specific;
  document.querySelectorAll('.chap').forEach((b,k)=>b.classList.toggle('on',k===i));
  $('pp').textContent=playing?'Pause':'Play';
}
function tick(ts){
  if(last===null)last=ts;const dt=ts-last;last=ts;
  if(playing&&visible){t=(t+dt*speed)%CYCLE;pinned=-1;apply();ui();}
  requestAnimationFrame(tick);
}
function seek(ms){t=Math.max(0,Math.min(CYCLE-1,ms));apply();ui();}
window.addEventListener('load',()=>{
  collect();
  if(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches)playing=false;
  $('pp').onclick=()=>{playing=!playing;if(playing)pinned=-1;ui();};
  $('rs').onclick=()=>{pinned=-1;seek(0);};
  $('sc').oninput=e=>{pinned=-1;playing=false;seek(+e.target.value);};
  $('sp').onchange=e=>{speed=+e.target.value;};
  document.querySelectorAll('.chap').forEach((b,k)=>b.onclick=()=>{playing=false;if(k<5){pinned=-1;seek(k*STEP+STEP*0.55);}else{pinned=5;seek(CYCLE-1);ui();}});
  document.addEventListener('keydown',e=>{if(e.code==='Space'){e.preventDefault();$('pp').click();}});
  if('IntersectionObserver' in window)new IntersectionObserver(es=>{visible=es[0].isIntersecting;},{threshold:0.05}).observe($('stage'));
  apply();ui();requestAnimationFrame(tick);
});
"""

_CSS = """
body{margin:0;background:#020617;color:#d7e3f1;font-family:'DM Sans',system-ui,sans-serif;overflow:hidden}
#stage svg{display:block;width:100%;height:auto}
#bar{display:flex;gap:10px;align-items:center;padding:8px 6px;flex-wrap:wrap}
button,select{background:#0b1b34;color:#d7e3f1;border:1px solid #1f6f9f;border-radius:8px;padding:6px 12px;font-size:13px;cursor:pointer}
button:hover{background:#12305a}
#sc{flex:1;min-width:160px;accent-color:#38bdf8}
#tm{font-variant-numeric:tabular-nums;color:#7dd3fc;font-size:12px;min-width:90px}
#chaps{display:flex;gap:6px;flex-wrap:wrap;padding:0 6px 6px}
.chap{font-size:12px;padding:5px 10px}.chap.on{background:#1f6f9f;border-color:#7dd3fc;color:#fff}
#cap{margin:4px 6px 8px;padding:10px 14px;border-left:3px solid #38bdf8;background:#06142a;border-radius:0 8px 8px 0;line-height:1.5;font-size:13.5px}
#ct{font-weight:700;color:#e6edf7;margin-bottom:4px}#cg{color:#b7c9db}#cs{color:#fbbf24;margin-top:6px}
"""


def player_html(svg_markup: str, captions: List[Dict[str, str]]) -> str:
    chaps = "".join(f"<button class='chap'>{html.escape(c['title'] if i == 5 else c['title'].split('. ', 1)[-1])}</button>" for i, c in enumerate(captions))
    js = _JS.replace("__CHAPTERS__", json.dumps(captions).replace("</", "<\\/")).replace("__CYCLE__", str(CYCLE_MS)).replace("__STEP__", str(STEP_MS))
    return (f"<style>{_CSS}</style><div id='stage'>{svg_markup}</div>"
            "<div id='bar'><button id='pp'>Pause</button><button id='rs' title='Back to the start'>Restart</button><input id='sc' type='range' min='0' max='" + str(CYCLE_MS) + "' value='0' step='10'>"
            "<span id='tm'>0.0 / 14 s</span><select id='sp' title='Speed'><option value='0.5'>0.5x</option><option value='1' selected>1x</option><option value='2'>2x</option></select></div>"
            "<div id='chaps'>" + chaps + "</div><div id='cap'><div id='ct'></div><div id='cg'></div><div id='cs'></div></div>"
            f"<script>{js}</script>")


def render_player(svg_markup: str, captions: List[Dict[str, str]], height: int = 1010) -> None:
    import streamlit.components.v1 as components
    components.html(player_html(svg_markup, captions), height=height, scrolling=False)
