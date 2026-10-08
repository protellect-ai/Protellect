"""Variant cascade: every stage is conditional on the variant's actual class and carries an evidence tag.

Tags: recorded (a database record), derived (computed from records), predicted (a model score), expected (the standard
consequence for this variant class, not measured here), untested (possible, needs an experiment). Nothing is asserted
beyond the tag. This replaces a fixed story that told the same tale for every variant.
"""
from __future__ import annotations

import html
import json
from typing import List

from .adapters import Bundle, Variant, plddt_at
from .analysis import variant_plan


def cascade_stages(b: Bundle, v: Variant) -> List[dict]:
    L = max(b.length, 1)
    pl = plddt_at(b.pdb, v.pos)
    dom = b.domain_at(v.pos)
    site = next((s for s in b.sites if v.pos and s["start"] <= v.pos <= s["end"]), None)
    st = [{"title": "The variant", "tag": "recorded", "text": f"{v.name or 'variant'}; ClinVar: {v.significance}, {v.stars} star(s)" + (f"; condition: {v.condition}" if v.condition else "") + ".", "url": v.url}]
    c = v.consequence
    if c == "missense":
        txt = f"One amino acid is replaced at residue {v.pos}" + (f", inside {dom}" if dom else "") + (f", at an annotated {site['type'].lower()}" if site else "") + "."
    elif c == "nonsense":
        txt = f"The chain is cut short at residue {v.pos}; about {100 * (L - (v.pos or L)) / L:.0f}% of the protein would be missing."
    elif c == "frameshift":
        txt = f"The reading frame shifts after residue {v.pos}, changing everything downstream."
    elif c == "splice":
        txt = "A splice-site change can cause exon skipping or intron retention; the exact product is not given by this record."
    elif c == "synonymous":
        txt = "No amino-acid change is recorded."
    else:
        txt = "The protein-level effect is not specified in this record."
    st.append({"title": "Change to the protein", "tag": "derived", "text": txt, "url": ""})
    if c == "missense":
        parts = []
        if v.am_score is not None:
            parts.append(f"AlphaMissense {v.am_score:.2f} ({v.am_class or 'unclassified'}; > 0.564 means likely pathogenic)")
        if pl is not None:
            parts.append(f"AlphaFold confidence at this residue is pLDDT {pl:.0f}")
        st.append({"title": "Predicted impact", "tag": "predicted", "text": ("; ".join(parts) + ". These are model outputs, not measurements.") if parts else "No prediction is available for this residue.", "url": "https://alphamissense.hegelab.org/"})
    elif c in ("nonsense", "frameshift"):
        st.append({"title": "Expected consequence", "tag": "expected", "text": "Truncating changes are usually removed by nonsense-mediated decay, so less protein is made. Confirm by measuring transcript and protein.", "url": ""})
    if b.is_gpcr and c == "missense" and dom and ("transmembrane" in dom.lower() or "loop" in dom.lower() or "topolog" in dom.lower()):
        st.append({"title": "Possible signalling effect", "tag": "untested", "text": f"A change in {dom} could affect receptor folding, surface expression or G-protein coupling. Only a functional assay can tell.", "url": ""})
    elif b.partners:
        names = ", ".join(p.name for p in sorted(b.partners, key=lambda p: -p.score)[:4])
        st.append({"title": "Possible effect on interactions", "tag": "untested", "text": f"If the change disturbs the protein, interactions with {names} (STRING partners) could be affected. This has not been tested.", "url": b.partners[0].url})
    if v.condition and v.significance in ("pathogenic", "likely pathogenic"):
        st.append({"title": "Disease association", "tag": "recorded", "text": f"Submitters link this variant to: {v.condition}.", "url": v.url})
    first = variant_plan(v, b)[3]
    st.append({"title": "What to measure next", "tag": "rule", "text": f"{first['do']} ({first['basis']})", "url": first.get("url", "")})
    return st


TAG_COLOR = {"recorded": "#34d399", "derived": "#38bdf8", "predicted": "#a78bfa", "expected": "#fbbf24", "untested": "#fb7185", "rule": "#94a3b8"}


def cascade_html(b: Bundle, v: Variant, height: int = 300) -> str:
    stages = cascade_stages(b, v)
    data = json.dumps(stages)
    cols = json.dumps(TAG_COLOR)
    return f"""<div style="background:#020617;border:1px solid #0c2040;border-radius:12px;padding:12px;font-family:Inter,system-ui,sans-serif;color:#cfe6f5">
<div style="font-size:12px;color:#7dd3fc;font-weight:700;margin-bottom:6px">Cascade for {html.escape(v.name[-60:] or 'variant')}: drag to step through</div>
<input id="sl" type="range" min="0" max="{len(stages) - 1}" value="0" style="width:100%"><div id="dots" style="display:flex;gap:6px;margin:6px 0"></div>
<div id="card" style="min-height:{height - 110}px;border:1px solid #0c2040;border-radius:10px;padding:12px;background:#06101f"></div></div>
<script>const S={data},C={cols};const sl=document.getElementById('sl'),card=document.getElementById('card'),dots=document.getElementById('dots');
function esc(t){{const d=document.createElement('div');d.textContent=t;return d.innerHTML}}
function draw(){{const i=+sl.value,s=S[i];dots.innerHTML=S.map((x,j)=>'<span style="flex:1;height:5px;border-radius:3px;background:'+(j<=i?C[x.tag]:'#12304f')+'"></span>').join('');
card.innerHTML='<div style="display:flex;justify-content:space-between;align-items:center"><b style="font-size:14px">'+(i+1)+'. '+esc(s.title)+'</b><span style="font-size:10px;padding:2px 8px;border-radius:10px;border:1px solid '+C[s.tag]+';color:'+C[s.tag]+'">'+s.tag+'</span></div><p style="font-size:13px;line-height:1.55;margin-top:8px">'+esc(s.text)+'</p>'+(s.url?'<a style="font-size:11px;color:#5cc3ec" target="_blank" href="'+esc(s.url)+'">source</a>':'')}}
sl.addEventListener('input',draw);draw();</script>"""
