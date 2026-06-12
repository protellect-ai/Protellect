# modules/disease_panel.py
from __future__ import annotations
import streamlit as st
from modules.utils import src_link

def render_disease_panel():
    if st.session_state.get("disease_proteins"):
        dp_list = st.session_state["disease_proteins"]
        dis_name = st.session_state["disease_search"]
        with st.expander(f"🏥 Disease → Proteins: '{dis_name}' — {len(dp_list)} genes found (ClinVar)", expanded=True):
            st.markdown(
                f"<div style='color:#1e4060;font-size:.96rem;margin-bottom:.6rem;'>"
                f"All genes with <b>pathogenic / likely-pathogenic</b> (disease-causing) germline variants for <b>{dis_name}</b>, "
                f"ranked by number of confirmed variants. Source: {src_link('ClinVar', f'https://www.ncbi.nlm.nih.gov/clinvar/?term={dis_name}[disease]')}"
                f"</div>",
                unsafe_allow_html=True,
            )
            for dp_idx, dp_row in enumerate(dp_list):
                gn = dp_row.get("gene", "?")
                np2 = dp_row.get("n_pathogenic", 0)
                conds = dp_row.get("conditions", [])
                cond_str = "; ".join(conds)[:80]
                cv_url = dp_row.get("clinvar_url", "")
                bar_w = min(100, int(np2 / max(dp_list[0].get("n_pathogenic", 1), 1) * 100))

                dp_col_a, dp_col_b = st.columns([5, 1], gap="small")
                with dp_col_a:
                    with st.expander(f"{np2} variants  ·  {gn}  ·  {cond_str[:50]}", expanded=False):
                        ec1, ec2 = st.columns([3, 2])
                        with ec1:
                            st.markdown(
                                f"<div style='margin-bottom:.5rem;'>"
                                f"<div style='color:#00e5ff;font-weight:800;font-size:1.1rem;'>{gn}</div>"
                                f"<div style='color:#3a6080;font-size:.82rem;margin-top:2px;'>{np2} confirmed pathogenic variants in ClinVar for <b style='color:#5a9ab0;'>{dis_name}</b></div>"
                                f"</div>"
                                + (f"<div style='color:#4a7090;font-size:.82rem;'><b style='color:#6a9ab0;'>Conditions:</b> {'; '.join(conds[:5])}</div>" if conds else "")
                                + f"<div style='height:8px;background:#07152a;border-radius:4px;overflow:hidden;margin-top:.6rem;'><div style='width:{bar_w}%;height:100%;background:#ff2d55;'></div></div>"
                                f"<div style='color:#ff2d55;font-size:.76rem;margin-top:2px;'>{bar_w}% of maximum variant burden in this disease</div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f"<a class='src-badge' href='{cv_url}' target='_blank'>ClinVar ↗</a> "
                                f"<a class='src-badge' href='https://www.uniprot.org/uniprotkb?query={gn}+AND+organism_id:9606' target='_blank'>UniProt ↗</a> "
                                f"<a class='src-badge' href='https://platform.opentargets.org/target?search={gn}' target='_blank'>OpenTargets ↗</a>",
                                unsafe_allow_html=True,
                            )
                        with ec2:
                            if st.button(f"Analyse {gn} now", key=f"dp_analyse_{dp_idx}_{gn}", type="primary", use_container_width=True):
                                st.session_state["last"] = ""
                                st.session_state["protein_query_val"] = gn
                                st.session_state["_trigger_search"] = gn
                                st.rerun()
                with dp_col_b:
                    if st.button(f"Analyse →", key=f"dp_btn_{dp_idx}_{gn}", use_container_width=True):
                        st.session_state["last"] = ""
                        st.session_state["protein_query_val"] = gn
                        st.session_state["_trigger_search"] = gn
                        st.rerun()
