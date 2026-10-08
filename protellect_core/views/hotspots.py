"""Druggable hotspots: where to drug it, what is known, pharmacokinetics and ADMET screens, adverse events, and what-if scenarios."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import adme
from ..analysis import CITE
from ..context import factor_claims, medication_claims
from ..network import track_svg
from ..pharma import scenarios
from .common import data_audit, render_claims
from .shell import Analysis


@st.cache_data(ttl=3600, show_spinner=False)
def _props(name: str):
    import requests
    return adme.fetch_properties(name, requests.get)


@st.cache_data(ttl=3600, show_spinner=False)
def _faers(name: str):
    import requests
    return adme.fetch_faers(name, requests.get)


def render_hotspots(a: Analysis) -> None:
    b, ctx = a.b, a.ctx
    if not b.loaded:
        st.info("Search a protein in the sidebar to see where it can be drugged.")
        return
    mine = medication_claims(ctx, b) + factor_claims(ctx, b)
    if mine:
        st.markdown("#### Relevance to your setup")
        render_claims(mine, b, "hmine")

    st.markdown("#### Hotspots on the protein")
    st.markdown(track_svg(b), unsafe_allow_html=True)
    rows = []
    for h in sorted(b.hotspots, key=lambda h: -h.fold)[:8]:
        mid = (h.start + h.end) // 2
        site = next((s for s in b.sites if s["start"] <= h.end and s["end"] >= h.start), None)
        rows.append({"Residues": f"{h.start}-{h.end}", "Variants": h.count, "Enrichment": f"{h.fold:.1f}x", "Domain": b.domain_at(mid) or "-", "Annotated site": f"{site['type']}: {site['desc']}" if site else "-"})
    if rows:
        st.dataframe(rows, hide_index=True)
        st.caption("A hotspot is a stretch where disease variants cluster more than chance; it marks functionally sensitive residues, not by itself a drug pocket.")
    else:
        st.info("No variant hotspots were found (too few pathogenic variants, or no ClinVar data).")

    st.markdown("#### Tractability and what already exists")
    chips = [("Small molecule", b.tractability.get("Small molecule")), ("Antibody", b.tractability.get("Antibody")), ("PROTAC", b.tractability.get("PROTAC"))]
    if b.tractability:
        st.markdown(" ".join(f":{'green' if on else 'gray'}[{k}: {'tractable' if on else 'not flagged'}]" for k, on in chips) + "  \nSource: [Open Targets](https://platform.opentargets.org/target)")
    else:
        st.warning("Open Targets returned no tractability data for this protein. This usually means a failed fetch, so nothing is concluded from it.")
    if b.drugs:
        st.dataframe([{"Drug": d.name, "Type": d.kind or d.mechanism or "-", "Phase": d.phase or "-", "Indication": d.indication or "-", "Source": d.source, "Link": d.url} for d in b.drugs], hide_index=True,
                     column_config={"Link": st.column_config.LinkColumn("Link")})
    else:
        st.caption("No drug-gene interactions were retrieved.")
    if b.trials:
        st.dataframe([{"Trial": t.get("title", "")[:90], "Phase": t.get("phase", ""), "Status": t.get("status", ""), "Condition": t.get("condition", "")} for t in b.trials[:12]], hide_index=True)

    st.markdown("#### Pharmacokinetics and ADMET screen")
    st.caption(f"Properties are computed descriptors from [PubChem](https://pubchem.ncbi.nlm.nih.gov/) for each named drug. The tests are published rules ({adme.CITES['lipinski']}; {adme.CITES['veber']}; {adme.CITES['cns']}), not a measured or machine-learned prediction.")
    names = list(dict.fromkeys(d.name for d in b.drugs))[:6]
    if not names:
        st.info("No named drugs to screen. For a new compound, the same rules apply to its molecular weight, logP, polar surface area and H-bond counts.")
    for nm in names:
        p = _props(nm)
        if not p:
            st.markdown(f"**{nm}**: not found in PubChem, or PubChem could not be reached.")
            continue
        rows = adme.admet_rules(p)
        st.markdown(f"**{nm}** · MW {p['mw']:.0f} · logP {p['xlogp'] if p['xlogp'] is not None else 'n/a'} · polar surface area {p['tpsa'] if p['tpsa'] is not None else 'n/a'}")
        st.dataframe([{"Test": r["test"], "Result": "passes" if r["pass"] else "does not pass", "Numbers": r["detail"], "Basis": r["basis"]} for r in rows], hide_index=True)

    st.markdown("#### Reported adverse events for drugs on this target")
    if names:
        pick = st.selectbox("Drug", names, key="hs_faers_drug")
        f = _faers(pick)
        if f:
            st.markdown(f"openFDA FAERS: **{f['total']:,}** spontaneous reports mention {pick}." if f["total"] else f"openFDA FAERS reports for {pick}:")
            st.bar_chart(pd.DataFrame({"reports": {t: n for t, n in f["top"]}}))
            st.caption("Spontaneous reports. They show what was reported, not how often it occurs or whether the drug caused it. [openFDA](https://open.fda.gov/apis/drug/event/)")
        else:
            st.info(f"No FAERS reports were returned for {pick}, or openFDA could not be reached.")
    else:
        st.caption("No known drugs on this target, so there are no adverse-event records to show.")

    st.markdown("#### What could happen if you drug it (ranked scenarios)")
    st.caption("Each scenario combines the direction of effect, the tissues where the protein is expressed, recorded drug precedent, and the available modality. They organise evidence; they do not predict a clinical outcome.")
    sc = scenarios(b, a.defects, a.systems, a.diseases, ctx)
    shown = render_claims(sc, b, "scn", empty="Not enough evidence to build a scenario for this protein.", how_label="What the drug must consist of and how it is given")
    for c in shown[:3]:
        t = c.tags
        st.caption(f"{c.text.split(':')[0]} · on-target safety risk tier: {t['risk']}" + (f" · organs: {', '.join(t['organs'])}" if t["organs"] else "") + (f" · could phenocopy: {', '.join(t['phenocopy'])}" if t["phenocopy"] else ""))
    data_audit(b)
