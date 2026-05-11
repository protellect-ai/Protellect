# 🔬 Protellect — Protein Intelligence Platform

The most powerful protein triage tool in biology.
Genetics-first · Reduces cost · Saves time · Improves outcomes.

---

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at **http://localhost:8501**

---

## Login

| Email | Password | Access |
|-------|----------|--------|
| `protellect@gmail.com` | `dev@protellect` | Enterprise (unlimited) |
| `demo@protellect.com` | `protellect2024` | Free (5 searches) |

---

## Research Domains

Select your domain on the landing page — every analysis is tailored:

| Domain | Specialisation |
|--------|---------------|
| 🧠 Neuroscience | BBB penetrance, iPSC-neurons, synaptic proteins, ion channels |
| 🎗 Cancer Biology | Somatic/germline split, metastasis, organoids, spatial transcriptomics |
| 💊 Pharmaceuticals | GPCR pipeline, Filamin Ser2152-P assay, HTS, ADMET |
| 🦠 Microbiome | Annotation engine, taxonomy KB, host-microbe interactions, BGC |
| ⚛️ Molecular Biology | Kinase assays, AP-MS interactome, HDX-MS, cryo-EM |

---

## Tabs

| Tab | Contents |
|-----|----------|
| 📋 Summary | Verdict banner, metrics, disease associations, top experiments |
| 🔴 Triage | Variant landscape, genomic integrity score, condition mapping |
| 📋 Case Study | Mutation cascade animation, clinical interpretation |
| 🔬 Explorer | 3D structure, domain expansion cards, AlphaMissense landscape |
| 🧪 Experiments | ROI-ranked experiment cards — unique per protein type, no generic fallbacks |
| 🤖 AI Report | Claude synthesis with live web search (requires API key) |
| 🗂️ Workspace | Search history, Excel export (9 sheets) |
| 🔗 Disease Link | Disease → proteins mapping |
| ⚗️ Chemistry | Hydrophobicity profile, amino acid composition, phosphorylation map, GPCR animation, electrostatic surface, **interactive chemical backbone renderer** |
| 💊 Pharma | Druggability atlas, per-domain drug scores, disease prevention strategies |

---

## Data Sources (all live, cached)

UniProt · ClinVar · AlphaFold EBI · AlphaMissense · gnomAD · STRING-DB ·
OpenTargets · GTEx · ClinicalTrials.gov · PubMed · DGIdb · Anthropic Claude API

---

## Key Science

**Genomic Integrity Score** — ClinVar P/LP variant density per 100 aa. Primary triage signal.

**Filamin Ser2152-P IP Assay** — GPCR agonist → H8 dislodges → PKA phosphorylates
Ser2152. More receptor-proximal than cAMP/IP3/β-arrestin. FLNA only (not B/C).
PMID: 26124276.

**AlphaMissense threshold** — 0.564 pathogenic (configurable, default 0.70).

**Tier 1 variant criteria** — ClinVar ≥4 stars + AlphaMissense ≥0.70 + gnomAD AF <0.001% + pLDDT ≥70.

---

## Deploy to Streamlit Cloud

1. Push to GitHub: `github.com/protellect-ai/Protellect`
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
3. Connect repo · Set main file: `app.py`
4. Deploy

**CRITICAL**: Upload `app.py` (starts with `from __future__ import annotations`)
NOT `config.toml` (starts with `[theme]`). These are different files.

---

## Fix GitHub if app.py is wrong

```bash
cd Protellect_Final
python3 fix_github.py ghp_YOUR_TOKEN_HERE
```

Get token: github.com/settings/tokens → New token (classic) → tick `repo` → Generate

---

*Protellect — Built for researchers who want to spend money on proteins that matter.*
