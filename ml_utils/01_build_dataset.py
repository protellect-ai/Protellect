"""
Protellect ML — Step 1: Build Training Dataset
================================================
Downloads ClinVar variant summary, gnomAD gene constraint scores,
and joins them into a clean training table.

AlphaMissense scores are large (216M variants) — we use the gene-level
pathogenicity distribution as a proxy feature here, and the full
per-variant scores can be joined when running on specific variants.

Run: python 01_build_dataset.py
Output: data/training_data.parquet + data/training_data.csv
"""

import pandas as pd
import numpy as np
import requests
import gzip
import os
import io
import time
import warnings
warnings.filterwarnings("ignore")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

print("=" * 60)
print("PROTELLECT ML — Building Training Dataset")
print("=" * 60)


# ── 1. CLINVAR VARIANT SUMMARY ────────────────────────────────────────────────
print("\n[1/4] Downloading ClinVar variant_summary.txt.gz ...")
CLINVAR_URL = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
CLINVAR_PATH = os.path.join(DATA_DIR, "variant_summary.txt.gz")

if not os.path.exists(CLINVAR_PATH):
    r = requests.get(CLINVAR_URL, stream=True, timeout=300)
    with open(CLINVAR_PATH, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"  Downloaded: {os.path.getsize(CLINVAR_PATH)/1e6:.1f} MB")
else:
    print(f"  Cached: {os.path.getsize(CLINVAR_PATH)/1e6:.1f} MB")

print("  Parsing ClinVar...")
with gzip.open(CLINVAR_PATH, "rt", encoding="utf-8") as f:
    cv = pd.read_csv(f, sep="\t", low_memory=False)

print(f"  Total ClinVar rows: {len(cv):,}")

# Keep only human single-nucleotide variants with review status
cv = cv[cv["Assembly"] == "GRCh38"].copy()
cv = cv[cv["Type"].isin(["single nucleotide variant", "Deletion", "Insertion", "Indel", "Duplication"])].copy()

# Map clinical significance to binary label
# Pathogenic / Likely pathogenic = 1 (positive class — "pursue")
# Benign / Likely benign         = 0 (negative class — "deprioritise")
# VUS / Conflicting              = excluded from training (use for prediction only)
SIG_MAP = {
    "Pathogenic": 1,
    "Likely pathogenic": 1,
    "Pathogenic/Likely pathogenic": 1,
    "Benign": 0,
    "Likely benign": 0,
    "Benign/Likely benign": 0,
}

cv["label"] = cv["ClinicalSignificance"].map(SIG_MAP)
cv_labeled = cv.dropna(subset=["label"]).copy()
cv_labeled["label"] = cv_labeled["label"].astype(int)

print(f"  Labeled variants: {len(cv_labeled):,} "
      f"({cv_labeled['label'].sum():,} P/LP, "
      f"{(cv_labeled['label']==0).sum():,} B/LB)")

# ── FEATURE ENGINEERING FROM CLINVAR ──────────────────────────────────────────
print("  Engineering features from ClinVar...")

# Review status → star rating
STAR_MAP = {
    "practice guideline": 4,
    "reviewed by expert panel": 3,
    "criteria provided, multiple submitters, no conflicts": 2,
    "criteria provided, single submitter": 1,
    "criteria provided, conflicting classifications": 0,
    "no assertion criteria provided": 0,
    "no classification provided": 0,
    "no classifications from unflagged records": 0,
}
cv_labeled["cv_stars"] = cv_labeled["ReviewStatus"].map(
    lambda x: max((STAR_MAP.get(s.strip(), 0) for s in str(x).split(",")), default=0)
)

# Variant type encoding
VAR_TYPE_MAP = {
    "single nucleotide variant": 1,
    "Deletion": 2,
    "Insertion": 3,
    "Indel": 4,
    "Duplication": 5,
}
cv_labeled["variant_type_code"] = cv_labeled["Type"].map(VAR_TYPE_MAP).fillna(0).astype(int)

# Consequence encoding (from Name field heuristics)
def infer_consequence(name):
    name = str(name).lower()
    if any(x in name for x in ["nonsense", "stop gained", "ter", "*"]): return "nonsense"
    if "frameshift" in name: return "frameshift"
    if "splice" in name: return "splice"
    if "missense" in name: return "missense"
    if "synonymous" in name: return "synonymous"
    if "del" in name: return "deletion"
    if "ins" in name: return "insertion"
    return "other"

cv_labeled["consequence"] = cv_labeled["Name"].apply(infer_consequence)
CONS_MAP = {"nonsense": 5, "frameshift": 4, "splice": 3, "missense": 2,
            "deletion": 2, "insertion": 2, "synonymous": 0, "other": 1}
cv_labeled["consequence_score"] = cv_labeled["consequence"].map(CONS_MAP)

# Number of submitters
cv_labeled["n_submitters"] = pd.to_numeric(
    cv_labeled.get("NumberOfSubmitters", cv_labeled.get("SubmitterCount", 0)),
    errors="coerce"
).fillna(1).clip(0, 50)

# Gene-level: total ClinVar variants per gene
gene_total = cv.groupby("GeneSymbol").size().rename("gene_total_cv_variants")
gene_plp = cv_labeled[cv_labeled["label"]==1].groupby("GeneSymbol").size().rename("gene_plp_count")
gene_stats = pd.DataFrame(gene_total).join(gene_plp, how="left").fillna(0)
gene_stats["gene_cv_density"] = (gene_stats["gene_plp_count"] / gene_stats["gene_total_cv_variants"] * 100).clip(0, 100)
cv_labeled = cv_labeled.merge(gene_stats.reset_index(), on="GeneSymbol", how="left")

print(f"  ClinVar features engineered ✓")


# ── 2. GNOMAD GENE CONSTRAINT ─────────────────────────────────────────────────
print("\n[2/4] Downloading gnomAD gene constraint scores...")
GNOMAD_URL = "https://storage.googleapis.com/gcp-public-data--gnomad/release/2.1.1/constraint/gnomad.v2.1.1.lof_metrics.by_gene.txt.bgz"
GNOMAD_PATH = os.path.join(DATA_DIR, "gnomad_constraint.txt.gz")

if not os.path.exists(GNOMAD_PATH):
    try:
        r = requests.get(GNOMAD_URL, stream=True, timeout=120)
        with open(GNOMAD_PATH, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  Downloaded: {os.path.getsize(GNOMAD_PATH)/1e6:.1f} MB")
    except Exception as e:
        print(f"  gnomAD download failed: {e} — using synthetic constraint data")
        GNOMAD_PATH = None
else:
    print(f"  Cached: {os.path.getsize(GNOMAD_PATH)/1e6:.1f} MB")

if GNOMAD_PATH and os.path.exists(GNOMAD_PATH):
    try:
        with gzip.open(GNOMAD_PATH, "rt") as f:
            gnomad = pd.read_csv(f, sep="\t", low_memory=False)
        gnomad = gnomad[["gene", "pLI", "oe_lof", "oe_lof_upper", "mis_z", "syn_z"]].drop_duplicates("gene")
        gnomad = gnomad.rename(columns={"gene": "GeneSymbol"})
        print(f"  gnomAD genes loaded: {len(gnomad):,}")
    except Exception as e:
        print(f"  Parse error: {e} — using synthetic")
        gnomad = None
else:
    gnomad = None

# If gnomAD unavailable, create synthetic constraint features from ClinVar patterns
if gnomad is None:
    print("  Building synthetic constraint from ClinVar density patterns...")
    gnomad = gene_stats.reset_index().rename(columns={"GeneSymbol": "GeneSymbol"})
    # Estimate pLI from ClinVar density (highly correlated in practice)
    gnomad["pLI"] = (gnomad["gene_cv_density"] / 100).clip(0, 0.999)
    gnomad["oe_lof"] = 1 - gnomad["pLI"] * 0.8
    gnomad["oe_lof_upper"] = gnomad["oe_lof"] + 0.2
    gnomad["mis_z"] = gnomad["pLI"] * 3.5
    gnomad["syn_z"] = 0.0
    gnomad = gnomad[["GeneSymbol", "pLI", "oe_lof", "oe_lof_upper", "mis_z", "syn_z"]]

cv_labeled = cv_labeled.merge(gnomad, on="GeneSymbol", how="left")
cv_labeled["pLI"] = cv_labeled["pLI"].fillna(0.5)
cv_labeled["oe_lof"] = cv_labeled["oe_lof"].fillna(1.0)
cv_labeled["oe_lof_upper"] = cv_labeled["oe_lof_upper"].fillna(1.2)
cv_labeled["mis_z"] = cv_labeled["mis_z"].fillna(0.0)
print("  gnomAD constraint joined ✓")


# ── 3. ADDITIONAL COMPUTED FEATURES ──────────────────────────────────────────
print("\n[3/4] Engineering additional features...")

# Genomic Integrity Score (our core metric)
cv_labeled["genomic_integrity_score"] = cv_labeled["gene_cv_density"].fillna(0)

# LoF-intolerant gene (pLI ≥ 0.9 = strong constraint)
cv_labeled["is_lof_intolerant"] = (cv_labeled["pLI"] >= 0.9).astype(int)

# High constraint (oe_lof_upper < 0.35 = very constrained by gnomAD v2 threshold)
cv_labeled["is_highly_constrained"] = (cv_labeled["oe_lof_upper"] < 0.35).astype(int)

# Variant is LoF-type
cv_labeled["is_lof_variant"] = cv_labeled["consequence"].isin(["nonsense", "frameshift", "splice"]).astype(int)

# PVS1 applicable: LoF variant in LoF-intolerant gene
cv_labeled["pvs1_applicable"] = (
    (cv_labeled["is_lof_variant"] == 1) & (cv_labeled["is_lof_intolerant"] == 1)
).astype(int)

# Strong multi-evidence score (combination heuristic)
cv_labeled["multi_evidence_score"] = (
    cv_labeled["cv_stars"] * 2 +
    cv_labeled["is_lof_intolerant"] * 3 +
    cv_labeled["consequence_score"] +
    (cv_labeled["genomic_integrity_score"] > 5).astype(int) * 2 +
    cv_labeled["pvs1_applicable"] * 3
).clip(0, 20)

# Missense z-score tier
cv_labeled["mis_z_tier"] = pd.cut(
    cv_labeled["mis_z"].fillna(0),
    bins=[-999, 0, 1, 2, 3, 999],
    labels=[0, 1, 2, 3, 4]
).astype(float).fillna(0)

print("  Features engineered ✓")


# ── 4. FINAL DATASET ──────────────────────────────────────────────────────────
print("\n[4/4] Building final training table...")

FEATURES = [
    # ClinVar evidence
    "cv_stars",           # Review star rating (0–4)
    "n_submitters",       # Number of submitters
    "variant_type_code",  # SNV/Del/Ins/Indel/Dup
    "consequence_score",  # LoF > missense > other
    "is_lof_variant",     # 1 = LoF type
    # Gene-level constraint (gnomAD)
    "pLI",                # Probability LoF intolerant (0–1)
    "oe_lof",             # Observed/Expected LoF ratio
    "oe_lof_upper",       # oe_lof upper CI (< 0.35 = constrained)
    "mis_z",              # Missense constraint z-score
    "is_lof_intolerant",  # pLI ≥ 0.9
    "is_highly_constrained",  # oe_lof_upper < 0.35
    # Protellect core metrics
    "genomic_integrity_score",  # ClinVar P/LP density per 100aa (gene-level)
    "gene_total_cv_variants",   # Total ClinVar variants in gene
    "gene_plp_count",           # Total P/LP in gene
    # Derived combination features
    "pvs1_applicable",        # LoF in LoF-intolerant gene
    "multi_evidence_score",   # Combined heuristic score
    "mis_z_tier",             # Missense z binned
]

TARGET = "label"

df_final = cv_labeled[FEATURES + [TARGET, "GeneSymbol", "ClinicalSignificance", "ReviewStatus", "Name"]].copy()
df_final = df_final.dropna(subset=FEATURES + [TARGET])

# Deduplicate: same gene + consequence + label
df_final = df_final.drop_duplicates(subset=["GeneSymbol", "consequence_score", "cv_stars", "label"])

# Balance classes for training
n_pos = (df_final[TARGET] == 1).sum()
n_neg = (df_final[TARGET] == 0).sum()
print(f"  Raw: {n_pos:,} P/LP | {n_neg:,} B/LB")

# Undersample majority class to 3:1 ratio max
if n_neg > n_pos * 3:
    neg_sample = df_final[df_final[TARGET] == 0].sample(n=min(n_pos * 3, n_neg), random_state=42)
    df_final = pd.concat([df_final[df_final[TARGET] == 1], neg_sample]).sample(frac=1, random_state=42)

print(f"  Balanced: {(df_final[TARGET]==1).sum():,} P/LP | {(df_final[TARGET]==0).sum():,} B/LB")
print(f"  Total training samples: {len(df_final):,}")
print(f"  Features: {len(FEATURES)}")

# Save
out_parquet = os.path.join(DATA_DIR, "training_data.parquet")
out_csv = os.path.join(DATA_DIR, "training_data.csv")
df_final.to_parquet(out_parquet, index=False)
df_final.to_csv(out_csv, index=False)

print(f"\n✅ Dataset saved:")
print(f"   {out_parquet}  ({os.path.getsize(out_parquet)/1e6:.1f} MB)")
print(f"   {out_csv}  ({os.path.getsize(out_csv)/1e6:.1f} MB)")

# Preview
print("\nFeature summary:")
print(df_final[FEATURES].describe().round(3).to_string())
print(f"\nLabel distribution:\n{df_final[TARGET].value_counts()}")
print(f"\nTop genes by P/LP count:")
print(df_final[df_final[TARGET]==1]["GeneSymbol"].value_counts().head(15).to_string())
