# modules/csv_handler.py
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from modules.utils import sh, mc
from modules.data_processing import analyse_csv_standalone, detect_csv_type

def handle_csv_mode():
    if st.session_state.get("csv_df") is not None and not st.session_state.get("pdata"):
        df = st.session_state["csv_df"]
        csv_type = st.session_state["csv_type"]
        active_goal = st.session_state.get("goal_label", "")
        gene = st.session_state.get("gene", "")
        scored = st.session_state.get("scored", [])
        variants = st.session_state.get("cv", {}).get("variants", [])
        am_scores = st.session_state.get("am", {})
        protein_length = st.session_state.get("pdata", {}).get("sequence", {}).get("length", 1) if st.session_state.get("pdata") else 1

        st.markdown("<hr style='border-color:#091830;margin:.8rem 0;'>", unsafe_allow_html=True)
        sh("📂", "Wet-Lab CSV Analysis — Standalone Mode")
        st.caption("No protein entered — analysing CSV data independently. Enter a gene/protein in the sidebar for integrated analysis.")

        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(mc(f"{len(df):,}", "Rows in dataset"), unsafe_allow_html=True)
        with c2: st.markdown(mc(len(df.columns), "Columns", "#4a90d9"), unsafe_allow_html=True)
        with c3: st.markdown(mc(csv_type.replace("_", " ").title(), "Data type detected", "#00c896"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        findings = analyse_csv_standalone(df, csv_type, active_goal, gene=gene, scored=scored, variants=variants, am_scores=am_scores, protein_length=protein_length)

        def _md2html(txt):
            import re as _re_rnd
            txt = _re_rnd.sub(r'\*\*(.+?)\*\*', lambda m: '<b style="color:#c0d8f0;">' + m.group(1) + '</b>', str(txt))
            txt = _re_rnd.sub(r'\*(.+?)\*', lambda m: '<i>' + m.group(1) + '</i>', txt)
            return txt

        for f_title_s, f_body_s in findings:
            st.markdown(f"<div class='card' style='animation:fadeInUp .4s ease both;margin-bottom:.7rem;'><h4 style='color:#00e5ff;font-size:.98rem;margin-bottom:.4rem;'>{f_title_s}</h4><p style='color:#7ab0c0;font-size:.88rem;line-height:1.65;'>{_md2html(f_body_s)}</p></div>", unsafe_allow_html=True)

        # Volcano plot for expression data
        fc_col = next((c for c in df.columns if any(k in c.lower() for k in ["fold", "logfc", "log2fc"])), None)
        p_col = next((c for c in df.columns if any(k in c.lower() for k in ["pvalue", "p_val", "padj", "fdr"])), None)
        if fc_col and p_col and df[fc_col].dtype in [float, 'float64'] and df[p_col].dtype in [float, 'float64']:
            fig_v = go.Figure()
            neg_log_p = (-np.log10(df[p_col].clip(1e-300))).clip(0, 50)
            colours_v = ["#ff2d55" if (fc > 1 and p2 < 0.05) else "#1e4060" if (fc < -1 and p2 < 0.05) else "#3a5a7a" for fc, p2 in zip(df[fc_col], df[p_col])]
            fig_v.add_trace(go.Scatter(x=df[fc_col], y=neg_log_p, mode="markers", marker=dict(color=colours_v, size=4, opacity=.7)))
            fig_v.add_vline(x=1, line_color="rgba(255,45,85,0.33)", line_dash="dot")
            fig_v.add_vline(x=-1, line_color="rgba(58,90,122,0.33)", line_dash="dot")
            fig_v.add_hline(y=-np.log10(0.05), line_color="rgba(255,214,10,0.33)", line_dash="dot")
            fig_v.update_layout(paper_bgcolor="#04080f", plot_bgcolor="#04080f", font_color="#1e4060", xaxis=dict(title="Fold change (log₂)", gridcolor="#060f1c"), yaxis=dict(title="-log₁₀(p-value)", gridcolor="#060f1c"), height=350, margin=dict(t=10, b=40, l=60, r=10))
            st.plotly_chart(fig_v, use_container_width=True, config={"displayModeBar": False})

        with st.expander("📋 Preview data"):
            st.dataframe(df.head(20), use_container_width=True)

        if st.button("✕ Close triage panel", key="close_triage"):
            st.session_state["csv_triage_active"] = False
            st.rerun()

        st.markdown("<hr style='border-color:#040c18;margin:1rem 0;'>", unsafe_allow_html=True)
