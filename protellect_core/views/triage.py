"""Triage: AlphaFold structure + interaction network in one space, and a variant navigator that drives the structure."""
from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ..analysis import _same_condition, _systems_in, rank_variants, variant_plan
from ..explain import plot_note
from ..adapters import plddt_at
from ..evidence import Claim, Proof
from ..network import bars_svg, interaction_svg
from ..topology import motifs as tm_motifs, segment_stats, topology as tm_topology
from ..viz import architecture_svg, topology_svg
from ..viewer import structure_viewer_html
from ..motion import normal_modes
from .common import render_claims, svg
from .shell import Analysis

CLASSES = ["pathogenic", "likely pathogenic", "conflicting", "uncertain", "likely benign", "benign", "other"]


def _label(v) -> str:
    return f"{v.pos if v.pos else '?'} · {(v.name.split('(')[-1].rstrip(')') or v.name)[:34]} · {v.significance} · {v.stars}★"


@st.cache_data(show_spinner=False, max_entries=8)
def _modes_cached(pdb_text: str):
    try:
        return normal_modes(pdb_text)
    except Exception:
        return None


def _select(a: Analysis):
    b = a.b
    ranked = [v for v in rank_variants(b) if v.pos]
    if not ranked:
        st.info("No ClinVar variants with a position were retrieved, so there is nothing to place on the structure." if b.variants else "No ClinVar variants were retrieved for this protein.")
        return None
    c1, c2 = st.columns([3, 1])
    classes = c1.multiselect("Show variant classes", CLASSES, default=["pathogenic", "likely pathogenic", "uncertain"], key="tri_cls")
    stars = c2.slider("Minimum review stars", 0, 4, 0, key="tri_stars")
    pool = [v for v in ranked if v.significance in classes and v.stars >= stars][:400]
    if not pool:
        st.warning("No variants match these filters.")
        return None
    labels = [_label(v) for v in pool]
    if st.session_state.get("tri_variant_sel") not in labels:
        st.session_state.pop("tri_variant_sel", None)
    pick = st.selectbox(f"Variant ({len(pool)} ranked: pathogenic first, then review quality, ML and AlphaMissense score)", labels, key="tri_variant_sel")
    v = pool[labels.index(pick)]
    st.session_state["sel_variant_name"] = v.name
    return v


def _detail(a: Analysis, v) -> None:
    b = a.b
    pl = plddt_at(b.pdb, v.pos)
    dom = b.domain_at(v.pos)
    site = next((s for s in b.sites if v.pos and s["start"] <= v.pos <= s["end"]), None)
    st.markdown(f"##### Variant at residue {v.pos}")
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("ClinVar", v.significance.title()); f2.metric("Review", f"{v.stars} star(s)")
    f3.metric("AlphaMissense", "n/a" if v.am_score is None else f"{v.am_score:.2f}"); f4.metric("AlphaFold pLDDT", "n/a" if pl is None else f"{pl:.0f}")
    st.caption(f"{v.consequence} · " + (f"in {dom}" if dom else "no annotated domain here") + (f" · annotated {site['type'].lower()}: {site['desc']}" if site else "") + (f" · [ClinVar record]({v.url})" if v.url else ""))

    st.markdown("**Linked disease**")
    links = [d for d in a.diseases if v.condition and _same_condition(v.condition, d.tags.get("disease", d.text))]
    if not links and v.condition and v.condition.lower() not in ("not provided", "not specified"):
        links = [Claim(text=v.condition, proofs=[Proof("ClinVar", f"Condition listed on this variant record (review: {v.review or 'not recorded'})", v.url)], tags={"n_supporting": 1, "max_stars": v.stars, "domain": "clinvar"})]
    render_claims(links, b, "vdis", empty="No condition is listed for this variant.")

    st.markdown("**Tissue and body-system defects**")
    sys_from_var = set(_systems_in(v.condition))
    rel = [s for s in a.systems if s.tags["system"] in sys_from_var or s.tags.get("has_tissue")]
    render_claims(rel[:4], b, "vsys", empty="No tissue or organ-system link can be made from the records for this variant.")

    cands = b.am.get(v.pos or -1, {})
    if cands:
        st.markdown("**AlphaMissense score for every substitution at this residue**")
        plot_note("am_residue")
        svg(bars_svg([f"{k}" for k in sorted(cands)], [cands[k]["score"] for k in sorted(cands)], f"AlphaMissense score for each substitution at residue {v.pos}", "above 0.564 = likely pathogenic, below 0.34 = likely benign (Cheng 2023)", fmt="{:.2f}",
                     colors=["#ff2d55" if cands[k]["score"] > 0.564 else "#34d399" if cands[k]["score"] < 0.34 else "#fbbf24" for k in sorted(cands)]))
    with st.expander("How to work this variant, step by step", expanded=True):
        for i, s in enumerate(variant_plan(v, b), 1):
            st.markdown(f"**{i}. {s['step']}.** {s['do']}  \n_Why:_ {s['basis']}" + (f" [source]({s['url']})" if s["url"].startswith("http") else ""))


def render_triage(a: Analysis, helpers: dict) -> None:
    b = a.b
    ss = st.session_state
    if ss.get("csv_df") is not None and helpers.get("render_csv"):
        with st.expander(f"Your uploaded data: {ss.get('csv_filename', 'wet-lab triage')}", expanded=not b.loaded):
            try:
                helpers["render_csv"]()
            except Exception as e:
                st.warning(f"Could not analyse the uploaded file: {type(e).__name__}: {e}")
    if not b.loaded:
        st.info("Search a protein in the sidebar to see its structure, interactions and variants here.")
        return
    viewer_box = st.container()
    nav = st.container()
    with nav:
        st.markdown("#### Variant navigator")
        v = _select(a)
    with viewer_box:
        left, right = st.columns([3, 2])
        with left:
            st.markdown("#### AlphaFold structure" + (f" · residue {v.pos}" if v else ""))
            segs = tm_topology(b)
            amr = {p: max(d["score"] for d in dd.values()) for p, dd in b.am.items() if dd}
            bur = {}
            for x in b.variants:
                if x.pos:
                    bur[x.pos] = bur.get(x.pos, 0) + 1
            plot_note("structure3d")
            components.html(structure_viewer_html(b.pdb, b.variants, 520, v.pos if v else None, segs, amr, bur, _modes_cached(b.pdb)), height=526, scrolling=False)
        with right:
            st.markdown("#### Interactions")
            plot_note("network")
            svg(interaction_svg(b.gene, b.partners, registry=a.engine.registry))
            if b.partners:
                st.markdown(" · ".join(f"[{p.name}]({p.url}) {p.score:.2f}" if p.url.startswith("http") else f"{p.name} {p.score:.2f}" for p in sorted(b.partners, key=lambda p: -p.score)[:10]))
            st.caption("Edge width is the STRING combined score. Hover a node for the exact value.")
    with nav:
        if v:
            _detail(a, v)
        st.markdown("#### Where the variants sit")
        segs2 = tm_topology(b)
        plot_note("topology" if segs2 else "architecture")
        svg(topology_svg(b, segs2, tm_motifs(b, segs2), segment_stats(b, segs2), v) if segs2 else architecture_svg(b, v))
        if b.hotspots:
            st.dataframe([{"Residues": f"{h.start}-{h.end}", "Variants": h.count, "Enrichment": f"{h.fold:.1f}x", "Domain": b.domain_at((h.start + h.end) // 2)} for h in sorted(b.hotspots, key=lambda h: -h.fold)], hide_index=True)
        if helpers.get("landscape"):
            with st.expander("Variant landscape plot"):
                try:
                    st.plotly_chart(helpers["landscape"](), use_container_width=True)
                except Exception as e:
                    st.caption(f"Plot unavailable: {type(e).__name__}")
