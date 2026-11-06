"""Deterministic critic: grounded counter-arguments against each hypothesis.

Every counter-argument is produced by a checkable rule over data the engine already holds
(case library, learned weights, the user's own experiment row, the refuted-pairings list, and the engine's
own historical misses). Nothing here is free-text model opinion. See llm_debate.py for the optional AI layer,
which may only cite these items.
"""
from __future__ import annotations

import json
import pathlib
from typing import Dict, List, Optional, Sequence

from .cases import DATA_DIR
from .ranker import PrecedentRanker, profile_from_case
from .schema import Case, QueryProfile

PENALTY = {"major": 0.75, "minor": 0.9}   # multiplicative, applied per counter-argument
NEAR_TIE = 0.05
VERDICT_ORDER = {"holds up": 0, "weakened": 1, "contested": 2}


def load_refuted(path: Optional[str] = None) -> List[dict]:
    p = pathlib.Path(path) if path else DATA_DIR / "refuted_pairings.json"
    return json.loads(p.read_text(encoding="utf-8"))["pairings"]


def class_precision(library: Sequence[Case], target: str = "ligand_class") -> Dict[str, dict]:
    """Leave-one-out precision of the engine's top pick, per predicted value (the engine's own track record)."""
    stats: Dict[str, dict] = {}
    for q in library:
        lib = [c for c in library if c.id != q.id]
        ranker = PrecedentRanker().fit(lib, target)
        scores = ranker.value_scores(profile_from_case(q), lib)
        if not scores:
            continue
        pred = max(scores, key=scores.get)
        s = stats.setdefault(pred, {"n": 0, "hits": 0})
        s["n"] += 1
        s["hits"] += int(pred == getattr(q, target))
    return {k: {**v, "rate": v["hits"] / v["n"]} for k, v in stats.items()}


def _c(check: str, severity: str, text: str, evidence: str) -> dict:
    return {"check": check, "severity": severity, "text": text, "evidence": evidence}


def critique(*, category: str, value: str, gene: str, profile: QueryProfile, library: Sequence[Case],
             ranker: PrecedentRanker, scores: Dict[str, float], supporting: List[dict],
             row=None, refuted: Sequence[dict] = (), precision: Optional[Dict[str, dict]] = None,
             use_history: bool = True) -> List[dict]:
    out: List[dict] = []

    # 1. Known refuted / contested pairing for this exact receptor
    if category == "ligand-class":
        for r in refuted:
            if r["gene"].upper() == gene.upper() and r["ligand_class"] == value:
                sev = "major" if r["status"] == "refuted" else "minor"
                out.append(_c("known_pairing_problem", sev,
                              f"A {r['status']} pairing exists for this receptor: {r['ligand']} ({value}). {r['note']}", r["source"]))

    # 2. Related receptors in the library that disagree with this hypothesis
    linked = []
    for d in ranker.scored_precedents(profile, library):
        f = d["features"]
        if f["neighbor_link"] or f["same_cluster"]:
            linked.append(d["case"])
    if linked and category in ("ligand-class", "signaling"):
        disagree = [c for c in linked if getattr(c, ranker.target) != value]
        if disagree:
            sev = "major" if len(disagree) / len(linked) >= 0.5 else "minor"
            names = ", ".join(f"{c.id} ({getattr(c, ranker.target)})" for c in disagree[:4])
            out.append(_c("related_receptors_disagree", sev,
                          f"{len(disagree)} of {len(linked)} related receptors point elsewhere: {names}.",
                          "case library: neighbor/cluster links"))

    # 3. Match rests on tissue overlap alone, which history says is the weaker signal
    if supporting and category != "disease-association":
        tissue_only = all(not d["features"]["neighbor_link"] and not d["features"]["same_cluster"] for d in supporting)
        w = ranker.weights()
        if tissue_only and w["tissue_overlap"] < max(w["neighbor_link"], w["same_cluster"]):
            out.append(_c("tissue_only_match", "minor",
                          f"The match rests on shared tissue alone. In the historical library, family relationships predicted ligand "
                          f"class better (learned weights: tissue {w['tissue_overlap']:.2f}, neighbor {w['neighbor_link']:.2f}, cluster {w['same_cluster']:.2f}).",
                          "ranker weights"))

    # 4. Near tie with a competing candidate
    ranked = sorted(scores.values(), reverse=True)
    if len(ranked) > 1 and scores.get(value, 0) >= ranked[1] and ranked[0] - ranked[1] < NEAR_TIE:
        out.append(_c("near_tie", "minor", "A competing candidate is within 0.05 relative support, so the order is not reliable.", "support scores"))
    elif len(ranked) > 1 and abs(scores.get(value, 0) - ranked[0]) < NEAR_TIE and scores.get(value, 0) < ranked[0]:
        out.append(_c("near_tie", "minor", "This candidate is within 0.05 relative support of the leader.", "support scores"))

    # 5. Single precedent
    if len(supporting) == 1:
        out.append(_c("single_precedent", "minor", f"Only one precedent ({supporting[0]['case'].id}) supports this.", "case library"))

    # 6. Weak experimental signal in the user's own data
    if row is not None:
        weak = []
        if getattr(row, "effect_type", "") == "log2 fold-change" and abs(float(row.effect)) < 1.0:
            weak.append(f"small effect (log2FC {float(row.effect):.2f})")
        sig = getattr(row, "significance", None)
        if sig is not None and sig == sig and float(sig) > 0.01:
            weak.append(f"borderline significance (p = {float(sig):.3g})")
        if weak:
            out.append(_c("weak_signal", "minor", "Your own data for this receptor is modest: " + " and ".join(weak) + ".", "your experiment"))

    # 7. The engine's own track record for this kind of prediction
    if use_history and category == "ligand-class" and precision and value in precision:
        p = precision[value]
        if p["n"] >= 3 and p["rate"] < 0.5:
            out.append(_c("poor_track_record", "major",
                          f"When this engine's top pick was '{value}', it was right only {p['hits']}/{p['n']} times in leave-one-out testing.",
                          "leave-one-out history (small, unverified library)"))
    return out


def verdict_from(counters: Sequence[dict]) -> str:
    major = sum(c["severity"] == "major" for c in counters)
    minor = sum(c["severity"] == "minor" for c in counters)
    refuted = any(c["check"] == "known_pairing_problem" and c["severity"] == "major" for c in counters)
    if refuted or major >= 2:
        return "contested"
    if major == 1 or minor >= 2:
        return "weakened"
    return "holds up"


def penalty(counters: Sequence[dict]) -> float:
    p = 1.0
    for c in counters:
        p *= PENALTY[c["severity"]]
    return p
