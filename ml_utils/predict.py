"""
Protellect ML — Step 3: Inference Module
=========================================
Drop-in replacement for the rule-based VUS scoring in the app.
Import this in app.py and call score_variant() instead of
the manual tier calculation.

Usage in app.py:
    from protellect_ml.predict import score_variant
    result = score_variant(
        gene="BRCA1",
        consequence="missense",
        gnomad_af=0.0,
        alphamissense_score=0.82,
        clinvar_stars=2,
        plddt=85.0,
        pli=0.998,
        cv_density=35.3,
    )
    tier = result["tier"]          # 1–4
    prob = result["probability"]   # 0.0–1.0
    explanation = result["explanation"]
"""

import os
import numpy as np
import joblib
from pathlib import Path

# ── MODEL LOADING ─────────────────────────────────────────────────────────────
_MODEL_PACK = None
_MODEL_PATH = Path(__file__).parent / "models" / "protellect_variant_clf.pkl"

def _load_model():
    global _MODEL_PACK
    if _MODEL_PACK is None:
        if not _MODEL_PATH.exists():
            return None
        _MODEL_PACK = joblib.load(_MODEL_PATH)
    return _MODEL_PACK


# ── FEATURE MAPPINGS ──────────────────────────────────────────────────────────
CONSEQUENCE_SCORE = {
    "nonsense": 5, "stop_gained": 5, "stop gained": 5,
    "frameshift": 4, "frameshift_variant": 4,
    "splice": 3, "splice_site": 3, "splice_acceptor": 3, "splice_donor": 3,
    "missense": 2, "missense_variant": 2,
    "in_frame_deletion": 2, "in_frame_insertion": 2,
    "deletion": 2, "insertion": 2,
    "synonymous": 0, "synonymous_variant": 0,
    "other": 1,
}

VARIANT_TYPE_CODE = {
    "snv": 1, "single nucleotide variant": 1, "snp": 1,
    "deletion": 2, "del": 2,
    "insertion": 3, "ins": 3,
    "indel": 4,
    "duplication": 5, "dup": 5,
}

TIER_LABELS = {
    1: ("PURSUE IMMEDIATELY",  "#22c55e", "Strong multi-evidence support. Full wet-lab investment justified."),
    2: ("INVESTIGATE FURTHER", "#ffd60a", "Moderate evidence. Additional functional data recommended before commitment."),
    3: ("LOW PRIORITY",        "#ff8c42", "Weak evidence. Computational triage only — do not commit wet-lab budget yet."),
    4: ("DEPRIORITISE",        "#ff2d55", "Insufficient evidence. Common in population or lacking conservation support."),
}


# ── RULE-BASED FALLBACK (used when model not loaded) ─────────────────────────
def _rule_based_score(
    consequence: str,
    clinvar_stars: int,
    pli: float,
    cv_density: float,
    gnomad_af: float,
    alphamissense_score: float,
    plddt: float,
) -> float:
    """Reproduce the existing Protellect tier system as a probability proxy."""
    score = 0.0
    max_score = 18.0

    # ClinVar stars (0–8 points)
    score += min(clinvar_stars * 2, 8)

    # Gene constraint (0–3 points)
    if pli >= 0.9:   score += 3
    elif pli >= 0.5: score += 1.5

    # Consequence type (0–5 points)
    cons_norm = consequence.lower().replace(" ", "_")
    score += CONSEQUENCE_SCORE.get(cons_norm, CONSEQUENCE_SCORE.get(consequence.lower(), 1))

    # gnomAD frequency (0–2 points)
    if gnomad_af == 0:       score += 2
    elif gnomad_af < 0.0001: score += 1.5
    elif gnomad_af < 0.001:  score += 1
    else: score -= 1  # too common for dominant disease

    # AlphaMissense (0–2 points for missense only)
    if "missense" in consequence.lower():
        if alphamissense_score >= 0.70: score += 2
        elif alphamissense_score >= 0.34: score += 1
        else: score -= 0.5

    # pLDDT structural confidence (0–1 point)
    if plddt >= 70: score += 1

    # Genomic integrity (0–2 points)
    if cv_density > 10: score += 2
    elif cv_density > 5: score += 1

    return max(0.0, min(score / max_score, 1.0))


# ── MAIN INFERENCE FUNCTION ───────────────────────────────────────────────────
def score_variant(
    gene: str = "",
    consequence: str = "missense",
    gnomad_af: float = 0.0,
    alphamissense_score: float = 0.0,
    clinvar_stars: int = 0,
    plddt: float = 50.0,
    pli: float = 0.5,
    cv_density: float = 0.0,
    gene_total_cv: int = 0,
    gene_plp_count: int = 0,
    n_submitters: int = 1,
    variant_type: str = "snv",
    oe_lof: float = 1.0,
    oe_lof_upper: float = 1.2,
    mis_z: float = 0.0,
) -> dict:
    """
    Score a variant and assign a Protellect priority tier.

    Returns:
        {
            "tier":        int (1–4),
            "probability": float (0–1, calibrated),
            "label":       str  ("PURSUE IMMEDIATELY" etc),
            "color":       str  (hex colour for UI),
            "explanation": str  (human-readable reason),
            "features":    dict (feature vector used),
            "source":      str  ("ml_model" or "rule_based"),
        }
    """
    # ── Encode features ──────────────────────────────────────────────────────
    cons_norm = consequence.lower().replace(" ", "_")
    cons_score = CONSEQUENCE_SCORE.get(cons_norm, CONSEQUENCE_SCORE.get(consequence.lower(), 1))
    vtype_code = VARIANT_TYPE_CODE.get(variant_type.lower(), 1)
    is_lof = int(cons_score >= 3)
    is_lof_intolerant = int(pli >= 0.9)
    is_highly_constrained = int(oe_lof_upper < 0.35)
    pvs1 = int(is_lof and is_lof_intolerant)
    mis_z_tier = min(4, int(max(0, mis_z) // 1))

    multi_ev = (
        clinvar_stars * 2 +
        is_lof_intolerant * 3 +
        cons_score +
        int(cv_density > 5) * 2 +
        pvs1 * 3
    )

    feature_vector = [
        float(clinvar_stars),
        float(n_submitters),
        float(vtype_code),
        float(cons_score),
        float(is_lof),
        float(pli),
        float(oe_lof),
        float(oe_lof_upper),
        float(mis_z),
        float(is_lof_intolerant),
        float(is_highly_constrained),
        float(cv_density),
        float(gene_total_cv),
        float(gene_plp_count),
        float(pvs1),
        float(min(multi_ev, 20)),
        float(mis_z_tier),
    ]

    # ── Run model or fallback ────────────────────────────────────────────────
    pack = _load_model()
    if pack is not None:
        try:
            X = np.array(feature_vector, dtype=np.float32).reshape(1, -1)
            prob = float(pack["model"].predict_proba(X)[0, 1])
            thresholds = pack["tier_thresholds"]
            if prob >= thresholds["tier1_min_prob"]:   tier = 1
            elif prob >= thresholds["tier2_min_prob"]: tier = 2
            elif prob >= thresholds["tier3_min_prob"]: tier = 3
            else: tier = 4
            source = "ml_model"
        except Exception:
            prob = _rule_based_score(consequence, clinvar_stars, pli, cv_density, gnomad_af, alphamissense_score, plddt)
            tier = 1 if prob >= 0.75 else 2 if prob >= 0.50 else 3 if prob >= 0.25 else 4
            source = "rule_based_fallback"
    else:
        prob = _rule_based_score(consequence, clinvar_stars, pli, cv_density, gnomad_af, alphamissense_score, plddt)
        tier = 1 if prob >= 0.75 else 2 if prob >= 0.50 else 3 if prob >= 0.25 else 4
        source = "rule_based"

    label, color, base_explanation = TIER_LABELS[tier]

    # ── Generate explanation ─────────────────────────────────────────────────
    reasons = []
    if clinvar_stars >= 3: reasons.append(f"ClinVar ≥3 stars ({clinvar_stars}★ — expert review)")
    elif clinvar_stars == 2: reasons.append("ClinVar 2 stars (multiple submitters)")
    elif clinvar_stars == 0: reasons.append("Not in ClinVar / conflicting evidence")

    if pvs1: reasons.append(f"PVS1 applicable: {consequence} in LoF-intolerant gene (pLI={pli:.2f})")
    elif is_lof: reasons.append(f"LoF variant ({consequence}) in gene pLI={pli:.2f}")
    elif is_lof_intolerant: reasons.append(f"LoF-intolerant gene (pLI={pli:.2f})")

    if gnomad_af == 0: reasons.append("Absent from gnomAD (PM2 applicable)")
    elif gnomad_af < 0.0001: reasons.append(f"Very rare in gnomAD (AF={gnomad_af:.2e})")
    elif gnomad_af > 0.001: reasons.append(f"⚠ Common in gnomAD (AF={gnomad_af:.4f}) — likely benign if dominant")

    if alphamissense_score >= 0.7 and "missense" in consequence.lower():
        reasons.append(f"AlphaMissense {alphamissense_score:.2f} — likely pathogenic (PP3)")
    elif alphamissense_score > 0 and "missense" in consequence.lower():
        reasons.append(f"AlphaMissense {alphamissense_score:.2f} — ambiguous")

    if cv_density > 10: reasons.append(f"High genomic integrity score ({cv_density:.1f}% ClinVar density)")
    if plddt >= 70: reasons.append(f"Structured region (pLDDT={plddt:.0f}) — AlphaMissense score reliable")
    elif plddt < 50 and plddt > 0: reasons.append(f"Disordered region (pLDDT={plddt:.0f}) — missense may be tolerated")

    explanation = base_explanation + " " + " · ".join(reasons) if reasons else base_explanation

    return {
        "tier": tier,
        "probability": round(prob, 4),
        "label": label,
        "color": color,
        "explanation": explanation,
        "reasons": reasons,
        "features": {
            "cv_stars": clinvar_stars,
            "pLI": pli,
            "consequence_score": cons_score,
            "is_lof_variant": is_lof,
            "pvs1_applicable": pvs1,
            "genomic_integrity_score": cv_density,
            "gnomad_af": gnomad_af,
            "alphamissense_score": alphamissense_score,
            "plddt": plddt,
            "multi_evidence_score": multi_ev,
        },
        "source": source,
    }


# ── BATCH SCORING ─────────────────────────────────────────────────────────────
def score_variants_batch(variants: list) -> list:
    """
    Score multiple variants at once.
    Each variant is a dict with the same keys as score_variant().
    Returns list of result dicts in same order.
    """
    return [score_variant(**v) for v in variants]


# ── GENE-LEVEL TRIAGE (from disease search results) ───────────────────────────
def triage_gene(
    gene: str,
    pli: float = 0.5,
    cv_density: float = 0.0,
    gene_total_cv: int = 0,
    gene_plp_count: int = 0,
    mis_z: float = 0.0,
    oe_lof_upper: float = 1.0,
) -> dict:
    """
    Gene-level triage without a specific variant.
    Used when a gene appears in disease search with no variant yet identified.
    """
    # Estimate consequence from gene properties (no specific variant)
    consequence = "frameshift" if pli >= 0.9 else "missense"
    return score_variant(
        gene=gene,
        consequence=consequence,
        gnomad_af=0.0,
        alphamissense_score=0.5 if pli >= 0.9 else 0.35,
        clinvar_stars=min(int(cv_density / 10), 3),
        plddt=75.0,
        pli=pli,
        cv_density=cv_density,
        gene_total_cv=gene_total_cv,
        gene_plp_count=gene_plp_count,
        n_submitters=max(1, gene_plp_count // 3),
        variant_type="snv",
        oe_lof_upper=oe_lof_upper,
        mis_z=mis_z,
    )


# ── SELF-TEST ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Protellect ML Inference — Self-test\n")
    test_cases = [
        {
            "name": "BRCA1 c.5266dupC (classic P/LP)",
            "gene": "BRCA1", "consequence": "frameshift", "gnomad_af": 0.0,
            "alphamissense_score": 0.0, "clinvar_stars": 4, "plddt": 82,
            "pli": 0.998, "cv_density": 35.3, "gene_total_cv": 150, "gene_plp_count": 53,
        },
        {
            "name": "SCN1A p.Arg1699Cys (Dravet GoF)",
            "gene": "SCN1A", "consequence": "missense", "gnomad_af": 0.0,
            "alphamissense_score": 0.91, "clinvar_stars": 3, "plddt": 88,
            "pli": 0.97, "cv_density": 22.1, "gene_total_cv": 200, "gene_plp_count": 44,
        },
        {
            "name": "Common SNP (expected benign)",
            "gene": "GENE1", "consequence": "missense", "gnomad_af": 0.025,
            "alphamissense_score": 0.12, "clinvar_stars": 0, "plddt": 45,
            "pli": 0.05, "cv_density": 0.3, "gene_total_cv": 10, "gene_plp_count": 0,
        },
        {
            "name": "VUS missense in constrained gene",
            "gene": "SYNGAP1", "consequence": "missense", "gnomad_af": 0.000003,
            "alphamissense_score": 0.65, "clinvar_stars": 1, "plddt": 71,
            "pli": 0.99, "cv_density": 18.5, "gene_total_cv": 80, "gene_plp_count": 15,
        },
    ]

    for tc in test_cases:
        name = tc.pop("name")
        result = score_variant(**tc)
        print(f"  {name}")
        print(f"    Tier {result['tier']} | Prob {result['probability']:.3f} | {result['label']}")
        print(f"    Source: {result['source']}")
        print(f"    Reasons: {' · '.join(result['reasons'][:2])}")
        print()
