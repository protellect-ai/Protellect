"""Pharmacokinetics / ADMET screening from REAL records, and real adverse-event counts.

Properties come from PubChem (computed descriptors for the named compound); the screens are published rules, not a
black-box model, and are labelled as such. Adverse events come from openFDA FAERS spontaneous reports (counts only).
Network access is injected (`get`) so everything is testable offline; the Streamlit views wrap these calls in a cache.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional
from urllib.parse import quote

PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/MolecularWeight,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount,RotatableBondCount/JSON"
OPENFDA = "https://api.fda.gov/drug/event.json?search=patient.drug.openfda.generic_name:%22{name}%22&count=patient.reaction.reactionmeddrapt.exact&limit={n}"
OPENFDA_TOTAL = "https://api.fda.gov/drug/event.json?search=patient.drug.openfda.generic_name:%22{name}%22&limit=1"

CITES = {
    "lipinski": "Lipinski et al. 2001, Adv Drug Deliv Rev 46:3",
    "veber": "Veber et al. 2002, J Med Chem 45:2615",
    "cns": "Pajouhesh & Lenz 2005, NeuroRx 2:541",
}


def _num(x) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def parse_pubchem(js: dict) -> Optional[Dict[str, float]]:
    try:
        p = js["PropertyTable"]["Properties"][0]
    except (KeyError, IndexError, TypeError):
        return None
    out = {"mw": _num(p.get("MolecularWeight")), "xlogp": _num(p.get("XLogP")), "tpsa": _num(p.get("TPSA")), "hbd": _num(p.get("HBondDonorCount")),
           "hba": _num(p.get("HBondAcceptorCount")), "rotb": _num(p.get("RotatableBondCount")), "cid": p.get("CID")}
    return out if any(out[k] is not None for k in ("mw", "tpsa")) else None


def fetch_properties(name: str, get: Callable) -> Optional[Dict[str, float]]:
    try:
        r = get(PUBCHEM.format(name=quote(name)), timeout=15)
        return parse_pubchem(r.json()) if r.status_code == 200 else None
    except Exception:
        return None


def admet_rules(p: Dict[str, float]) -> List[dict]:
    """Published rule screens. Each row says what was tested, on what numbers, and where the rule comes from."""
    rows = []
    mw, xl, tpsa, hbd, hba, rb = (p.get(k) for k in ("mw", "xlogp", "tpsa", "hbd", "hba", "rotb"))
    if None not in (mw, xl, hbd, hba):
        viol = [n for n, bad in (("MW > 500", mw > 500), ("logP > 5", xl > 5), ("H-bond donors > 5", hbd > 5), ("H-bond acceptors > 10", hba > 10)) if bad]
        rows.append({"test": "Oral drug-likeness (Rule of Five)", "pass": len(viol) <= 1, "detail": f"MW {mw:.0f}, logP {xl:.1f}, HBD {hbd:.0f}, HBA {hba:.0f}" + (f"; violations: {', '.join(viol)}" if viol else "; no violations"), "basis": CITES["lipinski"]})
    if None not in (tpsa, rb):
        rows.append({"test": "Oral absorption plausibility (Veber)", "pass": rb <= 10 and tpsa <= 140, "detail": f"rotatable bonds {rb:.0f}, polar surface area {tpsa:.0f} A^2", "basis": CITES["veber"]})
    if None not in (tpsa, mw, hbd):
        rows.append({"test": "Brain penetration plausibility (CNS guideline)", "pass": tpsa <= 90 and mw <= 450 and hbd <= 3, "detail": f"polar surface area {tpsa:.0f}, MW {mw:.0f}, HBD {hbd:.0f} (needs <= 90, <= 450, <= 3)", "basis": CITES["cns"]})
    return rows


def parse_faers(js: dict) -> List[tuple]:
    try:
        return [(str(r["term"]).title(), int(r["count"])) for r in js["results"]]
    except (KeyError, TypeError, ValueError):
        return []


def fetch_faers(name: str, get: Callable, n: int = 8) -> Optional[dict]:
    try:
        r = get(OPENFDA.format(name=quote(name.lower()), n=n), timeout=15)
        if r.status_code != 200:
            return None
        top = parse_faers(r.json())
        total = None
        try:
            t = get(OPENFDA_TOTAL.format(name=quote(name.lower())), timeout=15)
            total = int(t.json()["meta"]["results"]["total"]) if t.status_code == 200 else None
        except Exception:
            pass
        return {"top": top, "total": total} if top else None
    except Exception:
        return None
