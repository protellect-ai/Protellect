"""Historical deorphanization case library: loading, validation, temporal filtering."""
from __future__ import annotations

import json
import pathlib
from typing import List, Optional

from .schema import Case, COUPLINGS, LIGAND_CLASSES, TISSUE_VOCAB

DATA_DIR = pathlib.Path(__file__).parent / "data"


def validate_case(c: Case) -> None:
    if c.ligand_class not in LIGAND_CLASSES:
        raise ValueError(f"{c.id}: ligand_class {c.ligand_class!r} not in {LIGAND_CLASSES}")
    if c.coupling not in COUPLINGS:
        raise ValueError(f"{c.id}: coupling {c.coupling!r} not in {COUPLINGS}")
    bad = [t for t in c.tissues if t not in TISSUE_VOCAB]
    if bad:
        raise ValueError(f"{c.id}: unknown tissue terms {bad}")
    if not isinstance(c.resolution_year, int) or not (1990 <= c.resolution_year <= 2100):
        raise ValueError(f"{c.id}: bad resolution_year {c.resolution_year!r}")


def load_cases(path: Optional[str] = None) -> List[Case]:
    p = pathlib.Path(path) if path else DATA_DIR / "cases.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    cases = [Case(**r) for r in raw["cases"]]
    for c in cases:
        validate_case(c)
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case ids in case library")
    out = p.parent / "outcomes.json"                       # recorded experimental outcomes, committed by the lab; a bad file never blocks startup
    if path is None and out.exists():
        try:
            extra, _ = cases_from_outcomes(json.loads(out.read_text(encoding="utf-8")).get("outcomes", []), ids)
            cases += extra
        except Exception:  # noqa: BLE001
            pass
    return cases


def usable(cases: List[Case]) -> List[Case]:
    """Contested cases are never used for training or scoring."""
    return [c for c in cases if not c.contested]


def temporal_precedents(cases: List[Case], query_year: int, exclude_id: Optional[str] = None) -> List[Case]:
    """Strict temporal split: only cases resolved BEFORE the query's year, never the query itself."""
    return [c for c in usable(cases) if c.resolution_year < query_year and c.id != exclude_id]


def all_verified(cases: List[Case]) -> bool:
    return all(c.verified for c in usable(cases))


def cases_from_outcomes(records, base_ids=()):
    """Turn recorded experimental outcomes into library cases. Only CONFIRMED outcomes with a citation or note become cases;
    refuted or inconclusive ones are kept in the file for the record but never trained on. Returns (cases, rejected_reasons)."""
    cases, rejected = [], []
    ids = set(base_ids)
    for i, r in enumerate(records or []):
        try:
            if str(r.get("status", "confirmed")).lower() != "confirmed":
                continue
            if not (str(r.get("notes", "")).strip() or r.get("citations")):
                raise ValueError("a confirmed outcome needs a citation or note")
            cid = f"OUT-{str(r.get('gene', '')).upper()}-{r.get('resolution_year', '')}"
            if cid in ids:
                cid = f"{cid}-{i}"
            c = Case(id=cid, gene=str(r["gene"]).upper(), resolution_year=int(r["resolution_year"]), ligand=str(r.get("ligand", "")), ligand_class=r["ligand_class"],
                     coupling=r.get("coupling", "Gq"), cluster=str(r.get("cluster", "")), neighbors=list(r.get("neighbors", [])), tissues=list(r.get("tissues", [])),
                     later_outcome=str(r.get("later_outcome", "Recorded by a user experiment")), citations=list(r.get("citations", [])) or [str(r.get("notes", ""))[:80]],
                     verified=False, notes="User-recorded outcome. Not expert-verified.")
            validate_case(c)
            ids.add(c.id)
            cases.append(c)
        except Exception as e:  # noqa: BLE001
            rejected.append(f"outcome {i + 1}: {e}")
    return cases, rejected
