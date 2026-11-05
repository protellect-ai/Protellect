"""A short, fixed explanation above every plot: what it shows, why you are looking at it, how to read it, and what to be careful of.

Written once per plot type so that every figure in the app answers the same four questions. Nothing here depends on your data, so nothing here is a finding.
"""
from __future__ import annotations

import html
from typing import Dict

PLOTS: Dict[str, Dict[str, str]] = {
    "volcano": {
        "title": "Volcano plot of your differential table",
        "what": "Every dot is a gene in your table. Left to right is how much it changed (log2 fold change); height is how strong the statistical evidence is (-log10 p). Amber dots are orphan GPCRs, blue dots are characterised GPCRs, grey dots are everything else.",
        "why": "To show where receptors with no known ligand sit among everything that changed. An orphan that is both far from zero and high up is a lead worth a hypothesis.",
        "read": "Dotted vertical lines mark a two-fold change either way; the dotted horizontal line is p = 0.05. The twelve GPCRs with the largest change times significance are labelled.",
        "care": "With few replicates p-values are unstable. Rank by effect size, then confirm the top receptors in a second sample.",
    },
    "heatmap": {
        "title": "Where each GPCR is expressed",
        "what": "Rows are GPCRs, columns are cell contexts. Colour is expression scaled within each row, so you see where each receptor is highest, not which receptor is highest overall. Amber labels are orphans; the chip shows a known coupling.",
        "why": "Where an orphan is expressed limits where its ligand can come from and what it can do. Orphans that sit in the same contexts as characterised receptors are the basis of the coupling prediction.",
        "read": "A row with one bright column is cell-type specific; an even row is broad. Rows are grouped by the context in which they peak.",
        "care": "Row scaling exaggerates differences in weakly expressed genes. Check the absolute values in the table before trusting a pattern.",
    },
    "enrichment_bars": {
        "title": "Which signalling class dominates the cell state",
        "what": "For each class of receptors by G-protein partner (Gs, Gi/o, Gq/11, G12/13), a normalised enrichment score: positive if its members sit toward the top of your ranking, negative if toward the bottom.",
        "why": "To ask whether a signalling pathway, not just one gene, characterises a cell state, for example cAMP-linked Gs receptors in exhausted T cells. A pathway is something you can block with a drug or a pathway-level experiment.",
        "read": "A longer bar means stronger over- or under-representation. Act only on classes whose FDR in the table is below 0.05.",
        "care": "It depends on the coupling table, and the built-in table is unverified. A class with few members has little statistical power.",
    },
    "enrichment_curve": {
        "title": "Running enrichment curve for one coupling class",
        "what": "Genes are ordered from most increased (left) to most decreased (right) in your contrast. Each tick is a receptor of the chosen class. The curve climbs when members cluster at the left and falls when they fall to the right; its peak is the enrichment score.",
        "why": "It shows where in your ranking the class sits and which receptors drive the result (the labelled leading edge), so you know which ones to test first.",
        "read": "A high peak toward the left means the class is enriched among increased genes. Ticks spread evenly along the axis mean no enrichment.",
        "care": "The p-value comes from shuffling class labels, so it is only as good as the coupling table behind it.",
    },
    "programs": {
        "title": "What each receptor tracks across contexts",
        "what": "Each row is the correlation (Pearson, on log expression) between a receptor and a gene program such as T-cell exhaustion or YAP/TAZ targets, across your cell contexts. FDR comes from shuffling the contexts.",
        "why": "It ties a receptor nobody understands to a process you care about, which narrows what its ligand and function could be.",
        "read": "A high r with a low FDR means the receptor rises and falls with the program across your contexts.",
        "care": "With few contexts, two genes often correlate only because both are high in the same cell types. The 'program test' experiment separates cause from cell-type composition.",
    },
    "communication": {
        "title": "Who may be talking to whom",
        "what": "Arrows run from contexts that express a ligand-synthesising enzyme to contexts that express the matching receptor. Arrow width is the strength (the weaker of the two z-scores); parallel arrows for different ligands are stacked.",
        "why": "For a receptor with no known ligand, the missing half is the source. This shows which cells could make a candidate ligand and which cells could hear it.",
        "read": "A wide arrow between a producer and a receiver context is a plausible axis. An arrow back to the same context is autocrine.",
        "care": "RNA for a synthesising enzyme is an indirect proxy for the ligand being present. Confirm by measuring the molecule (mass spectrometry).",
    },
    "alterations": {
        "title": "How often the receptor gene is altered in tumours",
        "what": "Each bar is the fraction of tumours in your pan-cancer table in which the receptor gene is amplified, mutated or deleted.",
        "why": "A gene altered unusually often in a cancer may matter to it. For an orphan that is a reason to test dependency, which is one of the strongest arguments for pursuing one receptor over another.",
        "read": "Compare the same receptor across cancer types, and compare receptors within one cancer type.",
        "care": "Amplicons carry many genes: a receptor can be amplified only because a neighbour is the real driver. Check the neighbouring genes.",
    },
    "topology": {
        "title": "Receptor topology map (seven transmembrane helices)",
        "what": "The seven transmembrane helices with their residue ranges (from UniProt), conserved motifs found in the sequence, and variants placed by residue. Colour is AlphaMissense pathogenicity.",
        "why": "Where a variant lies, in the ligand pocket, at the G-protein interface or in a loop, changes what it is likely to break, and so which functional test to run.",
        "read": "Variants stacked on one helix or motif suggest a functional hot-spot. Helix statistics show how much of the variant burden each segment carries.",
        "care": "A motif match is a pattern in the sequence, not proof of function. Orphan receptors often have degenerate motifs.",
    },
    "architecture": {
        "title": "Protein architecture map",
        "what": "The protein drawn to scale by residue: domains and sites on the backbone, ClinVar variants as markers above it, and AlphaMissense and AlphaFold-confidence strips beneath.",
        "why": "It shows whether variants cluster in a domain or site, and whether that region is a confident part of the predicted structure.",
        "read": "Taller markers mean more review stars. Dark segments on the confidence strip are well-predicted regions; pale ones are floppy and uninformative.",
        "care": "Clusters can reflect where researchers looked as much as where biology is, since ClinVar is submission-driven.",
    },
    "network": {
        "title": "Interaction partners, coloured by signalling role",
        "what": "Proteins that STRING lists as functional partners of this protein. Colour shows signalling role: G alpha, G beta/gamma, arrestin, GRK, RGS, effector, Rho pathway, other GPCR, other. Closeness reflects the STRING score.",
        "why": "For a receptor, partners that are G proteins, arrestins or GRKs are clues to how it signals. For any protein it shows what it connects to.",
        "read": "Look at the roles present, not just the number of nodes.",
        "care": "STRING scores include text-mining and co-expression, so a link means association, not direct binding.",
    },
    "structure3d": {
        "title": "Predicted 3D structure (AlphaFold)",
        "what": "The AlphaFold model, with five colour modes: prediction confidence, the seven helices, AlphaMissense pathogenicity, ClinVar variant burden, or mechanical mobility. The Motion button animates the lowest-frequency collective motions of the fold (an elastic network model on the C-alpha atoms); pick mode 1, 2 or 3.",
        "why": "To see where variants and confident regions sit in space, and which of them are near each other even if far apart in sequence.",
        "read": "Click the viewer to interact; until then the page scrolls normally. Move the mouse out of it to give the wheel back to the page.",
        "care": "It is a prediction without a ligand. The binding pocket of an orphan is not reliable, and low-confidence loops should not be interpreted. The Motion animation shows what the resting fold is mechanically free to do. It is not an active state, not a ligand-induced change and has no lipid or G protein in it.",
    },
    "signalling": {
        "title": "What may be happening, step by step",
        "what": "An animated walk-through of GPCR activation for this receptor: ligand binding, helix movement, G-protein engagement, nucleotide exchange and effector signalling, with this receptor's own helix boundaries, motifs and predicted coupling.",
        "why": "To make the hypotheses concrete: each step names what could be measured, so you can see which experiment tests which step.",
        "read": "Use the player controls to play, pause, step or drag the timeline. The caption under the picture says what the current step means for your receptor.",
        "care": "It is a model of the generic mechanism with your receptor's data placed on it. A step shown for an orphan is a prediction, labelled as such.",
    },
    "candidates": {
        "title": "Ranked candidates and how the score is built",
        "what": "Receptors ranked by a transparent score. Each component (change in your data, specificity, link to a cell state, druggability, genetics) is shown with its weight; unavailable components are left out of the denominator, not set to zero.",
        "why": "To tell you where to spend the first experiment. The weights are design choices, not fitted to outcomes, and are shown so you can disagree with them.",
        "read": "Use the ranking to choose, and the component breakdown to see why. A candidate high on one component only is a different bet than one moderately high on four.",
        "care": "A score is a prioritisation aid, not a probability that the receptor is the right target.",
    },
    "retrodiction": {
        "title": "Blind test of the precedent model on a known receptor",
        "what": "For a receptor whose ligand is known, the model is retrained without it and asked what it would have predicted using only context and neighbours. The bars are its ranking of ligand classes.",
        "why": "It tells you how much to trust the model's guesses on orphans: if it cannot recover answers it was not shown, its orphan predictions deserve less weight.",
        "read": "The documented class is marked. A high bar there means the model would have pointed the right way.",
        "care": "The case library is small and not yet expert-verified, so one success is an illustration, not a measured accuracy.",
    },
    "clinvar": {
        "title": "ClinVar entries for this gene",
        "what": "How many ClinVar submissions fall in each classification, and the review quality (stars) behind the pathogenic and likely pathogenic ones.",
        "why": "To judge how well-established the gene-disease link is: many highly reviewed pathogenic entries are strong evidence; a few single-submitter entries are weak.",
        "read": "Compare the pathogenic bars to the uncertain ones, and look at the stars.",
        "care": "A gene with few entries may simply be understudied, not safe.",
    },
    "am_residue": {
        "title": "AlphaMissense score for each substitution at one residue",
        "what": "For the selected residue, the predicted pathogenicity of every possible amino-acid change.",
        "why": "To judge a variant in context: a residue where most substitutions score high is intolerant; one where only the observed change scores high is more specific.",
        "read": "Bars above the pathogenic threshold are predicted damaging.",
        "care": "A prediction, not a measurement. It is a reason to run the functional test, not a substitute.",
    },
    "systems": {
        "title": "Evidence by organ system",
        "what": "How many evidence items for this protein relate to each organ system.",
        "why": "To show where the biology concentrates, which is where a phenotype or side effect is most likely to appear.",
        "read": "Taller bars mean more supporting items, not more severe disease.",
        "care": "Counts reflect what has been studied, not only what is true.",
    },
    "cascade": {
        "title": "How a variant could propagate, stage by stage",
        "what": "Stages from the DNA change to the cell and the person. Each stage is tagged: recorded (in a database), derived (computed from recorded data), predicted (from a model), expected (follows from the mechanism) or untested.",
        "why": "To separate what is known about a variant from what is only plausible, so you can see exactly where the evidence stops.",
        "read": "Move the slider to choose the variant. Stages tagged 'recorded' are the solid ones; everything after the first 'predicted' or 'untested' stage is a hypothesis.",
        "care": "A tidy chain looks more certain than it is. Stop reading at the first stage that is not recorded.",
    },
    "faers": {
        "title": "Most-reported adverse reactions for a drug",
        "what": "Counts of spontaneous adverse-event reports for the selected drug from the FDA reporting system (openFDA FAERS).",
        "why": "To judge whether an existing drug is a sensible tool or repurposing lead for this target.",
        "read": "Compare reaction types, not the absolute numbers.",
        "care": "Counts reflect how widely a drug is prescribed and reported, not how risky it is. They cannot be turned into incidence rates.",
    },
}


def note_html(key: str) -> str:
    p = PLOTS.get(key)
    if not p:
        return ""
    row = lambda label, text: (f"<div style='margin:2px 0'><span style='color:#7dd3fc;font-weight:700'>{label}</span> "
                               f"<span style='color:#b7c9db'>{html.escape(text)}</span></div>")
    return ("<div style='border-left:3px solid #1f6f9f;background:#06142a;border-radius:0 8px 8px 0;padding:.55rem .9rem;margin:.2rem 0 .6rem 0;font-size:.82rem;line-height:1.5'>"
            f"<div style='color:#e6edf7;font-weight:700;margin-bottom:2px'>{html.escape(p['title'])}</div>"
            + row("What it shows.", p["what"]) + row("Why you are seeing it.", p["why"]) + row("How to read it.", p["read"])
            + f"<div style='margin:2px 0'><span style='color:#fbbf24;font-weight:700'>Be careful.</span> <span style='color:#b7c9db'>{html.escape(p['care'])}</span></div></div>")


def plot_note(key: str) -> None:
    """Draw the explanation above a plot."""
    import streamlit as st
    h = note_html(key)
    if h:
        st.markdown(h, unsafe_allow_html=True)
