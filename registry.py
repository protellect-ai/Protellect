"""GPCR registry (orphan vs characterized), receptor annotations, and an IUPHAR CSV importer."""
from __future__ import annotations

import pathlib
from typing import Dict, Optional

import pandas as pd

from .schema import TISSUE_VOCAB

DATA_DIR = pathlib.Path(__file__).parent / "data"

# free text -> controlled tissue vocabulary
_TISSUE_PATTERNS = {
    "pancreas": r"pancrea|islet|beta cell",
    "adipose": r"adipo|fat tissue|\bfat\b",
    "gut": r"gut|intestin|colon|bowel|ileum|colitis|crohn",
    "immune": r"immune|t cell|lymph|macrophage|neutrophil|leukocyte|inflamm",
    "brain": r"brain|neuro|striat|hypothalam|cortex|cns|habenula",
    "kidney": r"kidney|renal|nephr",
    "liver": r"liver|hepat",
    "heart": r"heart|cardi|myocard",
    "vasculature": r"vascul|endotheli|artery|blood vessel",
    "placenta": r"placent",
    "muscle": r"muscle|myo",
    "lung": r"lung|pulmon|airway",
    "endocrine": r"pituitar|endocrine|thyroid|adrenal",
}


def normalize_tissues(texts) -> list:
    import re
    found = []
    for t in texts:
        if not t:
            continue
        for term, pat in _TISSUE_PATTERNS.items():
            if re.search(pat, str(t).lower()) and term not in found:
                found.append(term)
    return found


def load_registry(path: Optional[str] = None) -> Dict[str, dict]:
    p = pathlib.Path(path) if path else DATA_DIR / "gpcr_registry.csv"
    df = pd.read_csv(p, dtype=str).fillna("")
    reg = {}
    for r in df.itertuples():
        reg[r.gene.strip().upper()] = {"status": r.status.strip().lower(), "note": r.note}
    return reg


def load_annotations(path: Optional[str] = None) -> Dict[str, dict]:
    p = pathlib.Path(path) if path else DATA_DIR / "receptor_annotations.csv"
    df = pd.read_csv(p, dtype=str).fillna("")
    ann = {}
    for r in df.itertuples():
        tissues = [t.strip() for t in r.tissues.split(";") if t.strip()]
        bad = [t for t in tissues if t not in TISSUE_VOCAB]
        if bad:
            raise ValueError(f"{r.gene}: unknown tissue terms {bad}; allowed: {TISSUE_VOCAB}")
        ann[r.gene.strip().upper()] = {
            "cluster": r.cluster.strip(),
            "neighbors": [n.strip() for n in r.neighbors.split(";") if n.strip()],
            "tissues": tissues,
            "source": r.source,
            "note": r.note,
        }
    return ann


def fetch_live_annotation(gene: str) -> Optional[dict]:
    """HOOK: plug in live data here (for example GPCRdb / UniProt via your protellect_data module).

    Return None when nothing is available, or a dict shaped like one entry of load_annotations():
        {"cluster": str, "neighbors": [str], "tissues": [vocab terms], "source": str, "note": str}
    The engine never guesses: no annotation means fewer (or no) hypotheses.
    """
    return None


def import_iuphar_csv(src_csv: str, out_csv: str, orphan_keyword: str = "orphan") -> int:
    """Build a registry from a Guide to Pharmacology targets-and-families CSV you download yourself.

    Assumes the file has columns for target Type, Family name and HGNC symbol (matched
    case-insensitively). Rows whose Type contains 'gpcr' are kept; a GPCR is 'orphan' when its
    family name contains `orphan_keyword`. CHECK THE OUTPUT: this was written against the expected
    file layout and tested only on a synthetic file, not the live download.
    """
    with open(src_csv, encoding="utf-8", errors="replace") as fh:
        skip = 1 if fh.readline().startswith("#") else 0
    df = pd.read_csv(src_csv, skiprows=skip, dtype=str).fillna("")
    lc = {c.strip().lower(): c for c in df.columns}
    need = {"type": None, "family name": None, "hgnc symbol": None}
    for k in need:
        if k not in lc:
            raise ValueError(f"Expected a {k!r} column; found {list(df.columns)}")
        need[k] = lc[k]
    g = df[df[need["type"]].str.lower().str.contains("gpcr")]
    g = g[g[need["hgnc symbol"]].str.strip() != ""]
    out = pd.DataFrame({
        "gene": g[need["hgnc symbol"]].str.strip().str.upper(),
        "status": g[need["family name"]].str.lower().str.contains(orphan_keyword).map({True: "orphan", False: "characterized"}),
        "source": "iuphar-import",
        "note": g[need["family name"]],
    }).drop_duplicates("gene")
    out.to_csv(out_csv, index=False)
    return len(out)
