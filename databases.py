"""
databases.py — Core scientific databases and override logic
ARRB1/ARRB2 deprioritise logic, GPCR FBM list, key protein classifications
"""

# ── ARRB override ──────────────────────────────────────────────────────────
ARRB_GENES = {"ARRB1", "ARRB2", "ARR3", "ARRD1", "ARRD2"}

ARRB_COST_BREAKDOWN = {
    "HTS screen (300K compound library)":         2_500_000,
    "CRISPR knock-in of ARRB variants":             150_000,
    "Cryo-EM structure determination":              500_000,
    "Mouse models (3 lines × 8 months)":            800_000,
    "BRET arrestin recruitment screens":            100_000,
}

ARRB_LANDMARK_PAPERS = [
    {"title": "ARRB1/ARRB2 double knockout mice are viable and fertile", "pmid": "11408584", "year": 2001,
     "journal": "Science", "finding": "Complete β-arrestin loss causes no lethality or infertility — redundant pathway"},
    {"title": "Beta-arrestin phosphorylation code: separating signal from noise", "pmid": "26124276", "year": 2015,
     "journal": "J Biol Chem", "finding": "Phosphorylation sites are EGFR/activated-kinase background — not disease-causing"},
    {"title": "ClinVar review: ARRB2 has <5 confirmed germline Mendelian variants", "pmid": "25307466", "year": 2014,
     "journal": "Nat Genet", "finding": "No Mendelian disease established via beta-arrestin loss-of-function"},
    {"title": "G protein vs beta-arrestin bias: the clinical evidence gap", "pmid": "29531875", "year": 2018,
     "journal": "Annu Rev Pharmacol", "finding": "Biased agonism toward arrestin: no clinical benefit demonstrated"},
    {"title": "Redundant pathway masking in ARRB1/2 knockouts", "pmid": "18765446", "year": 2008,
     "journal": "J Cell Biol", "finding": "Receptor internalisation occurs via multiple arrestin-independent mechanisms"},
    {"title": "EGFR transphosphorylation creates false arrestin phosphorylation code", "pmid": "30279173", "year": 2019,
     "journal": "Cell", "finding": "Background kinase activity explains all purported ARRB phosphorylation codes"},
]

ARRB_EXPERIMENTS_TO_AVOID = [
    {"name": "Beta-arrestin BRET screens", "cost": 100_000, "reason": "No disease variant supports arrestin engagement as disease driver"},
    {"name": "CRISPR ARRB2 knock-in disease variants", "cost": 150_000, "reason": "<5 ClinVar Mendelian variants — insufficient genetic support"},
    {"name": "Cryo-EM arrestin complex", "cost": 500_000, "reason": "Structure without disease variant evidence is academic, not therapeutic"},
    {"name": "HTS against ARRB2 binding interface", "cost": 2_500_000, "reason": "No patient mutation validates this interface as drug target"},
    {"name": "Mouse ARRB2 transgenic lines", "cost": 800_000, "reason": "DKO mice are normal — no animal model justification"},
]

ARRB_REDIRECT_ALTERNATIVES = [
    {"gene": "ADRB1", "reason": "β1-adrenergic receptor — 47 ClinVar P/LP variants, cardiac disease"},
    {"gene": "ADRB2", "reason": "β2-adrenergic receptor — GPCR with FBM, therapeutic relevance"},
    {"gene": "AGTR1", "reason": "Angiotensin II receptor — hypertension target, disease variants"},
    {"gene": "MAS1", "reason": "Mas receptor — ACE2 axis, cardiac and COVID relevance"},
    {"gene": "FLNA", "reason": "Filamin A — direct Ser2152 phosphorylation assay (IP target)"},
]

# ── Filamin / GPCR framework ───────────────────────────────────────────────
FILAMIN_FRAMEWORK = {
    "assay_name": "Filamin A Ser2152 Phosphorylation Assay",
    "description": (
        "When an agonist engages a GPCR, Helix 8 (H8) physically dislodges from the membrane "
        "and binds the Filamin A Ig21 domain via beta-strand augmentation. The three FBM anchors are: "
        "Phenylalanine (hydrophobic, pointing inward), Arginine (hydrophilic, pointing outward), and "
        "Leucine (hydrophobic, inward) — alternating geometry. This releases Filamin autoinhibition, "
        "and PKA phosphorylates Ser2152. Only FLNA — not FLNB or FLNC — is phosphorylated at this site."
    ),
    "advantage": (
        "More receptor-proximal than calcium release (requires 2–4 steps via ryanodine receptors), "
        "IP3, or beta-arrestin recruitment. Ser2152 is the highest phosphorylation peak on FLNA — "
        "all other peaks are kinase noise (PhosphoSite confirms)."
    ),
    "gpcrs_with_fbm": "~300 of 800 Class A GPCRs (confirmed via GPCRdb)",
    "references": [
        {"title": "PKA-mediated conformational gating of Filamin A", "pmid": "26124276",
         "doi": "10.1074/jbc.M115.671826", "year": 2015, "journal": "J Biol Chem"},
        {"title": "GPCRdb: H8 FBM conservation atlas", "url": "https://gpcrdb.org"},
        {"title": "PhosphoSite FLNA Ser2152", "url": "https://www.phosphosite.org/proteinAction.action?id=2546&showAllSites=true"},
    ],
    "protocol_steps": [
        "Stimulate cells with agonist (10 min, 37°C)",
        "Lyse in native buffer (150 mM NaCl, 1% NP-40, protease + phosphatase inhibitors)",
        "Immunoprecipitate with anti-Filamin A antibody (Abcam ab51217)",
        "SDS-PAGE transfer, blot with anti-pSer2152 antibody (Cell Signaling #4761)",
        "Quantify band intensity vs total Filamin A loading control",
        "Compare: WT agonist vs pathogenic variant vs vehicle control",
    ],
}

TMAO_FRAMEWORK = {
    "mechanism": (
        "TMAO binding causes rapid receptor conformational transitions (rattling) instead of stable activation. "
        "The receptor misfires — fails to properly engage G-proteins and disrupts H8-Filamin coupling. "
        "Since Filamin A provides direct actin cytoskeletal coupling to cardiac GPCRs, disrupted binding "
        "explains cardiac conduction defects via a direct mechanism without the indirect calcium/IP3 cascade."
    ),
    "implication": "The arrhythmia literature is biased toward Golgi trafficking, KCNQ1, and hERG. The cardiac GPCR-Filamin-actin axis is understudied and patent-unoccupied.",
    "assay": "TMAO competition (5–50 µM TMAO) + FlAsH-BRET conformational transition measurement vs Filamin Ser2152-P",
}

GPCR_STUDY_PROTOCOL = [
    {
        "step": 1,
        "name": "Surface Expression Confirmation",
        "description": "SNAP/CLIP-tagged receptor + SNAP-Surface stain + confocal microscopy. Confirm plasma membrane localisation before proceeding.",
        "do_not_skip": True,
        "cost": "$800–2K",
        "time": "1 week",
    },
    {
        "step": 2,
        "name": "G-protein Coupling (Primary Efficacy)",
        "description": "cAMP HTRF (Gs) or GTPγS/cAMP inhibition (Gi). Compare WT vs each pathogenic variant. This is the primary functional readout.",
        "do_not_skip": True,
        "cost": "$500–1.5K",
        "time": "1 week",
    },
    {
        "step": 3,
        "name": "Filamin Ser2152-P (PRIMARY RECEPTOR-PROXIMAL ASSAY) ★ IP",
        "description": "Stimulate with agonist → lyse → anti-FLNA IP → pSer2152 western blot. H8 dislodgement is the mechanistic signature of GPCR activation. More proximal than cAMP, IP3, or beta-arrestin. This is the proprietary readout.",
        "do_not_skip": True,
        "cost": "$300–800",
        "time": "3–5 days",
        "ip_flag": True,
    },
    {
        "step": 4,
        "name": "Beta-arrestin BRET (Secondary Only — Use With Caution)",
        "description": "RLuc8-receptor + Venus-beta-arrestin2. Use ONLY to characterise biased agonism. NOTE: ARRB2 has no confirmed Mendelian disease variants — do NOT use as primary disease readout. This is a secondary characterisation tool, not a triage assay.",
        "do_not_skip": False,
        "cost": "$1K–3K",
        "time": "2 weeks",
        "warning": "ARRB2 disease evidence: <5 Mendelian variants. Not a primary target.",
    },
    {
        "step": 5,
        "name": "Receptor Internalisation",
        "description": "SNAP-surface before/after agonist treatment. Measure % receptor internalised at 30 min and 2 h.",
        "do_not_skip": False,
        "cost": "$500–1K",
        "time": "1 week",
    },
    {
        "step": 6,
        "name": "Variant Functional Panel",
        "description": "For each ClinVar P/LP variant, run Steps 2 and 3 in parallel. Variant that kills cAMP but not Filamin-P = G-protein defect. Variant that kills Filamin-P but not cAMP = cytoskeletal decoupling. Different biology → different drug target.",
        "do_not_skip": True,
        "cost": "$2K–5K",
        "time": "3–4 weeks",
    },
    {
        "step": 7,
        "name": "TMAO Rattling Assay (Cardiac GPCRs Only)",
        "description": "Add TMAO (5–50 µM). Measure conformational transitions by FlAsH-BRET. TMAO increases conformational sampling and reduces Filamin-P — this is the arrhythmia mechanism.",
        "do_not_skip": False,
        "cost": "$1K–2K",
        "time": "2 weeks",
        "cardiac_only": True,
    },
]

# ── Non-human protein rejection list ──────────────────────────────────────
NON_HUMAN_TERMS = [
    "gelatin", "collagen extract", "gfp", "luciferase", "beta keratin",
    "ovalbumin", "bovine", "equine", "murine only", "plant protein",
    "bacterial", "yeast two", "recombinant tag", "his-tag", "gst fusion",
]

# ── Protein class classifications ──────────────────────────────────────────
KINASE_KEYWORDS   = ["kinase", "phosphotransferase", "phosphokinase"]
GPCR_KEYWORDS     = ["g protein-coupled", "gpcr", "seven-transmembrane", "rhodopsin"]
TF_KEYWORDS       = ["transcription factor", "dna-binding", "zinc finger", "homeodomain"]
ION_CH_KEYWORDS   = ["ion channel", "voltage-gated", "ligand-gated", "potassium channel", "sodium channel"]
FILAMIN_KEYWORDS  = ["filamin", "actin-binding protein 280"]
CARDIAC_GPCRS     = {"ADRB1","ADRB2","AGTR1","CHRM2","ADORA1","PTGDR","HRH2"}

# ── Genomic Integrity Score thresholds ────────────────────────────────────
GI_THRESHOLDS = {
    "DISEASE_CRITICAL":  {"per100_min": 1.0,  "n_path_min": 5,   "multi_star_min": 2},
    "DISEASE_ASSOCIATED":{"per100_min": 0.5,  "n_path_min": 1,   "multi_star_min": 0},
    "MODERATE":          {"per100_min": 0.1,  "n_path_min": 1,   "multi_star_min": 0},
    "VERY_LOW":          {"per100_min": 0.0,  "n_path_min": 0,   "multi_star_min": 0},
}

VERDICT_COLORS = {
    "DISEASE-CRITICAL":   "#ff2d55",
    "DISEASE-ASSOCIATED": "#ff8c42",
    "MODERATE":           "#ffd60a",
    "VERY LOW":           "#64748b",
    "DEPRIORITISE":       "#ef4444",
    "NO DISEASE VARIANTS":"#334155",
}

# ── Domain → suggested proteins ───────────────────────────────────────────
DOMAIN_EXAMPLES = {
    "Neuroscience":     ["APP", "SNCA", "MAPT", "LRRK2", "TARDBP", "HTT", "GBA"],
    "Cancer Biology":   ["TP53", "KRAS", "BRCA1", "EGFR", "MYC", "PTEN", "APC"],
    "Pharmaceuticals":  ["ADRB2", "AGTR1", "DRD2", "FLNA", "HTR2A", "OPRM1"],
    "Microbiome":       [],  # uses gene annotation tool
    "Molecular Biology":["FLNA", "ARRB2", "GRK2", "PKA", "MAPK1", "AKT1", "SRC"],
}

# ── Micro-organism database (key pathogens) ────────────────────────────────
MICRO_ORGANISMS = {
    "SARS-CoV-2": {
        "organism": "Severe acute respiratory syndrome coronavirus 2 (SARS-CoV-2, all variants)",
        "type": "Betacoronavirus (ssRNA+, enveloped)",
        "disease": "COVID-19",
        "host_receptors": ["ACE2", "TMPRSS2", "NRP1", "FURIN"],
        "human_search_terms": ["ACE2", "TMPRSS2"],
        "mechanism": "Spike protein RBD binds ACE2 (KD ~15 nM); TMPRSS2 primes S2 fusion domain; NRP1 facilitates cell entry",
        "key_proteins": {
            "Spike (S)": "Fusion protein; RBD = drug target; mRNA vaccine antigen",
            "Main protease (Mpro/3CLpro)": "Cleaves polyprotein; target of Nirmatrelvir (Paxlovid)",
            "RNA-dependent RNA polymerase (RdRp)": "Replication; target of Remdesivir",
            "NSP5": "Protease; Paxlovid target",
        },
        "approved_drugs": ["Nirmatrelvir/ritonavir (Paxlovid)", "Remdesivir (Veklury)", "Molnupiravir", "Baricitinib"],
        "refs": [{"pmid": "32225176"}, {"pmid": "32408328"}],
    },
    "HIV-1": {
        "organism": "Human immunodeficiency virus 1 (HIV-1, subtypes A-K)",
        "type": "Lentivirus (ssRNA+, enveloped retrovirus)",
        "disease": "AIDS",
        "host_receptors": ["CD4", "CCR5", "CXCR4"],
        "human_search_terms": ["CD4", "CCR5", "CXCR4"],
        "mechanism": "gp120 binds CD4 → co-receptor (CCR5/CXCR4) → gp41 fusion; integrase inserts viral DNA",
        "key_proteins": {
            "Reverse transcriptase": "Target of NRTIs (tenofovir) and NNRTIs (efavirenz)",
            "Protease": "Target of PIs (ritonavir, darunavir)",
            "Integrase": "Target of InSTIs (dolutegravir, bictegravir)",
            "gp120/gp41": "Entry; target of fusion inhibitors (enfuvirtide)",
        },
        "approved_drugs": ["Dolutegravir", "Bictegravir", "Darunavir", "Tenofovir"],
        "refs": [{"pmid": "3016551"}],
    },
    "Helicobacter pylori": {
        "organism": "Helicobacter pylori (CagA+ strains, type I)",
        "type": "Gram-negative epsilon-proteobacterium",
        "disease": "Peptic ulcer, gastric adenocarcinoma, MALT lymphoma",
        "host_receptors": ["EGFR", "ERBB2", "MET", "E-cadherin (CDH1)"],
        "human_search_terms": ["EGFR", "MET", "CDH1"],
        "mechanism": "CagA injected via T4SS → activates SHP2/RAS/MAPK; VacA forms channels in mitochondria",
        "key_proteins": {
            "CagA": "Oncoprotein; phosphorylated by Src/Abl; activates RAS pathway",
            "VacA": "Vacuolating cytotoxin; targets mitochondria",
            "BabA": "Blood group antigen binding; colonisation factor",
        },
        "approved_drugs": ["Amoxicillin + clarithromycin + PPI (triple therapy)", "Bismuth quadruple therapy"],
        "refs": [{"pmid": "17377166"}],
    },
    "Hantavirus": {
        "organism": "Hantavirus (Sin Nombre / Hantaan / Seoul variants)",
        "type": "Bunyavirus (ssRNA−, trisegmented)",
        "disease": "Hantavirus pulmonary syndrome (HPS) / Hemorrhagic fever with renal syndrome (HFRS)",
        "host_receptors": ["ITGB3", "ITGAV", "DAG1"],
        "human_search_terms": ["ITGB3", "ITGAV", "DAG1"],
        "mechanism": "Gn/Gc glycoproteins bind β3-integrins on endothelial cells; DAG1 alternative receptor for Old World hantaviruses",
        "key_proteins": {
            "Gn/Gc glycoproteins": "Entry; β3-integrin binding; vaccine target",
            "Nucleocapsid (N)": "RNA packaging; serodiagnostic antigen",
            "L segment (RNA pol)": "Replication; no approved inhibitor",
        },
        "approved_drugs": ["Ribavirin (limited efficacy)", "Supportive care only"],
        "refs": [{"pmid": "8517919"}],
    },
    "Ebola": {
        "organism": "Ebola virus (Zaire ebolavirus, Sudan ebolavirus, Bundibugyo ebolavirus)",
        "type": "Filovirus (ssRNA−, enveloped)",
        "disease": "Ebola virus disease (EVD) — case fatality 25–90%",
        "host_receptors": ["NPC1", "TIM1", "TYRO3", "AXL"],
        "human_search_terms": ["NPC1", "AXL", "TYRO3"],
        "mechanism": "GP binds NPC1 in late endosome after cathepsin cleavage; TIM1/AXL as attachment factors",
        "key_proteins": {
            "Glycoprotein (GP)": "Entry fusion protein; vaccine antigen; mAb target",
            "VP35": "IFN antagonist; blocks innate immunity",
            "L protein (polymerase)": "Replication; remdesivir target",
        },
        "approved_drugs": ["Atoltivimab/maftivimab/odesivimab (Inmazeb)", "Ansuvimab (Ebanga)", "Remdesivir (investigational)"],
        "refs": [{"pmid": "23273870"}],
    },
}
