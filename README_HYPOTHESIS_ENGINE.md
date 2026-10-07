# Protellect Hypothesis Engine (beta scaffold)

Upload a processed experiment (expression table, variant table, or screen hits) plus disease and tissue
context. The engine finds the orphan GPCRs in it, compares each to documented historical deorphanization
cases, and returns ranked **hypotheses** (likely ligand class, likely G-protein coupling, a weak
disease-association analogy) with the reasoning, the precedents used, evidence flags, and the lab
experiment that would test each one.

**Hypotheses, not answers.** Only a wet-lab experiment confirms what a receptor does.

## Install (3 steps, no edits to app.py)
1. Copy `protellect_hypothesis/` and `pages/` into your repo root (next to `app.py`).
2. Nothing to add to `requirements.txt`: the engine uses only numpy, pandas, requests and streamlit, which your app already has. (An earlier version needed scikit-learn; that dependency is gone.)
3. Run Streamlit as usual. A "Hypothesis Engine" page appears in the sidebar.

To embed it inside an existing tab instead:
```python
from protellect_hypothesis.streamlit_tab import render_hypothesis_tab
render_hypothesis_tab()
```

## Check it works
```bash
python -m pytest protellect_hypothesis/tests -q          # 61 tests
python -m protellect_hypothesis.benchmark --mode loo      # retrospective benchmark
python -m protellect_hypothesis.benchmark --mode temporal # strict temporal split
python -m protellect_hypothesis.benchmark --critic        # does the critic help?
```

## Make it part of Protellect (one system, not a side page)
The engine becomes a **Hypotheses tab inside your app**, using what the app already holds:
- the **CSV uploaded in the sidebar** is analyzed directly, so there is no second upload;
- the **protein you searched** can be analyzed in lookup mode, with its UniProt tissue text used as annotation;
- the sidebar **disease field** prefills the context;
- a **Receptor registry** panel inside the tab loads the full Guide to Pharmacology list (the seed list recognizes only 4 orphans).

To add the tab, either:
1. **Send your live `app.py` to whoever maintains this** and get back a patched, compile-checked file to upload; or
2. Make the three edits by hand using `app_py_edits.txt` (copy-paste, about 2 minutes), or
3. Run the patcher yourself from the repo root: `python protellect_hypothesis/patch_app.py app.py --check` (preview), then without `--check` to apply. It writes `app.py.bak`; `--undo` restores it.

The patch is three small, marked edits (look for `protellect_hypothesis integration` in `app.py`): the tab name is added to `ALL_TAB_NAMES`; the tab is forced into the visible set (right after Triage) so users who already finished onboarding or set a research goal still see it; and a `with tabN:` block calls the engine inside try/except, so if the engine ever fails the rest of the app is unaffected. The patcher checks every anchor before writing and refuses, changing nothing, if `app.py` has a different structure. After patching you can delete `pages/` (the standalone page), or keep it.

**Tested:** the patcher and the embedded tab were tested against a stand-in host app with the same tab registry (tab placement, sidebar CSV flow, lookup mode, failure isolation, undo) and the patcher was run on an older copy of your `app.py`. **Not tested:** inside your live app, which I have not seen (its sidebar shows an "Orphan GPCR" domain that my older copy lacks). Check the new tab there after deploying.

## What the user sees
The page has two tabs. **Guide** shows exactly what to upload (three accepted shapes, downloadable CSV templates, the rules for every file), what to enter as context, what comes back, how to read the critic column, and what is NOT delivered. The table in the guide is generated live by the engine from the bundled example, so it cannot drift from the code. **Run an analysis** takes the upload and returns a results-at-a-glance table, hypothesis cards, a CSV of every hypothesis, and a readable report. `Protellect_User_Guide.docx` is the same guide as a shareable 2-page document.

## What is in the box
| File | Job |
|---|---|
| `io_parsers.py` | Reads the three experiment shapes, auto-detects columns, cleans, one row per gene |
| `registry.py` | Orphan vs characterized GPCR registry, receptor annotations, IUPHAR CSV importer, live-annotation hook |
| `cases.py` + `data/cases.json` | Historical case library, validation, strict temporal filtering |
| `ranker.py` | The ML layer: logistic regression over precedent-similarity features, learned from historical cases only |
| `engine.py` | Orphan detection, hypothesis generation, evidence flags, caveats, abstention |
| `benchmark.py` | Leave-one-out and strict temporal retrospective benchmark with baselines |
| `templates.py` | Single source of truth for what to upload (used by the UI, the templates and the guide) |
| `report.py` | Results table, flat hypotheses table, downloadable report |
| `critic.py`, `llm_debate.py` | Counter-argument layer (see below) |
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

**6. The ML layer is plain numpy now.** It matches the scikit-learn model it replaced to three decimals, with no extra install.

**7. `support` is a relative ranking, not a probability.** It splits 1.0 across one receptor's candidates.
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


## Critic and AI debate (the "check every argument with counter-arguments" layer)

**Layer 1: deterministic critic (`critic.py`), always on.** Every hypothesis gets counter-arguments from
checkable rules, never from free-text model opinion: a refuted or contested pairing for that exact receptor
(`data/refuted_pairings.json`), related receptors that bind a different class, a match that rests on tissue
alone, a near-tie, a single precedent, a weak signal in your own data, and the engine's own leave-one-out
track record. Verdict: `holds up`, `weakened`, or `contested`. Example: GPR151's peptide hypothesis is
flagged contested because galanin, a peptide, is the pairing that failed replication.

**Layer 2: AI debate (`llm_debate.py`), optional, runs on a button click.** A model argues against the
hypothesis but may only cite numbered evidence we supply. Code enforces: uncited reasons are dropped; the
verdict can stay or get more cautious but never more confident than Layer 1; anything it wants checked
beyond the evidence is shown as an unverified "open question". To enable it, add ONE of these keys to your Streamlit app's Secrets (never to GitHub):
```
GEMINI_API_KEY = "your-google-key"        # Google Gemini; a free tier may apply, check current limits
ANTHROPIC_API_KEY = "sk-ant-your-key"     # Claude; paid, billed separately from a chat subscription
```
`GOOGLE_API_KEY` also works for Gemini (the same names your main app uses). If both keys are present, a
selector lets you pick a preferred provider, and if it fails (bad key, rate limit, retired model) the other is tried
automatically; the page says which one answered and why the first failed. With no key, the debate button says so and everything else still works.
Gemini keys are sent in a request header, not in the URL, so they cannot leak into error messages.
Defaults: `gemini-2.0-flash` and `claude-sonnet-4-20250514`. If a model has been retired or your account cannot
use it you will see a 404 message; set `PROTELLECT_GEMINI_MODEL` or `PROTELLECT_MODEL` to one you can use.
**Neither live API was called during development (no keys in the build environment).** Request and response
handling is tested with a fake HTTP layer, including errors (401/403, 404, 429, empty reply), so try one real
click and tell me what it shows.

**Does the critic actually help? Measured, not assumed** (`--critic`, leave-one-out, 13 unverified cases):
- Re-ranking by critic penalties did not change top-1 accuracy (8/13 both ways), so the critic does NOT reorder results.
- As a confidence flag it looked useful: predictions rated "holds up" were right 8/10 times; "weakened" 0/3.
  Three weakened cases is a hint, not a result. The critic's related-receptor check also uses the same
  family features as the ranker, so some overlap with the ranker's information is expected.

**"Background" caveat.** Streamlit runs on user actions and has no background workers on Community Cloud.
The critic runs inline (it is fast); the AI debate runs when you click. A true always-on background agent
would need a separate worker service.
