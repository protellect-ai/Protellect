"""Case Study: which diseases, tissues and organ systems the protein is tied to, with the source for each link."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ..analysis import _systems_in
from .common import data_audit, render_claims
from .shell import Analysis


def render_casestudy(a: Analysis, ncbi: dict) -> None:
    b = a.b
    if not b.loaded:
        st.info("Search a protein in the sidebar to see its disease, tissue and body-system associations.")
        return
    st.markdown("#### Body systems involved")
    if a.systems:
        st.bar_chart(pd.DataFrame({"evidence items": {s.tags["system"]: s.tags["n_supporting"] for s in a.systems}}))
        st.caption("Evidence items = tissue statements plus linked diseases. Systems are assigned by keyword match, and each row shows the rule and its source.")
        render_claims(a.systems, b, "sys")
    else:
        st.info("No tissue statement or disease name could be mapped to an organ system.")

    st.markdown("#### Tissue expression")
    if b.tissue_text:
        st.markdown(f"> {b.tissue_text}")
        st.caption(f"Source: [UniProt {b.uid}](https://www.uniprot.org/uniprotkb/{b.uid}/entry). Expression text is curated, not quantitative.")
    else:
        st.info("UniProt records no tissue specificity for this protein.")
    if b.subcellular:
        st.caption("Subcellular location: " + ", ".join(dict.fromkeys(s for s in b.subcellular if s)))

    st.markdown("#### Diseases, inheritance and organ systems")
    rows = []
    for d in a.diseases:
        name = d.tags.get("disease", d.text)
        rows.append({"Disease": name, "Inheritance": d.tags.get("inheritance") or "not stated", "Organ systems": ", ".join(_systems_in(name)) or "not mapped",
                     "Pathogenic variants": d.tags.get("n_supporting") if d.tags.get("domain") == "clinvar" else 0, "Best ClinVar review": d.tags.get("max_stars", 0),
                     "Sources": ", ".join(d.sources)})
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.info("No disease association was retrieved.")

    if ncbi:
        st.markdown("#### Where it is in the genome")
        st.markdown(f"Chromosome **{ncbi.get('chr', '?')}** · band **{ncbi.get('map', '?')}** · exons **{ncbi.get('exons', '?')}** · [NCBI Gene](https://www.ncbi.nlm.nih.gov/gene/?term={b.gene}%5Bsym%5D+AND+human%5Borgn%5D)")
    data_audit(b)
