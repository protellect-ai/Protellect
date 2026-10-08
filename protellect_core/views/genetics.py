"""Genetics: thresholds the gene meets or misses, the variant cascade, interactions, and how to go about it."""
from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ..analysis import genetic_thresholds, rank_variants, variant_plan
from ..cascade import cascade_html
from ..context import factor_claims
from ..network import interaction_svg
from .common import data_audit, render_claims
from .shell import Analysis

ICON = {"meets": "✓ meets", "does not meet": "✗ does not meet", "unavailable": "– no data"}


def render_genetics(a: Analysis) -> None:
    b = a.b
    if not b.loaded:
        st.info("Search a protein in the sidebar to see its genetic evidence.")
        return
    st.markdown("#### Genetic thresholds")
    rows = genetic_thresholds(b)
    st.dataframe([{"Measure": r["metric"], "Value": r["value"], "Threshold": r["threshold"], "Result": ICON[r["status"]], "What it means": r["meaning"], "Source": r["proof"].detail} for r in rows], hide_index=True)
    st.caption("Sources: " + " · ".join(f"[{r['proof'].source}]({r['proof'].url})" for r in rows if r["proof"].url.startswith("http")))

    st.markdown("#### ClinVar composition")
    if b.variants:
        counts = pd.Series([v.significance for v in b.variants]).value_counts()
        c1, c2 = st.columns(2)
        c1.bar_chart(counts)
        stars = pd.Series([v.stars for v in b.plp]).value_counts().sort_index() if b.plp else pd.Series(dtype=int)
        c2.bar_chart(stars) if len(stars) else c2.caption("No pathogenic variants, so no review-star distribution.")
        c2.caption("Review stars of pathogenic / likely-pathogenic entries (NCBI definition).")
    else:
        st.warning("No ClinVar variants were retrieved. Thresholds that depend on them are shown as 'no data', not as failures.")

    st.markdown("#### Variant cascade")
    ranked = [v for v in rank_variants(b) if v.is_plp] or rank_variants(b)
    if ranked:
        names = [v.name for v in ranked[:25]]
        cur = st.session_state.get("sel_variant_name")
        idx = names.index(cur) if cur in names else 0
        pick = st.selectbox("Variant", names, index=idx, key="gen_variant")
        v = ranked[names.index(pick)]
        components.html(cascade_html(b, v), height=330, scrolling=False)
        st.caption("Each stage is tagged: recorded (a database record), derived (computed from records), predicted (a model score), expected (the usual consequence of this variant type, not measured here) or untested.")
    else:
        st.info("No variants to build a cascade from.")

    st.markdown("#### What it interacts with")
    left, right = st.columns([2, 3])
    with left:
        st.markdown(interaction_svg(b.gene, b.partners), unsafe_allow_html=True)
    with right:
        if b.partners:
            st.dataframe([{"Partner": p.name, "STRING score": round(p.score, 3), "Link": p.url} for p in sorted(b.partners, key=lambda p: -p.score)], hide_index=True,
                         column_config={"Link": st.column_config.LinkColumn("Link")})
        fc = factor_claims(a.ctx, b)
        if fc:
            st.markdown("**Your microenvironment factors**")
            render_claims(fc, b, "gfac")

    alt = st.session_state.get("alterations")
    if alt is not None:
        from ..alterations import summary as alt_summary
        rows = alt_summary(alt, b.gene, 0.01)
        st.markdown("#### Pan-cancer alterations (from your table)")
        if rows:
            st.dataframe([{"Cancer type": r["cancer"], "Alteration frequency": r["text"]} for r in rows], hide_index=True)
            st.caption("Your own table, unchanged. Frequencies of 1% or more are listed.")
        else:
            st.caption(f"Your table has no alteration of {b.gene} at 1% or more in any cancer type.")

    st.markdown("#### How to go about it")
    render_claims(a.strategies, b, "gstrat", empty="No strategy rule is triggered by the genetic data retrieved.")
    if ranked:
        with st.expander(f"Step-by-step plan for the top variant ({ranked[0].pos})"):
            for i, s in enumerate(variant_plan(ranked[0], b), 1):
                st.markdown(f"**{i}. {s['step']}.** {s['do']}  \n_Why:_ {s['basis']}")
    data_audit(b)
