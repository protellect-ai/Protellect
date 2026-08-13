# Protellect app.py — Reliability Pass Changelog

**Before:** 15,995 lines, would not run (`SyntaxError`)
**After:** 14,710 lines, compiles clean, verified with `python3 -m py_compile`

## Fixed (safe, verified, zero-risk)

1. **Syntax error crash** — a duplicated `requests.post(...)` block left an
   unmatched `)` and broke the `try/except` in `ai_synthesize()`. The app would
   not start at all. Removed the duplicate.

2. **Hallucination escape hatch** — the AI synthesis prompt said "based on the
   data above AND your knowledge of current biomedical literature," which let
   the model fill gaps from training data instead of only the verified data
   passed to it. Changed to "based ONLY on the data explicitly provided
   above... if a field cannot be supported by the data, say so."

3. **Dead code removed — confirmed via execution-path tracing, not guessed:**
   - `render_lab_chatbot()` (~520 lines) — defined but never called anywhere
     in the file.
   - Duplicate second definitions of `render_oncology_workspace()`,
     `render_neuroscience_workspace()`, `render_pharma_workspace()`,
     `render_molbio_workspace()` (~600 lines) — unreachable because the live
     call sites hit `st.stop()` before the script ever runs far enough to
     reach these later definitions.
   - `assess_gpcr_piggybacking()` (~170 lines) — never called; the function
     actually used in the UI is `g_gpcr_full()`, which is more conservative
     (labels uncertain classifications "— presumed" rather than asserting
     confidence).
   - **Total: ~1,290 lines of dead code removed, zero behavior change** —
     each deletion was verified unreachable before removal, not assumed.

4. **Registration honesty** — added a visible disclaimer on the sign-up form:
   accounts are session-only and not yet persisted. Previously the UI implied
   a real account was created.

5. **Payment honesty** — "Upgrade to Pro / Enterprise" buttons (3 locations)
   now check if the Stripe link is still a placeholder and show "Payments
   coming soon" instead of linking to a dead checkout URL.

## Found, NOT fixed — needs a decision, not a guess

- **`call_claude_api` inconsistency:** two versions of this function still
  exist. The main workspace gene-chat feature uses a simpler version with no
  Gemini fallback or offline fallback. A separate lab-setup chat elsewhere in
  the app uses a fuller multi-provider version. Both are still actually used
  by different live features, so neither could be safely deleted without
  restructuring where each is defined in the file. This should be
  consolidated into one version, but that's a real refactor, not a two-day
  fix — flagging rather than rushing it.

- **Severity/prevalence/onset heuristic labeling** — already labeled in the
  uploaded file ("Est. Severity ... *" with a disclaimer footnote). No
  further change needed here; confirmed present.

## What this does NOT include
This pass did not implement the full `VerifiedDataPoint` provenance wrapper,
per-claim LLM verification against source data, or the ground-truth
regression suite discussed earlier — those are larger, structural changes
that need dedicated implementation time, not a same-day patch pass. This
changelog covers what was safe to fix without risking new breakage right
before your meeting.
