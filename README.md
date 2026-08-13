# Protellect

Auditable orphan-GPCR prioritisation for receptor pharmacology teams. Enter a
receptor or UniProt accession and get a paper-cited target dossier combining
ligand evidence, structural tractability, receptor-family context, expression,
and supporting genetic evidence from public databases.

**Live app:** https://protellect-wkyps2qupri6aqhstt48wd.streamlit.app/

---

## Launch focus

Protellect is initially designed for receptor pharmacology teams evaluating
orphan GPCRs. The product treats deorphanization as evidence to be audited —
not a label to infer from a single screen. Its public workflow emphasises:

- ligand and functional-evidence review
- binding-pocket and structure tractability
- GPCR-family context and selectivity risk
- tissue-expression context and follow-up experiments

Legacy therapeutic-area workspaces are retained behind an internal beta switch
(`PROTELLECT_ENABLE_BETA_DOMAINS=true`) and are not part of the public launch.
Microbiome relevance belongs as metabolite-ligand evidence, rather than a
top-level product domain.

## What it does

Protellect collapses the manual, multi-database workflow researchers use to evaluate
a protein target into a single search. For any gene or UniProt accession it returns:

- A receptor-prioritisation dossier that keeps source evidence visible and separates raw data from derived scores
- Associated diseases and pathogenic variant burden
- AlphaFold 3D structure with disease variants overlaid
- Druggability assessment (OpenTargets tractability, DGIdb drugs, GPCR binding)
- ROI-ranked follow-up experiment roadmap
- An AI copilot grounded in the loaded protein's data, with literature citations

Every methodological claim links to a peer-reviewed reference.

## Integrated data sources

UniProt · ClinVar · gnomAD · AlphaFold · AlphaMissense · STRING · OpenTargets ·
DGIdb · ClinGen · ClinicalTrials.gov · GPCRdb · PubMed · Semantic Scholar ·
OpenAlex · CrossRef

## Tech stack

- **Frontend/runtime:** Streamlit, deployed on Streamlit Cloud
- **Variant scoring:** transparent weighted formula (see VALIDATION.md); optional trained model pack loads if present
- **AI providers:** Anthropic Claude and Google Gemini (configured via secrets)

## Project structure

```
app.py                    Main application — UI flow, tabs, auth, workspace logic
protellect_data.py        All external API fetchers (UniProt, ClinVar, gnomAD, …)
protellect_citations.py   Peer-reviewed citation library + cite() helper
protellect_icons.py       SVG icon system
requirements.txt          Python dependencies
```

The data, citation, and icon layers are imported by `app.py`. They are
side-effect-free (no Streamlit calls at import time), so `set_page_config`
remains the first Streamlit command as required.

## Configuration

All credentials and API keys are read from Streamlit secrets — never hardcoded.
See [DEPLOY.md](DEPLOY.md) for full deployment instructions.

Required secrets (Streamlit Cloud → Settings → Secrets):

```toml
ANTHROPIC_API_KEY = "sk-ant-..."     # optional — enables Claude
GEMINI_API_KEY    = "AIza..."        # optional — enables Gemini

[credentials]
"you@example.com" = "your-password"  # app login accounts

[credential_plans]
"you@example.com" = "enterprise"     # free | pro | enterprise
```

If no credentials are configured, the app falls back to a single free-tier demo
account and guest access.

## Validation

The variant-scoring model and the genomic-integrity verdict are evaluated against
held-out ClinVar classifications. See [VALIDATION.md](VALIDATION.md) for methodology,
baselines, and metrics.

## Status

Private beta. For research use only — not a clinical diagnostic device.

## License

See [LICENSE](LICENSE).

## Contact

protellect@gmail.com
