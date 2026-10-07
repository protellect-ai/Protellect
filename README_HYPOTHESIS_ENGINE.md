# Protellect Hypothesis Engine (beta scaffold)

Upload a processed experiment (expression table, variant table, or screen hits) plus disease and tissue
context. The engine finds the orphan GPCRs in it, compares each to documented historical deorphanization
cases, and returns ranked **hypotheses** (likely ligand class, likely G-protein coupling, a weak
disease-association analogy) with the reasoning, the precedents used, evidence flags, and the lab
experiment that would test each one.

**Hypotheses, not answers.** Only a wet-lab experiment confirms what a receptor does.

## Install (3 steps, no edits to app.py)
1. Copy `protellect_hypothesis/` and `pages/` into your repo root (next to `app.py`).
2. Add the lines in `requirements_hypothesis.txt` to your `requirements.txt`.
3. Run Streamlit as usual. A "Hypothesis Engine" page appears in the sidebar.

To embed it inside an existing tab instead:
```python
from protellect_hypothesis.streamlit_tab import render_hypothesis_tab
render_hypothesis_tab()
```

## Check it works
```bash
python -m pytest protellect_hypothesis/tests -q          # 18 tests
python -m protellect_hypothesis.benchmark --mode loo      # retrospective benchmark
python -m protellect_hypothesis.benchmark --mode temporal # strict temporal split
```

## What is in the box
| File | Job |
|---|---|
| `io_parsers.py` | Reads the three experiment shapes, auto-detects columns, cleans, one row per gene |
| `registry.py` | Orphan vs characterized GPCR registry, receptor annotations, IUPHAR CSV importer, live-annotation hook |
| `cases.py` + `data/cases.json` | Historical case library, validation, strict temporal filtering |
| `ranker.py` | The ML layer: logistic regression over precedent-similarity features, learned from historical cases only |
| `engine.py` | Orphan detection, hypothesis generation, evidence flags, caveats, abstention |
| `benchmark.py` | Leave-one-out and strict temporal retrospective benchmark with baselines |
| `streamlit_tab.py`, `pages/1_Hypothesis_Engine.py` | The UI |

## Read this before you trust any output
**1. The case library is a seed, and it is unverified.** I (an AI assistant) wrote the 14 cases in
`data/cases.json` from memory. Every row has `verified: false`, and the app and benchmark say so loudly.
Before any result is shown to anyone as evidence, an expert must check every row against primary sources:
ligand, class, coupling, year, citations, and above all that `tissues`, `neighbors` and `cluster` list
**only what was known before `resolution_year`**. Then set `verified: true` per row.

**2. Hindsight bias is a real threat.** Whoever fills in "what was known before" already knows the answer.
Have someone who did not curate the features audit them.

**3. The registry is a seed.** `data/gpcr_registry.csv` lists only 4 orphans. Download the Guide to
Pharmacology targets-and-families CSV yourself and run `import_iuphar_csv(src, out)` (see its docstring;
tested only on a synthetic file, so inspect the output).

**4. Annotations are sparse.** With no cluster/neighbor annotation, matches rest on tissue overlap alone, and
receptors in the same tissue context get near-identical hypotheses. The engine says so on each card. Fill
`data/receptor_annotations.csv`, or implement `fetch_live_annotation()` in `registry.py` using your own
data modules (GPCRdb/UniProt). It never guesses: no evidence means no hypothesis.

**5. Structural similarity is NOT implemented.** The proposal mentions binding-pocket similarity.
This version uses tissue, family cluster and neighbors only. Adding an AlphaFold pocket-similarity
feature is the highest-value next feature.

**6. `support` is a relative ranking, not a probability.** It splits 1.0 across one receptor's candidates.
Real hit rates come only from the benchmark.

## What the benchmark showed on the seed library (illustrative only)
- Leave-one-out, ligand class: **8/13** top-1 hits vs about **3.3/13** expected from random guessing.
  The learned weights favored neighbor/cluster links over tissue overlap.
- Misses were informative: GPR119 (a lipid mediator) and GPR120/GPR15/GPR109A/GPR81 were mispredicted,
  mostly because tissue overlap pulled them toward the wrong class.
- Strict temporal mode: **1/10** with 5 abstentions and 3 skipped. Early cases have almost no earlier
  precedent, so a library this small cannot support a temporal claim yet.
- The majority-class baseline is degenerate on balanced data (leave-one-out removes a member of the true
  class), which is why the report leads with the random baseline.
- With 13 cases, one or two hits is noise. These numbers are not validation and must not be cited as such.

## The "ML layer", stated plainly
A logistic regression over three features (tissue overlap, neighbor link, same cluster), trained on
precedent pairs from the library. It is deliberately small and its weights are inspectable
(`engine.ligand_ranker.weights()`), because a deep model would just memorize 13 cases. It becomes a
meaningful ML layer when the library grows to hundreds of verified cases and the feature set widens.

## Path from scaffold to claim
1. Expert-verify and extend the case library (target 50+ cases, more ligand classes: amines, nucleotides, lipids, ions).
2. Build the full registry with the IUPHAR importer; fill annotations or wire live data.
3. Add structural-pocket similarity as a fourth feature.
4. Re-run both benchmark modes; report results including misses. Only then use `--save-summary`
   (it refuses while data is unverified unless you pass `--allow-unverified`, and then labels the result).
5. Have outside researchers test it on their own data and report outcomes back.
