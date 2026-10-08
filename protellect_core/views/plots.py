"""GPCR-aware volcano plot: the receptors are the point, so they are labelled and coloured by status."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from ..engine.io_parsers import GENE_COLS


def render_volcano(df: pd.DataFrame, fc_col: str, p_col: str, registry: dict) -> None:
    import plotly.graph_objects as go
    low = {str(c).strip().lower().replace(" ", "_"): c for c in df.columns}
    gcol = next((low[c] for c in GENE_COLS if c in low), df.columns[0])
    d = df[[gcol, fc_col, p_col]].copy()
    d.columns = ["gene", "fc", "p"]
    d["gene"] = d["gene"].astype(str).str.upper()
    d = d.dropna()
    d["y"] = (-np.log10(d["p"].astype(float).clip(lower=1e-300))).clip(0, 60)
    d["status"] = d["gene"].map(lambda g: registry.get(g, {}).get("status", ""))
    fig = go.Figure()
    other = d[d["status"] == ""]
    fig.add_trace(go.Scattergl(x=other["fc"], y=other["y"], mode="markers", name=f"other genes ({len(other)})", marker=dict(color="#2a4060", size=4, opacity=.55), text=other["gene"], hovertemplate="%{text}<br>log2FC %{x:.2f}<br>-log10 p %{y:.2f}<extra></extra>"))
    for stt, colr, nm in (("characterized", "#38bdf8", "characterised GPCR"), ("orphan", "#fbbf24", "orphan GPCR")):
        s = d[d["status"] == stt]
        if len(s):
            fig.add_trace(go.Scatter(x=s["fc"], y=s["y"], mode="markers", name=f"{nm} ({len(s)})", marker=dict(color=colr, size=9, line=dict(color="#020617", width=1)), text=s["gene"], hovertemplate="%{text}<br>log2FC %{x:.2f}<br>-log10 p %{y:.2f}<extra></extra>"))
    gp = d[d["status"] != ""].assign(rank=lambda x: x["fc"].abs() * x["y"]).sort_values("rank", ascending=False).head(12)
    for _, r in gp.iterrows():
        fig.add_annotation(x=r["fc"], y=r["y"], text=r["gene"], showarrow=True, arrowhead=0, arrowcolor="#3a5a7a", font=dict(color="#fbbf24" if r["status"] == "orphan" else "#9ccbe6", size=11), ax=24, ay=-22)
    fig.add_vline(x=1, line_color="rgba(255,45,85,.35)", line_dash="dot"); fig.add_vline(x=-1, line_color="rgba(58,90,122,.5)", line_dash="dot")
    fig.add_hline(y=-np.log10(0.05), line_color="rgba(255,214,10,.35)", line_dash="dot")
    fig.update_layout(paper_bgcolor="#020617", plot_bgcolor="#020617", font_color="#9ab", height=420, margin=dict(t=40, b=50, l=60, r=10),
                      title=dict(text="Volcano plot: GPCRs labelled, orphans in amber", font_size=13), xaxis=dict(title="log2 fold change", gridcolor="#07142b", zeroline=False),
                      yaxis=dict(title="-log10 p", gridcolor="#07142b"), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    if not registry or all(v.get("status") == "" for v in registry.values()):
        st.caption("No receptor registry is loaded, so GPCRs cannot be highlighted.")
