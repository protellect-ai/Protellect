# 🔬 Protellect v5
**The most powerful protein triage tool in biology.**  
Genetics-first. Reduces cost, time, and saves lives.

---

## Quick Start

### 1 — Install Python 3.11
Download from https://python.org/downloads — make sure to check "Add to PATH"

### 2 — Install dependencies
```bash
pip install -r requirements.txt
```

### 3 — Run Protellect
```bash
streamlit run app.py
```

Opens at **http://localhost:8501**

---

## Login Credentials

| Email | Password | Tier |
|-------|----------|------|
| `protellect@gmail.com` | `dev@protellect` | Enterprise (unlimited) |
| `demo@protellect.io` | `demo2025` | Free (5 searches) |

---

## What Protellect Does

Protellect pulls live data from 11 databases and tells you — in seconds — whether a protein is worth pursuing:

| Verdict | Meaning | Action |
|---------|---------|--------|
| 🔴 DISEASE-CRITICAL | ≥5 P/LP variants, expert-reviewed | Pursue immediately |
| 🟠 DISEASE-ASSOCIATED | Moderate genetic evidence | Selective pursuit |
| 🟡 MODERATE EVIDENCE | Some signal, needs validation | Validate first |
| ⬜ NO DISEASE VARIANTS | No ClinVar P/LP | Deprioritise |

---

## Data Sources (all live, cached 24h)

| Source | What it provides |
|--------|-----------------|
| **UniProt** | Protein function, sequence, domains, binding sites, phosphorylation |
| **ClinVar** | Pathogenic/Likely Pathogenic variants, disease associations |
| **AlphaFold EBI** | 3D structure (v4→v3→v2 fallback), pLDDT confidence |
| **AlphaMissense** | Per-residue pathogenicity scores (threshold 0.564) |
| **gnomAD** | pLI, o/e LoF, o/e Missense — constraint metrics |
| **STRING-DB** | Protein interaction partners (score ≥700, top 20) |
| **OpenTargets** | Tractability, known drugs |
| **GTEx v8** | Tissue expression (median TPM) |
| **ClinicalTrials.gov v2** | Active recruiting trials |
| **PubMed** | Evidence-tiered literature (5 query strategies) |
| **DGIdb** | Drug-gene interaction database |

---

## Seven Tabs

1. **Overview** — AlphaFold 3D + pLDDT histogram + disease associations with mechanism + top 5 experiments + gnomAD + binding sites + domain-specific context + literature
2. **Triage** — Mutation dynamics chart (all variants by position/severity) + full disease table + GTEx tissue distribution + per-variant expanders with AlphaMissense concordance
3. **Protein Explorer** — 3D backbone + domain architecture + phosphorylation/kinase/phosphatase biology + GPCR coupling animation + STRING network + residue inspector + "if mutated" simulator + AlphaMissense landscape
4. **Experiments** — 7 color-coded experiment cards (🟢 PURSUE / 🟡 CAUTION / 🔴 AVOID) with cost, timeline, P(success), FOCUS ON, NEGLECT, HYPOTHESIS TREE, citations
5. **Therapeutic Targets** — 3D surface view + druggability score (6 factors) + drug strategy by class + protein dynamics animation + timeline to clinic (8 phases)
6. **AI Report** — Evidence-tiered literature + Claude synthesis with web search (requires Anthropic API key)
7. **Workspace** — Metrics + 9-sheet Excel download + search history + lab profile

---

## Try These First

| Gene | Why |
|------|-----|
| **FLNA** | 1000+ ClinVar variants, GPCR coupling hub, Filamin Ser2152-P assay |
| **TP53** | The cancer archetype — 2000+ variants |
| **ADRB2** | Class A GPCR, β2-adrenergic receptor, H8-Filamin coupling |
| **LRRK2** | Parkinson's disease kinase |
| **BRCA1** | Hereditary breast/ovarian cancer |

---

## AI Report (Tab 6)

Add your Anthropic API key in the sidebar to enable Claude synthesis with live web search.  
Get a key at: https://console.anthropic.com

---

## Scientific Framework

**Genomic Integrity Score** — ClinVar P/LP variant density per 100 amino acids. Primary triage signal.

**Filamin Ser2152-P IP Assay** — GPCR agonist → H8 dislodges → PKA phosphorylates Ser2152 on FLNA. More receptor-proximal than cAMP/IP3/arrestin. Only FLNA (not FLNB/FLNC). Nakamura et al. JBC 2015, PMID:26124276.

**AlphaMissense threshold** — 0.564 (configurable via sensitivity slider, default 0.70).

---

## Requirements

```
streamlit>=1.32.0
requests>=2.31.0
plotly>=5.20.0
pandas>=2.1.0
numpy>=1.26.0
anthropic>=0.20.0
openpyxl>=3.1.0
```

Python 3.11 recommended (specified in runtime.txt).

---

## Troubleshooting

**"Module not found"** → Run `pip install -r requirements.txt`

**AlphaFold structure shows warning** → Large proteins (>2700 aa) may not have AlphaFold models. All variant data remains valid.

**gnomAD returns nothing** → Rate limiting. Wait 30s and retry. Data is cached after first successful call.

**AI Report not working** → API key missing or invalid. Add `sk-ant-...` key in sidebar.

**Excel download fails** → Run `pip install openpyxl`

---

## Deployment (Streamlit Cloud)

1. Push to GitHub
2. Go to https://streamlit.io/cloud
3. Connect your GitHub repo
4. Set main file: `app.py`
5. Deploy

No secrets or environment variables required.

---

*Protellect v5 — Built for researchers who want to spend money on proteins that matter.*
