# Validation & Methodology

This document describes how Protellect's scoring is computed and how it should
(and should not) be interpreted. We write it plainly because a triage tool used
in a scientific context must be auditable.

## What the scoring actually is

Protellect produces two scores per variant:

1. **ClinVar-derived classification** — passed through directly from ClinVar's
   submitted clinical significance. This is not our judgment; it is the existing
   expert classification, surfaced and aggregated.

2. **ML re-score (`ml`)** — a composite priority score combining:
   - ClinVar base score
   - Loss-of-function signal (stop-gain, frameshift)
   - Physicochemical change (hydropathy delta, charge delta between wild-type and mutant residue)
   - ClinVar review status (star rating)

   This is currently a **transparent weighted formula**, not a black-box trained
   classifier. The weights are visible in `ml_score_variants()` in `app.py`. We
   chose a transparent formula over an opaque model deliberately: a reviewer can
   read exactly why any variant got its score.

> **Important honesty note.** Earlier internal notes referenced "LightGBM, AUC 1.0."
> An AUC of 1.0 indicates evaluation on training data (leakage), not genuine
> perfect performance. We do not claim that figure. The infrastructure to load a
> trained model exists (`joblib` pack loading), but the scoring in production is
> the transparent formula described above. A properly held-out, leakage-free
> model evaluation is [TODO — see "Planned validation" below].

## What the verdict means

The pursue / proceed / deprioritize verdict is a function of:
- Pathogenic/likely-pathogenic variant density (P/LP count ÷ sequence length)
- gnomAD constraint (pLI — loss-of-function intolerance)
- ClinGen gene-disease validity classification

These are established, citable metrics (see references in the app). The verdict
is **decision support, not a diagnosis or an investment recommendation.**

## Planned validation (not yet done — be honest about this)

To make this defensible as a triage aid, the following is needed and is **not
yet complete**:

1. **Held-out benchmark.** Take a set of genes, hide their ClinVar labels, run the
   verdict, and measure agreement with the known classification. Report precision,
   recall, and the confusion matrix — with the train/test split documented so there
   is no leakage.

2. **Baseline comparison.** Compare the verdict against (a) ClinVar alone and
   (b) AlphaMissense alone, to show what the integration adds.

3. **Expert agreement.** Have a clinical geneticist independently triage N genes
   and measure concordance with Protellect's verdict (Cohen's kappa).

Until these are done, the honest positioning is: *"Protellect aggregates and
surfaces established evidence faster than manual integration. We are validating
the verdict layer against held-out classifications; results forthcoming."*

## Reproducibility

All data is fetched live from public APIs at analysis time (see README for the
source list). The same protein analyzed twice returns the same result because the
inputs are deterministic public records, not a stochastic model.

## Methodology references

The methods underlying each score are cited inline in the app (Summary, Triage,
and Pharma tabs each carry a references footer) and include: ACMG/AMP variant
interpretation guidelines (Richards 2015), AlphaMissense (Cheng 2023), gnomAD
constraint (Karczewski 2020), ClinGen validity framework (Strande 2017), and the
genetic-evidence-for-targets work (Nelson 2015, King 2019).
