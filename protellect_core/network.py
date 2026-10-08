"""Interaction network with roles, and the labelled bar chart used across the app. Self-contained SVG: nothing here depends on a drawing library."""
from __future__ import annotations

import html
import math
import re
from typing import Dict, List, Optional, Sequence

from .adapters import Partner

ROLES = [  # (role, pattern, colour)
    ("G protein alpha", r"^GNA(S|L|I\d|O1|Q|11|12|13|14|15|T\d|Z|OLF)", "#34d399"),
    ("G protein beta/gamma", r"^GN(B|G)\d", "#a5b4fc"),
    ("Arrestin", r"^(ARRB\d|ARR3|SAG)$", "#f472b6"),
    ("GRK kinase", r"^GRK\d", "#fbbf24"),
    ("RGS regulator", r"^RGS\d", "#fb923c"),
    ("Effector enzyme / kinase", r"^(ADCY\d|PLCB\d|PLCG\d|PDE\d|PRKA|PRKC|PIK3|AKT\d|MAPK|MAP2K|RAF\d|SRC$|KRAS|HRAS|NRAS|MTOR)", "#38bdf8"),
    ("Rho pathway", r"^(ARHGEF|RHO[ABC]$|ROCK\d|TRIO|YAP1|WWTR1|LATS\d|TEAD\d)", "#c084fc"),
]
GPCR_COL, OTHER_COL = "#f87171", "#475569"


def role_of(name: str, registry: Optional[dict] = None) -> tuple:
    n = name.upper()
    for role, pat, col in ROLES:
        if re.match(pat, n):
            return role, col
    if registry and n in registry:
        return "GPCR", GPCR_COL
    return "other", OTHER_COL


def interaction_svg(gene: str, partners: List[Partner], max_nodes: int = 12, size: int = 600, highlight: Sequence[str] = (), registry: Optional[dict] = None) -> str:
    ps = sorted(partners, key=lambda p: -p.score)[:max_nodes]
    H = size + 70
    c, cy = size / 2, size / 2
    r = size * 0.30
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {H}" width="100%" role="img" aria-label="Interaction network of {html.escape(gene)}" style="background:#020617;border:1px solid #0c2040;border-radius:12px;font-family:Inter,system-ui,sans-serif">'
         f'<rect width="{size}" height="{H}" fill="#020617" rx="12"/>'
         f'<text x="16" y="24" font-size="13" font-weight="700" fill="#cfe6f5">Interaction partners of {html.escape(gene)}</text>'
         f'<text x="16" y="40" font-size="9.5" fill="#6b8aa3">STRING combined score on each edge · node colour = role in GPCR signalling</text>']
    if not ps:
        o.append(f'<text x="{c}" y="{cy}" fill="#8da8bf" font-size="13" text-anchor="middle">No interaction partners were returned for {html.escape(gene)}.</text></svg>')
        return "".join(o)
    pos = []
    for i, p in enumerate(ps):
        a = -math.pi / 2 + 2 * math.pi * i / len(ps)
        pos.append((c + r * math.cos(a), cy + 10 + r * math.sin(a), a))
    for p, (x, y, _) in zip(ps, pos):
        role, col = role_of(p.name, registry)
        o.append(f'<line x1="{c}" y1="{cy + 10}" x2="{x:.1f}" y2="{y:.1f}" stroke="{col}" stroke-opacity="{0.3 + 0.6 * min(1, p.score):.2f}" stroke-width="{0.8 + 3.2 * min(1, p.score):.1f}"/>')
        o.append(f'<text x="{(c + x) / 2:.1f}" y="{(cy + 10 + y) / 2 - 3:.1f}" font-size="9" fill="#7da3c0" text-anchor="middle">{p.score:.2f}</text>')
    roles_seen = {}
    for p, (x, y, a) in zip(ps, pos):
        role, col = role_of(p.name, registry)
        roles_seen[role] = col
        hi = p.name.upper() in {h.upper() for h in highlight}
        node = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{9 + 8 * min(1, p.score):.1f}" fill="{col}" fill-opacity=".9" stroke="{"#f59e0b" if hi else "#e6f2ff"}" stroke-width="{2.4 if hi else 1}"><title>{html.escape(p.name)} · {role} · STRING {p.score:.3f}</title></circle>'
                f'<text x="{x + (20 if math.cos(a) >= 0 else -20):.1f}" y="{y + 1:.1f}" font-size="11.5" font-weight="700" fill="#e6f2ff" text-anchor="{"start" if math.cos(a) >= 0 else "end"}">{html.escape(p.name)}</text>'
                f'<text x="{x + (20 if math.cos(a) >= 0 else -20):.1f}" y="{y + 13:.1f}" font-size="9" fill="#7da3c0" text-anchor="{"start" if math.cos(a) >= 0 else "end"}">{html.escape(role)}</text>')
        o.append(f'<a href="{html.escape(p.url, quote=True)}" target="_blank">{node}</a>' if p.url.startswith("http") else node)
    o.append(f'<circle cx="{c}" cy="{cy + 10}" r="27" fill="#38bdf8"/><text x="{c}" y="{cy + 14}" font-size="12" font-weight="800" fill="#001" text-anchor="middle">{html.escape(gene)}</text>')
    lx, ly = 16, H - 22
    for role, col in roles_seen.items():
        o.append(f'<circle cx="{lx + 5}" cy="{ly}" r="5" fill="{col}"/><text x="{lx + 14}" y="{ly + 4}" font-size="9.5" fill="#9ab">{html.escape(role)}</text>')
        lx += 26 + len(role) * 5.6
        if lx > size - 90:
            lx, ly = 16, ly + 16
    o.append("</svg>")
    return "".join(o)


def track_svg(b, width: int = 900) -> str:
    from .viz import architecture_svg
    return architecture_svg(b, None, width)


def bars_svg(labels: Sequence[str], values: Sequence[float], title: str, subtitle: str = "", color: str = "#38bdf8", fmt: str = "{:g}", signed: bool = False, colors: Optional[Sequence[str]] = None) -> str:
    """A labelled horizontal bar chart: every bar carries its value; the axis and zero line are drawn."""
    n = len(labels)
    if not n:
        return ""
    W, rowh, top = 760, 28, 70
    H = top + n * rowh + 30
    mx = max(max(abs(v) for v in values), 1e-9)
    lab_w = 230
    x0 = lab_w + 30
    span = W - x0 - 80
    zero = x0 + (span / 2 if signed else 0)
    sc = (span / 2 if signed else span) / mx
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{html.escape(title)}" style="background:#020617;border:1px solid #0c2040;border-radius:12px;font-family:Inter,system-ui,sans-serif">'
         f'<rect width="{W}" height="{H}" fill="#020617" rx="12"/><text x="18" y="28" font-size="14" font-weight="700" fill="#cfe6f5">{html.escape(title)}</text>'
         + (f'<text x="18" y="46" font-size="10.5" fill="#6b8aa3">{html.escape(subtitle)}</text>' if subtitle else "") + f'<line x1="{zero}" y1="{top - 10}" x2="{zero}" y2="{top + n * rowh}" stroke="#2a4a6a"/>']
    for i, (l, v) in enumerate(zip(labels, values)):
        y = top + i * rowh
        w = abs(v) * sc
        x = zero if v >= 0 else zero - w
        cc = (colors[i] if colors else (color if v >= 0 or not signed else "#fb7185"))
        o.append(f'<text x="{lab_w}" y="{y + 15}" font-size="11.5" fill="#cfe6f5" text-anchor="end">{html.escape(str(l))[:34]}</text>')
        o.append(f'<rect x="{x:.1f}" y="{y + 3}" width="{max(w, 1.5):.1f}" height="{rowh - 9}" rx="4" fill="{cc}" opacity=".9"><title>{html.escape(str(l))}: {fmt.format(v)}</title></rect>')
        o.append(f'<text x="{(x + w + 7) if v >= 0 else (x - 7):.1f}" y="{y + 15}" font-size="11" fill="#9ccbe6" font-weight="600" text-anchor="{"start" if v >= 0 else "end"}">{fmt.format(v)}</text>')
    o.append("</svg>")
    return "".join(o)
