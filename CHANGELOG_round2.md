# Protellect Reliability Pass — Round 2 Changelog (Step 3 focus)

Builds on the previous round (syntax fix, escape hatch, dead code removal,
registration/payment honesty). This round targets **Step 3: verify LLM
output before it's shown.**

## Fixed and verified this round

### 1. Closed a real, structural grounding hole (found while implementing Step 3)
`ai_synthesize()`'s API call was still passing `web_search` as an available
tool, even though the prompt text said "use ONLY the data provided." A text
instruction cannot override a tool the model can actually call — this let
the model search the live internet mid-response regardless of what the
prompt said. **Removed the tool entirely.** This is arguably a more
important fix than the wording change from the previous round, since it
closes an actual capability, not just an instruction.

### 2. Built `verify_ai_claims()` — a real, tested claim-verification function
After `ai_synthesize()` gets a response back from Claude, this function:
- Extracts PMIDs and numeric values from the model's free-text output fields
  (executive_summary, drug_opportunity, population_genetics_interpretation,
  etc.)
- Cross-checks each against the actual source data that was passed into the
  prompt (gnomAD pLI/oe scores, ClinVar counts, STRING interaction scores,
  known abstract PMIDs)
- Flags anything that doesn't match, rather than letting it through silently

**This was tested, not just written** — I ran it against two synthetic
cases: source-matching data (0 flags, correct) and a case with a fabricated
PMID and a made-up percentage (both correctly flagged). Test code and
output are reproducible; not just asserted.

**Honest limitation, stated plainly:** this is a heuristic checker. It
catches numbers and citations that don't trace to source data — a real and
useful class of error. It will NOT catch a plausible-sounding claim built
from real numbers used the wrong way, or subtler hallucination that doesn't
involve a fabricated number or PMID. Treat "0 flags" as "no crude
fabrication detected," not "this output is correct." One known imprecision:
a fabricated PMID's digits currently get flagged twice (once as a citation,
once as a bare number) — over-flagging, which is the safer failure
direction, but worth knowing about.

### 3. Wired the flags into the actual UI, not just the returned dict
The AI Verdict card in the report now shows a visible warning banner with
flag count and flag rate when unverified claims are detected, with an
expandable list of the specific flagged claims and why. When nothing is
flagged, it shows a small confirmation line instead of silence, so absence
of a warning is a stated fact, not an assumption.

### 4. Step 4 test harness — scaffold built, explicitly NOT claiming to run
`test_ground_truth.py` loads `ground_truth_test_set.csv` and defines the
per-row check logic. **I ran it, and it correctly refuses to report any
pass/fail results** — it exits with an error explaining that
`run_pipeline_for_gene()` is a stub, because it depends on `fetch_uniprot`,
`fetch_clinvar`, etc. from `protellect_data.py`, which has not been
provided. This is intentional: a harness that silently fabricated results
here would be exactly the failure mode this whole project exists to
prevent. It's ready to run for real the moment that file is available.

## Still blocked on `protellect_data.py`

**Step 1 (VerifiedDataPoint wrapping of API responses) — cannot be done.**
This has to happen inside `fetch_uniprot()`, `fetch_clinvar()`,
`fetch_gnomad()`, etc., which live in a file I have never seen. I will not
guess at the internals of functions I don't have — that would risk writing
something that looks plausible but doesn't match your actual API response
shapes.

**Step 4 (running the test harness for real) — same blocker.**

## What to do next
Upload `protellect_data.py` (and ideally `protellect_citations.py` /
`protellect_icons.py` since `app.py` imports from those too) and I can:
1. Wrap the real fetch functions in `VerifiedDataPoint` (Step 1)
2. Wire `run_pipeline_for_gene()` in the test harness to the real pipeline
3. Actually run the ground-truth suite and report real per-row results —
   not estimated, not assumed
