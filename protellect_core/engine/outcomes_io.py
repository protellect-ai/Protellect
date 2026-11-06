"""Lab outcomes -> outcomes.json, so a result a lab records becomes a case the library can learn from.

CSV columns: gene, status (confirmed / refuted / inconclusive), ligand, ligand_class, coupling, resolution_year, notes, citations (separate with ;)
Only 'confirmed' rows with a note or citation ever become cases (see cases.cases_from_outcomes). Refuted and inconclusive rows are kept for the record
and shown back, because knowing what failed is part of what a lab needs. Nothing here is expert-verified."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

TEMPLATE_COLUMNS = ["gene", "status", "ligand", "ligand_class", "coupling", "resolution_year", "notes", "citations"]


def outcomes_from_csv(csv_path, outcomes_json) -> int:
    df = pd.read_csv(csv_path).fillna("")
    missing = [c for c in ("gene", "status") if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")
    p = Path(outcomes_json)
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"outcomes": []}
    n = 0
    for _, r in df.iterrows():
        rec = {k: r[k] for k in TEMPLATE_COLUMNS if k in df.columns and r[k] != ""}
        if "citations" in rec:
            rec["citations"] = [x.strip() for x in str(rec["citations"]).split(";") if x.strip()]
        if "resolution_year" in rec:
            rec["resolution_year"] = int(rec["resolution_year"])
        data["outcomes"].append(rec)
        n += 1
    p.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return n
