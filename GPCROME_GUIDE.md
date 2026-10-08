# GPCRome analysis: what it does, how to test it, what to trust

## What changed in this version
- **Present in your experiment, then what it might mean.** For each orphan: the observations from your own data, then ranked hypotheses on three questions (what it couples to, what it might bind, what it might be doing), each with justification and counter-evidence. Where two methods disagree it says so and names the assay that settles it.
- **Experiments come from your table.** No protein search needed. Receptors are grouped so one plate answers several. Every assay has an "if you see X, it suggests Y, then Z" table.
- **Each orphan is matched on where it is expressed in your matrix**, not on the sidebar tissue. An orphan in tissue the precedent library has no case for gets no precedent hypothesis (it abstains) rather than a borrowed one.
- **Every plot has a note:** what it shows, why you see it, how to read it, what to be careful of.
- **Video-style player** for the signalling animation: play/pause, drag the timeline, jump between steps, caption for each step using your receptor's data. It pauses when off-screen.
- **Precedent library: 30 cases, 7 ligand classes**, all unverified (curated from memory). Leave-one-out: 10/29 top picks (34%) versus 28% for always guessing the commonest class and 14% for random. Use the ranked list as where to start screening, not as an answer.
- **Fixed:** hotspot clustering returned nothing for every protein; numbers from APIs arriving as text crashed the scorers; an unsourced gnomAD table was removed (constraint now shows only if it came from gnomAD); a receptor could be scored against its own documented case.

## Earlier changes
- **Candidates view (default):** two ranked lists from every analysis on your data: receptors worth pursuing in a cell state, and orphans worth deorphanising. Components and weights are shown; weights are design choices, not fitted.
- **Pattern-learned hypotheses** at the top of the Overview: for an orphan, the precedent model's ligand-class and coupling hypotheses; for a receptor in the case library, a **blind test** (the model is retrained without that receptor and asked what it would have predicted).
- **Annotated visuals:** receptor topology map, residue-scaled protein map, expression heatmap, enrichment plot, ligand-to-receptor communication diagram, signalling-role network, and 3D colour modes (confidence, topology with TM1-TM7, AlphaMissense, variant burden).
- **Full receptor list** loads automatically from IUPHAR (396 GPCRs, 41 orphans in release 2026.2); if it cannot, the app says why and falls back to a small seed list.
- The generic recipe cards (qPCR, Western blot, knockdown) were removed because they were not derived from your data.

## The questions it answers
Built around the questions a cancer-immune GPCR group asks of single-cell or bulk data:
1. **Which G-protein class dominates the receptors that change in a cell state?** (for example Gs, Gi, Gq, G12 among receptors higher in exhausted than effector T cells)
2. **What does each uncharacterised (orphan) GPCR probably couple to, and in which cell type is it?**
3. **What does each GPCR track?** T-cell exhaustion, YAP/TAZ targets, hypoxia, Treg, cytotoxicity, or a gene set you paste in.
4. **Which ligand producers and receptors line up** across cell types (prostaglandin E2, adenosine, CXCL12 and others)?
5. **Which of the receptors that matter already have drugs** that act in the direction you want?
6. **Are they altered in cancer?** (from your own mutation / amplification / deletion table)

## What to give it
- Your differential table (gene, fold-change, p-value), in the sidebar under **Your Experiment**. It is used for the orphan hypotheses and for the coupling enrichment.
- Optional: an expression matrix (genes by cell types, tumours or conditions), a coupling table, and an alteration table. Templates are in the app.
- The microenvironment (sidebar): disease, tissue, model, patient context.

## What it checks about itself
- **Self-test:** it hides each known receptor's coupling and predicts it from the others, then compares with a naive baseline. If it cannot beat the baseline on your data, every prediction is marked unsupported.
- **Null behaviour:** shuffled data gives no significant coupling class, and receptors with no structure get no call and no program association (tested).
- **ML validation:** each claim lists its counter-arguments (unverified coupling table, few contexts, a receptor confined to one cell type, a signal from one or two receptors).

## The test case
Press **Load the example case** (Overview). It is SYNTHETIC: invented numbers with answers planted in them (19 checks, including noise controls that must get no call).
It shows the software finds structure that is there and stays silent where nothing is. It says nothing about biology.

## Test it on real data
Aggregate a public tumour single-cell atlas to one column per cell type (for example GSE103322, a head and neck atlas; check the accession) and upload it. Read the self-test first.
The best test is a dataset where your group already knows the answer.

## Limits to keep in mind
- The built-in coupling table is a **small seed curated from memory and not verified**. Replace it with your own or IUPHAR / GproteinDb couplings (upload in the app). Every claim says which table it used.
- Marker-gene programs and the ligand-producer / receptor pairs are short curated lists. Edit or replace them. Producer expression stands in for ligand availability; secretion is not measured.
- Correlation and enrichment are associations, not regulation. A prediction is a reason to run a G-protein-selective assay, not a result.
- With about 8 or fewer contexts the statistics are weak and the tool says so. 14 or more give clean results on the example.
- Needs at least 8 characterised receptors with a known coupling, across 2 or more classes, to test itself.
- Drug lookups show recorded interactions only. They are not approvals or recommendations.
