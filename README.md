# PROTELLECT v32 — Protein Intelligence Platform

**The most powerful tool in biological experimentation**

A genetics-first protein triage and experimental guidance platform built to eliminate bias, maximize accuracy, and deliver precision insights across 5 specialized biological domains.

---

## 🚀 WHAT'S NEW IN v32

### Two Novel IP Engines
1. **Filamin H8 / RxxS Phosphorylation Readout** — Replaces β-arrestin recruitment as the receptor-proximal activation assay. Detects amphipathic H8 segments and multi-arginine clusters preceding S/T phosphorylation sites.

2. **Cross-Disease Variant Database Scanner** — Identifies pathway partners through shared Mendelian disease genetics. Flags digenic candidates and founder mutations. Triages disease-relevant vs background noise variants.

### Chemistry & PTM Visualization
- **Animated peptide backbone** with R-groups, phosphorylation sites, H8 helices
- **Phosphorylation cycle animations** (kinase ATP → phospho-residue → phosphatase)
- **Side-chain detail viewer** with hydropathy, charge, and binding annotations
- **3D AlphaFold structure** with pLDDT coloring, variant spheres, phospho-site highlights

### Five Domain-Specialized Modules

#### 1. **ONCOLOGY**
- Somatic vs germline driver classification (TIER_1_TS, TIER_1_ONC, EMT, DDR)
- Early-event scoring (founder/trunk mutations across cancer types)
- Metastasis-risk panel (EMT pathway genes)
- Patient-tailored treatment recommendations (by cancer type, stage, age)

#### 2. **NEUROSCIENCE**
- Synaptic-protein classifier (ion channels, glutamate/GABA receptors, vesicle proteins)
- Synaptic layer inference (presynaptic / postsynaptic / axon / glial)
- Epilepsy / cortical-malformation / intellectual-disability phenotype breakdown
- Therapeutic axes (sodium-channel inhibitors, K-channel openers, mTOR modulators, ASO trials)

#### 3. **CARDIOLOGY**
- Filamin / actin-binding axis analysis (FLNA vascular aneurysms, heterotopia)
- β-adrenergic / GPCR signalling (ADRB1, ADRB2, GRK family, β-arrestin piggyback detection)
- Arrhythmia ion-channel panel (long QT, Brugada, SCN5A, KCNH2)
- Cardiomyopathy genes (HCM, DCM, TTN, MYH7, FLNC)

#### 4. **RARE DISEASE / MENDELIAN**
- Inheritance pattern inference (autosomal recessive/dominant, X-linked, de novo, mitochondrial)
- Syndrome breakdown with penetrance estimates
- Orphan drug eligibility assessment (FDA criteria)

#### 5. **MICROBIOME**
- NCBI Taxonomy lineage (kingdom → species)
- LLM-powered pathway annotation expansion (via Claude API when ANTHROPIC_API_KEY is provided)
- Curated microbial function annotations (E. coli, B. fragilis, Akkermansia, etc.)
- Vague pathway labels (biosynthesis, chemosynthesis, protein aggregation) → specific KEGG/MetaCyc sub-pathways

### Pharmaceuticals & Druggability
- Tractability assessment (small molecule, antibody, PROTAC, ASO)
- Known-drug pipeline (by clinical phase)
- Druggable hotspots with variant-cluster fold-enrichment
- Kinase/phosphatase drug-target sites
- Active clinical trials (ClinicalTrials.gov API v2)

---

## 📦 INSTALLATION

### 1. Clone or Download
```bash
unzip protellect_v32.zip
cd protellect_v32
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional) Add Anthropic API Key for Microbiome LLM Expansion
Create `.streamlit/secrets.toml`:
```toml
ANTHROPIC_API_KEY = "sk-ant-api03-..."
```

### 4. Run Locally
```bash
streamlit run app.py
```

### 5. Deploy to Streamlit Cloud
1. Push to GitHub
2. Connect at https://share.streamlit.io
3. Select `app.py` as the main file
4. (Optional) Add `ANTHROPIC_API_KEY` in Streamlit Cloud secrets

---

## 🎯 USAGE

### Domain Selection
Choose your analysis domain from the sidebar:
- **Core Triage** — Full genetics-first analysis with all features
- **Oncology** — Cancer-specific driver classification & patient recommendations
- **Neuroscience** — Neural protein families & synaptic therapeutics
- **Cardiology** — Filamin axis, arrhythmias, cardiomyopathy panel
- **Rare Disease** — Mendelian inheritance & orphan drug pathways
- **Microbiome** — Taxonomy + LLM pathway expansion
- **Pharmaceuticals** — Druggability map & clinical trials
- **Chemistry & PTM** — Peptide backbone, phosphorylation cycles, side chains

### Protein Search (Human-Only for Most Domains)
Enter:
- Gene symbol: `TP53`, `FLNC`, `BRCA1`, `SCN1A`, `MYH7`
- UniProt accession: `P04637`

The platform validates human taxon (9606) at UniProt fetch. Non-human proteins are rejected except in **Microbiome** mode.

### Microbiome Mode
Search by:
- Organism: `Escherichia coli`, `Bacteroides fragilis`, `Akkermansia muciniphila`
- Protein + organism: `MetK Escherichia coli`

Returns: taxonomy lineage, functional role, LLM-expanded pathway annotations.

### Patient-Tailored Oncology
In Oncology mode, provide:
- **Cancer type** (Breast, Lung, Colorectal, Pancreatic, etc.)
- **Stage** (I, II, III, IV, Metastatic)
- **Patient age**

Platform returns patient-specific treatment recommendations, germline/hereditary-syndrome counselling, and targeted-therapy options.

---

## 🧬 CORE ANALYTICAL WORKFLOW

1. **Human Validation** — UniProt organism_id:9606 filter
2. **ClinVar Variant Fetch** — Pathogenic, likely pathogenic, VUS, benign
3. **Genomic Integrity Computation** — Pathogenic variant density → Verdict (PRIORITISE / PROCEED / SELECTIVE / CAUTION / DEPRIORITISE)
4. **ML Variant Scoring** — Hydropathy shift, charge change, stop-gain, frameshift, splice-site, AlphaMissense
5. **AlphaFold Structure** — pLDDT-coloured 3D model with variant spheres
6. **gnomAD Constraint** — pLI, oe_lof, oe_mis (loss-of-function intolerance)
7. **STRING Interactions** — Top network partners (experimental evidence score > 700)
8. **OpenTargets Drug Landscape** — Tractability, known drugs, clinical phase
9. **DGIdb Interactions** — Drug-gene interaction types
10. **ClinicalTrials.gov** — Active/recruiting trials
11. **PubMed Abstracts** — Experiment-type classification (structural, CRISPR, in vivo, clinical)
12. **Hotspot Clustering** — Sliding-window variant density with fold-enrichment
13. **Filamin H8 / RxxS Engine** — Amphipathic helix detection, phosphorylation-motif scanning
14. **Cross-Disease Partner Discovery** — Shared-disease pathway reconstruction
15. **Variant Triage** — Disease-relevant vs VUS-reclassify vs background-noise
16. **Founder Mutation Detection** — Recurrent pathogenic variants (historical origin / hotspot)

---

## 📊 OUTPUT TABS

### Core Triage Domain
- **Overview** — Disease associations, pathway partners
- **Variants** — Triage (disease-relevant / VUS-reclassify / noise), founder mutations
- **3D Structure** — AlphaFold interactive viewer (rotate, zoom, click residues for detail)
- **Chemistry & PTM** — Peptide backbone, phosphorylation cycle animation, filamin H8 readout
- **Pharmaceuticals** — Tractability, known drugs, druggable hotspots SVG map

### Oncology Domain
- **Dashboard** — Driver tier, somatic/germline counts, metastasis risk, early events
- **Somatic/Germline** — Side-by-side variant lists
- **Targeted Therapy** — Actionable drugs by phase

### Neuroscience Domain
- **Neural Profile** — Gene family, synaptic layer, phenotype breakdown
- **Ion Channels & Synapses** — Functional context
- **Neuro Therapeutics** — Therapeutic axes (channel inhibitors, mTOR modulators, ASO)

### Cardiology Domain
- **Cardiology Panel** — Family, arrhythmia/cardiomyopathy counts, piggyback flag
- **Filamin Axis** — H8 detection, phosphorylation readout recommendation
- **Cardiac Drugs** — β-blockers, sodium-channel modulators, mavacamten, ARBs

### Rare Disease Domain
- **Mendelian Analysis** — Inheritance patterns, syndromes
- **Inheritance & Penetrance** — De novo count, penetrance estimate, orphan drug eligibility
- **Orphan Drugs** — Known therapies or gene-therapy recommendation

### Microbiome Domain
- **Taxonomy Lineage** — Kingdom → phylum → class → order → family → genus → species
- **Functional Role** — Curated role (commensal, pathogen, SCFA producer, mucin degrader)
- **Pathway Annotations (LLM-Expanded)** — Vague labels → specific KEGG/MetaCyc sub-pathways

---

## 🔬 TECHNICAL ARCHITECTURE

- **Framework**: Streamlit 1.30+
- **APIs**: UniProt, NCBI E-utilities (ClinVar, PubMed, Taxonomy), gnomAD GraphQL, AlphaFold EBI, OpenTargets GraphQL, STRING, DGIdb, ClinicalTrials.gov v2, Anthropic Claude (optional)
- **Visualization**: Plotly, 3Dmol.js (CDN), SVG (inline), HTML components
- **ML Scoring**: Hand-crafted physicochemical features + ClinVar review quality
- **Caching**: Streamlit `@st.cache_data` with TTL (1h for most fetchers, 24h for AlphaFold)
- **Deployment**: Streamlit Cloud, Heroku, AWS EC2, local

---

## 🎨 DARK THEME

- Terminal-grade monospace UI (JetBrains Mono + Space Grotesk)
- Radial-gradient background (#04101e → #02060d)
- CSS variables for consistent color palette:
  - `--acc-cyan`: #00f5d4
  - `--acc-amber`: #ffb02e
  - `--acc-pink`: #ff3d7f
  - `--acc-violet`: #9d4edd
  - `--acc-lime`: #9bff4a
  - `--acc-red`: #ff2d55
- Animated verdict banners, KPI cards, badge ranks
- Hover states with glow effects

---

## 📚 DATA SOURCES

- **UniProt** — Protein function, PTMs, tissue specificity, isoforms
- **ClinVar** — Clinical significance, germline/somatic origin, conditions
- **gnomAD** — pLI, o/e LoF, o/e missense, allele frequencies
- **AlphaFold** — Per-residue pLDDT confidence, 3D structure (PDB)
- **AlphaMissense** — Per-position, per-substitution pathogenicity scores
- **OpenTargets** — Tractability (small molecule, antibody, PROTAC), known drugs, disease associations
- **DGIdb** — Drug-gene interactions, mechanism types
- **ClinicalTrials.gov** — Active trials, phase, status
- **STRING** — Protein-protein interactions (experimental evidence)
- **PubMed** — Abstracts, experiment-type classification
- **NCBI Taxonomy** — Organism lineage (microbiome mode)
- **Anthropic Claude** — LLM pathway annotation (microbiome mode, optional)

---

## ⚖️ LICENSE

**Confidential — Internal Working Document**

Protellect v32 is proprietary software. All intellectual property rights belong to the copyright holders. Unauthorized distribution, reproduction, or commercial use is prohibited.

**Two Novel IP Assets**:
1. Filamin H8 / RxxS phosphorylation-readout predictor
2. Cross-disease variant-database scanner with digenic detection

---

## 🤝 SUPPORT & FEEDBACK

For questions, bug reports, or feature requests:
- Email: support@protellect.bio (placeholder)
- GitHub Issues: (if open-sourced)
- Documentation: Workflow_Document.pdf

---

## 🏆 CREDITS

- **Architecture**: Protellect Research Team
- **Filamin IP**: Based on PI transcript (GPCR H8 / actin-binding axis)
- **Microbiome LLM Expansion**: Claude API integration for vague-pathway refinement
- **Domain Modules**: Oncology, Neuroscience, Cardiology, Rare Disease, Microbiome
- **Theme**: Terminal-grade dark mode with aggressive CSS customization
- **Visualization**: 3Dmol.js, Plotly, SVG animations

---

**Version**: 32  
**Build Date**: 2026-05-11  
**Lines of Code**: 2405  
**Status**: Production-ready  

---

**"Genetics must be the starting point of any biology."**
