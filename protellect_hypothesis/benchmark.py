"""Retrospective benchmark: would the engine have pointed at the right ligand class using only earlier knowledge?

Two modes
  loo      leave-one-out: library = every other usable case.
  temporal strict: library = only cases resolved BEFORE the query case's resolution year.
In both modes the query case is never in its own library or training set.

IMPORTANT: with a small, unverified seed library the numbers are illustrative, not evidence. The report
says so, and the summary JSON records whether the case data was verified.
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
from collections import Counter
from typing import List, Optional

from .cases import DATA_DIR, all_verified, load_cases, temporal_precedents, usable
from .ranker import PrecedentRanker, profile_from_case
from .schema import Case

MIN_LIBRARY = 3


def evaluate(cases: List[Case], mode: str = "loo", target: str = "ligand_class") -> dict:
    if mode not in ("loo", "temporal"):
        raise ValueError("mode must be 'loo' or 'temporal'")
    pool = usable(cases)
    rows = []
    for q in pool:
        if mode == "loo":
            library = [c for c in pool if c.id != q.id]
        else:
            library = temporal_precedents(cases, q.resolution_year, exclude_id=q.id)
        truth = getattr(q, target)
        if len(library) < MIN_LIBRARY:
            rows.append({"case": q.id, "truth": truth, "status": "skipped (library too small)", "library_size": len(library)})
            continue
        ranker = PrecedentRanker().fit(library, target)
        scores = ranker.value_scores(profile_from_case(q), library)
        majority = Counter(getattr(c, target) for c in library).most_common(1)[0][0]
        if not scores:
            rows.append({"case": q.id, "truth": truth, "status": "abstained", "pred": None, "majority": majority,
                         "library_size": len(library)})
            continue
        ranked = sorted(scores, key=scores.get, reverse=True)
        rows.append({"case": q.id, "truth": truth, "status": "predicted", "pred": ranked[0], "majority": majority,
                     "hit": ranked[0] == truth, "majority_hit": majority == truth, "library_size": len(library)})
    evaluable = [r for r in rows if r["status"] in ("predicted", "abstained")]
    n = len(evaluable)
    # Expected hits from guessing uniformly among the classes present in each query's library.
    random_expected = sum(1.0 / len({getattr(c, target) for c in
                          ([c for c in pool if c.id != r["case"]] if mode == "loo"
                           else temporal_precedents(cases, next(x for x in pool if x.id == r["case"]).resolution_year, exclude_id=r["case"]))})
                          for r in evaluable)
    return {
        "mode": mode, "target": target, "rows": rows, "n_evaluable": n,
        "n_skipped": len(rows) - n,
        "n_abstained": sum(r["status"] == "abstained" for r in evaluable),
        "top1_hits": sum(bool(r.get("hit")) for r in evaluable),
        "majority_hits": sum(bool(r.get("majority_hit")) for r in evaluable),
        "random_expected_hits": round(random_expected, 2),
        "data_verified": all_verified(cases),
        "generated": datetime.date.today().isoformat(),
    }


def report_markdown(res: dict) -> str:
    n = res["n_evaluable"]
    lines = [f"# Retrospective benchmark ({res['mode']}, target: {res['target']})", ""]
    if not res["data_verified"]:
        lines += ["> **WARNING: the case library has not been expert-verified. These numbers are illustrative only and must not be cited as validation.**", ""]
    lines += [f"- Cases evaluated: {n} (skipped: {res['n_skipped']}, abstained: {res['n_abstained']})",
              f"- Top-1 hits: {res['top1_hits']}/{n}",
              f"- Random-guess baseline (expected hits): {res['random_expected_hits']}/{n}",
              f"- Majority-class baseline hits: {res['majority_hits']}/{n}  (unreliable when classes are balanced: leave-one-out removes a member "
              "of the true class, so the majority is rarely the truth. Use the random baseline.)",
              "- Interpretation: with this few cases a difference of one or two hits is noise. Grow and verify the library before drawing conclusions.", "",
              "| case | truth | status | predicted | majority | library |", "|---|---|---|---|---|---|"]
    for r in res["rows"]:
        lines.append(f"| {r['case']} | {r['truth']} | {r['status']} | {r.get('pred') or '-'} | {r.get('majority') or '-'} | {r['library_size']} |")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["loo", "temporal"], default="loo")
    ap.add_argument("--target", choices=["ligand_class", "coupling"], default="ligand_class")
    ap.add_argument("--cases", default=None, help="path to a cases.json (defaults to the bundled seed library)")
    ap.add_argument("--out", default=None, help="write the markdown report here")
    ap.add_argument("--save-summary", action="store_true", help="save data/benchmark_summary.json so the app can show it")
    ap.add_argument("--allow-unverified", action="store_true", help="required to save a summary while case data is unverified")
    a = ap.parse_args(argv)
    cases = load_cases(a.cases)
    res = evaluate(cases, a.mode, a.target)
    md = report_markdown(res)
    print(md)
    if a.out:
        pathlib.Path(a.out).write_text(md, encoding="utf-8")
    if a.save_summary:
        if not res["data_verified"] and not a.allow_unverified:
            print("Refusing to save summary: case data is unverified. Re-run with --allow-unverified to save it anyway (it will be labeled).")
            return 2
        (DATA_DIR / "benchmark_summary.json").write_text(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
