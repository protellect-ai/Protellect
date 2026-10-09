# This round

## 1. The `'>=' not supported between 'str' and 'int'` crash
Reproduced with a test data layer that returns every number as text (what the live APIs sometimes do).
Cause: ClinVar variant `score` and UniProt sequence `length` arrived as text and were compared with numbers in `compute_gi`
and the scorer. Fix is at the boundary: `_clean_clinvar` and `_clean_pdata` in app.py turn them into numbers right after the fetch.
Checked: FFAR1, GPR-40 and TP53 all run with no error box, in normal and in text-numbers mode
(`protellect_core/tests/e2e/hostile_run.py`).

**Important:** the screenshot you sent (collapsed "Analysis trace · 15 steps") looks like the OLD app. Replace app.py,
protellect_data.py and the protellect_core/ folder on your repo, delete `pages/` and `protellect_hypothesis/`, and reboot the app.

## 2. Same information on every tab
- Data audit: Overview only (was on six tabs).
- Medication relevance: Hotspots only. Microenvironment factors: Genetics only. Overview keeps only comorbidity/family matches.
- Precedent hypotheses for the searched orphan: shown once, in the Pattern panel; Overview no longer repeats them.
- The "this follows from a rule" caveat is stated once per list instead of inside every proof box.

## 3. Motion
Triage > 3D viewer: **Motion** button animates the 3 lowest-frequency collective motions of the AlphaFold fold
(anisotropic network model, Atilgan 2001). **Mobility** colours the fold by how free each part is to move.
Labelled in the viewer: resting model, NOT an active state, no ligand/lipid/G protein.
(The step-by-step signalling video player is on Overview.)

## 4. Your wish-list: what is real and what is not
Built (from real inputs): elastic-network motion; binding-kinetics calculator on rates you measured (Experiments);
assay protocols with controls; outcome entry that re-weights the precedent model; ICL/TM topology.
Not built, on purpose: docking, binding free energy (dG), kon/koff prediction, lipid-raft/membrane simulation,
active-state prediction, heterodimer shift curves (MT1/MT2 with GPR50). They need AlphaFold-Multimer/docking suites,
explicit-membrane molecular dynamics, or BRET/co-IP data. Any number from this app for those would be invented. The Overview
guide has a table saying exactly this. The pasted app with mock data was not adopted for the same reason.

Tests: 174 package tests pass; hostile (text-number) searches pass.
