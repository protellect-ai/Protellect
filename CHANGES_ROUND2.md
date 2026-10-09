# Round 2: building what was left

All of it runs from real inputs. Nothing here invents a number. 208 package tests pass; text-number (hostile) searches pass.

## Experiments tab
- **Fit your dose-response curves** (upload CSV): EC50 per curve with 95% CI, and an F-test for an EC50 shift between two conditions
  (alone vs co-expressed, with/without an allosteric compound; the GPR50 + MT1/MT2 case). Tested: recovers a planted 10-fold shift,
  and a null test gives ~5% false positives.
- **Fit SPR/BLI traces**: global 1:1 fit across concentrations -> kon, koff, Kd, residence time, with uncertainty and warnings
  (no dissociation seen, rate at bound, poor 1:1 fit). Tested on simulated sensorgrams.
- **Bring in docking / AlphaFold-Multimer / Boltz results**: you run them elsewhere; paste scores with known binders and decoys and
  it tells you whether the score separates them (AUROC with bootstrap CI), or says it does NOT, and places new compounds against
  the decoys. Also reads ipTM/pTM/pLDDT JSON and says what they do not mean.

## Hotspots tab
- **Candidate pockets** on the AlphaFold structure (LIGSITE-style), with lining helices, lipid-exposed share, low-confidence share,
  and a Fisher test of whether pathogenic ClinVar residues concentrate in them. Pockets are also a colour mode in the 3D viewer.
  Validated on synthetic shapes only; check against a ligand-bound structure of a related receptor.

## Triage tab
- **Compare two states**: upload an inactive and an active structure (RCSB, GPCRdb models, your own). Superposed on a stable core;
  per-helix movement table (flags TM6); animated as a straight-line morph in the 3D viewer. Not a simulated pathway.

## Genetics tab
- **Mouse knockout phenotypes** from Open Targets (IMPC/MGI), grouped by system. Written against the API schema as I know it and
  NOT tested against the live API; if the section is empty on your site, the data audit on Overview shows the error.

## Patterns tab
- **Sequence-based coupling classifier** with a built-in self-test (hold out whole subfamilies; must beat the majority-class guess
  AND shuffled labels). It declined on the built-in 34-receptor table, correctly. Upload a larger verified coupling table
  (CSV: gene, primary) to get a real test. During testing the first version of the gate was fooled by a leave-one-out artefact; that is fixed and covered by a null test.

## Citation check for the case library
`python -m protellect_core.engine.verify` (run on a machine with internet) checks that each cited paper exists and matches the
author/year/receptor, writes cases_citation_check.csv, and never flips `verified`. I could not run it from here (Europe PMC
was blocked/rate-limited for me). A domain expert still has to confirm every field of every case.

## Still not built (needs external compute or partners)
Lipid-raft / membrane MD, kon/koff prediction, active-state prediction, free-energy calculations. See the table on the Overview guide.

## Streamlit compatibility
Streamlit deprecated `st.components.v1.html` (the call behind the 3D viewer, signalling player and cascade animation) and says it
is removed after 2026-06-01. All four uses now go through one helper that uses the old call where it works and falls back to
`st.iframe`. Tested with the old call removed; not tested in a real browser on the new path.

## Install
Replace app.py, protellect_data.py (adds fetch_gpcr_sequences) and the protellect_core/ folder; reboot. Add scipy and scikit-learn to
requirements.txt. If either is missing, only its own panel shows a message; the rest of the app still loads.
