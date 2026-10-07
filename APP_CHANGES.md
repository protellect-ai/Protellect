# app.py change record (lean build)

16,010 lines -> 9,396 lines (41% smaller than the app you uploaded). Same sign-in, same protein analysis, one new Hypotheses tab.

## What a visitor sees
- Sign in (or Continue as Guest) -> straight into the app. Before: 3 clicks (sign-in, onboarding, domain screen).
- Eight tabs in one fixed order: Summary, Hypotheses, Triage, Explorer, Pharma, Experiments, Disease Link, Case Study.
- Hypotheses uses the CSV you upload in the sidebar, the protein you searched (with its UniProt tissue data) and the disease field.
- The main app makes no AI-provider calls. The only AI is the optional "Run AI debate" button inside Hypotheses (Gemini or Claude key).

## Removed in this round
- **Chemistry tab** (the chemical-backbone renderer and its CSV twin).
- **AI Report tab** (the report generator, its prompts, and the Claude/Gemini chat plumbing).
- **Workspace tab**: saved-protein history, the multi-protein screener, the lab configurator chatbot, shortlist downloads.
- **Sidebar Workspace Chat** and the sidebar lab-profile summary.
- **Lab profile and paper library.** Its only purpose was feeding AI Report citations and the chat, so it went too.
- 18 functions and 14 constants nothing used any more (incl. duplicate helper copies).

## Removed in the previous round
- The research-domain system (gate screen, badge, Change Domain, registry, six domain workspaces), the blocking onboarding wizard,
  goal-driven tab reordering, and ~20 unused/duplicate functions.

## Still in the app, for you to judge
Triage (wet-lab CSV triage), Explorer (structure/property views, "What if it mutates?"), Pharma (druggability, drugs, trials),
Experiments (suggested experiment roadmap), Disease Link, Case Study (protein-domain cards), the sidebar exports (Markdown report, Excel).

## How it was checked
- Compiles; no new undefined names against the original; no leftover references to removed tabs, chat, or domain code.
- Ran the previous build and this one side by side under Streamlit's test harness with stand-in data modules, for a searched protein
  and for a loaded CSV: no exceptions in either, and the only differences are the removed items (plus example-gene hint text).
- The Hypotheses tab works in both modes (sidebar CSV; searched protein in lookup mode). Engine tests: 61 pass.
- Per click in the harness: 1.20s (original) -> 1.00s (previous build) -> 0.76s (this build). Indicative only.

## NOT checked
- The real data modules (protellect_data.py etc.) were not available: real fetches, real data and the real look were not exercised.
  Click through each remaining tab once after deploying.
- Removed features are gone for good from the app. Restore from GitHub history if you miss one.

## Deploy
Replace app.py. Keep the protellect_hypothesis folder from the latest zip (unchanged). Reboot. Rollback: GitHub -> app.py -> History.
