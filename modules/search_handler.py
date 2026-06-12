# modules/search_handler.py
from __future__ import annotations
import streamlit as st
from modules.api import fetch_uniprot, fetch_clinvar, fetch_pdb, fetch_papers, fetch_gnomad, fetch_string_interactions, fetch_clinical_trials, fetch_dgidb, fetch_pubmed_abstracts, fetch_opentargets, fetch_alphamissense, fetch_isoforms
from modules.data_processing import g_gene, g_name, g_seq, g_diseases, compute_gi, ml_score_variants, classify_organism, compute_hotspot_clusters, estimate_patient_population
from modules.auth import check_search_limit, decrement_search, save_to_workspace

def handle_search():
    query = st.session_state.get("protein_query_box", "")
    search = st.session_state.get("_search_clicked", False)
    last = st.session_state.get("last", "")

    if search and query and query != last:
        if not check_search_limit():
            st.markdown(
                "<div style='background:#0a0300;border:2px solid #ffd60a;border-radius:10px;padding:.9rem 1.2rem;margin:.5rem 0;'>"
                "<div style='color:#ffd60a;font-weight:800;'>Search limit reached</div>"
                "<div style='color:#8a7040;font-size:.86rem;margin:.3rem 0;'>Free plan: 5 analyses included. Upgrade to Pro for 200/month.</div>"
                f"<a href='{STRIPE_LINKS['pro']}' target='_blank' style='background:#00e5ff;color:#000;font-weight:700;padding:4px 18px;border-radius:8px;font-size:.82rem;text-decoration:none;display:inline-block;margin-top:.3rem;'>"
                "Upgrade to Pro — $49/month</a></div>",
                unsafe_allow_html=True,
            )
            st.session_state["_search_clicked"] = False
            return

        decrement_search()
        fetch_uniprot.clear()

        with st.spinner("🔬 Fetching UniProt · ClinVar · AlphaFold · PubMed…"):
            try:
                pdata = fetch_uniprot(query)
                _org_check = pdata.get("organism", {})
                _sci_name = _org_check.get("scientificName", "")
                _tax_id = _org_check.get("taxonId", 0)
                if "Homo sapiens" not in _sci_name and _tax_id != 9606:
                    _common = _org_check.get("commonName", _sci_name)
                    raise ValueError(f"Non-human protein: '{query}' resolved to {_common} ({_sci_name}). Protellect only analyses human proteins.")

                st.session_state["pdata"] = pdata
                gene = g_gene(pdata)
                uid = pdata.get("primaryAccession", "")
                st.session_state["gene"] = gene
                st.session_state["uid"] = uid

                max_v = st.session_state.get("max_variants", 150)
                cv = fetch_clinvar(gene, max_v)
                st.session_state["cv"] = cv

                pdb = fetch_pdb(uid)
                st.session_state["pdb"] = pdb

                papers = fetch_papers(gene)
                st.session_state["papers"] = papers

                sensitivity = st.session_state.get("sensitivity", 50)
                scored = ml_score_variants(cv.get("variants", []), sensitivity)
                st.session_state["scored"] = scored

                protein_len = pdata.get("sequence", {}).get("length", 1)
                gi = compute_gi(cv, protein_len)
                st.session_state["gi"] = gi

                save_to_workspace(g_gene(pdata), pdata, gi, g_diseases(pdata), [])

                st.session_state["last"] = query
                st.session_state["_search_clicked"] = False

                # Extended data fetches
                with st.spinner("🔗 Fetching interactions, population genetics & drug data..."):
                    gnomad_data = fetch_gnomad(gene)
                    string_data = fetch_string_interactions(gene)
                    trials_data = fetch_clinical_trials(gene)
                    drugs_data = fetch_dgidb(gene)
                    abstracts = fetch_pubmed_abstracts(gene)
                    org_class = classify_organism(pdata)

                    st.session_state["gnomad"] = gnomad_data
                    st.session_state["string"] = string_data
                    st.session_state["trials"] = trials_data
                    st.session_state["drugs"] = drugs_data
                    st.session_state["abstracts"] = abstracts
                    st.session_state["org"] = org_class

                with st.spinner("🧬 Fetching OpenTargets, AlphaMissense & computing hotspots..."):
                    ot_data = fetch_opentargets(gene)
                    am_scores = fetch_alphamissense(uid)
                    isoforms = fetch_isoforms(uid)
                    hotspots = compute_hotspot_clusters(cv.get("variants", []), pdata.get("sequence", {}).get("length", 1))
                    patient_d = estimate_patient_population(g_diseases(pdata), cv, compute_gi(cv, pdata.get("sequence", {}).get("length", 1)))

                    st.session_state["ot"] = ot_data
                    st.session_state["am"] = am_scores
                    st.session_state["isoforms"] = isoforms
                    st.session_state["hotspots"] = hotspots
                    st.session_state["patients"] = patient_d

                st.rerun()

            except Exception as e:
                err_msg = str(e)
                if "non-human" in err_msg.lower() or "homo sapiens" in err_msg.lower():
                    st.markdown(
                        "<div style='background:#0a0300;border:2px solid #ff8c42;border-radius:12px;padding:1.1rem 1.4rem;margin:.5rem 0;'>"
                        "<div style='color:#ff8c42;font-weight:800;font-size:1rem;margin-bottom:5px;'>"
                        "⚠️ Non-human protein detected — Protellect is human-only</div>"
                        f"<div style='color:#8a6040;font-size:.88rem;line-height:1.6;'>{err_msg}</div>"
                        "<div style='margin-top:.7rem;color:#5a4030;font-size:.82rem;'>"
                        "<b style='color:#7a6040;'>Try these human proteins instead:</b> "
                        "TP53 · FLNC · BRCA1 · EGFR · ACM2 · ARRB2 · KRT5 · INS"
                        "</div></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div style='background:#0a0100;border:2px solid #ff2d55;border-radius:12px;padding:1rem 1.4rem;margin:.5rem 0;'>"
                        "<div style='color:#ff2d55;font-weight:800;font-size:.95rem;margin-bottom:4px;'>⚠️ Search error</div>"
                        f"<div style='color:#804050;font-size:.86rem;'>{err_msg}</div>"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                st.session_state["_search_clicked"] = False
