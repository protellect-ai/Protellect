"""Hypothesis engine: experiment table -> orphan GPCRs -> ranked, explained hypotheses.

Principles baked into the code:
  * Hypotheses, never answers. Every card says a wet-lab experiment is what confirms it.
  * Abstain instead of guessing. If no precedent shares any evidence with the receptor, no
    hypothesis is produced.
  * `support` is a RELATIVE ranking inside one receptor's candidates, not a probability of being
    correct. Real hit rates come from benchmark.py.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from . import registry as reg
from .cases import all_verified, load_cases, usable
from .critic import class_precision, critique, load_refuted, penalty, verdict_from
from .ranker import PrecedentRanker, FEATURES
from .schema import Case, Hypothesis, QueryProfile, ReceptorResult

DATA_DIR = pathlib.Path(__file__).parent / "data"

TEST_EXPERIMENTS = {
    "fatty acid": "Express the receptor in a reporter cell line (empty-vector control alongside) and screen a free fatty acid panel "
                  "(short, medium, long chain; saturated and unsaturated) using a Ca2+ mobilization or cAMP assay.",
    "lipid mediator": "Screen lipid-mediator candidates (for example lysophospholipids and N-acyl amides) in receptor-expressing cells "
                      "with empty-vector controls, using cAMP or beta-arrestin readouts.",
    "organic acid": "Screen a panel of carboxylic-acid metabolites (for example lactate, succinate, ketone bodies, TCA-cycle intermediates) "
                    "in receptor-expressing cells with empty-vector controls, using Ca2+, cAMP or beta-arrestin readouts.",
    "peptide": "Reverse pharmacology: test fractionated extracts from the tissue where the receptor is expressed, plus candidate peptide "
               "libraries, against receptor-expressing cells; then purify and identify the active peptide.",
    "nucleotide": "Screen nucleotides, nucleoside diphosphates and nucleotide sugars (ATP, ADP, UTP, UDP, UDP-glucose) and their breakdown products in receptor-expressing cells "
                  "with empty-vector controls. Treat the medium with apyrase first, because contaminating nucleotides are a common false positive.",
    "ion / proton": "Vary extracellular pH in small steps (for example 6.4 to 7.8) and test divalent ions (zinc, calcium) in receptor-expressing cells and empty-vector cells in "
                    "a well-buffered system; endogenous proton-sensing receptors in the host cells are the main confound.",
    "amine": "Screen biogenic amines and trace amines (for example histamine, tyramine, beta-phenylethylamine, tryptamine) in receptor-expressing cells with "
             "empty-vector controls, using cAMP or calcium readouts.",
}
COUPLING_TEST = ("After stimulating with a candidate ligand (or using a constitutive-activity or BRET G-protein sensor assay), measure "
                 "Ca2+ for Gq, cAMP decrease for Gi, or cAMP increase for Gs.")
DRUGGABILITY = {
    "peptide": "Peptide-binding class. Small-molecule versus antibody tractability depends on the binding pocket, which this engine does not assess.",
    "default": "Precedent receptors in this class have been small-molecule accessible. This is an estimate from the class only, not from this receptor's structure.",
}
EVIDENCE_TYPE = {
    "expression": "somatic / expression association (germline evidence not assessed)",
    "variant": "genetic association (confirm germline vs somatic from the cohort design)",
    "screen": "functional perturbation (neither an inherited variant nor an expression association)",
    "lookup": "none: no experiment was supplied, this is a lookup by gene name",
}
DIAGNOSTIC = {
    "expression": "Weak: continuous fold-change only. A clean binary signal or an independent cohort would be needed before biomarker use.",
    "variant": "Possible, but requires validation in an independent cohort.",
    "screen": "Not assessed: a perturbation screen does not by itself indicate biomarker potential.",
    "lookup": "Not assessed: no experiment was supplied.",
}


@dataclass
class RunSummary:
    n_input_genes: int
    n_gpcr: int
    n_orphan: int
    results: List[ReceptorResult] = field(default_factory=list)
    characterized: List[str] = field(default_factory=list)


class HypothesisEngine:
    def __init__(self, cases: Optional[List[Case]] = None, registry: Optional[dict] = None,
                 annotations: Optional[dict] = None, use_live_annotations: bool = True):
        self.cases = cases if cases is not None else load_cases()
        self.library = usable(self.cases)
        self.registry = registry if registry is not None else reg.load_registry()
        self.annotations = annotations if annotations is not None else reg.load_annotations()
        self.use_live_annotations = use_live_annotations
        self.ligand_ranker = PrecedentRanker().fit(self.library, "ligand_class")
        self.coupling_ranker = PrecedentRanker().fit(self.library, "coupling")
        self.library_verified = all_verified(self.cases)
        self.refuted = load_refuted()
        self.precision = class_precision(self.library, "ligand_class")
        self.benchmark = self._load_benchmark()

    # ---------------------------------------------------------------- helpers
    def _load_benchmark(self) -> Optional[dict]:
        """Leave-one-out result on the current case library, computed live so it can never be stale or contradict the data."""
        from .benchmark import evaluate
        try:
            return evaluate(self.cases, "loo")
        except Exception:
            return None

    def calibration_note(self) -> str:
        b = self.benchmark
        if not b:
            return "No benchmark has been run yet, so there is no measured hit rate for these rankings."
        tag = "" if b.get("data_verified") else " (case data NOT expert-verified: illustrative only)"
        return (f"Leave-one-out benchmark on {b['n_evaluable']} historical cases: top-1 ligand-class hit "
                f"{b['top1_hits']}/{b['n_evaluable']} vs {b['random_expected_hits']} expected from random guessing{tag}.")

    def profile_for(self, gene: str, context: dict, extra: Optional[dict] = None) -> (QueryProfile, List[str]):
        notes: List[str] = []
        ann = self.annotations.get(gene)
        if ann is None and self.use_live_annotations:
            ann = reg.fetch_live_annotation(gene)
        tissues, sources = [], {}
        if ann:
            for t in ann["tissues"]:
                tissues.append(t); sources[t] = f"annotation ({ann.get('source', '')})"
        if extra:                                    # e.g. UniProt tissue data the main app already fetched
            for t in extra.get("tissues", []):
                if t not in tissues:
                    tissues.append(t)
                sources.setdefault(t, extra.get("source", "supplied annotation"))
        if not ann and not extra:
            notes.append("No receptor annotation (tissues, cluster, neighbors) available; hypotheses rest on your experiment context only.")
        own = bool(extra and extra.get("authoritative"))
        if own:
            notes.append("Tissue context comes from where THIS receptor is most expressed in your matrix (" + str(extra.get("source", "")) + "), not from the experiment-wide setting."
                         + ("" if tissues else " That context maps to no tissue in the precedent library, so no precedent can be matched."))
        else:
            for t in reg.normalize_tissues([context.get("tissue"), context.get("disease")]):
                if t not in tissues:
                    tissues.append(t)
                sources.setdefault(t, "your experiment context")
        prof = QueryProfile(id=gene, names=[gene], tissues=tissues,
                            neighbors=(ann or {}).get("neighbors", []), cluster=(ann or {}).get("cluster", ""),
                            tissue_sources=sources)
        if not prof.neighbors and not prof.cluster:
            notes.append("Matches rest on tissue overlap alone (no family-cluster or neighbor annotation), so receptors in the same "
                         "tissue context will receive similar hypotheses.")
        return prof, notes

    @staticmethod
    def _explain(feats: Dict[str, float], case: Case, profile: QueryProfile) -> str:
        bits = []
        shared = sorted(set(profile.tissues) & set(case.tissues))
        if shared:
            bits.append("shares tissue context (" + ", ".join(shared) + ")")
        if feats.get("neighbor_link"):
            bits.append("sits among related receptors")
        if feats.get("same_cluster"):
            bits.append(f"same family cluster ({case.cluster})")
        return f"{case.id}: " + "; ".join(bits)

    def _caveats(self, extra: List[str]) -> List[str]:
        c = ["Hypothesis, not a finding: only a wet-lab experiment can confirm what this receptor does.",
             "Structural (binding-pocket) similarity is not part of this version; matches use tissue, family cluster and neighbors only."]
        if not self.library_verified:
            c.append("The historical case library has NOT been expert-verified yet; treat all rankings as illustrative.")
        return c + extra

    # ------------------------------------------------------------- generation
    def _make(self, category: str, ranker: PrecedentRanker, profile: QueryProfile, row, extra_notes: List[str],
              top_n: int) -> List[Hypothesis]:
        scores = ranker.value_scores(profile, self.library)
        if not scores:
            return []
        scored = ranker.scored_precedents(profile, self.library)
        out = []
        for value, support in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_n]:
            supporting = [d for d in scored if getattr(d["case"], ranker.target) == value][:3]
            precedents = [{"case": d["case"].id, "gene": d["case"].gene, "similarity": round(d["score"], 3),
                           "ligand": d["case"].ligand, "later_outcome": d["case"].later_outcome} for d in supporting]
            if category == "ligand-class":
                statement = f"Likely activated by a {value}-class ligand"
                test = TEST_EXPERIMENTS[value]
                flags = {"diagnostic_potential": DIAGNOSTIC[row.shape],
                         "druggability": DRUGGABILITY["peptide" if value == "peptide" else "default"]}
            else:
                statement = f"Likely couples to {value} signaling"
                test = COUPLING_TEST
                flags = {"diagnostic_potential": DIAGNOSTIC[row.shape], "druggability": "Not assessed for signaling hypotheses."}
            cited = sorted({c for d in supporting for c in d["case"].citations})
            axes = {
                "evidence_type": EVIDENCE_TYPE[row.shape],
                "method_class": f"computational analogy to precedent receptors (your data type: {row.shape})",
                "replication_depth": f"This receptor: one experiment (yours), unreplicated. Precedents cite {len(cited)} reports (unverified).",
                "signal_character": row.signal_character,
            }
            tie = [f"Near tie with another candidate (top supports within 0.05): do not over-read the order."]\
                if (len(scores) > 1 and sorted(scores.values(), reverse=True)[0] - sorted(scores.values(), reverse=True)[1] < 0.05
                    and support >= sorted(scores.values(), reverse=True)[1]) else []
            counters = critique(category=category, value=value, gene=profile.id, profile=profile, library=self.library,
                                ranker=ranker, scores=scores, supporting=supporting, row=row, refuted=self.refuted,
                                precision=self.precision)
            out.append(Hypothesis(
                category=category, statement=statement, value=value,
                support=round(float(support), 3), precedent_strength=round(float(supporting[0]["score"]), 3),
                rationale=[self._explain(d["features"], d["case"], profile) for d in supporting],
                precedents=precedents, evidence_axes=axes, test_experiment=test, flags=flags,
                caveats=self._caveats(extra_notes + tie), counterarguments=counters, verdict=verdict_from(counters),
                adjusted_support=round(float(support) * penalty(counters), 3)))
        return out

    def _disease_hypothesis(self, profile: QueryProfile, row, context: dict, extra_notes: List[str]) -> List[Hypothesis]:
        ctx_t = reg.normalize_tissues([context.get("tissue"), context.get("disease")])
        label = context.get("disease") or context.get("tissue")
        if not ctx_t or not label:
            return []
        for d in self.ligand_ranker.scored_precedents(profile, self.library):
            c = d["case"]
            if set(ctx_t) & set(c.tissues):
                counters = critique(category="disease-association", value=c.id, gene=profile.id, profile=profile,
                                    library=self.library, ranker=self.ligand_ranker, scores={}, supporting=[d], row=row,
                                    refuted=self.refuted, precision=self.precision)
                return [Hypothesis(
                    category="disease-association",
                    statement=f"May play a role in {label} biology, by analogy to {c.gene} ({c.later_outcome})",
                    value=c.id, support=round(d["score"], 3), precedent_strength=round(d["score"], 3),
                    rationale=[self._explain(d["features"], c, profile)],
                    precedents=[{"case": c.id, "gene": c.gene, "similarity": round(d["score"], 3),
                                 "ligand": c.ligand, "later_outcome": c.later_outcome}],
                    evidence_axes={"evidence_type": EVIDENCE_TYPE[row.shape],
                                   "method_class": "computational analogy only (weakest category)",
                                   "replication_depth": "Single analogy; no independent support",
                                   "signal_character": row.signal_character},
                    test_experiment=f"Perturb the receptor (knockdown or knockout) in a {label}-relevant model and test whether the disease-relevant phenotype changes.",
                    flags={"diagnostic_potential": DIAGNOSTIC[row.shape], "druggability": "Not assessed."},
                    caveats=self._caveats(extra_notes), counterarguments=counters, verdict=verdict_from(counters),
                    adjusted_support=round(d["score"] * penalty(counters), 3))]
        return []

    def run(self, parsed: pd.DataFrame, context: Optional[dict] = None, top_n: int = 3,
            extra_annotations: Optional[dict] = None) -> RunSummary:
        context = context or {}
        summary = RunSummary(n_input_genes=len(parsed), n_gpcr=0, n_orphan=0)
        for row in parsed.itertuples():
            info = self.registry.get(row.gene)
            if info is None:
                continue
            summary.n_gpcr += 1
            if info["status"] != "orphan":
                summary.characterized.append(row.gene)
                continue
            summary.n_orphan += 1
            profile, notes = self.profile_for(row.gene, context, (extra_annotations or {}).get(row.gene))
            # a receptor must never be scored against its own documented answer: hide its case while scoring it
            g = str(row.gene).upper()
            own = [c for c in self.library if c.gene.upper() == g or c.id.upper() == g]
            saved = (self.library, self.ligand_ranker, self.coupling_ranker)
            if own:
                self.library = [c for c in self.library if c not in own]
                self.ligand_ranker = PrecedentRanker().fit(self.library, "ligand_class")
                self.coupling_ranker = PrecedentRanker().fit(self.library, "coupling")
                notes.append(f"{row.gene} has its own documented case in the library ({', '.join(c.id for c in own)}); that case was hidden while scoring it.")
            try:
                hyps = (self._make("ligand-class", self.ligand_ranker, profile, row, notes, top_n)
                        + self._make("signaling", self.coupling_ranker, profile, row, notes, 1)
                        + self._disease_hypothesis(profile, row, context, notes))
            finally:
                self.library, self.ligand_ranker, self.coupling_ranker = saved
            sig = None if pd.isna(row.significance) else float(row.significance)
            if hyps:
                summary.results.append(ReceptorResult(row.gene, "hypotheses", float(row.effect), row.effect_type, sig, hyps,
                                                      message="; ".join(notes)))
            else:
                summary.results.append(ReceptorResult(
                    row.gene, "insufficient_evidence", float(row.effect), row.effect_type, sig, [],
                    message="No precedent shares tissue, family cluster or neighbors with this receptor, so no hypothesis is generated. "
                            "Add it to receptor_annotations.csv or set the tissue in your experiment context."))
        return summary
