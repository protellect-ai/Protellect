"""Interaction network as a self-contained SVG (radial layout; edge width = STRING score; nodes link to STRING)."""
from __future__ import annotations

import html
import math
from typing import List

from .adapters import Partner


def interaction_svg(gene: str, partners: List[Partner], max_nodes: int = 12, size: int = 420, highlight: List[str] = ()) -> str:
    ps = sorted(partners, key=lambda p: -p.score)[:max_nodes]
    c = size / 2
    r = size * 0.36
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="100%" role="img" aria-label="Interaction network of {html.escape(gene)}" '
           f'style="background:#020617;border:1px solid #0c2040;border-radius:12px;font-family:Inter,system-ui,sans-serif"><rect width="{size}" height="{size}" fill="#020617" rx="12"/>']
    if not ps:
        out.append(f'<text x="{c}" y="{c}" fill="#8da8bf" font-size="13" text-anchor="middle">No interaction partners were returned for {html.escape(gene)}.</text></svg>')
        return "".join(out)
    pos = []
    for i, p in enumerate(ps):
        a = -math.pi / 2 + 2 * math.pi * i / len(ps)
        pos.append((c + r * math.cos(a), c + r * math.sin(a), a))
    for p, (x, y, _) in zip(ps, pos):
        out.append(f'<line x1="{c}" y1="{c}" x2="{x:.1f}" y2="{y:.1f}" stroke="#38bdf8" stroke-opacity="{0.25 + 0.6 * min(1, p.score):.2f}" stroke-width="{0.6 + 3.4 * min(1, p.score):.1f}"/>')
    for p, (x, y, a) in zip(ps, pos):
        hi = p.name.upper() in {h.upper() for h in highlight}
        fill = "#f59e0b" if hi else "#0f2a4a"
        node = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{10 + 8 * min(1, p.score):.1f}" fill="{fill}" stroke="#38bdf8" stroke-width="1.2"><title>{html.escape(p.name)}: STRING combined score {p.score:.3f}</title></circle>'
                f'<text x="{x + (22 if math.cos(a) >= 0 else -22) * 1:.1f}" y="{y + 4:.1f}" font-size="11" fill="#cfe6f5" text-anchor="{"start" if math.cos(a) >= 0 else "end"}">{html.escape(p.name)}</text>')
        out.append(f'<a href="{html.escape(p.url, quote=True)}" target="_blank">{node}</a>' if p.url.startswith("http") else node)
    out.append(f'<circle cx="{c}" cy="{c}" r="26" fill="#38bdf8"/><text x="{c}" y="{c + 4}" font-size="12" font-weight="700" fill="#001" text-anchor="middle">{html.escape(gene)}</text></svg>')
    return "".join(out)


def track_svg(b, width: int = 900) -> str:
    """Linear track of the protein: domains, annotated sites, variant hotspots and pathogenic/likely-pathogenic positions (all real records)."""
    L = max(b.length, 1)
    x = lambda p: 20 + (width - 40) * p / L
    rows = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 150" width="100%" role="img" aria-label="Variant and domain track" style="background:#020617;border:1px solid #0c2040;border-radius:12px;font-family:Inter,system-ui,sans-serif"><rect width="{width}" height="150" fill="#020617" rx="12"/>',
            f'<rect x="20" y="62" width="{width - 40}" height="18" rx="5" fill="#0f2a4a"/>']
    for d in b.domains[:10]:
        rows.append(f'<rect x="{x(d["start"]):.1f}" y="62" width="{max(3, x(d["end"]) - x(d["start"])):.1f}" height="18" rx="4" fill="#38bdf8" opacity=".7"><title>{html.escape(d["desc"] or d["type"])} {d["start"]}-{d["end"]}</title></rect>')
    for s in b.sites[:20]:
        rows.append(f'<rect x="{x(s["start"]):.1f}" y="84" width="{max(3, x(s["end"]) - x(s["start"])):.1f}" height="7" rx="2" fill="#34d399"><title>{html.escape(s["type"])} {html.escape(s["desc"])} {s["start"]}-{s["end"]}</title></rect>')
    for h in b.hotspots:
        rows.append(f'<rect x="{x(h.start):.1f}" y="40" width="{max(3, x(h.end) - x(h.start)):.1f}" height="14" rx="3" fill="#f59e0b"><title>Hotspot {h.start}-{h.end}: {h.count} variants, {h.fold:.1f}x enriched</title></rect>')
    for v in b.plp[:200]:
        if v.pos:
            rows.append(f'<line x1="{x(v.pos):.1f}" y1="94" x2="{x(v.pos):.1f}" y2="116" stroke="#ff2d55" stroke-width="1.2" opacity=".8"/>')
    rows.append('<text x="20" y="30" fill="#7dd3fc" font-size="11" font-weight="700">Hotspots (orange) | domains (blue) | annotated sites (green) | pathogenic / likely pathogenic positions (red)</text>')
    rows.append(f'<text x="20" y="140" fill="#6b8aa3" font-size="10">1</text><text x="{width - 20}" y="140" fill="#6b8aa3" font-size="10" text-anchor="end">{b.length}</text></svg>')
    return "".join(rows)
