# Protellect rebuild: what changed, what is verified, what is not

`app.py` is now 4,721 lines (from 16,010) and the engine lives in a new folder, `protellect_core/`.

## The three problems in your screenshot
1. **"Hypotheses tab unavailable: ImportError ... convert_iuphar_bytes".** Your repo had an older copy of the engine files, so the new `app.py` and the old
   folder disagreed. There is no separate Hypotheses tab any more, and the engine now lives in a **new folder name** (`protellect_core`) so stale files cannot
   collide. `app.py` checks the folder's version on start-up and shows a plain message ("upload the whole protellect_core folder") instead of a traceback.
2. **"Search error: unsupported operand type(s) for +: 'int' and 'dict'".** This bug is in your original app, not in my edits. AlphaMissense data is
   `position -> amino acid -> {score, class}`, and the analysis trace did `sum()` over those dictionaries. It blocked the whole analysis for any protein that
   has AlphaMissense data. Fixed. A second bug sat beside it: the ACMG check filtered AlphaMissense values with `isinstance(s, (int, float))`, which discards every
   real score, so AlphaMissense never reached it. Fixed, and the rule itself was wrong (ACMG's PP3 is judged per variant, but the code declared a gene-level PP3).
3. **Scrolling.** `iframe { overscroll-behavior: contain }` stopped the page scrolling whenever the cursor was over any embedded view (the structure, animations).
   Every nested tab strip was also sticky. Both fixed, and the 3D viewer now has a click-to-interact guard so the mouse wheel scrolls the page until you click it.

## Where the "hallucinated" information came from
- A **fixed mutation-cascade story** ("ER stress... caspase cascade... cell blebbing") shown for every variant of every protein. Replaced by a cascade whose stages
  depend on the variant's class and are each tagged recorded / derived / predicted / expected / untested.
- `compute_gi` text stating, as fact, that a protein with no ClinVar pathogenic variants "may be redundant", followed by a canned list of other proteins. Replaced by factual statements.
- An **experiment ROI table of invented numbers** (`p_success 0.85`, `cost_usd 2000`, "eliminates ~50% of candidates"). Removed everywhere, including the Excel export.
- A **hand-typed disease prevalence table** and the "orphan-drug eligibility" derived from it. Removed.
- The Experiments tab's templated protocols. Rebuilt from evidence.
- **The rule now enforced:** nothing is shown as a finding unless it carries a proof (a named source with the specific record). Rule-based statements must state their
  rule. Anything without proof is withheld and counted ("N statements withheld"). Every claim has a "Proof and ML validation" popover.

## Your brief, mapped
| You asked for | Where it is |
|---|---|
| Niche + what to give / expect, one window | Overview, "What to give, what to expect" (and the first-open tutorial) |
| Overview with a technical animation of the experiment | Overview (SVG animation driven by your data; anything predicted is labelled PREDICTED) |
| Possibility and strategy, backed by genetics and ClinVar | Overview: score with every component, its rule and source; strategy rules with the data that triggered them |
| Associated diseases, defects, ranked "what may happen", how to go about it | Overview |
| "ML validation" instead of "AI debate" | Every claim; optional language-model cross-check |
| Triage = AlphaFold structure + interactions + variant navigator, merged with Explorer | Triage |
| Pharma -> Druggable hotspots with PK/ADMET, side effects, scenarios | Druggable hotspots |
| Disease Link -> Genetics: thresholds, cascade, interactions | Genetics |
| Case Study: diseases, tissues, body systems | Case Study |
| Top banner from the experiment, pointing to the tab to follow | Banner above the tabs |
| Sidebar microenvironment that changes the whole workspace | Sidebar "Microenvironment" |
| Tutorial only on open | First open only; reopen from the sidebar |
| ML that learns | Record an outcome (Overview): a confirmed outcome becomes a case and the model retrains immediately |

## Verified (with realistic stand-in data, not your live data modules)
- 88 package tests pass from a fresh unzip. The whole app runs end to end 30/30: first open, TP53 search (no Search error), an orphan GPCR, a loaded CSV,
  microenvironment tailoring, tutorial opening once, and recording an outcome (the model went from 13 to 14 cases).
- The viewer's scroll guard and focus-on-variant were tested in a headless DOM. SVGs were rendered and inspected.
- ADMET parsing, rules and FAERS parsing are tested against fake PubChem and openFDA replies.

## NOT verified, and what is not true yet
- **I do not have `protellect_data.py`.** Your trace showed OpenTargets, DGIdb, Europe PMC, ClinGen and isoforms returning **0 results for TP53**, which cannot be
  right. Those fetchers are probably failing silently, and the app counted that as success. Sections that depend on them say "no data", but the real fix is in that file.
- Real PubChem, openFDA and Gemini/Claude calls were not made (no network here). Their parsing is tested; your first real use is the live test.
- The tab-jump button in the banner uses a small script and could not be tested here. The text beside it always says which tab to open.
- The ML is a three-feature logistic regression on 13 expert-**unverified** cases. It will not be accurate until the library is verified and grows; it is a
  working learning loop, not a trained product.
- ADMET is published rule screens plus real compound properties, not a learned model. Side effects are spontaneous-report counts (not causation). The "scenarios" organise evidence; they do not predict clinical outcomes.
- The "Possibility" weights are design choices, shown in full, not fitted parameters.

## Before selling (the honest list)
Verified case library and a measured accuracy; working data fetchers (above); data-licence checks for each source you display; real accounts and payments
(the plan/payment screens are placeholders); a clear "research use only" statement; and a few real labs running it on their own data.

## Deploy
1. Upload the whole `protellect_core` folder to the repo root. Delete the old `protellect_hypothesis` folder, the `pages` folder, and any loose engine files from earlier uploads.
2. Replace `app.py` with the new one. Reboot. Nothing new needs adding to `requirements.txt`.
3. Open the Overview and load the full receptor registry (Guide to Pharmacology file); only 4 orphan GPCRs are known by default.
Rollback: GitHub -> app.py -> History.
