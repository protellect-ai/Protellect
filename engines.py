"""
engines.py — Genomic Integrity Scorer + Experiment ROI Engine
Every protein gets a unique experiment list based on its specific variant profile.
"""
from databases import (ARRB_GENES, GI_THRESHOLDS, VERDICT_COLORS, GPCR_STUDY_PROTOCOL,
                        FILAMIN_FRAMEWORK, KINASE_KEYWORDS, GPCR_KEYWORDS,
                        TF_KEYWORDS, ION_CH_KEYWORDS, FILAMIN_KEYWORDS, CARDIAC_GPCRS)

# ── Genomic Integrity Scorer ───────────────────────────────────────────────

def score_genomic_integrity(gene: str, clinvar_variants: list, seq_len: int) -> dict:
    """
    Compute GI score. Returns verdict, score, reasoning.
    ARRB1/ARRB2 always → DEPRIORITISE regardless of ClinVar count.
    """
    if gene.upper() in ARRB_GENES:
        return {
            "verdict": "DEPRIORITISE",
            "color": VERDICT_COLORS["DEPRIORITISE"],
            "score": 0,
            "per100": 0,
            "n_pathogenic": 0,
            "n_critical": 0,
            "density": 0,
            "multi_star_count": 0,
            "reasons": ["ARRB override: <5 confirmed Mendelian disease variants", "DKO mice viable and fertile"],
            "pursue": False,
        }

    path = [v for v in clinvar_variants if v.get("ml_class") in ("CRITICAL","HIGH")]
    n_path = len(path)
    n_critical = sum(1 for v in clinvar_variants if v.get("ml_class") == "CRITICAL")
    multi_star = sum(1 for v in path if v.get("stars", 0) >= 2)

    density  = n_path / seq_len if seq_len > 0 else 0
    per100   = density * 100

    reasons = []
    if n_path >= 5: reasons.append(f"{n_path} pathogenic/likely-pathogenic ClinVar variants")
    if multi_star >= 2: reasons.append(f"{multi_star} variants with ≥2-star expert review")
    if per100 >= 1.0: reasons.append(f"High variant density: {per100:.2f} per 100 residues")

    if per100 >= 1.0 and n_path >= 5 and multi_star >= 2:
        verdict = "DISEASE-CRITICAL"
        pursue  = True
    elif per100 >= 0.5 or n_path >= 3:
        verdict = "DISEASE-ASSOCIATED"
        pursue  = True
    elif per100 >= 0.1 or n_path >= 1:
        verdict = "MODERATE"
        pursue  = None  # selective
    elif n_path == 0:
        verdict = "NO DISEASE VARIANTS"
        pursue  = False
        reasons.append("No ClinVar P/LP variants — consider redundant pathway")
    else:
        verdict = "VERY LOW"
        pursue  = False

    return {
        "verdict": verdict,
        "color": VERDICT_COLORS.get(verdict, "#64748b"),
        "score": n_path * 10 + multi_star * 5,
        "per100": round(per100, 3),
        "n_pathogenic": n_path,
        "n_critical": n_critical,
        "density": round(density, 5),
        "multi_star_count": multi_star,
        "reasons": reasons or ["Insufficient variant density for prioritisation"],
        "pursue": pursue,
    }


# ── Experiment ROI Engine ──────────────────────────────────────────────────

def compute_experiment_roi(gene: str, gi: dict, protein_data: dict,
                            clinvar_variants: list, gnomad_data: dict,
                            string_data: list, ot_data: dict,
                            am_scores: list = None) -> list:
    """
    Generate a UNIQUE experiment list for this specific protein.
    Uses variant names, STRING partners, disease context, protein class.
    """
    gene_upper = gene.upper()
    am = am_scores or []

    # ── ARRB → show avoidance list ─────────────────────────────────────────
    if gene_upper in ARRB_GENES:
        from databases import ARRB_EXPERIMENTS_TO_AVOID
        return [{"name": e["name"], "category": "AVOID", "cost_usd": e["cost"],
                 "time_weeks": 0, "p_success": 0.0, "value_score": 0,
                 "expected_value": 0, "rationale": e["reason"],
                 "do_first": False, "avoid": True}
                for e in ARRB_EXPERIMENTS_TO_AVOID]

    # ── Determine protein class ────────────────────────────────────────────
    kws_lower = " ".join(protein_data.get("keywords", [])).lower()
    func_text  = " ".join(protein_data.get("functions", [])).lower()
    combined   = kws_lower + " " + func_text
    seq_len    = protein_data.get("seq_len", 500)

    is_gpcr    = protein_data.get("is_gpcr", False)
    is_kinase  = any(k in combined for k in KINASE_KEYWORDS)
    is_tf      = any(k in combined for k in TF_KEYWORDS)
    is_channel = any(k in combined for k in ION_CH_KEYWORDS)
    is_filamin = any(k in combined for k in FILAMIN_KEYWORDS)
    is_cardiac = gene_upper in CARDIAC_GPCRS
    is_cancer  = any("cancer" in d.get("name","").lower() or "carcinoma" in d.get("name","").lower()
                     for d in protein_data.get("diseases", []))
    is_neuro   = any(any(t in d.get("name","").lower() for t in ["neuro","parkinson","alzheimer","epilepsy","als","huntington"])
                     for d in protein_data.get("diseases", []))

    # ── AlphaMissense concordance ──────────────────────────────────────────
    path_variants = [v for v in clinvar_variants if v.get("ml_class") in ("CRITICAL","HIGH")]
    path_positions = {v["position"] for v in path_variants if v.get("position")}
    am_path_set = {a["position"] for a in am if a.get("class") == "pathogenic"}
    concordant = len(path_positions & am_path_set)
    discordant = len(path_positions - am_path_set)

    # ── STRING partners ────────────────────────────────────────────────────
    top_partners = [p["partner"] for p in string_data[:3]] if string_data else ["interacting partners"]

    # ── Top variant names ──────────────────────────────────────────────────
    top_variants = [v.get("protein_change","?") for v in path_variants[:3]]
    variant_str  = ", ".join(top_variants) if top_variants else "prioritised ClinVar variants"

    # ── Disease cell type ──────────────────────────────────────────────────
    if is_cardiac:    cell_type = "iPSC-cardiomyocytes (HL-1 or patient-derived)"
    elif is_neuro:    cell_type = "iPSC-neurons (NGN2-induced) or SH-SY5Y"
    elif is_cancer:   cell_type = "patient-derived organoids / relevant cancer cell line"
    else:             cell_type = "HEK293T or disease-relevant primary cells"

    # ── pLI ────────────────────────────────────────────────────────────────
    pLI = gnomad_data.get("pLI")
    pLI_str = f"pLI={pLI:.2f}" if pLI is not None else "pLI unknown"

    # ── Tractability ───────────────────────────────────────────────────────
    sm_tractable = ot_data.get("sm_tractable", False)
    ab_tractable = ot_data.get("ab_tractable", False)
    existing_drugs = ot_data.get("known_drugs", [])

    # ── Dominant variant type ──────────────────────────────────────────────
    n_lof = sum(1 for v in path_variants if any(t in v.get("protein_change","").lower()
               for t in ["ter","*","del","ins","fs","splice"]))
    n_mis = len(path_variants) - n_lof
    dominant_type = "LoF" if n_lof >= n_mis else "missense" if n_mis > 0 else "missense"

    experiments = []

    # ── 1. First assay based on variant type ──────────────────────────────
    if dominant_type == "LoF":
        experiments.append({
            "name": f"Western blot — {gene} protein expression in LoF backgrounds",
            "category": "Protein Expression",
            "cost_usd": 800, "time_weeks": 1, "p_success": 0.85,
            "value_score": 8, "expected_value": 6.8,
            "rationale": f"{gene} has {n_lof} LoF variants ({variant_str}). First confirm protein-level loss in patient-derived cells or CRISPR heterozygous knockout. Use anti-{gene} antibody; compare to WT control lysate.",
            "do_first": True,
        })
    elif dominant_type == "missense":
        experiments.append({
            "name": f"Thermal Shift Assay — stability of {gene} missense variants",
            "category": "Protein Stability",
            "cost_usd": 500, "time_weeks": 1, "p_success": 0.80,
            "value_score": 7, "expected_value": 5.6,
            "rationale": f"{gene} has {n_mis} missense variants ({variant_str}). TSA measures ΔTm vs WT — destabilising variants (ΔTm < -2°C) are candidates for pharmacological chaperone rescue.",
            "do_first": True,
        })

    # ── 2. GPCR-specific ──────────────────────────────────────────────────
    if is_gpcr:
        experiments.append({
            "name": f"Filamin A Ser2152-P assay — {gene} activation readout (IP ASSAY)",
            "category": "GPCR Activation — Receptor-Proximal",
            "cost_usd": 600, "time_weeks": 1, "p_success": 0.90,
            "value_score": 10, "expected_value": 9.0,
            "rationale": f"{gene} is a GPCR. Filamin Ser2152 phosphorylation is MORE receptor-proximal than cAMP, IP3, or beta-arrestin. Stimulate {cell_type} with agonist → IP anti-FLNA → pSer2152 western. Compare WT vs {variant_str}. Variant that blocks Filamin-P but not cAMP = cytoskeletal decoupling (different target). Ref: Nakamura et al. JBC 2015 (PMID 26124276).",
            "do_first": True,
        })
        experiments.append({
            "name": f"cAMP HTRF — {gene} Gs coupling, WT vs {variant_str}",
            "category": "GPCR Signalling",
            "cost_usd": 1200, "time_weeks": 2, "p_success": 0.85,
            "value_score": 8, "expected_value": 6.8,
            "rationale": f"Primary G-protein efficacy readout. Use HTRF cAMP kit (Cisbio). Compare EC50 and Emax for WT vs each ClinVar pathogenic variant. Variants with reduced Emax = partial agonism or loss-of-function.",
            "do_first": False,
        })
        if is_cardiac:
            experiments.append({
                "name": f"TMAO rattling assay — {gene} conformational disruption",
                "category": "Cardiac GPCR",
                "cost_usd": 2000, "time_weeks": 3, "p_success": 0.75,
                "value_score": 9, "expected_value": 6.75,
                "rationale": f"{gene} is a cardiac GPCR. TMAO (5–50 µM) increases receptor conformational sampling, reducing Filamin Ser2152-P — the proposed arrhythmia mechanism. Measure by FlAsH-BRET conformational transition rate. This axis is understudied and patent-unoccupied.",
                "do_first": False,
            })

    # ── 3. Filamin-specific ────────────────────────────────────────────────
    if is_filamin:
        experiments.append({
            "name": f"SPR binding — GPCR H8 FBM peptides vs {gene} Ig21 domain",
            "category": "Filamin Binding",
            "cost_usd": 3000, "time_weeks": 3, "p_success": 0.85,
            "value_score": 9, "expected_value": 7.65,
            "rationale": f"{gene} (Filamin family). Surface plasmon resonance measures KD of synthetic H8 FBM peptides (Phe-X-Arg-X-Leu pattern) vs {gene} Ig21 domain. Pathogenic variants at R2149/S2152 should reduce binding — validates therapeutic target. PhosphoSite confirms S2152 as highest phosphorylation peak.",
            "do_first": True,
        })

    # ── 4. Kinase-specific ────────────────────────────────────────────────
    if is_kinase:
        experiments.append({
            "name": f"ADP-Glo kinase activity assay — {gene} WT vs {variant_str}",
            "category": "Kinase Activity",
            "cost_usd": 1500, "time_weeks": 2, "p_success": 0.85,
            "value_score": 8, "expected_value": 6.8,
            "rationale": f"{gene} is a kinase. ADP-Glo quantifies ATP→ADP conversion. Compare Vmax and Km of WT vs pathogenic variants. Hyperactivating variants = gain-of-function = different therapeutic approach than kinase-dead LoF.",
            "do_first": True,
        })

    # ── 5. Co-IP with specific STRING partners ─────────────────────────────
    if top_partners:
        partner = top_partners[0]
        experiments.append({
            "name": f"Co-immunoprecipitation — {gene} with {partner}",
            "category": "Protein–Protein Interaction",
            "cost_usd": 700, "time_weeks": 1, "p_success": 0.80,
            "value_score": 7, "expected_value": 5.6,
            "rationale": f"STRING predicts high-confidence interaction between {gene} and {partner} (score>0.7). Co-IP validates this in {cell_type}. Flag-tagged {gene} (WT vs {variant_str}) → IP → western for {partner}. Variant that disrupts {partner} binding identifies the interaction interface for drug design.",
            "do_first": False,
        })

    # ── 6. CRISPR (only if evidence justifies) ────────────────────────────
    crispr_justified = gi.get("n_critical", 0) >= 2 and concordant >= 1
    if crispr_justified:
        experiments.append({
            "name": f"CRISPR knock-in — {gene} {top_variants[0] if top_variants else 'p.Var'} in {cell_type}",
            "category": "Disease Modelling",
            "cost_usd": 15000, "time_weeks": 10, "p_success": 0.70,
            "value_score": 9, "expected_value": 6.3,
            "rationale": f"Justified: {gi['n_critical']} CRITICAL ClinVar variants + {concordant} AlphaMissense-concordant. Knock-in {variant_str} into {cell_type}. Primary readout: {'Filamin Ser2152-P' if is_gpcr else 'disease-relevant phenotype'}. ({pLI_str} — {'essential gene, proceed with care' if gnomad_data.get('essential') else 'not highly constrained'})",
            "do_first": False,
        })
    else:
        experiments.append({
            "name": f"CRISPR premature — {gene} lacks sufficient genetic evidence",
            "category": "PREMATURE — Do Not Run",
            "cost_usd": 15000, "time_weeks": 10, "p_success": 0.15,
            "value_score": 1, "expected_value": 0.15,
            "rationale": f"Only {gi.get('n_critical',0)} CRITICAL variants and {concordant} AlphaMissense concordant. CRISPR at this stage = high cost, low return. Run TSA, Co-IP, and functional assays first. Return to CRISPR after establishing mechanism.",
            "do_first": False,
            "avoid": True,
        })

    # ── 7. Drug screen (tractability-dependent) ────────────────────────────
    if sm_tractable and gi.get("n_pathogenic", 0) >= 3:
        if existing_drugs:
            experiments.append({
                "name": f"Drug analogue screen — test {existing_drugs[0]} analogues against {gene}",
                "category": "Drug Discovery",
                "cost_usd": 50000, "time_weeks": 8, "p_success": 0.60,
                "value_score": 9, "expected_value": 5.4,
                "rationale": f"OpenTargets confirms small-molecule tractability for {gene}. Existing drug {existing_drugs[0]} provides scaffold. Screen analogue library (200–500 compounds) before full HTS. Superimpose {variant_str} onto drug crystal structure to confirm target engagement.",
                "do_first": False,
            })
        else:
            experiments.append({
                "name": f"Fragment-based screen — {gene} binding pockets",
                "category": "Drug Discovery",
                "cost_usd": 80000, "time_weeks": 12, "p_success": 0.50,
                "value_score": 8, "expected_value": 4.0,
                "rationale": f"OpenTargets: small-molecule tractable. No existing drugs. Use FBDD (SPR primary, DSF confirmation). Start with AlphaFold structure to identify druggable pockets. Only proceed if {concordant} AlphaMissense-concordant variants confirm structural mechanism.",
                "do_first": False,
            })

    # ── 8. AlphaFold-Multimer ─────────────────────────────────────────────
    if top_partners:
        experiments.append({
            "name": f"AlphaFold-Multimer — {gene}:{top_partners[0]} complex modelling",
            "category": "Structural Prediction",
            "cost_usd": 0, "time_weeks": 0.5, "p_success": 0.80,
            "value_score": 7, "expected_value": 5.6,
            "rationale": f"Free in silico first step. Model {gene}:{top_partners[0]} complex via ColabFold. ipTM>0.8 = high-confidence interface. Map {variant_str} onto interface — variants disrupting predicted contacts prioritise Co-IP and SPR experiments. Do before committing wet-lab budget.",
            "do_first": True,
        })

    # Sort: do_first first, then by expected_value desc
    experiments.sort(key=lambda x: (0 if x.get("do_first") else 1, -x.get("expected_value", 0)))
    return experiments
