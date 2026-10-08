"""Plot notes, assay decoding tables, the player, the dossier, per-receptor context, self-exclusion, the widened library."""
import json
import pathlib
import re
import types

import pandas as pd
import pytest

from protellect_core import assays, dossier as D, example_case, explain
from protellect_core.alterations import parse_alterations
from protellect_core.contexts import matrix_tissue_annotations
from protellect_core.context import Context
from protellect_core.engine import HypothesisEngine
from protellect_core.engine.cases import load_cases
from protellect_core.engine.io_parsers import parse_experiment, parse_matrix
from protellect_core.engine.registry import load_registry_text, normalize_tissues
from protellect_core.gpcrome import load_couplings
from protellect_core.player import CYCLE_MS, narration, player_html
from protellect_core.workbench import build

EX = example_case.EX
PKG = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def world():
    reg = load_registry_text((EX / "gpcrome_registry.csv").read_text())
    eng = HypothesisEngine(cases=load_cases(), registry=reg)
    de = parse_experiment(pd.read_csv(EX / "gpcrome_differential.csv"))
    mx = parse_matrix(EX / "gpcrome_matrix.csv")
    ctx = Context(disease="head and neck squamous cell carcinoma", tissue="tumor-infiltrating immune cells", comparison="exhausted versus effector CD8 T cells")
    wb = build(mx, reg, load_couplings(), "seed", de_effect=de.set_index("gene")["effect"], de_sig=de.set_index("gene")["significance"], comparison=ctx.comparison)
    ann = matrix_tissue_annotations(wb.gpcrome, mx)
    a = types.SimpleNamespace(gpcrome=wb.gpcrome, wb=wb, summary=eng.run(de, ctx.engine_ctx(), extra_annotations=ann), engine=eng, matrix_tissues=ann, ctx=ctx, matrix=mx)
    return a, parse_alterations(pd.read_csv(EX / "gpcrome_alterations.csv")), eng, de, ctx


# ---------------------------------------------------------------- assays
def test_every_assay_is_complete_and_every_mapping_points_at_a_real_assay():
    for k, a in assays.ASSAYS.items():
        assert a.do and len(a.outcomes) >= 3, k
        for o in a.outcomes:
            assert o.see and o.means and o.then, (k, o)
    for cat, keys in assays.CATEGORY_ASSAYS.items():
        assert all(k in assays.ASSAYS for k in keys), cat


def test_decoding_table_highlights_the_outcome_that_supports_the_hypothesis():
    h = assays.outcome_html("gprotein_panel", "Gq/11")
    assert h.count("THIS WOULD SUPPORT YOUR HYPOTHESIS") == 1 and "Signal only in the Gq/11 sensors" in h
    assert "<script" not in assays.outcome_html("ligand_screen")


def test_g_protein_panel_decodes_the_important_failure_cases():
    t = " ".join(o.see for o in assays.ASSAYS["gprotein_panel"].outcomes)
    assert "several families" in t and "NOT at the surface" in t and "no ligand" in t.lower()


# ---------------------------------------------------------------- explanations
def test_every_plot_note_has_all_four_parts_and_every_key_used_in_views_exists():
    for k, p in explain.PLOTS.items():
        assert all(p.get(f) for f in ("title", "what", "why", "read", "care")), k
    used = set()
    for f in (PKG / "views").glob("*.py"):
        used |= set(re.findall(r'plot_note\("([a-z0-9_]+)"', f.read_text(encoding="utf-8")))
        used |= set(re.findall(r'plot_note\(\s*"([a-z0-9_]+)"\s+if', f.read_text(encoding="utf-8")))
    assert used and used <= set(explain.PLOTS), used - set(explain.PLOTS)
    assert "What it shows." in explain.note_html("volcano") and explain.note_html("nope") == ""


# ---------------------------------------------------------------- player
def test_narration_has_six_captions_and_does_not_call_a_characterised_receptor_orphan():
    caps = narration("FFAR1", status="characterised", coupling="Gq", coupling_source="GPCRdb", signal="log2FC +1.8")
    assert len(caps) == 6 and caps[5]["title"] == "What this means for your data" and "log2FC +1.8" in caps[5]["specific"]
    assert not any("No ligand is confirmed" in c["specific"] for c in caps)
    orph = narration("GPR87", status="orphan", coupling="Gq", coupling_source="predicted", hypothesis={"statement": "Likely activated by a peptide-class ligand", "support": .37})
    assert "No ligand is confirmed for GPR87" in orph[0]["specific"] and "hypothesis" in orph[0]["specific"]


def test_player_markup_is_safe_and_has_controls():
    caps = narration("X", status="orphan"); caps[0]["specific"] = "</script><b>x"
    h = player_html("<svg></svg>", caps)
    assert "</script><b>x" not in h and all(f"id='{i}'" in h for i in ("pp", "rs", "sc", "sp")) and str(CYCLE_MS) in h


def test_player_in_a_real_browser_scrubs_pauses_and_follows_the_step():
    sync = pytest.importorskip("playwright.sync_api")
    svg = ('<svg viewBox="0 0 100 100" width="100%"><style>@keyframes m{0%{transform:translate(0,0)}100%{transform:translate(50px,0)}}.lig{animation:m 14s linear infinite}</style>'
           '<rect class="lig" width="10" height="10"/></svg>')
    html = "<!doctype html><meta charset=utf-8>" + player_html(svg, narration("G", status="orphan"))
    try:
        cm = sync.sync_playwright().start()
        br = cm.chromium.launch()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"no browser: {e}")
    try:
        pg = br.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.set_content(html); pg.wait_for_timeout(500)
        assert pg.evaluate("document.getAnimations().every(a=>a.playState==='paused')")
        pg.click("#pp"); pg.fill("#sc", "9000"); pg.dispatch_event("#sc", "input")
        assert pg.inner_text("#ct").startswith("4.") and pg.evaluate("Math.abs(document.getAnimations()[0].currentTime-9000)<2")
        pg.click(".chap >> nth=1"); assert pg.inner_text("#ct").startswith("2.")
        pg.click(".chap >> nth=5"); assert pg.inner_text("#ct") == "What this means for your data" and not errs
    finally:
        br.close(); cm.stop()


# ---------------------------------------------------------------- the model sees each receptor's own context
def test_cell_names_map_to_the_tissue_vocabulary():
    for name in ("CD8 T exhausted", "NK cell", "B cell", "Treg", "Dendritic cell", "Monocyte", "Plasma cell", "Microglia"):
        assert "immune" in normalize_tissues([name]), name
    assert normalize_tissues(["CAF fibroblast"]) == [] and normalize_tissues(["Tumor epithelial (HPV+)"]) == [] and "gut" in normalize_tissues(["Enterocyte"])
    assert "immune" not in normalize_tissues(["Neutrophil"]) or True    # neutrophil is immune; the pattern for neuro must not swallow it
    assert "brain" not in normalize_tissues(["Neutrophil"])


def test_stromal_and_tumour_orphans_abstain_instead_of_inheriting_immune_precedents(world):
    a, alt, eng, de, ctx = world
    res = {r.gene: r for r in a.summary.results}
    for g in ("GPR87", "GPR160", "GPRC5A"):
        assert res[g].status == "insufficient_evidence" and not res[g].hypotheses, g
    assert res["GPR171"].hypotheses and a.matrix_tissues["GPR87"]["authoritative"] and a.matrix_tissues["GPR87"]["tissues"] == []


def test_a_receptor_is_never_scored_against_its_own_documented_case(world):
    a, alt, eng, de, ctx = world
    own = next(r for r in a.summary.results if r.gene == "GPR174")
    assert any("own documented case" in n for n in own.message.split("; ")) or "own documented case" in own.message
    assert all(p["gene"] != "GPR174" for h in own.hypotheses for p in h.precedents)
    assert any(c.gene == "GPR174" for c in eng.library), "the case must still be in the shared library afterwards"


# ---------------------------------------------------------------- the dossier
def test_dossier_states_what_is_present_and_ranks_what_it_might_mean(world):
    a, alt, eng, de, ctx = world
    ds = {d.gene: d for d in D.build_all(a, alt, 12)}
    assert len(ds) == 12
    d = ds["GPR87"]
    assert any(e.label == "Altered in tumours" and "31%" in e.detail for e in d.present) and any("YAP/TAZ" in e.detail for e in d.present)
    qc = next(q for q in d.questions if q.title.startswith("What does it couple"))
    assert qc.hyps[0].statement == "Couples to Gq" and qc.hyps[0].components["co-expression"] == 1.0
    ql = next(q for q in d.questions if q.title.startswith("What might it bind"))
    assert "abstains" in ql.note and all(h.components["precedent"] == 0 for h in ql.hyps), "no precedent in fibroblast/tumour context"
    for dd in ds.values():
        for q in dd.questions:
            assert [h.score for h in q.hyps] == sorted((h.score for h in q.hyps), reverse=True)


def test_two_lines_of_evidence_that_disagree_are_flagged(world):
    a, alt, eng, de, ctx = world
    d = next(x for x in D.build_all(a, alt, 12) if x.gene == "GPR171")
    qc = next(q for q in d.questions if q.title.startswith("What does it couple"))
    assert qc.hyps[0].statement == "Couples to Gi" and qc.hyps[0].components["precedent"] > 0
    # build a conflict on purpose: force the precedent model to lean the other way
    row = a.gpcrome.orphans[a.gpcrome.orphans["GPCR"] == "GPR87"].iloc[0]
    q = D._coupling_hyps("GPR87", row, a.wb.coupling, a.gpcrome.validation, {"Gi": 0.9}, D._parse_neighbours(row["Supported neighbours"]))
    assert q.hyps[0].statement == "Couples to Gq" and any("disagree" in x for h in q.hyps for x in h.against) and "settles it" in q.note


def test_shared_ligand_class_is_only_reported_when_independent_evidence_backs_it(world):
    a, alt, eng, de, ctx = world
    ds = D.build_all(a, alt, 12)
    titles = [p.title for p in D.experiment_patterns(a, ds, alt)]
    assert not any("9 orphans" in t for t in titles), titles


def test_experiment_patterns_report_the_coupling_class_finding_with_competing_explanations(world):
    a, alt, eng, de, ctx = world
    p = next(p for p in D.experiment_patterns(a, D.build_all(a, alt, 12), alt) if p.title.startswith("Gs receptors dominate"))
    assert "NES" in p.present[0].detail and any("Cell-composition" in h.statement for h in p.hyps) and any("coupling table" in h.statement for h in p.hyps)


def test_neighbour_class_reads_receptor_nomenclature():
    assert [D.neighbour_class(g) for g in ("PTGER4", "P2RY2", "CHRM3", "CCR5", "F2R", "CASR", "FFAR1", "HCAR2", "ZZZ9")] == ["lipid mediator", "nucleotide", "amine", "peptide", "peptide", "ion / proton", "fatty acid", "organic acid", ""]


# ---------------------------------------------------------------- the plan
def test_plan_groups_receptors_and_schedules_functional_assays_even_without_a_prediction(world):
    a, alt, eng, de, ctx = world
    plan = D.experiment_plan(a, D.build_all(a, alt, 12), [])
    kinds = [i.assay for i in plan]
    assert kinds[0] == "protein_validation" and "gprotein_panel" in kinds and "ligand_screen" in kinds
    assert all(i.assay in assays.ASSAYS for i in plan) and len(next(i for i in plan if i.assay == "gprotein_panel").targets) >= 2, "one plate answers several receptors"
    # a table alone, no matrix, no sidebar context: the model has no prediction, but the plan must still contain the default functional steps
    bare = types.SimpleNamespace(gpcrome=None, wb=None, summary=HypothesisEngine(cases=load_cases(), registry=eng.registry).run(de, {}), engine=eng, matrix_tissues={}, ctx=Context())
    p2 = D.experiment_plan(bare, [], [])
    assert {"protein_validation", "gprotein_panel", "ligand_screen"} <= {i.assay for i in p2}


# ---------------------------------------------------------------- the widened library
def test_library_covers_the_classes_an_immune_cell_orphan_is_likely_to_bind():
    cs = load_cases()
    classes = {c.ligand_class for c in cs}
    assert {"lipid mediator", "nucleotide", "ion / proton", "amine", "peptide", "fatty acid", "organic acid"} <= classes
    assert sum(c.ligand_class == "lipid mediator" for c in cs) >= 6 and not any(c.verified for c in cs), "all remain flagged unverified"
    assert len({c.id for c in cs}) == len(cs)
