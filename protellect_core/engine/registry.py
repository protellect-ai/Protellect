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
    "gut": r"gut|intestin|colon|bowel|ileum|colitis|crohn|enterocyt|goblet|paneth|colonocyt",
    "immune": r"immune|\bt[ -]?cells?\b|\bcd[348]\b|\bnk\b|\bb[ -]?cells?\b|treg|\bth[0-9]+\b|dendritic|monocyt|myeloid|plasma cell|mast cell|\btam\b|microglia|lymph|macrophag|neutrophil|eosinophil|basophil|leukocyte|inflamm",
    "brain": r"brain|neuron|neural|neuro(?!phil)|striat|hypothalam|cortex|cns|habenula|astrocyt|oligodendro|microglia",
    "kidney": r"kidney|renal|nephr|podocyt|tubul",
    "liver": r"liver|hepat",
    "heart": r"heart|cardi|myocard",
    "vasculature": r"vascul|endotheli|artery|blood vessel|pericyt",
    "placenta": r"placent",
    "muscle": r"muscle|myo",
    "lung": r"lung|pulmon|airway|alveol|pneumocyt",
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
    """Guide to Pharmacology targets-and-families file -> registry CSV (gene, status, family, aliases, source, note). Returns the number of GPCRs.
    The first line holds the database version (quoted or not), so the header row is found by looking for it, not by position."""
    import re
    with open(src_csv, encoding="utf-8-sig", errors="replace") as fh:
        head = [fh.readline() for _ in range(6)]
    skip = next((n for n, l in enumerate(head) if "family name" in l.lower() and "hgnc symbol" in l.lower()), None)
    if skip is None:
        raise ValueError("Could not find the header row (needs 'Family name' and 'HGNC symbol'). Is this the targets-and-families file?")
    df = pd.read_csv(src_csv, skiprows=skip, dtype=str, encoding="utf-8-sig", encoding_errors="replace").fillna("")
    lc = {c.strip().lower(): c for c in df.columns}
    for k in ("type", "family name", "hgnc symbol"):
        if k not in lc:
            raise ValueError(f"Expected a {k!r} column; found {list(df.columns)}")
    g = df[df[lc["type"]].str.lower().str.contains("gpcr")]
    g = g[g[lc["hgnc symbol"]].str.strip() != ""]
    strip = lambda x: re.sub(r"<[^>]+>", "", x)
    syn = g[lc["synonyms"]] if "synonyms" in lc else pd.Series("", index=g.index)
    abbr = g[lc["target abbreviated name"]] if "target abbreviated name" in lc else pd.Series("", index=g.index)
    out = pd.DataFrame({
        "gene": g[lc["hgnc symbol"]].str.strip().str.upper(),
        "status": g[lc["family name"]].str.lower().str.contains(orphan_keyword).map({True: "orphan", False: "characterized"}),
        "family": g[lc["family name"]],
        "aliases": [strip(f"{a}|{s_}").strip("|") for a, s_ in zip(abbr, syn)],
        "source": "iuphar-import",
        "note": g[lc["family name"]],
    })
    out = out.sort_values("status").drop_duplicates("gene")        # a target listed in several families: an orphan listing wins only if it is the only one
    out.to_csv(out_csv, index=False)
    return len(out)


def load_registry_text(csv_text: str) -> Dict[str, dict]:
    """Registry from CSV text (columns: gene, status; optional: family, aliases, note)."""
    import io
    df = pd.read_csv(io.StringIO(csv_text), dtype=str).fillna("")
    if not {"gene", "status"} <= set(df.columns):
        raise ValueError("Registry CSV needs 'gene' and 'status' columns.")
    n = len(df)
    col = lambda c: list(df[c]) if c in df.columns else [""] * n
    return {g.strip().upper(): {"status": s_.strip().lower(), "note": nt, "family": fam, "aliases": [a for a in str(al).split("|") if a.strip()]}
            for g, s_, nt, fam, al in zip(df["gene"], df["status"], col("note"), col("family"), col("aliases"))}


def convert_iuphar_bytes(data: bytes) -> str:
    """Uploaded IUPHAR targets-and-families file -> registry CSV text. Raises ValueError on an unexpected layout."""
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        src, out = os.path.join(d, "in.csv"), os.path.join(d, "out.csv")
        with open(src, "wb") as fh:
            fh.write(data)
        n = import_iuphar_csv(src, out)
        if n == 0:
            raise ValueError("No GPCR rows found. Is this the Guide to Pharmacology targets-and-families file?")
        return open(out, encoding="utf-8").read()
