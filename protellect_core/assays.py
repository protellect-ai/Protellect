"""How to read each experiment: what you might observe, what it suggests, and what to do next.

These are standard assay-interpretation rules, not findings about any particular receptor. They are shown as rules (the app never presents them as
a result about your protein) and only cite a source where one is known with confidence. Every outcome has the same three parts:
    see   : what you observe
    means : what it suggests (and what it does NOT prove)
    then  : the next step
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Outcome:
    see: str
    means: str
    then: str


@dataclass(frozen=True)
class Assay:
    key: str
    name: str
    question: str
    do: Tuple[str, ...]
    outcomes: Tuple[Outcome, ...]
    pitfalls: Tuple[str, ...] = ()
    refs: Tuple[str, ...] = ()


ASSAYS: Dict[str, Assay] = {a.key: a for a in [
    Assay(
        "gprotein_panel", "G-protein coupling profile",
        "Which G-protein family does this receptor engage?",
        ("Express the receptor (with an N-terminal epitope tag) in HEK293 cells together with a panel of G-protein activity sensors, for example the BRET-based TRUPATH set or TGF-alpha shedding with chimeric G proteins.",
         "Measure basal activity against an empty-vector control; add a candidate ligand if you have one.",
         "Read each G-protein family separately, on the same plate as a receptor of known coupling.",
         "Run the surface-expression check alongside, so a flat result can be interpreted."),
        (Outcome("Signal only in the Gq/11 sensors", "Supports Gq/11 coupling (what the co-expression prediction would call).", "Confirm with a calcium or IP1 readout and block it with the Gq/11 inhibitor YM-254890."),
         Outcome("Signal only in the Gi/o sensors", "Supports Gi/o coupling.", "Confirm that cAMP falls after forskolin and that pertussis toxin removes the effect."),
         Outcome("Signal only in the Gs sensor", "Supports Gs coupling.", "Confirm a cAMP rise; check it is absent in empty-vector cells."),
         Outcome("Signal in several families", "Either genuine promiscuity or an over-expression artefact; the panel alone cannot tell which.", "Repeat at lower expression (titrate the DNA). Coupling that persists at low expression is more believable."),
         Outcome("Signal above empty vector with no ligand added", "Constitutive (ligand-independent) activity, which is common among orphans and is itself a finding.", "Show it scales with expression, then look for an inverse agonist."),
         Outcome("No signal, and the receptor IS at the surface", "Likely needs its ligand, or couples to a transducer not in the panel (G12/13, arrestin only), or needs an accessory protein.", "Run a ligand screen and an arrestin-recruitment readout."),
         Outcome("No signal, and the receptor is NOT at the surface", "A trafficking problem, not evidence about signalling. Treat as inconclusive.", "Try an N-terminal export-signal tag, a different cell line, or a lower growth temperature.")),
        ("Over-expression can make a receptor couple to G proteins it does not use in its own cells.", "Sensor baselines differ between families; compare each to its own empty-vector control."),
        ("Inoue et al., Cell 2019 (G-protein coupling selectivity of GPCRs)", "Olsen et al., Nat Chem Biol 2020 (TRUPATH)")),
    Assay(
        "second_messenger", "Second-messenger readout (cAMP, calcium, IP1, RhoA)",
        "Does the receptor change the signal that its predicted G-protein family controls?",
        ("cAMP: measure basal and forskolin-stimulated cAMP (a rise suggests Gs; a fall from the forskolin level suggests Gi/o).",
         "Calcium or IP1: measure the transient or accumulated response (suggests Gq/11).",
         "RhoA or SRF-response-element reporter: suggests G12/13.",
         "Always include empty-vector cells and a known control receptor."),
        (Outcome("cAMP rises", "Consistent with Gs.", "Check the rise disappears in empty-vector cells and with a PKA-independent control."),
         Outcome("Forskolin-stimulated cAMP falls", "Consistent with Gi/o.", "Pertussis toxin pre-treatment should abolish it; if not, the effect is not Gi/o."),
         Outcome("Calcium transient or IP1 accumulation", "Consistent with Gq/11.", "YM-254890 should abolish it; if not, suspect an endogenous receptor or a Gq-independent route."),
         Outcome("The same response in empty-vector cells", "The host cells have an endogenous receptor for what you added; the result says nothing about your receptor.", "Use a knockout of the endogenous receptor or a different host cell line."),
         Outcome("No response to any ligand but basal activity is raised", "Constitutive activity.", "Titrate expression and test for an inverse agonist.")),
        ("A calcium response can be produced by many routes; do not call it Gq without a blocker.",)),
    Assay(
        "antagonist_pathway", "Pathway blockers to confirm the transducer",
        "Is the G-protein family you inferred really the one carrying the signal?",
        ("Repeat the signalling readout after pretreating with a family-selective blocker: pertussis toxin (Gi/o), YM-254890 (Gq/11).",
         "For Gs and G12/13, use dominant-negative constructs or knockout lines for the G alpha subunit.",
         "Compare receptor-expressing and empty-vector cells at each condition."),
        (Outcome("Response abolished by the blocker", "That family carries the signal.", "Report it as coupling to that family, tested with a selective inhibitor."),
         Outcome("Response partly reduced", "Mixed coupling or a second pathway.", "Test the other families' blockers, alone and together."),
         Outcome("Response unchanged by every blocker", "The response is not carried by the family you assumed, or arises from an endogenous receptor or arrestin.", "Run an arrestin-recruitment readout and the empty-vector control.")),
        (), ("Takasaki et al., J Biol Chem 2004 (YM-254890)",)),
    Assay(
        "surface_expression", "Surface expression check",
        "Is the receptor actually at the cell surface, so that a flat functional result means something?",
        ("Express an N-terminally tagged receptor; label intact, non-permeabilised cells with an antibody to the tag.",
         "Read by flow cytometry or a plate-based immunoassay against an empty-vector background.",
         "Compare wild-type with any variant on the same day."),
        (Outcome("Clear surface signal above empty vector", "A negative functional result is informative: the receptor was there and did not signal under the conditions tested.", "Test other ligands, readouts or cell types before concluding anything."),
         Outcome("Little or no surface signal (intracellular only)", "A trafficking or folding problem. A negative functional result is not informative.", "Try an export-signal tag, a chaperone, a lower temperature, or another cell line."),
         Outcome("A variant has much less surface signal than wild type", "A folding or trafficking defect, the commonest mechanism for loss of function in GPCR missense variants.", "Test whether a pharmacological chaperone or lower temperature restores it."),
         Outcome("A variant matches wild type at the surface but signals less", "A signalling defect rather than a trafficking defect.", "Map it onto the G-protein interface or ligand pocket (topology map).")),
        ()),
    Assay(
        "constitutive_activity", "Constitutive (ligand-independent) activity",
        "Does the receptor signal without any ligand?",
        ("Transfect increasing amounts of receptor DNA with a constant amount of the readout reporter.",
         "Plot basal signal against measured surface expression.",
         "Add a candidate inverse agonist if one exists."),
        (Outcome("Basal signal rises with expression and is absent in empty vector", "Constitutive activity: a real property of many orphans, and it means a ligand may not be needed for a signal.", "Identify the G-protein family it drives, then look for inverse agonists."),
         Outcome("Basal signal stays flat as expression rises", "Activity needs a ligand (or the readout is saturated).", "Run a ligand screen; check the readout is not saturated at low expression."),
         Outcome("An inverse agonist lowers the basal signal", "Confirms the signal comes from the receptor itself.", "Use it as a tool compound and a starting point for pharmacology.")),
        ()),
    Assay(
        "ligand_screen", "Ligand screen with a universal readout",
        "Which class of molecule activates the receptor?",
        ("Express the receptor in a reporter line with a universal readout (for example arrestin recruitment such as PRESTO-Tango, or the G-protein sensors above).",
         "Screen focused libraries chosen by the ranked hypothesis (lipid mediators, nucleotides and nucleosides, metabolites, peptides), not everything at once.",
         "Always run empty-vector cells in parallel; run dose-response on every hit.",
         "Also test conditioned medium from the context where the receptor is highest in your data."),
        (Outcome("A compound activates receptor cells in a dose-response and not empty cells", "A candidate ligand. A lead, not yet a deorphanisation.", "Confirm with a second readout, structural analogues, an antagonist, and the native cell type."),
         Outcome("The same compound also activates empty cells", "It acts on an endogenous receptor of the host cells; for your receptor this is an artefact.", "Switch host cells or knock out the endogenous receptor, then retest."),
         Outcome("Many unrelated compounds hit", "Non-specific signal or over-expression artefact.", "Lower expression and add a counter-screen."),
         Outcome("No hit in the class you chose", "The class hypothesis is weakened, not refuted: the ligand may lie in another class or need a cofactor or processing.", "Move to the next-ranked class, or fractionate conditioned medium."),
         Outcome("Activity only in conditioned medium from one context", "An endogenous ligand is made by that context.", "Fractionate the medium and identify the active component by mass spectrometry.")),
        ("A hit in a screen is a lead. Deorphanisation needs independent confirmation in a second assay and in a native setting.",),
        ("Kroeze et al., Nat Struct Mol Biol 2015 (PRESTO-Tango)",)),
    Assay(
        "binding_validation", "Binding validation",
        "Does the candidate ligand physically bind the receptor?",
        ("Use a radioligand or NanoBRET-type binding assay in membranes or cells expressing the receptor.",
         "Show specific binding is displaced by unlabelled ligand and is absent in empty-vector membranes."),
        (Outcome("Specific, displaceable binding", "A direct interaction.", "Measure affinity and compare it with the functional potency."),
         Outcome("Functional response but no detectable binding", "Possibly allosteric or indirect, or binding is below the assay sensitivity.", "Try a different tracer or assay format before concluding."),
         Outcome("Binding in empty-vector membranes too", "Non-specific binding.", "Increase washes or change the tracer; use a structurally distinct ligand.")),
        ()),
    Assay(
        "knockdown_function", "Loss of function in the cell state",
        "Does removing the receptor change the cell state it is associated with?",
        ("Knock out or knock down the receptor in the relevant cells (for example in vitro-exhausted CD8 T cells) with at least two independent guides plus a non-targeting control.",
         "Read the state markers that define your contrast (for example PD-1, TIM-3, TOX) and function (cytokines such as IFN-gamma, killing).",
         "Confirm the knockdown at protein level, not only RNA."),
        (Outcome("Loss improves function or reduces exhaustion markers", "The receptor contributes to the dysfunction; a candidate target to antagonise.", "Test a receptor antagonist or an inverse agonist if one exists; look for the ligand."),
         Outcome("Loss worsens function", "The receptor supports function; agonism, not blockade, may be what is needed.", "Look for an agonist; check the effect in vivo."),
         Outcome("No change", "Not required in this model, or a related receptor compensates, or the RNA does not become protein.", "Check protein, then knock out the closest paralog as well."),
         Outcome("An effect with one guide only", "Probably off-target.", "Use a second guide and a rescue construct.")),
        ("Cell-state markers shift in culture for many reasons; compare to non-targeting guides run in the same experiment.",)),
    Assay(
        "conditioned_medium", "Conditioned-medium transfer",
        "Is the ligand made by a different cell type than the one carrying the receptor?",
        ("Collect medium from the cells your data predict produce the ligand (the producer context).",
         "Put it on receptor-bearing cells, with and without inhibiting the producing enzyme in the donor cells (or adding a ligand-degrading enzyme to the medium).",
         "Read the receptor's signalling readout; include empty-vector receiver cells."),
        (Outcome("The response transfers and is lost when the producing enzyme is inhibited", "The ligand is made by that enzyme in the producer cells.", "Identify the molecule by mass spectrometry and test it directly."),
         Outcome("The response transfers but is not lost with the inhibitor", "The active molecule is not the one you assumed, or another source makes it.", "Fractionate the medium and test the fractions."),
         Outcome("No response", "The ligand may be unstable, not secreted, or needs cell-cell contact.", "Try co-culture, or test medium collected under the same stress as the tumour (for example hypoxia).")),
        ("RNA for a synthesising enzyme is an indirect proxy for the ligand being present.",)),
    Assay(
        "ligand_presence", "Measure the candidate ligand",
        "Is the candidate ligand present, and at a concentration the receptor could respond to?",
        ("Measure the molecule by mass spectrometry or immunoassay in tumour interstitial fluid or conditioned medium from the relevant cells.",
         "Compare the measured concentration with the receptor's EC50 for that molecule from your dose-response."),
        (Outcome("Present at or above the receptor's EC50", "A physiologically plausible ligand in that context.", "Test whether removing the source or the ligand changes the phenotype."),
         Outcome("Present but far below the EC50", "Unlikely to activate the receptor at that site unless it is concentrated locally.", "Measure at the cell surface or in a micro-environment sample."),
         Outcome("Not detected", "Absent, unstable, or below the detection limit.", "Use a more sensitive method or stabilise the sample.")),
        ()),
    Assay(
        "protein_validation", "Confirm the receptor protein in the context",
        "Is the receptor protein found where your RNA data say it is?",
        ("Use flow cytometry, immunohistochemistry or RNAscope on the context where the RNA is highest, and on one where it is low.",
         "Validate the antibody against knockout or over-expressing cells; GPCR antibodies are notoriously unreliable."),
        (Outcome("Protein found in the same context, not in the low context", "Supports the RNA finding.", "Go ahead with the functional tests in that cell type."),
         Outcome("RNA high, no protein detected", "Post-transcriptional regulation, a poor antibody, or RNA with no protein.", "Treat every hypothesis built on that RNA signal with caution until protein is shown."),
         Outcome("Protein in many contexts, not only the predicted one", "Less specific than the RNA suggested.", "Revisit the specificity claim.")),
        ("GPCR antibodies often give signal in knockout cells; use a knockout control.",)),
    Assay(
        "program_test", "Is the receptor upstream or downstream of the program it tracks?",
        "Co-variation across contexts does not say which way the arrow points, or whether there is one. Which is it?",
        ("Inhibit or stimulate the program (for example a YAP/TEAD inhibitor, or a stimulus that activates it) and measure the receptor's RNA.",
         "In the other direction, knock down the receptor and measure the program's target genes.",
         "Do both in one purified cell type, not in a mixed population."),
        (Outcome("Blocking the program lowers receptor RNA", "The receptor is downstream, perhaps a target of the program.", "Check for program-factor binding at the receptor's promoter."),
         Outcome("Knocking down the receptor lowers program targets", "The receptor feeds the program.", "Test whether receptor activation is sufficient to switch it on."),
         Outcome("Neither changes in a single cell type", "The correlation came from cell-type composition: both are simply high in the same cell types.", "Drop this hypothesis, or look within a single cell type."),
         Outcome("Both change", "A feedback loop.", "Test time order with a time course.")),
        ("Across few contexts, shared cell identity is the usual reason two genes correlate.",)),
    Assay(
        "variant_function", "Functional test of a variant",
        "Does a ClinVar variant change the receptor's surface level or signalling?",
        ("Express wild type and variant at matched surface levels (check with the surface-expression assay).",
         "Measure the signalling readout for both, with the same ligand or basal condition.",
         "Include a known loss-of-function and a known benign variant as references."),
        (Outcome("Loss of signal with normal surface level", "A signalling defect: supports a pathogenic role.", "Map the residue onto the ligand pocket or G-protein interface."),
         Outcome("Loss of surface level", "A folding or trafficking defect, a frequent mechanism for GPCR missense variants.", "Test a pharmacological chaperone or lower growth temperature."),
         Outcome("Raised basal signal", "Constitutive activation.", "Test an inverse agonist."),
         Outcome("Same as wild type", "Not damaging in this assay; the assay may not capture the real defect.", "Test another readout; keep the ClinVar classification in mind.")),
        ("A functional assay in an over-expression system does not replace clinical classification.",),
        ("Richards et al., Genet Med 2015 (ACMG/AMP variant-classification guidelines)",)),
]}

# which assays follow from which kind of hypothesis, in the order they should be run
CATEGORY_ASSAYS: Dict[str, Tuple[str, ...]] = {
    "ligand-class": ("ligand_screen", "gprotein_panel", "binding_validation"),
    "ligand": ("ligand_screen", "gprotein_panel", "binding_validation"),
    "coupling": ("gprotein_panel", "second_messenger", "antagonist_pathway"),
    "signalling": ("gprotein_panel", "second_messenger", "antagonist_pathway"),
    "constitutive": ("constitutive_activity", "gprotein_panel"),
    "state": ("protein_validation", "knockdown_function"),
    "disease": ("protein_validation", "knockdown_function"),
    "program": ("program_test", "knockdown_function"),
    "axis": ("conditioned_medium", "ligand_presence"),
    "variant": ("surface_expression", "variant_function"),
    "specificity": ("protein_validation",),
}


def assays_for(category: str) -> List[str]:
    return list(CATEGORY_ASSAYS.get(str(category or "").lower(), ()))


def rows(key: str) -> List[Outcome]:
    return list(ASSAYS[key].outcomes) if key in ASSAYS else []


def outcome_html(key: str, expect: Optional[str] = None, max_rows: Optional[int] = None) -> str:
    """A compact 'if you see X, it suggests Y, then Z' table. `expect` highlights the row that would confirm the hypothesis being tested."""
    a = ASSAYS.get(key)
    if a is None:
        return ""
    e = (expect or "").lower().strip()
    body = []
    for o in (a.outcomes[:max_rows] if max_rows else a.outcomes):
        hit = bool(e) and e in o.see.lower()
        bg = "background:#0b2a1c;" if hit else ""
        tag = "<div style='color:#22c55e;font-size:.68rem;font-weight:700;letter-spacing:.05em'>THIS WOULD SUPPORT YOUR HYPOTHESIS</div>" if hit else ""
        body.append(f"<tr style='{bg}'><td style='padding:6px 8px;vertical-align:top;border-top:1px solid #16314d'>{tag}<b>{html.escape(o.see)}</b></td>"
                    f"<td style='padding:6px 8px;vertical-align:top;border-top:1px solid #16314d'>{html.escape(o.means)}</td>"
                    f"<td style='padding:6px 8px;vertical-align:top;border-top:1px solid #16314d;color:#9fb6cc'>{html.escape(o.then)}</td></tr>")
    return ("<div style='overflow-x:auto'><table style='width:100%;border-collapse:collapse;font-size:.82rem;color:#d7e3f1'>"
            "<tr style='color:#6b8aa3;text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em'><th style='padding:4px 8px'>If you see</th><th style='padding:4px 8px'>It suggests</th><th style='padding:4px 8px'>Then</th></tr>"
            + "".join(body) + "</table></div>")


def render_assay(st, key: str, expect: Optional[str] = None, label: Optional[str] = None) -> None:
    """Streamlit rendering: steps, the outcome table, and the pitfalls. Uses an expander, so do not call it from inside another expander."""
    a = ASSAYS.get(key)
    if a is None:
        return
    with st.expander(label or f"How to run it and how to read the result: {a.name}"):
        st.markdown(f"**Question it answers:** {a.question}")
        st.markdown("**What to do**")
        for i, s in enumerate(a.do, 1):
            st.markdown(f"{i}. {s}")
        st.markdown("**How to read the result**")
        st.markdown(outcome_html(key, expect), unsafe_allow_html=True)
        for p in a.pitfalls:
            st.caption("Watch out: " + p)
        if a.refs:
            st.caption("Sources: " + "; ".join(a.refs) + ". These outcome tables are interpretation rules for the assay, not findings about your receptor.")
        else:
            st.caption("These outcome tables are interpretation rules for the assay, not findings about your receptor.")


def render_assay_inline(st, key: str, expect: Optional[str] = None) -> None:
    """Same content as render_assay but without an expander, so it can be placed inside one (Streamlit does not allow nested expanders)."""
    a = ASSAYS.get(key)
    if a is None:
        return
    st.markdown(f"**Test it: {a.name}.** {a.question}")
    for i, step in enumerate(a.do, 1):
        st.markdown(f"{i}. {step}")
    st.markdown("**How to read the result**")
    st.markdown(outcome_html(key, expect), unsafe_allow_html=True)
    for pit in a.pitfalls:
        st.caption("Watch out: " + pit)
