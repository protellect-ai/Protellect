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
    return cases


def usable(cases: List[Case]) -> List[Case]:
    """Contested cases are never used for training or scoring."""
    return [c for c in cases if not c.contested]


def temporal_precedents(cases: List[Case], query_year: int, exclude_id: Optional[str] = None) -> List[Case]:
    """Strict temporal split: only cases resolved BEFORE the query's year, never the query itself."""
    return [c for c in usable(cases) if c.resolution_year < query_year and c.id != exclude_id]


def all_verified(cases: List[Case]) -> bool:
    return all(c.verified for c in usable(cases))
