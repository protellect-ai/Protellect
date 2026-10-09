"""Check the case library's citations against Europe PMC. Run it on a machine with internet access:

    python -m protellect_core.engine.verify            # writes cases_citation_check.csv next to where you run it

For each case and each 'Author Year' citation it searches Europe PMC for that first author and year (+-1) together with the
receptor's name(s), and records the PMID and title it found. It tells you whether a paper EXISTS that matches the citation.
It does NOT check that the ligand, coupling, tissues or neighbours in the case are right, and it never sets `verified`.
A domain expert still has to read each paper and confirm every field, and that the features list only what was known
before the resolution year.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List

API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def split_citation(c: str):
    m = re.match(r"\s*([A-Za-z'\-À-ɏ ]+?)(?:\s+et al\.?)?\s+((?:19|20)\d\d)\s*$", c or "")
    return (m.group(1).strip(), int(m.group(2))) if m else (None, None)


def build_query(author: str, year: int, names: List[str]) -> str:
    nm = " OR ".join(f'"{n}"' for n in names if n)
    return f'AUTH:"{author}" AND PUB_YEAR:[{year - 1} TO {year + 1}] AND ({nm})'


def judge(result_json: dict, author: str, year: int, names: List[str]) -> Dict:
    """Pick the best matching record from a Europe PMC lite search result."""
    rows = (result_json.get("resultList") or {}).get("result") or []
    best = None
    for r in rows:
        first = (r.get("authorString") or "").split(",")[0].strip().lower()
        if not first.startswith((author or "").lower()):
            continue
        title = r.get("title") or ""
        names_in_title = any(n and n.lower() in title.lower() for n in names)
        try:
            y_ok = abs(int(r.get("pubYear")) - year) <= 1
        except (TypeError, ValueError):
            y_ok = False
        if not y_ok:
            continue
        cand = {"found": True, "pmid": r.get("pmid") or "", "title": title, "year": r.get("pubYear"), "first_author": first,
                "note": "title names the receptor" if names_in_title else "author and year match but the title does not name the receptor: read it to confirm"}
        if names_in_title:
            return cand
        best = best or cand
    return best or {"found": False, "pmid": "", "title": "", "year": "", "first_author": "", "note": "no record with this first author, year and receptor name"}


def run(cases_path: Path, out_csv: Path, fetch=None, sleep: float = 0.3) -> List[Dict]:
    if fetch is None:
        import requests
        def fetch(q):
            r = requests.get(API, params={"query": q, "format": "json", "pageSize": 10, "resultType": "lite"}, timeout=30)
            r.raise_for_status()
            return r.json()
    data = json.loads(Path(cases_path).read_text())
    rows = []
    for cid, case in (data.items() if isinstance(data, dict) else [(c.get("id"), c) for c in data]):
        names = [case.get("id"), case.get("gene")] + list(case.get("aliases") or [])
        for cit in case.get("citations", []):
            a, y = split_citation(cit)
            if not a:
                rows.append({"case": cid, "citation": cit, "found": False, "pmid": "", "title": "", "note": "could not read the citation as 'Author Year'"})
                continue
            try:
                res = judge(fetch(build_query(a, y, names)), a, y, names)
            except Exception as e:  # noqa: BLE001
                res = {"found": False, "pmid": "", "title": "", "note": f"lookup failed: {e}"}
            rows.append({"case": cid, "citation": cit, "found": res["found"], "pmid": res["pmid"], "title": res["title"], "note": res["note"]})
            time.sleep(sleep)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["case", "citation", "found", "pmid", "title", "note"])
        w.writeheader(); w.writerows(rows)
    return rows


if __name__ == "__main__":
    here = Path(__file__).parent / "data" / "cases.json"
    out = run(here, Path("cases_citation_check.csv"))
    ok = sum(1 for r in out if r["found"])
    print(f"{ok}/{len(out)} citations matched a paper. See cases_citation_check.csv. 'verified' flags were NOT changed.")
