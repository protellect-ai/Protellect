"""Technical visuals. Every label, residue number, count and colour comes from the loaded data; nothing is decorative.

- topology_svg: the receptor's seven annotated helices with residue ranges, loop lengths, conserved motifs, variants placed by residue and
  helices coloured by mean AlphaMissense.
- architecture_svg: any protein as a residue-scaled map (ruler, domains, sites, hotspots, variant lollipops, AlphaMissense strip, pLDDT strip).
- signalling_svg: an animated, labelled walk through ligand binding, TM6 movement, G-protein cycle, class-specific effectors and the assay that reads each step.
"""
from __future__ import annotations

import html
from typing import Dict, List, Optional

from .adapters import Bundle, Variant, mean_plddt
from .topology import Segment, segment_of

E = lambda s: html.escape(str(s), quote=True)
BG, PANEL, LINE, TXT, MUTED, ACC = "#020617", "#06101f", "#0c2040", "#cfe6f5", "#6b8aa3", "#38bdf8"
SIG = {"pathogenic": "#ff2d55", "likely pathogenic": "#ff8c42", "uncertain": "#ffd60a", "conflicting": "#ffd60a", "benign": "#34d399", "likely benign": "#34d399"}
FONT = "font-family:Inter,system-ui,sans-serif"


def _mix(c1: str, c2: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{int(x + (y - x) * t):02x}" for x, y in zip(a, b))


def _wrap(text: str, width: int) -> List[str]:
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + ([cur] if cur else [])


def _frame(w: int, h: int, body: str, label: str, extra_css: str = "") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{E(label)}" style="background:{BG};border:1px solid {LINE};border-radius:14px;{FONT}">'
            f'<style>text{{{FONT}}}{extra_css}</style><rect width="{w}" height="{h}" fill="{BG}" rx="14"/>{body}</svg>')


def _t(x, y, s, size=12, fill=TXT, weight=400, anchor="start", extra="") -> str:
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" {extra}>{E(s)}</text>'


# ═══════════════════════════════════════════════════════════════ topology
def topology_svg(b: Bundle, segs: List[Segment], motifs: List[dict], stats: Dict[str, dict], selected: Optional[Variant] = None) -> str:
    W, H = 1230, 700
    xs = [150 + i * 140 for i in range(7)]
    y_top, y_bot = 250, 430
    o = []
    o.append(_t(24, 34, f"{b.gene} · transmembrane topology", 17, TXT, 700))
    o.append(_t(24, 54, f"UniProt {b.uid} · {b.length} residues · helix boundaries from UniProt feature annotations · helix colour = mean of the highest AlphaMissense score per residue", 11, MUTED))
    o.append(f'<rect x="80" y="{y_top + 14}" width="990" height="{y_bot - y_top - 28}" rx="18" fill="#10264a" opacity=".55"/>')
    o.append(_t(92, y_top + 36, "plasma membrane", 11, "#5f86ad", 400, extra='font-style="italic"'))
    o.append(_t(24, 238, "EXTRACELLULAR", 10.5, "#5f86ad", 700, extra='letter-spacing="1.5"'))
    o.append(_t(24, 458, "CYTOPLASM", 10.5, "#5f86ad", 700, extra='letter-spacing="1.5"'))
    seg = {s.name: s for s in segs}
    loop_names = ["ICL1", "ECL1", "ICL2", "ECL2", "ICL3", "ECL3"]
    for i, nm in enumerate(loop_names):
        s = seg[nm]
        x1, x2 = xs[i], xs[i + 1]
        up = nm.startswith("ECL")
        h = 38 + min(86, s.length * 1.1)
        y0 = y_top - 20 if up else y_bot + 20
        yc = y0 - h if up else y0 + h
        o.append(f'<path d="M{x1},{y0} C{x1},{yc} {x2},{yc} {x2},{y0}" fill="none" stroke="#5aa9d6" stroke-width="2.2"/>')
        ty = (yc + 0.25 * (y0 - yc)) - 22 if up else yc - 0.25 * (yc - y0) + 30
        st = stats.get(nm, {})
        o.append(_t((x1 + x2) / 2, ty - 8 if up else ty, nm, 14, TXT, 700, "middle"))
        o.append(_t((x1 + x2) / 2, ty + 7 if up else ty + 15, f"{s.start}–{s.end} · {s.length} aa", 10.5, MUTED, 400, "middle"))
        if st.get("plp") or st.get("vus"):
            o.append(_t((x1 + x2) / 2, ty + 21 if up else ty + 30, f"P/LP {st['plp']} · VUS {st['vus']}", 10.5, SIG["pathogenic"] if st["plp"] else SIG["uncertain"], 600, "middle"))
    n, c = seg["N-terminus"], seg["C-terminus"]
    o.append(f'<path d="M{xs[0]},{y_top - 20} C{xs[0]},150 150,130 70,126" fill="none" stroke="#5aa9d6" stroke-width="2.2"/>')
    o.append(_t(24, 108, "N-terminus", 14, TXT, 700)); o.append(_t(24, 124, f"{n.start}–{n.end} · {n.length} aa · extracellular", 10.5, MUTED))
    sn = stats.get("N-terminus", {})
    if sn.get("plp") or sn.get("vus"):
        o.append(_t(24, 140, f"P/LP {sn['plp']} · VUS {sn['vus']}", 10.5, SIG["pathogenic"] if sn["plp"] else SIG["uncertain"], 600))
    o.append(f'<path d="M{xs[6]},{y_bot + 20} C{xs[6]},{y_bot + 120} 1040,540 1110,546" fill="none" stroke="#5aa9d6" stroke-width="2.2"/>')
    o.append(_t(1206, 528, "C-terminus", 14, TXT, 700, "end")); o.append(_t(1206, 544, f"{c.start}–{c.end} · {c.length} aa · intracellular", 10.5, MUTED, 400, "end"))
    sc = stats.get("C-terminus", {})
    if sc.get("plp") or sc.get("vus"):
        o.append(_t(1206, 560, f"P/LP {sc['plp']} · VUS {sc['vus']}", 10.5, SIG["pathogenic"] if sc["plp"] else SIG["uncertain"], 600, "end"))
    for i in range(7):
        s = seg[f"TM{i + 1}"]
        am = stats.get(s.name, {}).get("am_mean")
        fill = _mix("#2f8fc4", "#ff2d55", (am - 0.3) / 0.6) if am is not None else "#2f8fc4"
        o.append(f'<rect x="{xs[i] - 26}" y="{y_top - 20}" width="52" height="{y_bot - y_top + 40}" rx="22" fill="{fill}" opacity=".92"><title>{s.name}: residues {s.start}–{s.end}'
                 + (f"; mean AlphaMissense {am:.2f}" if am is not None else "") + "</title></rect>")
        o.append(_t(xs[i], 226, s.name, 14, "#fff", 700, "middle"))
    # per-helix information row, below every loop arc so nothing crosses it
    o.append(_t(24, 612, "helix", 10.5, MUTED, 700)); o.append(_t(24, 628, "residues", 10, MUTED)); o.append(_t(24, 643, "length", 10, MUTED)); o.append(_t(24, 658, "variants", 10, MUTED)); o.append(_t(24, 673, "mean AM", 10, MUTED))
    for i in range(7):
        s = seg[f"TM{i + 1}"]
        st = stats.get(s.name, {})
        o.append(f'<line x1="{xs[i]}" y1="{y_bot + 20}" x2="{xs[i]}" y2="598" stroke="#1c3a5c" stroke-dasharray="2 4"/>')
        o.append(_t(xs[i], 612, s.name, 12, TXT, 700, "middle"))
        o.append(_t(xs[i], 628, f"{s.start}–{s.end}", 10.5, MUTED, 400, "middle"))
        o.append(_t(xs[i], 643, f"{s.length} aa", 10, MUTED, 400, "middle"))
        o.append(_t(xs[i], 658, f"P/LP {st.get('plp', 0)} · VUS {st.get('vus', 0)}", 10.5, SIG["pathogenic"] if st.get("plp") else SIG["uncertain"] if st.get("vus") else MUTED, 600, "middle"))
        o.append(_t(xs[i], 673, "n/a" if st.get("am_mean") is None else f"{st['am_mean']:.2f}", 10, "#9ccbe6", 400, "middle"))
    placed = 0
    pos_xy = {}
    for v in sorted(b.variants, key=lambda v: (v.significance not in ("pathogenic", "likely pathogenic"), v.pos or 0)):
        if v.pos is None or placed >= 90:
            continue
        for i in range(7):
            s = seg[f"TM{i + 1}"]
            if s.contains(v.pos):
                frac = (v.pos - s.start) / max(1, s.end - s.start)
                y = (y_top - 8 + frac * (y_bot - y_top + 16)) if i % 2 == 0 else (y_bot + 8 - frac * (y_bot - y_top + 16))
                x = xs[i] + (((v.pos * 7) % 13) - 6)
                col = SIG.get(v.significance, "#9ab")
                o.append(f'<circle cx="{x}" cy="{y:.1f}" r="4.6" fill="{col}" stroke="#020617" stroke-width="1"><title>{E(v.name[-48:])}: {v.significance}, residue {v.pos} ({s.name})</title></circle>')
                placed += 1
                break
    # conserved motifs: a compact tag in the gap to the right of the helix that carries it
    for m in motifs:
        tm = "TM3" if m["where"].startswith("TM3") else "TM6" if m["where"] == "TM6" else "TM7"
        i = int(tm[2]) - 1
        s = seg[tm]
        frac = max(0, min(1, (((m["start"] + m["end"]) / 2) - s.start) / max(1, s.end - s.start)))
        y = (y_top + frac * (y_bot - y_top)) if i % 2 == 0 else (y_bot - frac * (y_bot - y_top))
        bx = xs[i] + 34
        short = m["motif"].split(" (")[0]
        o.append(f'<line x1="{xs[i] + 26}" y1="{y:.0f}" x2="{bx}" y2="{y:.0f}" stroke="#a78bfa" stroke-width="1.2"/>')
        o.append(f'<rect x="{bx}" y="{y - 16:.0f}" width="88" height="32" rx="7" fill="#1b1040" stroke="#a78bfa"/>')
        o.append(_t(bx + 44, y - 3, short, 10.5, "#d8ccff", 700, "middle"))
        o.append(_t(bx + 44, y + 11, f"{m['start']}–{m['end']} {m['seq']}", 9.5, "#b9a8f5", 400, "middle"))
    if selected is not None and selected.pos:
        tgt = segment_of(segs, selected.pos)
        s = seg.get(tgt)
        if s is not None:
            if s.kind == "TM":
                i = int(tgt[2:]) - 1
                frac = (selected.pos - s.start) / max(1, s.end - s.start)
                y = (y_top - 8 + frac * (y_bot - y_top + 16)) if i % 2 == 0 else (y_bot + 8 - frac * (y_bot - y_top + 16))
                x = xs[i] + (((selected.pos * 7) % 13) - 6)
            else:
                x = 110 if tgt == "N-terminus" else 1110 if tgt == "C-terminus" else (xs[loop_names.index(tgt)] + xs[loop_names.index(tgt) + 1]) / 2
                y = 128 if tgt == "N-terminus" else 546 if tgt == "C-terminus" else (y_top - 20 - (38 + min(86, s.length * 1.1))) if tgt.startswith("ECL") else (y_bot + 20 + (38 + min(86, s.length * 1.1)))
            lab = f"selected: residue {selected.pos} · {tgt} · {selected.significance}"
            lw = 7.2 * len(lab) + 24
            lx = max(10, min(W - lw - 10, x - lw / 2))
            o.append(f'<line x1="{x:.1f}" y1="{y - 11:.1f}" x2="{x:.1f}" y2="96" stroke="#fff" stroke-width="1" stroke-dasharray="3 3"/>')
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="none" stroke="#fff" stroke-width="2.2"/>')
            o.append(f'<rect x="{lx:.1f}" y="70" width="{lw:.1f}" height="26" rx="8" fill="#fff" opacity=".96"/>')
            o.append(_t(lx + lw / 2, 87, lab, 12, "#020617", 700, "middle"))
    lx = 24
    for lab, col in (("pathogenic", SIG["pathogenic"]), ("likely pathogenic", SIG["likely pathogenic"]), ("uncertain (VUS)", SIG["uncertain"])):
        o.append(f'<circle cx="{lx + 5}" cy="692" r="5" fill="{col}"/>')
        o.append(_t(lx + 16, 696, lab, 11, MUTED))
        lx += 26 + len(lab) * 6.3
    o.append(f'<rect x="{lx + 8}" y="684" width="34" height="14" rx="5" fill="#1b1040" stroke="#a78bfa"/>')
    o.append(_t(lx + 50, 696, "conserved class A motif found in this sequence", 11, MUTED))
    o.append(_t(lx + 330, 696, "helix colour: mean AlphaMissense", 11, MUTED))
    o.append(f'<defs><linearGradient id="amg"><stop offset="0" stop-color="#2f8fc4"/><stop offset="1" stop-color="#ff2d55"/></linearGradient></defs><rect x="{lx + 520}" y="686" width="70" height="10" rx="4" fill="url(#amg)"/>')
    o.append(_t(lx + 596, 696, "low → high", 11, MUTED))
    return _frame(W, H, "".join(o), f"Transmembrane topology of {b.gene}")


# ═══════════════════════════════════════════════════════════════ architecture
def architecture_svg(b: Bundle, selected: Optional[Variant] = None, width: int = 1180) -> str:
    L = max(b.length, 1)
    x0, x1 = 150, width - 40
    X = lambda p: x0 + (x1 - x0) * (p - 1) / max(1, L - 1)
    H = 440
    o = [_t(24, 32, f"{b.gene} · residue-scaled map", 17, TXT, 700),
         _t(24, 52, f"UniProt {b.uid} · {L} residues · domains and sites from UniProt · variants from ClinVar · strips: AlphaMissense (max per residue) and AlphaFold pLDDT", 11, MUTED)]
    # hotspots
    for h in b.hotspots:
        o.append(f'<rect x="{X(h.start):.1f}" y="76" width="{max(4, X(h.end) - X(h.start)):.1f}" height="16" rx="4" fill="#f59e0b"><title>hotspot {h.start}–{h.end}: {h.count} variants, {h.fold:.1f}x enriched</title></rect>')
        if X(h.end) - X(h.start) > 30:
            o.append(_t((X(h.start) + X(h.end)) / 2, 88, f"{h.count} · {h.fold:.1f}x", 9.5, "#1a1000", 700, "middle"))
    o.append(_t(24, 88, "hotspots", 10.5, "#f59e0b", 600))
    # variant lollipops
    by_pos: Dict[int, List[Variant]] = {}
    for v in b.variants:
        if v.pos:
            by_pos.setdefault(v.pos, []).append(v)
    base = 250
    top_pos = sorted(by_pos, key=lambda p: -sum(v.is_plp for v in by_pos[p]))[:6]
    for p, vs in by_pos.items():
        n_plp = sum(v.is_plp for v in vs)
        sev = "pathogenic" if any(v.significance == "pathogenic" for v in vs) else "likely pathogenic" if n_plp else vs[0].significance
        h = 14 + 16 * min(5, len(vs))
        col = SIG.get(sev, "#9ab")
        o.append(f'<line x1="{X(p):.1f}" y1="{base}" x2="{X(p):.1f}" y2="{base - h}" stroke="{col}" stroke-width="1.3" opacity=".85"/>')
        o.append(f'<circle cx="{X(p):.1f}" cy="{base - h}" r="{3.2 + min(3, len(vs) - 1)}" fill="{col}"><title>residue {p}: {len(vs)} variant(s), {n_plp} P/LP</title></circle>')
    last_x = -99
    for p in sorted(top_pos):
        if sum(v.is_plp for v in by_pos[p]) >= 1 and X(p) - last_x > 24:
            h = 14 + 16 * min(5, len(by_pos[p]))
            o.append(_t(X(p), base - h - 9, str(p), 10, TXT, 600, "middle"))
            last_x = X(p)
    o.append(_t(24, 130, "variants", 10.5, MUTED, 600))
    o.append(f'<line x1="{x0}" y1="{base}" x2="{x1}" y2="{base}" stroke="#2a4a6a"/>')
    # ruler
    step = 50 if L <= 600 else 100 if L <= 1500 else 250
    p = 0
    while p <= L:
        if p >= 1:
            o.append(f'<line x1="{X(p):.1f}" y1="{base}" x2="{X(p):.1f}" y2="{base + 6}" stroke="#2a4a6a"/>')
            o.append(_t(X(p), base + 20, str(p), 10, MUTED, 400, "middle"))
        p += step
    # domains
    dom_y = base + 36
    palette = ["#38bdf8", "#818cf8", "#2dd4bf", "#c084fc", "#60a5fa"]
    rows: List[float] = []
    for i, d in enumerate(sorted([d for d in b.domains if d["type"] != "Transmembrane"], key=lambda d: d["start"])[:12]):
        row = 0
        while row < len(rows) and rows[row] > X(d["start"]) - 4:
            row += 1
        if row == len(rows):
            rows.append(0)
        rows[row] = X(d["end"])
        y = dom_y + row * 24
        o.append(f'<rect x="{X(d["start"]):.1f}" y="{y}" width="{max(4, X(d["end"]) - X(d["start"])):.1f}" height="18" rx="5" fill="{palette[i % 5]}" opacity=".8"><title>{E(d["type"])}: {E(d["desc"])} {d["start"]}–{d["end"]}</title></rect>')
        lab = f'{d["desc"] or d["type"]} {d["start"]}–{d["end"]}'
        if X(d["end"]) - X(d["start"]) > len(lab) * 5.6:
            o.append(_t(X(d["start"]) + 5, y + 13, lab, 10, "#020617", 700))
        else:
            o.append(_t(X(d["end"]) + 5, y + 13, lab, 10, TXT))
    tm = [d for d in b.domains if d["type"] == "Transmembrane"]
    for d in tm:
        o.append(f'<rect x="{X(d["start"]):.1f}" y="{base + 28}" width="{max(3, X(d["end"]) - X(d["start"])):.1f}" height="5" rx="2" fill="#a78bfa"><title>{E(d["desc"])} {d["start"]}–{d["end"]}</title></rect>')
    sy = dom_y + max(1, len(rows)) * 24 + 6
    for s in b.sites[:20]:
        o.append(f'<rect x="{X(s["start"]):.1f}" y="{sy}" width="{max(3, X(s["end"]) - X(s["start"])):.1f}" height="8" rx="2" fill="#34d399"><title>{E(s["type"])} {E(s["desc"])} {s["start"]}–{s["end"]}</title></rect>')
    o.append(_t(24, sy + 8, "sites", 10.5, "#34d399", 600))
    # AlphaMissense strip and pLDDT strip
    ay = sy + 22
    o.append(_t(24, ay + 11, "AlphaMissense", 10.5, MUTED, 600))
    if b.am:
        nb = min(L, 220)
        for k in range(nb):
            lo, hi = int(k * L / nb) + 1, int((k + 1) * L / nb)
            vals = [max(d["score"] for d in b.am[p].values()) for p in range(lo, hi + 1) if p in b.am and b.am[p]]
            if vals:
                o.append(f'<rect x="{X(lo):.1f}" y="{ay}" width="{(x1 - x0) / nb + .6:.1f}" height="14" fill="{_mix("#12304f", "#ff2d55", (sum(vals) / len(vals) - .2) / .7)}"/>')
    else:
        o.append(_t(x0, ay + 11, "no AlphaMissense data", 10, MUTED))
    py = ay + 22
    o.append(_t(24, py + 11, "AlphaFold pLDDT", 10.5, MUTED, 600))
    pl = {}
    for line in (b.pdb or "").splitlines():
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            try:
                pl[int(line[22:26])] = float(line[60:66])
            except ValueError:
                pass
    if pl:
        nb = min(L, 220)
        for k in range(nb):
            lo, hi = int(k * L / nb) + 1, int((k + 1) * L / nb)
            vals = [pl[p] for p in range(lo, hi + 1) if p in pl]
            if vals:
                m = sum(vals) / len(vals)
                o.append(f'<rect x="{X(lo):.1f}" y="{py}" width="{(x1 - x0) / nb + .6:.1f}" height="14" fill="{"#1565C0" if m >= 90 else "#29B6F6" if m >= 70 else "#FDD835" if m >= 50 else "#FF7043"}"/>')
    else:
        o.append(_t(x0, py + 11, "no structure loaded", 10, MUTED))
    # selected variant
    if selected is not None and selected.pos:
        o.append(f'<line x1="{X(selected.pos):.1f}" y1="100" x2="{X(selected.pos):.1f}" y2="{py + 14}" stroke="#fff" stroke-width="1.4" stroke-dasharray="4 3"/>')
        o.append(f'<rect x="{max(20, min(width - 270, X(selected.pos) - 125)):.1f}" y="98" width="250" height="22" rx="7" fill="#fff"/>')
        o.append(_t(max(20, min(width - 270, X(selected.pos) - 125)) + 125, 113, f"selected: residue {selected.pos} · {selected.significance}", 11.5, "#020617", 700, "middle"))
    # legend
    ly = H - 18
    lx = 24
    for lab, col in (("pathogenic", SIG["pathogenic"]), ("likely pathogenic", SIG["likely pathogenic"]), ("VUS", SIG["uncertain"])):
        o.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{col}"/>')
        o.append(_t(lx + 16, ly, lab, 11, MUTED))
        lx += 24 + len(lab) * 6.4
    o.append(_t(lx + 10, ly, "stem height = number of variants at that residue · pLDDT: >=90 dark blue, 70–90 light blue, 50–70 yellow, <50 orange", 11, MUTED))
    return _frame(width, H, "".join(o), f"Residue-scaled map of {b.gene}")


# ═══════════════════════════════════════════════════════════════ signalling animation
PATHWAYS = {
    "Gs": {"title": "Gαs (GNAS)", "color": "#34d399", "readout": "cAMP up",
           "boxes": [("Adenylyl cyclase", "ADCY1–9"), ("ATP → cAMP", "second messenger"), ("PKA", "PRKACA · PRKACB"), ("CREB p-Ser133 → CRE targets", "CREB1")],
           "note": "cAMP–PKA signalling restrains YAP through LATS in many cells (Yu 2012, Cell 150:780)."},
    "Gi": {"title": "Gαi/o (GNAI1–3, GNAO1)", "color": "#fbbf24", "readout": "cAMP down",
           "boxes": [("Adenylyl cyclase inhibited", "ADCY5 · ADCY6: less cAMP"), ("Gβγ → GIRK channels", "KCNJ3 · KCNJ6"), ("Gβγ → PI3Kγ → AKT", "PIK3CG"), ("Gβγ → MAPK / ERK", "via Ras and PI3K")],
           "note": "Gi/o-coupled lipid receptors (LPA, S1P) can activate YAP (Yu 2012, Cell 150:780)."},
    "Gq": {"title": "Gαq/11 (GNAQ, GNA11)", "color": "#38bdf8", "readout": "Ca2+ up",
           "boxes": [("Phospholipase C-β", "PLCB1–4"), ("PIP₂ → IP₃ + DAG", "membrane lipid cleavage"), ("IP₃ → IP₃R → ER Ca²⁺ release", "ITPR1–3"), ("DAG + Ca²⁺ → PKC", "PRKCA · PRKCB")],
           "note": "Gαq/11 also signals through Trio–RhoA to activate YAP (Feng 2014, Cancer Cell 25:831)."},
    "G12": {"title": "Gα12/13 (GNA12, GNA13)", "color": "#f472b6", "readout": "RhoA up",
            "boxes": [("RhoGEFs", "ARHGEF1 · ARHGEF11 · ARHGEF12"), ("RhoA·GTP", "RHOA"), ("ROCK → actomyosin", "ROCK1 · ROCK2"), ("YAP/TAZ activation", "LATS inhibition")],
            "note": "Gα12/13 signalling through RhoA activates YAP/TAZ (Yu 2012, Cell 150:780)."},
}
ASSAYS = {  # per coupling class: (second messenger readout, pathway reporter)
    "Gs": ("cAMP: GloSensor luminescence or HTRF", "CRE-luciferase reporter"),
    "Gi": ("forskolin-stimulated cAMP decrease", "CRE reporter (forskolin) decrease"),
    "Gq": ("IP1 accumulation (HTRF) or Ca²⁺ (Fluo-4 / FLIPR)", "NFAT-RE or SRE-luciferase"),
    "G12": ("RhoA activity (G-LISA or FRET sensor)", "SRE or TEAD-luciferase"),
    "": ("class-specific: cAMP, IP1/Ca²⁺ or RhoA", "CRE, NFAT-RE, SRE or TEAD reporter"),
}
CYCLE = 14
ANIM_CSS = """
@keyframes s1{0%,19.9%{opacity:1}20%,100%{opacity:.3}}
@keyframes s2{0%,19.9%{opacity:.3}20%,39.9%{opacity:1}40%,100%{opacity:.3}}
@keyframes s3{0%,39.9%{opacity:.3}40%,59.9%{opacity:1}60%,100%{opacity:.3}}
@keyframes s4{0%,59.9%{opacity:.3}60%,79.9%{opacity:1}80%,100%{opacity:.3}}
@keyframes s5{0%,79.9%{opacity:.3}80%,100%{opacity:1}}
@keyframes s34{0%,39.9%{opacity:.3}40%,79.9%{opacity:1}80%,100%{opacity:.3}}
@keyframes lig{0%{transform:translate(0,-135px)}18%,99%{transform:translate(0,0)}100%{transform:translate(0,-135px)}}
@keyframes tm6{0%,19%{transform:rotate(0deg)}38%,99%{transform:rotate(13deg)}100%{transform:rotate(0deg)}}
@keyframes cleft{0%,19%{opacity:0}38%,99%{opacity:1}100%{opacity:0}}
@keyframes gdp{0%,39%{transform:translate(0,0);opacity:1}50%{transform:translate(-46px,-64px);opacity:0}99%{opacity:0}100%{transform:translate(0,0);opacity:1}}
@keyframes gtp{0%,49%{transform:translate(50px,-64px);opacity:0}60%,99%{transform:translate(0,0);opacity:1}100%{transform:translate(50px,-64px);opacity:0}}
@keyframes galpha{0%,69%{transform:translate(0,0)}82%,99%{transform:translate(168px,-78px)}100%{transform:translate(0,0)}}
@keyframes gbg{0%,69%{transform:translate(0,0)}82%,99%{transform:translate(96px,70px)}100%{transform:translate(0,0)}}
@keyframes dash{to{stroke-dashoffset:-24}}
@keyframes eff1{0%,71%{opacity:.4}78%,99%{opacity:1}100%{opacity:.4}}
@keyframes eff2{0%,77%{opacity:.4}84%,99%{opacity:1}100%{opacity:.4}}
@keyframes eff3{0%,83%{opacity:.4}90%,99%{opacity:1}100%{opacity:.4}}
@keyframes eff4{0%,89%{opacity:.4}95%,99%{opacity:1}100%{opacity:.4}}
@keyframes mess{0%,79%{transform:translateY(0);opacity:0}84%{opacity:1}99%{transform:translateY(190px);opacity:0}100%{opacity:0}}
.s1{animation:s1 %ss infinite}.s2{animation:s2 %ss infinite}.s3{animation:s3 %ss infinite}.s4{animation:s4 %ss infinite}.s5{animation:s5 %ss infinite}.s34{animation:s34 %ss infinite}
.lig{animation:lig %ss ease-in-out infinite}.tm6{animation:tm6 %ss ease-in-out infinite}.cleft{animation:cleft %ss infinite}
.gdp{animation:gdp %ss ease-in infinite}.gtp{animation:gtp %ss ease-out infinite}.galpha{animation:galpha %ss ease-in-out infinite}.gbg{animation:gbg %ss ease-in-out infinite}
.flow{stroke-dasharray:6 6;animation:dash 1s linear infinite}
.e1{animation:eff1 %ss infinite}.e2{animation:eff2 %ss infinite}.e3{animation:eff3 %ss infinite}.e4{animation:eff4 %ss infinite}.mess{animation:mess %ss linear infinite}
""".replace("%s", str(CYCLE))
STEPS = ["Ligand binds the orthosteric pocket", "TM6 swings out and the cytoplasmic cleft opens", "Gα engages (α5 helix inserts) and GDP is released", "GTP binds; Gα·GTP and Gβγ dissociate", "Effectors act; messengers and readouts appear"]


def _panel(x, y, w, h, title, sub="") -> str:
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{PANEL}" stroke="{LINE}"/>' + _t(x + 16, y + 26, title, 12.5, ACC, 700, extra='letter-spacing="1.1"')
            + (_t(x + 16, y + 43, sub, 10.5, MUTED) if sub else ""))


def signalling_svg(b: Bundle, segs: Optional[List[Segment]], motifs: List[dict], stats: Dict[str, dict], *, coupling: str = "", coupling_source: str = "", status: str = "unknown",
                   ligand_lines: Optional[List[str]] = None, hypothesis: Optional[dict] = None, signal: str = "", context: str = "", first_assay: str = "") -> str:
    W, H = 1300, 860
    o: List[str] = []
    key = coupling if coupling in PATHWAYS else ""
    pw = PATHWAYS.get(key)
    cls_label = {"Gs": "Gs", "Gi": "Gi/o", "Gq": "Gq/11", "G12": "G12/13", "": "not established"}[key]
    col = pw["color"] if pw else "#94a3b8"
    ttl = f"{b.gene} · {b.name}"
    o.append(_t(24, 34, ttl if len(ttl) <= 38 else ttl[:37] + "…", 18, TXT, 700))
    stat_txt = {"orphan": "ORPHAN (no confirmed ligand in the registry)", "characterised": "characterised (not an orphan in the registry)", "unknown": "registry status unknown"}.get(status, status)
    o.append(_t(24, 55, f"UniProt {b.uid} · {b.length} aa · {stat_txt}", 11.5, "#fbbf24" if status == "orphan" else MUTED, 600 if status == "orphan" else 400))
    o.append(_t(24, 74, f"G-protein coupling: {cls_label}" + (f" ({coupling_source})" if coupling_source else ""), 11.5, col, 600))
    if context or signal:
        o.append(_t(24, 93, "In your data: " + " · ".join(x for x in (context and f"context {context}", signal) if x), 11.5, MUTED))
    for k in range(5):
        px = 500 + k * 156
        o.append(f'<g class="s{k + 1}"><rect x="{px}" y="16" width="148" height="76" rx="10" fill="#0b1b34" stroke="{ACC}"/>' + _t(px + 12, 34, f"STEP {k + 1}", 10, ACC, 700, extra='letter-spacing="1"')
                 + "".join(_t(px + 12, 50 + 13 * j, ln, 10.5, TXT) for j, ln in enumerate(_wrap(STEPS[k], 24)[:3])) + "</g>")
    # ── panel 1: receptor
    o.append(_panel(20, 108, 460, 500, "1 · RECEPTOR", "seven annotated helices; motifs found in the sequence"))
    xs = [78 + i * 60 for i in range(7)]
    yt, yb = 262, 418
    seg = {s.name: s for s in segs} if segs else {}
    o.append(f'<rect x="36" y="{yt + 20}" width="428" height="{yb - yt - 40}" rx="14" fill="#10264a" opacity=".6"/>')
    o.append(_t(44, yt + 36, "membrane", 9.5, "#5f86ad", 400, extra='font-style="italic"'))
    for i, nm in enumerate(["ICL1", "ECL1", "ICL2", "ECL2", "ICL3", "ECL3"]):
        up = nm.startswith("ECL")
        x1, x2 = xs[i], xs[i + 1]
        y0 = yt - 8 if up else yb + 8
        yc = y0 - 28 if up else y0 + 28
        o.append(f'<path d="M{x1},{y0} C{x1},{yc} {x2},{yc} {x2},{y0}" fill="none" stroke="#5aa9d6" stroke-width="2"/>')
        o.append(_t((x1 + x2) / 2, yc - 6 if up else yc + 14, nm, 10, MUTED, 600, "middle"))
        if nm in seg:
            o.append(_t((x1 + x2) / 2, yc - 18 if up else yc + 26, f"{seg[nm].start}–{seg[nm].end}", 9, "#4d7194", 400, "middle"))
    o.append(f'<path d="M{xs[0]},{yt - 8} C{xs[0]},{yt - 44} 52,{yt - 48} 46,{yt - 66}" fill="none" stroke="#5aa9d6" stroke-width="2"/>')
    o.append(_t(36, yt - 74, "N-term" + (f" 1–{seg['N-terminus'].end}" if "N-terminus" in seg else ""), 10, MUTED, 600))
    o.append(f'<path d="M{xs[6]},{yb + 8} C{xs[6]},{yb + 30} 452,{yb + 30} 460,{yb + 44}" fill="none" stroke="#5aa9d6" stroke-width="2"/>')
    o.append(_t(472, yb + 62, "C-term" + (f" {seg['C-terminus'].start}–{seg['C-terminus'].end}" if "C-terminus" in seg else ""), 9.5, MUTED, 600, "end"))
    o.append(f'<rect x="{xs[2] - 24}" y="{yt + 28}" width="{xs[6] - xs[2] + 48}" height="{yb - yt - 56}" rx="12" fill="none" stroke="#a78bfa" stroke-dasharray="5 4" opacity=".75"/>')
    for i in range(7):
        if i == 5:
            continue
        o.append(f'<rect x="{xs[i] - 14}" y="{yt}" width="28" height="{yb - yt}" rx="12" fill="#2f8fc4" opacity=".92"/>')
    o.append(f'<g transform="translate({xs[5]},{yt})"><g class="tm6"><rect x="-14" y="0" width="28" height="{yb - yt}" rx="12" fill="#f59e0b" opacity=".95"/></g></g>')
    for i in range(7):
        o.append(_t(xs[i], yt + 78, f"TM{i + 1}", 11, "#fff", 700, "middle"))
        if f"TM{i + 1}" in seg:
            o.append(_t(xs[i], yt + 92, f"{seg[f'TM{i + 1}'].start}–{seg[f'TM{i + 1}'].end}", 8.5, "#e6f2ff", 400, "middle"))
    o.append(f'<ellipse class="cleft" cx="{(xs[2] + xs[5]) / 2:.0f}" cy="{yb + 2}" rx="{(xs[5] - xs[2]) / 2 + 6:.0f}" ry="10" fill="none" stroke="#f59e0b" stroke-width="2" stroke-dasharray="4 3"/>')
    lx, ly = (xs[2] + xs[5]) / 2 + 6, yt + 40
    o.append(f'<g transform="translate({lx:.0f},{ly})"><g class="lig"><circle r="15" fill="#a78bfa" stroke="#e9ddff" stroke-width="1.5"/>' + _t(0, 5, "L", 14, "#1b1040", 800, "middle") + "</g></g>")
    lab = {"orphan": "ligand: unknown (orphan)", "characterised": "ligand: known (see below)", "unknown": "ligand: not specified"}.get(status, "ligand")
    o.append(f'<g class="s1">{_t(lx, yt - 70, "① " + lab, 10.5, "#c4b5fd", 700, "middle")}</g>')
    o.append(f'<g class="s2">{_t(xs[5] + 20, yt - 6, "② TM6 swings out", 10, "#f59e0b", 700, "start")}</g>')
    row_y = yb + 80
    for k, m in enumerate(motifs[:3]):
        i = int(("TM3" if m["where"].startswith("TM3") else "TM6" if m["where"] == "TM6" else "TM7")[2]) - 1
        tx = 40 + k * 146
        short = m["motif"].split(" (")[0]
        o.append(f'<polyline points="{xs[i]},{yb + 10} {xs[i]},{yb + 70} {tx + 66},{yb + 70} {tx + 66},{row_y}" fill="none" stroke="#a78bfa" stroke-width="1" stroke-dasharray="2 3"/>')
        o.append(f'<rect x="{tx}" y="{row_y}" width="132" height="30" rx="7" fill="#1b1040" stroke="#a78bfa"/>')
        o.append(_t(tx + 66, row_y + 12, short, 10, "#d8ccff", 700, "middle"))
        o.append(_t(tx + 66, row_y + 24, f"residues {m['start']}–{m['end']} ({m['seq']})", 8.5, "#b9a8f5", 400, "middle"))
    if not segs:
        o.append(_t(250, 300, "helix boundaries are not annotated in UniProt for this protein", 10.5, "#fbbf24", 400, "middle"))
    plp = sum(v.is_plp for v in b.variants)
    top = sorted(((n, d["plp"]) for n, d in stats.items() if d["plp"]), key=lambda x: -x[1])[:4]
    dl = ["dashed purple box: typical class A orthosteric pocket (TM3, 5, 6, 7)", f"ClinVar: {plp} pathogenic / likely pathogenic variants" + (" · most in " + ", ".join(f"{n} {c}" for n, c in top) if top else "")] + list(ligand_lines or [])
    yy = row_y + 46
    for n_, ln in enumerate(dl[:5]):
        for sub in _wrap(ln, 72)[:2]:
            o.append(_t(36, yy, sub, 10, "#9ccbe6" if n_ == 1 else MUTED))
            yy += 13
    # ── panel 2: G-protein cycle
    o.append(_panel(500, 108, 360, 500, "2 · G-PROTEIN CYCLE", f"{cls_label} heterotrimer" if pw else "heterotrimer (class not established)"))
    gname = {"Gs": "Gαs", "Gi": "Gαi/o", "Gq": "Gαq/11", "G12": "Gα12/13", "": "Gα"}[key]
    o.append(f'<rect x="522" y="306" width="64" height="34" rx="9" fill="#2f8fc4"/>' + _t(554, 327, "R*", 13, "#fff", 700, "middle") + _t(554, 356, "active receptor", 9.5, MUTED, 400, "middle") + '<path d="M524,340 L584,340" stroke="#f59e0b" stroke-width="3"/>')
    o.append(f'<g class="s3"><circle cx="640" cy="250" r="12" fill="#475569"/>{_t(640, 253.5, "GDP", 8.5, "#fff", 700, "middle")}{_t(640, 232, "GDP", 9.5, "#94a3b8", 600, "middle")}</g>')
    o.append(f'<g transform="translate(640,250)"><g class="gdp"><circle r="12" fill="#ef4444"/>{_t(0, 3.5, "GDP", 8.5, "#fff", 700, "middle")}</g></g>')
    o.append(f'<g transform="translate(640,250)"><g class="gtp"><circle r="12" fill="#22c55e"/>{_t(0, 3.5, "GTP", 8.5, "#fff", 700, "middle")}</g></g>')
    o.append(f'<g transform="translate(646,336)"><g class="galpha"><circle r="46" fill="#1d4e89" stroke="{col}" stroke-width="2.5"/>{_t(0, -2, gname, 16, "#fff", 700, "middle")}{_t(0, 15, "α5 helix → R*", 8.5, "#bcd7f0", 400, "middle")}</g></g>')
    o.append(f'<g transform="translate(730,396)"><g class="gbg"><circle r="27" fill="#4338ca" stroke="#a5b4fc"/>{_t(0, 4, "Gβ", 12, "#fff", 700, "middle")}<circle cx="38" cy="-14" r="14" fill="#6d28d9" stroke="#c4b5fd"/>{_t(38, -10, "Gγ", 9.5, "#fff", 700, "middle")}</g></g>')
    o.append(f'<g class="s4">{_t(730, 442, "Gβγ effectors: GIRK (KCNJ3), PI3Kγ (PIK3CG),", 9, "#a5b4fc", 400, "middle")}{_t(730, 454, "PLCβ2/3, ADCY2/4/7", 9, "#a5b4fc", 400, "middle")}</g>')
    # nucleotide-state timeline
    o.append(_t(520, 466, "Gα nucleotide state", 10, MUTED, 700))
    for k, (lab_, c_, cl) in enumerate((("GDP · inactive", "#475569", "s1"), ("empty", "#7c3aed", "s3"), ("GTP · active", "#16a34a", "s4"))):
        o.append(f'<g class="{cl}"><rect x="{520 + k * 108}" y="472" width="104" height="22" rx="6" fill="{c_}"/>{_t(520 + k * 108 + 52, 487, lab_, 9, "#fff", 600, "middle")}</g>')
    for k, sline in enumerate(["① engagement: Gα α5 helix inserts into the cleft opened by TM6 (β2AR–Gs, Rasmussen 2011, Nature 477:549)", "② GDP leaves; ③ cytosolic GTP binds", "④ Gα·GTP and Gβγ dissociate; each regulates effectors"]):
        cls = ("s2", "s3", "s4")[k]
        o.append(f'<g class="{cls}">' + "".join(_t(520, 514 + k * 24 + 11 * j, ln, 9.5, TXT) for j, ln in enumerate(_wrap(sline, 66)[:2])) + "</g>")
    for j, ln in enumerate(_wrap("Termination: RGS proteins speed GTP hydrolysis; GRKs phosphorylate the receptor tail and β-arrestin binds, desensitising the receptor.", 78)[:2]):
        o.append(_t(520, 586 + 11 * j, ln, 8.5, "#7d9bb5"))
    # ── panel 3: effectors
    o.append(_panel(880, 108, 400, 500, "3 · EFFECTORS AND SECOND MESSENGERS", (pw["title"] + " pathway") if pw else "coupling not established: candidate branches"))
    if pw:
        for k, (nm, genes) in enumerate(pw["boxes"]):
            y = 168 + k * 84
            o.append(f'<g class="e{k + 1}"><rect x="902" y="{y}" width="356" height="56" rx="11" fill="#0b1b34" stroke="{col}" stroke-width="1.6"/>' + _t(920, y + 24, nm, 13, TXT, 700) + _t(920, y + 43, genes, 10.5, MUTED) + "</g>")
            if k < 3:
                o.append(f'<line class="flow" x1="1080" y1="{y + 56}" x2="1080" y2="{y + 84}" stroke="{col}" stroke-width="2"/>')
                o.append(f'<path d="M1074,{y + 76} L1080,{y + 84} L1086,{y + 76}" fill="none" stroke="{col}" stroke-width="2"/>')
        for k in range(3):
            o.append(f'<circle class="mess" cx="{1236 - k * 14}" cy="176" r="4.5" fill="{col}" style="animation-delay:{k * 0.9}s"/>')
        for j, ln in enumerate(_wrap(pw["note"], 62)[:3]):
            o.append(_t(902, 528 + 12 * j, ln, 9.5, "#8fb0c8"))
    else:
        for k, kk in enumerate(("Gs", "Gi", "Gq", "G12")):
            p = PATHWAYS[kk]
            y = 168 + k * 84
            o.append(f'<g class="e{k + 1}"><rect x="902" y="{y}" width="356" height="62" rx="11" fill="#0b1b34" stroke="{p["color"]}" stroke-width="1.4" stroke-dasharray="5 4"/>' + _t(920, y + 24, p["title"], 13, p["color"], 700)
                     + _t(920, y + 44, " → ".join(x for x, _ in p["boxes"][:2]) + f": {p['readout']}", 10.5, MUTED) + "</g>")
        for j, ln in enumerate(_wrap("No recorded or predicted coupling. A G-protein panel (TRUPATH or TGF-α shedding) is the first experiment that resolves which branch applies.", 62)[:3]):
            o.append(_t(902, 528 + 13 * j, ln, 10, "#fbbf24"))
    # ── readouts
    o.append(_panel(20, 622, 1260, 228, "READOUTS: which assay measures which step", ""))
    sm, rep = ASSAYS[key]
    chips = [("s1", "① Ligand binding", ["NanoBRET tracer or radioligand binding", "needs a known ligand" if status != "orphan" else "no ligand yet: use a surrogate agonist or a constitutive-activity assay"]),
             ("s34", "③④ G-protein activation", ["TRUPATH BRET (Olsen 2020, Nat Chem Biol 16:841)", "NanoBiT-G (Inoue 2019, Cell 177:1933)", "TGF-α shedding (Inoue 2012, Nat Methods 9:1021)"]),
             ("s5", "⑤ Second messenger", [sm, f"expected: {pw['readout']}" if pw else "direction depends on the coupling class"]),
             ("s5", "⑤ Pathway reporter", [rep, "hours; integrates the whole branch"]),
             ("s2", "②–⑤ β-arrestin, trafficking", ["PRESTO-Tango (Kroeze 2015, NSMB 22:362)", "or β-arrestin recruitment BRET", "termination: GRK phosphorylation, then arrestin"])]
    for k, (cls, title, lines) in enumerate(chips):
        x = 38 + k * 248
        wrapped = [w for l in lines for w in _wrap(l, 38)][:6]
        o.append(f'<g class="{cls}"><rect x="{x}" y="660" width="236" height="104" rx="11" fill="#0b1b34" stroke="{ACC}"/>' + _t(x + 12, 682, title, 12.5, TXT, 700)
                 + "".join(_t(x + 12, 700 + 13 * j, ln, 10, MUTED) for j, ln in enumerate(wrapped)) + "</g>")
    fa = first_assay or ("a G-protein panel (TRUPATH or TGF-α shedding) to establish coupling" if not pw else f"{sm}, with empty-vector cells as the control")
    o.append(f'<rect x="38" y="776" width="1224" height="58" rx="10" fill="#08182c" stroke="#f59e0b"/>' + _t(54, 797, "First experiment", 11.5, "#f59e0b", 700))
    for j, ln in enumerate(_wrap(fa + (f" · hypothesis: {hypothesis['statement']} (support {hypothesis['support']:.2f})" if hypothesis else ""), 170)[:2]):
        o.append(_t(54, 815 + 14 * j - 2, ln, 11, TXT))
    return _frame(W, H, "".join(o), f"Annotated signalling animation for {b.gene}", ANIM_CSS)


# ═══════════════════════════════════════════════════════════════ GPCRome visuals
COUP_COL = {"Gs": "#34d399", "Gi": "#fbbf24", "Gq": "#38bdf8", "G12": "#f472b6", "": "#94a3b8"}


def communication_svg(axes, coupling: Optional[Dict[str, str]] = None, limit: int = 10) -> str:
    """Ligand-producing contexts on the left, receptor-bearing contexts on the right, one labelled flowing edge per axis."""
    t = axes.head(limit).reset_index(drop=True)
    if t.empty:
        return ""
    src = list(dict.fromkeys(t["Source context"]))
    tgt = list(dict.fromkeys(t["Target context"]))
    rows = max(len(src), len(tgt))
    H = 150 + rows * 124 + 56
    W = 1200
    ys = {c: 150 + i * 124 + 44 for i, c in enumerate(src)}
    yt = {c: 150 + i * 124 + 44 for i, c in enumerate(tgt)}
    o = [_t(24, 34, "Oncocrine axes: who could be talking to whom", 17, TXT, 700),
         _t(24, 54, "left: contexts whose ligand-producing genes peak · right: contexts whose receptors peak · edge colour = receptor's G-protein class · width = strength (lowest z of the pair)", 11, MUTED),
         _t(40, 100, "LIGAND-PRODUCING CONTEXT", 11, ACC, 700, extra='letter-spacing="1"'), _t(1160, 100, "RECEPTOR-BEARING CONTEXT", 11, ACC, 700, "end", 'letter-spacing="1"')]
    for c in src:
        sub = t[t["Source context"] == c]
        o.append(f'<rect x="40" y="{ys[c] - 40}" width="270" height="88" rx="12" fill="#0b1b34" stroke="{ACC}"/>' + _t(56, ys[c] - 16, c, 14, TXT, 700)
                 + "".join(_t(56, ys[c] + 3 + 13 * j, ln, 10.5, MUTED) for j, ln in enumerate(_wrap("producer genes: " + ", ".join(sorted(set(sub["Producer"]))), 40)[:2]))
                 + _t(56, ys[c] + 36, "z in this context: " + ", ".join(f"{z:.1f}" for z in sorted(set(sub["Source z"]), reverse=True)[:3]), 10, "#6f93b3"))
    for c in tgt:
        sub = t[t["Target context"] == c]
        recs = [f"{r['Receptor']}" + (f" ({r['Receptor coupling']})" if r["Receptor coupling"] else "") for _, r in sub.iterrows()]
        o.append(f'<rect x="890" y="{yt[c] - 40}" width="270" height="88" rx="12" fill="#0b1b34" stroke="{ACC}"/>' + _t(906, yt[c] - 16, c, 14, TXT, 700)
                 + "".join(_t(906, yt[c] + 3 + 13 * j, ln, 10.5, MUTED) for j, ln in enumerate(_wrap("receptors: " + ", ".join(recs), 40)[:2]))
                 + _t(906, yt[c] + 36, "z in this context: " + ", ".join(f"{z:.1f}" for z in sorted(set(sub["Target z"]), reverse=True)[:3]), 10, "#6f93b3"))
    group_n, group_i = {}, {}
    for _, r in t.iterrows():
        group_n[(r["Source context"], r["Target context"])] = group_n.get((r["Source context"], r["Target context"]), 0) + 1
    for k, r in t.iterrows():
        key = (r["Source context"], r["Target context"])
        gi = group_i.get(key, 0)
        group_i[key] = gi + 1
        off = (gi - (group_n[key] - 1) / 2) * 11
        sx, sy, tx, ty = 310, ys[r["Source context"]] + off, 890, yt[r["Target context"]] + off
        cc = COUP_COL.get(r["Receptor coupling"], "#94a3b8")
        w = 1.2 + 1.2 * float(r["Strength"])
        o.append(f'<path d="M{sx},{sy} C{sx + 200},{sy} {tx - 200},{ty} {tx},{ty}" fill="none" stroke="{cc}" stroke-width="{w:.1f}" opacity=".85" class="flow" style="animation-delay:{k * 0.15:.2f}s"><title>{E(r["Ligand"])}: {E(r["Producer"])} in {E(r["Source context"])} → {E(r["Receptor"])} in {E(r["Target context"])}</title></path>')
        o.append(f'<path d="M{tx - 9},{ty - 6} L{tx},{ty} L{tx - 9},{ty + 6}" fill="none" stroke="{cc}" stroke-width="2"/>')
        lab = f"{r['Ligand']} → {r['Receptor']}" + (f" ({r['Receptor coupling']})" if r["Receptor coupling"] else "")
        mx, my = 600, (sy + ty) / 2 + (gi - (group_n[key] - 1) / 2) * 26 + (-10 if group_n[key] == 1 else 0)
        wlab = 6.4 * len(lab) + 18
        o.append(f'<rect x="{mx - wlab / 2:.0f}" y="{my - 11:.0f}" width="{wlab:.0f}" height="22" rx="8" fill="#08182c" stroke="{cc}"/>')
        o.append(_t(mx, my + 4, lab, 10.5, TXT, 600, "middle"))
    lx = 40
    for lab, c in (("Gs", COUP_COL["Gs"]), ("Gi/o", COUP_COL["Gi"]), ("Gq/11", COUP_COL["Gq"]), ("G12/13", COUP_COL["G12"]), ("coupling unknown", COUP_COL[""])):
        o.append(f'<line x1="{lx}" y1="{H - 24}" x2="{lx + 26}" y2="{H - 24}" stroke="{c}" stroke-width="3"/>' + _t(lx + 34, H - 20, lab, 11, MUTED))
        lx += 60 + len(lab) * 6.5
    o.append(_t(W - 24, H - 20, "producer expression stands in for ligand availability; secretion is not measured", 10.5, MUTED, 400, "end"))
    return _frame(W, H, "".join(o), "Oncocrine communication axes", "@keyframes dash{to{stroke-dashoffset:-24}}.flow{stroke-dasharray:7 5;animation:dash 1.1s linear infinite}")


def heatmap_svg(matrix, rows: List[str], status: Dict[str, str], coupling: Dict[str, str], tau: Dict[str, float], limit: int = 45) -> str:
    """Row-scaled expression of GPCRs across contexts, rows grouped by the context in which they peak."""
    import numpy as np
    ctx = list(matrix.columns)
    sub = np.log2(matrix.loc[[r for r in rows if r in matrix.index]].to_numpy(float) + 1.0)
    names = [r for r in rows if r in matrix.index]
    if not len(names):
        return ""
    z = (sub - sub.mean(axis=1, keepdims=True)) / np.where(sub.std(axis=1, keepdims=True) == 0, 1, sub.std(axis=1, keepdims=True))
    order = sorted(range(len(names)), key=lambda i: (int(np.argmax(z[i])), -float(z[i].max())))[:limit]
    cw, rh = 56, 17
    x0, y0 = 200, 190
    W = x0 + cw * len(ctx) + 250
    H = y0 + rh * len(order) + 70
    o = [_t(24, 32, "GPCR expression across contexts", 17, TXT, 700),
         _t(24, 52, "row-scaled log2(expression + 1) · rows grouped by the context where each receptor peaks · amber = orphan · coupling chip: Gs / Gi / Gq / G12", 11, MUTED)]
    for j, c in enumerate(ctx):
        o.append(f'<text transform="translate({x0 + j * cw + cw / 2},{y0 - 8}) rotate(-45)" font-size="11" fill="{TXT}">{E(c[:26])}</text>')
    pal = [(0.0, "#0b1b34"), (0.35, "#1d4e89"), (0.65, "#38bdf8"), (1.0, "#fde68a")]

    def colour(v):
        t = max(0.0, min(1.0, (v + 1.2) / 3.2))
        for (a, ca), (b_, cb) in zip(pal, pal[1:]):
            if t <= b_:
                return _mix(ca, cb, (t - a) / (b_ - a))
        return pal[-1][1]
    for r, i in enumerate(order):
        g = names[i]
        y = y0 + r * rh
        orphan = status.get(g) == "orphan"
        o.append(_t(x0 - 62, y + 12, g, 11.5, "#fbbf24" if orphan else TXT, 700 if orphan else 400, "end"))
        cp = coupling.get(g, "")
        o.append(f'<rect x="{x0 - 54}" y="{y + 2}" width="14" height="13" rx="3" fill="{COUP_COL[cp] if cp else "#1a2c46"}"><title>{E(g)} coupling: {cp or "not in the coupling table"}</title></rect>')
        if cp:
            o.append(_t(x0 - 47, y + 12, cp[1] if len(cp) > 1 else cp, 9, "#020617", 800, "middle"))
        for j in range(len(ctx)):
            o.append(f'<rect x="{x0 + j * cw}" y="{y}" width="{cw - 1}" height="{rh - 1}" fill="{colour(z[i][j])}"><title>{E(g)} in {E(ctx[j])}: {matrix.loc[g].iloc[j]:.3g} (row z {z[i][j]:+.2f})</title></rect>')
        o.append(_t(x0 + cw * len(ctx) + 10, y + 12, f"tau {tau.get(g, 0):.2f}", 10, MUTED))
        o.append(_t(x0 + cw * len(ctx) + 70, y + 12, ctx[int(np.argmax(z[i]))][:28], 10, "#9ccbe6"))
    ly = y0 + rh * len(order) + 22
    for k in range(40):
        o.append(f'<rect x="{x0 + k * 5}" y="{ly}" width="5.5" height="10" fill="{colour(-1.2 + 3.2 * k / 39)}"/>')
    o.append(_t(x0 - 6, ly + 9, "low", 10, MUTED, 400, "end")); o.append(_t(x0 + 208, ly + 9, "high (row z)", 10, MUTED))
    o.append(_t(x0 + 320, ly + 9, f"showing {len(order)} of {len(names)} GPCRs · hover a cell for the raw value", 10, MUTED))
    return _frame(W, H, "".join(o), "GPCR expression heatmap")


def gsea_svg(res, cls: str) -> str:
    """The standard enrichment plot: running enrichment score, hit barcode, and the ranked metric."""
    cv = (res.curves or {}).get(cls)
    if not cv:
        return ""
    row = res.table[res.table["Coupling class"] == cls].iloc[0]
    run, hits, n = cv["run"], cv["hits"], len(cv["run"])
    vals = res.ranked.to_numpy(float)
    W, H, x0, x1 = 980, 470, 80, 940
    X = lambda i: x0 + (x1 - x0) * i / max(1, n - 1)
    lo, hi = min(run + [0]), max(run + [0])
    Y1 = lambda v: 120 + 150 * (1 - (v - lo) / max(1e-9, hi - lo))
    col = COUP_COL.get(cls, ACC)
    o = [_t(24, 32, f"{cls}-coupled receptors: enrichment plot", 17, TXT, 700),
         _t(24, 52, f"NES {row['NES']:+.2f} · enrichment score {row['ES']:+.3f} · permutation p {row['p']:.3g} · FDR {row['FDR']:.3g} · {int(row['Receptors ranked'])} {cls}-coupled of {n} ranked receptors", 11.5, MUTED)]
    o.append(f'<line x1="{x0}" y1="{Y1(0):.1f}" x2="{x1}" y2="{Y1(0):.1f}" stroke="#2a4a6a" stroke-dasharray="4 4"/>')
    pts = " ".join(f"{X(i):.1f},{Y1(v):.1f}" for i, v in enumerate(run))
    o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.6"/>')
    pk = cv["peak"]
    o.append(f'<line x1="{X(pk):.1f}" y1="{Y1(run[pk]):.1f}" x2="{X(pk):.1f}" y2="{Y1(0):.1f}" stroke="{col}" stroke-dasharray="3 3"/><circle cx="{X(pk):.1f}" cy="{Y1(run[pk]):.1f}" r="5" fill="{col}"/>')
    o.append(_t(X(pk) + 8, Y1(run[pk]) - 8, f"peak at rank {pk + 1}", 10.5, col, 700))
    o.append(_t(24, 120, "running", 10.5, MUTED, 600)); o.append(_t(24, 133, "enrichment", 10.5, MUTED, 600)); o.append(_t(24, 146, "score", 10.5, MUTED, 600))
    o.append(f'<rect x="{x0}" y="296" width="{x1 - x0}" height="30" fill="#0b1b34" stroke="{LINE}"/>')
    for i in hits:
        o.append(f'<line x1="{X(i):.1f}" y1="298" x2="{X(i):.1f}" y2="324" stroke="{col}" stroke-width="1.4"/>')
    o.append(_t(24, 314, f"{cls} hits", 10.5, MUTED, 600))
    lead = [g for i, g in zip(hits, cv["genes"]) if (i <= pk if row["ES"] >= 0 else i >= pk)][:8]
    for k, (i, g) in enumerate([(i, g) for i, g in zip(hits, cv["genes"]) if g in lead]):
        o.append(f'<text transform="translate({X(i):.1f},{284 - (k % 3) * 11}) rotate(-52)" font-size="10" fill="{TXT}">{E(g)}</text>')
    mx = max(abs(vals.max()), abs(vals.min()), 1e-9)
    base = 392
    Y2 = lambda v: base - 38 * v / mx
    area = " ".join(f"{X(i):.1f},{Y2(v):.1f}" for i, v in enumerate(vals))
    o.append(f'<line x1="{x0}" y1="{base}" x2="{x1}" y2="{base}" stroke="#2a4a6a"/><polyline points="{area}" fill="none" stroke="#9ccbe6" stroke-width="1.6"/>')
    o.append(_t(24, 386, "ranked", 10.5, MUTED, 600)); o.append(_t(24, 399, "metric", 10.5, MUTED, 600))
    o.append(_t(x0, 440, "rank 1 · highest in the foreground", 10.5, MUTED)); o.append(_t(x1, 440, "lowest in the foreground · rank " + str(n), 10.5, MUTED, 400, "end"))
    o.append(_t((x0 + x1) / 2, 460, f"ranking metric: {res.metric} · {n} receptors · {res.n_perm} random gene sets for the null", 10.5, MUTED, 400, "middle"))
    return _frame(W, H, "".join(o), f"Enrichment plot for {cls}-coupled receptors")
