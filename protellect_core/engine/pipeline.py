"""Build a sourced case library from public data, instead of typing cases by hand.

Inputs (all free downloads, versioned):
  - IUPHAR/BPS Guide to Pharmacology: targets_and_families.csv and interactions.csv   (guidetopharmacology.org, Downloads)
  - optional: Human Protein Atlas tissue expression, rna_tissue_consensus.tsv         (proteinatlas.org, Downloads)
Each case carries the PubMed IDs IUPHAR lists for the receptor's natural (endogenous) ligand. Cases are NOT expert-verified.
Ligand classes are the coarse ones IUPHAR records (peptide, metabolite), so this is a harder, blunter test than the hand-typed library.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from .schema import Case, TISSUE_VOCAB

# Human Protein Atlas tissue names -> the app's tissue vocabulary
HPA_TO_VOCAB = {
    "pancreas": "pancreas", "adipose tissue": "adipose", "colon": "gut", "small intestine": "gut", "duodenum": "gut", "stomach": "gut",
    "lymph node": "immune", "spleen": "immune", "tonsil": "immune", "bone marrow": "immune", "thymus": "immune",
    "cerebral cortex": "brain", "hippocampus": "brain", "cerebellum": "brain", "hypothalamus": "brain", "amygdala": "brain", "basal ganglia": "brain",
    "kidney": "kidney", "liver": "liver", "heart muscle": "heart", "placenta": "vasculature" if False else "placenta",
    "skeletal muscle": "muscle", "smooth muscle": "muscle", "lung": "lung", "thyroid gland": "endocrine", "adrenal gland": "endocrine", "pituitary gland": "endocrine",
}


def file_version(path) -> str:
    """The '# GtoPdb Version: ...' header line, or the file's SHA-256 if there is none."""
    p = Path(path)
    first = p.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    return first.strip('"# ').strip() if "GtoPdb" in first else "sha256:" + sha256(p)


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read(path) -> pd.DataFrame:
    p = Path(path)
    first = p.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    return pd.read_csv(p, sep="\t" if str(p).endswith(".tsv") else ",", skiprows=1 if "GtoPdb" in first else 0, low_memory=False)


def band_of(loc) -> Optional[str]:
    m = re.match(r"(\d+|X|Y)([pq])(\d+)?", str(loc))
    return "".join(m.group(1, 2, 3)) if m and m.group(3) else None


def load_tissues(hpa_tsv, min_ntpm: float = 10.0) -> Dict[str, List[str]]:
    """gene symbol -> tissues (in the app's vocabulary) where the Human Protein Atlas reports expression >= min_ntpm."""
    d = pd.read_csv(hpa_tsv, sep="\t")
    gcol = next(c for c in d.columns if c.lower() in ("gene name", "gene_name", "gene"))
    tcol = next(c for c in d.columns if c.lower() == "tissue")
    vcol = next(c for c in d.columns if c.lower() in ("ntpm", "tpm", "ptpm"))
    out: Dict[str, set] = {}
    for g, t, v in zip(d[gcol], d[tcol], d[vcol]):
        voc = HPA_TO_VOCAB.get(str(t).strip().lower())
        if voc and v == v and float(v) >= min_ntpm:
            out.setdefault(str(g).upper(), set()).add(voc)
    return {g: sorted(s) for g, s in out.items()}


def labelled_table(targets_csv, interactions_csv) -> pd.DataFrame:
    """One row per human GPCR with a natural peptide or metabolite ligand: symbol, class, ligand, band, PubMed IDs."""
    t, i = _read(targets_csv), _read(interactions_csv)
    g = t[(t.Type == "gpcr") & t["HGNC symbol"].notna()][["HGNC symbol", "Human genetic localisation"]].drop_duplicates("HGNC symbol")
    e = i[(i["Target Species"] == "Human") & (i["Endogenous"] == True) & i["Target Gene Symbol"].isin(g["HGNC symbol"])]  # noqa: E712
    cls = e.groupby("Target Gene Symbol")["Ligand Type"].agg(lambda s: s.value_counts().index[0]).rename("cls").reset_index()
    pm = e.groupby("Target Gene Symbol")["PubMed ID"].agg(lambda s: sorted({x.strip() for v in s.dropna() for x in str(v).split("|") if x.strip()})[:3]).rename("pmids")
    lig = e.groupby("Target Gene Symbol")["Ligand"].agg(lambda s: s.value_counts().index[0]).rename("ligand")
    d = cls.merge(g, left_on="Target Gene Symbol", right_on="HGNC symbol").merge(pm, left_on="Target Gene Symbol", right_index=True).merge(lig, left_on="Target Gene Symbol", right_index=True)
    d = d[d.cls.isin(["Peptide", "Metabolite"])].copy()
    d["band"] = d["Human genetic localisation"].map(band_of)
    return d.reset_index(drop=True)


def orphan_table(targets_csv) -> pd.DataFrame:
    t = _read(targets_csv)
    o = t[(t.Type == "gpcr") & t["HGNC symbol"].notna() & t["Family name"].str.contains("rphan", na=False)][["HGNC symbol", "Family name", "Human genetic localisation"]].drop_duplicates("HGNC symbol").copy()
    o["band"] = o["Human genetic localisation"].map(band_of)
    return o.reset_index(drop=True)


def build_cases(targets_csv, interactions_csv, hpa_tsv=None) -> List[Case]:
    d = labelled_table(targets_csv, interactions_csv)
    tissues = load_tissues(hpa_tsv) if hpa_tsv else {}
    bands = d.groupby("band")["HGNC symbol"].apply(list).to_dict()
    ver = file_version(interactions_csv)
    out = []
    for _, r in d.iterrows():
        sym = r["HGNC symbol"]
        nb = [x for x in bands.get(r.band, []) if x != sym] if r.band else []
        out.append(Case(id=sym, gene=sym, resolution_year=2026, ligand=str(r["ligand"]), ligand_class=r.cls.lower(), coupling="Gq",
                        cluster=r.band or "", neighbors=nb, tissues=tissues.get(sym.upper(), []),
                        later_outcome="", citations=[f"PMID {x}" for x in r["pmids"]], verified=False,
                        notes=f"From {ver}. Class is IUPHAR's coarse ligand type. Not expert-verified."))
    return out
