"""Repurposing candidates for a panel of GPCRs: recorded drugs whose action matches the direction you want."""
from __future__ import annotations

import re
from typing import Dict, List

import pandas as pd

INHIBIT = re.compile(r"inhibit|antagon|block|inverse|negative|suppress|antibod|inactiv|degrad|silenc", re.I)
ACTIVATE = re.compile(r"agonis|activat|positive|potentiat|stimulat|partial", re.I)


def action_of(kind: str) -> str:
    k = kind or ""
    if INHIBIT.search(k):
        return "inhibit"
    if ACTIVATE.search(k):
        return "activate"
    return "unspecified"


def table(genes: List[str], drug_map: Dict[str, List[dict]], desired: str, why: Dict[str, str] | None = None) -> pd.DataFrame:
    rows = []
    for g in genes:
        ds = drug_map.get(g, []) or []
        match = [d for d in ds if action_of(d.get("type", "")) == desired]
        other = [d for d in ds if action_of(d.get("type", "")) != desired]
        rows.append({"GPCR": g, "Why listed": (why or {}).get(g, ""), f"Recorded {desired}-type drugs": ", ".join(f"{d['drug']} ({d.get('type') or 'type not given'})" for d in match[:6]) or "none recorded",
                     "Count": len(match), "Other recorded interactions": ", ".join(f"{d['drug']} ({d.get('type') or '?'})" for d in other[:4]), "Source": (match or other or [{}])[0].get("url", "")})
    t = pd.DataFrame(rows)
    return t.sort_values("Count", ascending=False).reset_index(drop=True) if len(t) else t
