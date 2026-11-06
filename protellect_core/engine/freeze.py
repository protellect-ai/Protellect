"""Predict-and-freeze: write down today's predictions for the receptors that are still orphans, with a hash, so that a later
IUPHAR release can score them honestly. A new release that gives one of them a natural ligand is a free, genuinely held-out test."""
from __future__ import annotations

import datetime
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import List

import pandas as pd

from .learned import LearnedModel
from .pipeline import file_version, labelled_table, orphan_table, build_cases, sha256
from .schema import Case


def freeze(targets_csv, interactions_csv, out_json, hpa_tsv=None, model_name=None) -> dict:
    model_name = model_name or ("learned (chromosome neighbours + tissue)" if hpa_tsv else "learned (chromosome neighbours only)")
    cases = build_cases(targets_csv, interactions_csv, hpa_tsv)
    model = LearnedModel(use_tissue=bool(hpa_tsv)).fit(cases)
    labelled = {c.id for c in cases}
    orph = orphan_table(targets_csv)
    from .pipeline import load_tissues
    tissues = load_tissues(hpa_tsv) if hpa_tsv else {}
    preds = []
    for _, r in orph.iterrows():
        sym = r["HGNC symbol"]
        if sym in labelled:
            continue
        q = Case(id=sym, gene=sym, resolution_year=2026, ligand="", ligand_class="", coupling="Gq", cluster=r.band or "", neighbors=[],
                 tissues=tissues.get(sym.upper(), []), later_outcome="", citations=[])
        sc = model.predict(q)
        if sc is None:
            preds.append({"gene": sym, "prediction": None, "reason": "abstained: no chromosome neighbour with a known ligand and no tissue data"})
        else:
            top = max(sc, key=sc.get)
            preds.append({"gene": sym, "prediction": top, "scores": {k: round(v, 3) for k, v in sc.items()}})
    body = {"frozen_on": datetime.date.today().isoformat(), "model": model_name, "targets_version": file_version(targets_csv),
            "interactions_version": file_version(interactions_csv), "targets_sha256": sha256(targets_csv), "interactions_sha256": sha256(interactions_csv),
            "n_orphans_predicted": sum(1 for p in preds if p["prediction"]), "n_abstained": sum(1 for p in preds if not p["prediction"]),
            "predictions": preds, "note": "Predictions are of the coarse ligand type (peptide or metabolite). Made before any outcome was known."}
    body["predictions_sha256"] = hashlib.sha256(json.dumps(preds, sort_keys=True).encode()).hexdigest()
    Path(out_json).write_text(json.dumps(body, indent=1), encoding="utf-8")
    return body


def check(frozen_json, new_targets_csv, new_interactions_csv) -> pd.DataFrame:
    """Score a frozen file against a LATER release: every frozen prediction whose receptor now has a natural peptide or metabolite ligand."""
    f = json.loads(Path(frozen_json).read_text(encoding="utf-8"))
    truth = labelled_table(new_targets_csv, new_interactions_csv).set_index("HGNC symbol")["cls"].str.lower().to_dict()
    rows = [{"gene": p["gene"], "predicted": p["prediction"], "now_known": truth[p["gene"]], "correct": p["prediction"] == truth[p["gene"]] if p["prediction"] else None}
            for p in f["predictions"] if p["gene"] in truth]
    return pd.DataFrame(rows, columns=["gene", "predicted", "now_known", "correct"])
