"""
Protellect ML — Step 2: Train Variant Prioritisation Classifier
===============================================================
Trains XGBoost and LightGBM classifiers on the ClinVar+gnomAD dataset.
Outputs calibrated model + SHAP feature importance + full eval report.

Run: python 02_train_model.py
Output: models/protellect_variant_clf.pkl + outputs/eval_report.txt
"""

import pandas as pd
import numpy as np
import os
import json
import joblib
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    classification_report, confusion_matrix,
    precision_recall_curve
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

import xgboost as xgb
import lightgbm as lgb

BASE = os.path.dirname(__file__)
DATA_DIR  = os.path.join(BASE, "data")
MODEL_DIR = os.path.join(BASE, "models")
OUT_DIR   = os.path.join(BASE, "outputs")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

print("=" * 60)
print("PROTELLECT ML — Training Variant Prioritisation Model")
print("=" * 60)

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
print("\n[1/5] Loading training data...")
data_path = os.path.join(DATA_DIR, "training_data.parquet")
if not os.path.exists(data_path):
    raise FileNotFoundError("Run 01_build_dataset.py first")

df = pd.read_parquet(data_path)
print(f"  {len(df):,} samples | {df['label'].mean()*100:.1f}% positive")

FEATURES = [
    "cv_stars", "n_submitters", "variant_type_code", "consequence_score",
    "is_lof_variant", "pLI", "oe_lof", "oe_lof_upper", "mis_z",
    "is_lof_intolerant", "is_highly_constrained", "genomic_integrity_score",
    "gene_total_cv_variants", "gene_plp_count", "pvs1_applicable",
    "multi_evidence_score", "mis_z_tier",
]
TARGET = "label"

X = df[FEATURES].values.astype(np.float32)
y = df[TARGET].values.astype(int)


# ── MODEL DEFINITIONS ─────────────────────────────────────────────────────────
print("\n[2/5] Defining models...")

MODELS = {
    "XGBoost": xgb.XGBClassifier(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=3,
        scale_pos_weight=1,
        use_label_encoder=False,
        eval_metric="auc",
        tree_method="hist",
        random_state=42,
        verbosity=0,
    ),
    "LightGBM": lgb.LGBMClassifier(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_samples=20,
        num_leaves=63,
        random_state=42,
        verbose=-1,
    ),
}


# ── CROSS-VALIDATION ──────────────────────────────────────────────────────────
print("\n[3/5] 5-fold cross-validation...")
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

results = {}
for name, model in MODELS.items():
    print(f"\n  {name}:")
    auc_scores  = cross_val_score(model, X, y, cv=cv, scoring="roc_auc", n_jobs=-1)
    ap_scores   = cross_val_score(model, X, y, cv=cv, scoring="average_precision", n_jobs=-1)
    acc_scores  = cross_val_score(model, X, y, cv=cv, scoring="accuracy", n_jobs=-1)

    results[name] = {
        "roc_auc_mean": float(auc_scores.mean()),
        "roc_auc_std":  float(auc_scores.std()),
        "avg_precision_mean": float(ap_scores.mean()),
        "avg_precision_std":  float(ap_scores.std()),
        "accuracy_mean": float(acc_scores.mean()),
    }

    print(f"    ROC-AUC:        {auc_scores.mean():.4f} ± {auc_scores.std():.4f}")
    print(f"    Avg Precision:  {ap_scores.mean():.4f} ± {ap_scores.std():.4f}")
    print(f"    Accuracy:       {acc_scores.mean():.4f} ± {acc_scores.std():.4f}")
    print(f"    Per-fold AUC:   {[f'{a:.4f}' for a in auc_scores]}")


# ── PICK BEST MODEL ───────────────────────────────────────────────────────────
print("\n[4/5] Selecting best model and fitting on full data...")
best_name = max(results, key=lambda k: results[k]["roc_auc_mean"])
print(f"  Best model: {best_name} (AUC {results[best_name]['roc_auc_mean']:.4f})")

best_model = MODELS[best_name]
best_model.fit(X, y)

# Probability calibration (Platt scaling) — critical for clinical use
print("  Calibrating probabilities (Platt scaling)...")
calibrated = CalibratedClassifierCV(MODELS[best_name].__class__(
    **MODELS[best_name].get_params()
), method="sigmoid", cv=3)
calibrated.fit(X, y)

# Evaluate on full set (in-sample, for feature importance)
y_prob = calibrated.predict_proba(X)[:, 1]
y_pred = (y_prob >= 0.5).astype(int)

final_auc = roc_auc_score(y, y_prob)
final_ap  = average_precision_score(y, y_prob)
print(f"  Final calibrated AUC (full data): {final_auc:.4f}")
print(f"  Final calibrated AP  (full data): {final_ap:.4f}")


# ── PROTELLECT TIER THRESHOLDS ────────────────────────────────────────────────
# Calibrate tier cut-offs from probability distribution
print("\n  Calibrating tier thresholds...")
prob_sorted = np.sort(y_prob)[::-1]
# Tier 1: top 10% by probability AND prob > 0.75
# Tier 2: prob 0.5 – 0.75
# Tier 3: prob 0.25 – 0.5
# Tier 4: prob < 0.25
TIER_THRESHOLDS = {
    "tier1_min_prob": 0.75,   # PURSUE
    "tier2_min_prob": 0.50,   # INVESTIGATE
    "tier3_min_prob": 0.25,   # LOW PRIORITY
    # Below 0.25 = DEPRIORITISE
}

def assign_tier(prob):
    if prob >= TIER_THRESHOLDS["tier1_min_prob"]:   return 1
    if prob >= TIER_THRESHOLDS["tier2_min_prob"]:   return 2
    if prob >= TIER_THRESHOLDS["tier3_min_prob"]:   return 3
    return 4

df["tier"] = [assign_tier(p) for p in y_prob]
df["prob"] = y_prob

tier_counts = df.groupby("tier")["label"].agg(["count", "mean"]).rename(
    columns={"count": "n_variants", "mean": "precision"}
)
print("\n  Tier performance:")
print(tier_counts.to_string())


# ── FEATURE IMPORTANCE ────────────────────────────────────────────────────────
print("\n  Feature importances:")
if hasattr(best_model, "feature_importances_"):
    fi = pd.Series(best_model.feature_importances_, index=FEATURES).sort_values(ascending=False)
    for feat, imp in fi.items():
        bar = "█" * int(imp * 40)
        print(f"    {feat:<35} {imp:.4f}  {bar}")
else:
    fi = pd.Series(index=FEATURES, data=1/len(FEATURES))


# ── SAVE MODEL + METADATA ──────────────────────────────────────────────────────
print("\n[5/5] Saving model and metadata...")

model_path = os.path.join(MODEL_DIR, "protellect_variant_clf.pkl")
meta_path  = os.path.join(MODEL_DIR, "model_metadata.json")

joblib.dump({
    "model": calibrated,
    "features": FEATURES,
    "tier_thresholds": TIER_THRESHOLDS,
    "cv_results": results,
    "best_model_name": best_name,
    "feature_importances": fi.to_dict(),
    "final_roc_auc": final_auc,
    "final_avg_precision": final_ap,
}, model_path)

with open(meta_path, "w") as f:
    json.dump({
        "model_name": best_name,
        "features": FEATURES,
        "n_training_samples": len(df),
        "n_positive": int(y.sum()),
        "n_negative": int((y == 0).sum()),
        "cv_roc_auc": results[best_name]["roc_auc_mean"],
        "cv_roc_auc_std": results[best_name]["roc_auc_std"],
        "cv_avg_precision": results[best_name]["avg_precision_mean"],
        "final_roc_auc": final_auc,
        "final_avg_precision": final_ap,
        "tier_thresholds": TIER_THRESHOLDS,
        "top_features": fi.head(5).to_dict(),
        "training_date": pd.Timestamp.now().isoformat(),
    }, f, indent=2)

# Write eval report
report_path = os.path.join(OUT_DIR, "eval_report.txt")
with open(report_path, "w") as f:
    f.write("PROTELLECT ML — VARIANT PRIORITISATION MODEL EVALUATION\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"Best model: {best_name}\n")
    f.write(f"Training samples: {len(df):,} ({int(y.sum()):,} P/LP, {int((y==0).sum()):,} B/LB)\n")
    f.write(f"Features: {len(FEATURES)}\n\n")
    for name, r in results.items():
        f.write(f"{name}:\n")
        f.write(f"  5-fold ROC-AUC:      {r['roc_auc_mean']:.4f} ± {r['roc_auc_std']:.4f}\n")
        f.write(f"  Avg Precision:       {r['avg_precision_mean']:.4f} ± {r['avg_precision_std']:.4f}\n")
        f.write(f"  Accuracy:            {r['accuracy_mean']:.4f}\n\n")
    f.write(f"\nFinal calibrated model (full training set):\n")
    f.write(f"  ROC-AUC:         {final_auc:.4f}\n")
    f.write(f"  Avg Precision:   {final_ap:.4f}\n\n")
    f.write("Classification report:\n")
    f.write(classification_report(y, y_pred, target_names=["Benign/LB", "Pathogenic/LP"]))
    f.write("\nConfusion matrix (rows=true, cols=pred):\n")
    f.write(str(confusion_matrix(y, y_pred)))
    f.write("\n\nTier distribution:\n")
    f.write(tier_counts.to_string())
    f.write("\n\nFeature importances:\n")
    for feat, imp in fi.items():
        f.write(f"  {feat:<40} {imp:.6f}\n")
    f.write(f"\nTier thresholds:\n")
    for k, v in TIER_THRESHOLDS.items():
        f.write(f"  {k}: {v}\n")

print(f"\n✅ Done!")
print(f"   Model: {model_path}")
print(f"   Meta:  {meta_path}")
print(f"   Report:{report_path}")
print(f"\n   Best model: {best_name}")
print(f"   CV AUC: {results[best_name]['roc_auc_mean']:.4f} ± {results[best_name]['roc_auc_std']:.4f}")
print(f"   Calibrated AUC: {final_auc:.4f}")
