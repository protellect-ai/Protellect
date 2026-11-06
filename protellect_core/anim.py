"""Technical animation of what happens in the experiment, driven by the loaded data (SVG + CSS; no scripts).

GPCR: sample -> ligand binding and TM6 swing -> G protein and second messenger -> assay readout.
Other proteins: sample -> protein architecture with domains and real variant positions -> interaction partners -> validation readout.
Anything that is a hypothesis (ligand class, coupling) is labelled PREDICTED on the graphic itself.
"""
from __future__ import annotations

import html
from typing import Optional

from .adapters import Bundle

E = lambda s: html.escape(str(s), quote=True)
CSS = """<style>
@keyframes pulse{0%,100%{opacity:.55;r:9}50%{opacity:1;r:11}}
@keyframes dock{0%{transform:translate(0,0)}35%{transform:translate(0,0)}70%,100%{transform:translate(78px,64px)}}
@keyframes swing{0%,40%{transform:rotate(0)}75%,100%{transform:rotate(-16deg)}}
@keyframes flow{0%{transform:translate(0,0);opacity:0}10%{opacity:1}100%{transform:translate(0,92px);opacity:0}}
@keyframes draw{0%{stroke-dashoffset:260}60%,100%{stroke-dashoffset:0}}
@keyframes reveal{0%{opacity:0}30%,100%{opacity:1}}
.cell{animation:pulse 2.4s ease-in-out infinite}.lig{animation:dock 6s ease-in-out infinite}.tm6{transform-origin:84px 70px;animation:swing 6s ease-in-out infinite}
.p1{animation:flow 3s linear infinite}.p2{animation:flow 3s linear .8s infinite}.p3{animation:flow 3s linear 1.6s infinite}
.curve{stroke-dasharray:260;animation:draw 6s ease-in-out infinite}.rev{animation:reveal 6s ease-in infinite}
text{font-family:Inter,system-ui,sans-serif}</style>"""


def _panel(x, w, title, sub=""):
    return (f'<rect x="{x}" y="14" width="{w}" height="372" rx="14" fill="#06101f" stroke="#0c2040"/>'
            f'<text x="{x + w/2}" y="38" fill="#7dd3fc" font-size="12" font-weight="700" text-anchor="middle">{E(title)}</text>'
            + (f'<text x="{x + w/2}" y="54" fill="#6b8aa3" font-size="9.5" text-anchor="middle">{E(sub)}</text>' if sub else ""))


def experiment_animation(b: Bundle, ctx=None, ligand_class: str = "", coupling: str = "", signal: str = "", assay: str = "", coupling_recorded: bool = False) -> str:
    tissue = (getattr(ctx, "tissue", "") or "your sample")[:26]
    plp = b.plp
    parts = [f'<div style="background:#020617;border:1px solid #0c2040;border-radius:14px;padding:6px"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 400" width="100%" role="img" aria-label="Animation of the experiment for {E(b.gene)}"><rect width="1000" height="400" fill="#020617"/>', CSS]
    parts.append(_panel(14, 190, "1. Your sample", tissue))
    for i, (cx, cy) in enumerate([(60, 120), (110, 105), (160, 125), (80, 175), (135, 180), (105, 235), (55, 240), (160, 240)]):
        parts.append(f'<circle class="cell" cx="{cx}" cy="{cy}" r="9" fill="#38bdf8" style="animation-delay:{i*0.25}s"/>')
    parts.append(f'<text x="109" y="300" fill="#cfe6f5" font-size="11" text-anchor="middle">{E(b.gene)}{(" " + E(signal)) if signal else ""}</text>')
    parts.append(f'<text x="109" y="318" fill="#6b8aa3" font-size="9.5" text-anchor="middle">{"from your uploaded data" if signal else "no experiment signal supplied"}</text>')
    if b.is_gpcr:
        parts.append(_panel(216, 330, "2. Receptor at the membrane", "7-transmembrane receptor"))
        parts.append('<rect x="236" y="190" width="290" height="14" rx="7" fill="#1a3556" opacity=".85"/><rect x="236" y="262" width="290" height="14" rx="7" fill="#1a3556" opacity=".85"/>')
        for i in range(7):
            x = 300 + i * 24
            cls = ' class="tm6"' if i == 5 else ""
            parts.append(f'<rect{cls} x="{x}" y="176" width="14" height="114" rx="6" fill="{"#f59e0b" if i == 5 else "#38bdf8"}" opacity=".9"/>')
        parts.append(f'<g class="lig"><circle cx="276" cy="110" r="13" fill="#a78bfa"/><text x="276" y="92" fill="#c4b5fd" font-size="9.5" text-anchor="middle">{E(ligand_class + " ligand") if ligand_class else "ligand (unknown)"}</text></g>')
        parts.append(f'<text x="381" y="318" fill="#6b8aa3" font-size="9.5" text-anchor="middle">{"PREDICTED ligand class from precedent analysis" if ligand_class else "ligand not identified: this is what the experiment must find"}</text>')
        tm = sum(1 for v in plp if "transmembrane" in b.domain_at(v.pos).lower())
        parts.append(f'<text x="381" y="338" fill="#fda4af" font-size="10" text-anchor="middle">{len(plp)} pathogenic or likely-pathogenic variants on record</text>')
        if tm:
            parts.append(f'<text x="381" y="352" fill="#fda4af" font-size="10" text-anchor="middle">{tm} of them in transmembrane helices</text>')
        parts.append(_panel(558, 190, "3. G protein and messenger", (("recorded in GPCRdb: " if coupling_recorded else "PREDICTED coupling: ") + coupling) if coupling else "coupling not established"))
        msg = {"Gq": "Ca2+ / IP3", "Gi": "cAMP falls", "Gs": "cAMP rises"}.get(coupling, "second messenger")
        parts.append('<circle cx="653" cy="104" r="22" fill="#0f2a4a" stroke="#38bdf8"/>' f'<text x="653" y="108" fill="#cfe6f5" font-size="11" text-anchor="middle">{E(coupling or "G\u03b1")}</text>')
        for cls, dx in (("p1", 620), ("p2", 653), ("p3", 686)):
            parts.append(f'<circle class="{cls}" cx="{dx}" cy="140" r="5" fill="#34d399"/>')
        parts.append(f'<text x="653" y="262" fill="#86efac" font-size="11" text-anchor="middle">{E(msg)}</text>')
        panel4_title = "4. Readout"
    else:
        parts.append(_panel(216, 330, "2. Protein architecture", f"{b.length} residues; real variant positions"))
        L = max(b.length, 1)
        parts.append('<rect x="240" y="170" width="282" height="26" rx="6" fill="#12304f"/>')
        for d in b.domains[:8]:
            x = 240 + 282 * d["start"] / L
            w = max(4, 282 * (d["end"] - d["start"]) / L)
            parts.append(f'<rect x="{x:.1f}" y="170" width="{w:.1f}" height="26" rx="4" fill="#38bdf8" opacity=".75"><title>{E(d["desc"] or d["type"])} {d["start"]}-{d["end"]}</title></rect>')
        for i, v in enumerate([v for v in plp if v.pos][:60]):
            x = 240 + 282 * v.pos / L
            parts.append(f'<line class="rev" x1="{x:.1f}" y1="150" x2="{x:.1f}" y2="170" stroke="#ff2d55" stroke-width="1.4" style="animation-delay:{(i % 10) * 0.15}s"/>')
        parts.append(f'<text x="381" y="228" fill="#fda4af" font-size="10" text-anchor="middle">{len(plp)} pathogenic or likely-pathogenic variants (red ticks)</text>')
        parts.append(f'<text x="381" y="243" fill="#6b8aa3" font-size="9.5" text-anchor="middle">on {len(b.domains)} annotated region(s) (blue)</text>')
        parts.append(_panel(558, 190, "3. Interaction partners", "STRING"))
        for i, p in enumerate(sorted(b.partners, key=lambda p: -p.score)[:6]):
            parts.append(f'<circle class="cell" cx="{600 + (i % 2) * 90}" cy="{100 + (i // 2) * 60}" r="9" fill="#a78bfa" style="animation-delay:{i*0.3}s"/><text x="{600 + (i % 2) * 90}" y="{122 + (i // 2) * 60}" fill="#cfe6f5" font-size="9.5" text-anchor="middle">{E(p.name)}</text>')
        panel4_title = "4. Validation readout"
    parts.append(_panel(760, 226, panel4_title, "what the confirmatory assay measures"))
    parts.append('<line x1="782" y1="320" x2="966" y2="320" stroke="#2a4a6a"/><line x1="782" y1="320" x2="782" y2="90" stroke="#2a4a6a"/>')
    parts.append('<path class="curve" d="M782 310 C 830 308, 850 300, 872 230 S 920 120, 966 112" fill="none" stroke="#34d399" stroke-width="3"/>')
    parts.append(f'<text x="873" y="344" fill="#cfe6f5" font-size="10" text-anchor="middle">{E(assay[:52]) if assay else "assay to be chosen from the strategy"}</text>')
    parts.append('<text x="873" y="362" fill="#6b8aa3" font-size="9" text-anchor="middle">schematic curve for illustration, not data</text>')
    parts.append('</svg></div>')
    return "".join(parts)
