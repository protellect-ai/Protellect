"""Top banner: what the experiment says to prioritise or deprioritise, and which tab to follow."""
from __future__ import annotations

import html
from typing import List

import streamlit as st
from ..frame import html_frame

from ..routing import Priority
from .common import LEVEL_COLOR


def _goto_script(tab: str) -> str:
    t = html.escape(tab, quote=True)
    return ("<script>(function(){var want='" + t + "';var d=window.parent.document;var tabs=d.querySelectorAll('button[role=\"tab\"]');"
            "for(var i=0;i<tabs.length;i++){if(tabs[i].innerText.trim().toLowerCase()===want.toLowerCase()){tabs[i].click();break}}})();</script>")


def render_priority_banner(items: List[Priority]) -> None:
    if not items:
        return
    main, rest = items[0], items[1:]
    col = LEVEL_COLOR.get(main.level, "#64748b")
    why = "".join(f"<li>{html.escape(r)}</li>" for r in main.reasons if r)
    nxt = f"<div style='margin-top:6px;color:#cfe6f5;font-size:.85rem'><b>Next:</b> {html.escape(main.action)}" + (f" Open the <b>{html.escape(main.goto)}</b> tab." if main.goto else "") + "</div>" if main.action else ""
    st.markdown(f"<div style='border:1px solid {col}55;border-left:5px solid {col};background:#050d1e;border-radius:10px;padding:.8rem 1.1rem;margin:.2rem 0 .5rem'>"
                f"<div style='color:{col};font-size:.72rem;font-weight:800;letter-spacing:.08em'>{html.escape(main.level)}</div>"
                f"<div style='color:#e6edf7;font-size:1.05rem;font-weight:700;margin:2px 0'>{html.escape(main.headline)}</div>"
                f"<ul style='color:#8fb0c8;font-size:.82rem;margin:.2rem 0 0 1.1rem'>{why}</ul>{nxt}</div>", unsafe_allow_html=True)
    if rest:
        cols = st.columns(min(3, len(rest)))
        for i, p in enumerate(rest[:3]):
            c = LEVEL_COLOR.get(p.level, "#64748b")
            cols[i].markdown(f"<div style='border:1px solid {c}44;border-radius:8px;padding:.45rem .7rem;background:#050d1e;height:100%'><div style='color:{c};font-size:.65rem;font-weight:800'>{html.escape(p.level)}</div>"
                             f"<div style='color:#cfe6f5;font-size:.82rem'>{html.escape(p.headline)}</div>"
                             + (f"<div style='color:#6b8aa3;font-size:.72rem;margin-top:2px'>Go to the <b>{html.escape(p.goto)}</b> tab</div>" if p.goto else "") + "</div>", unsafe_allow_html=True)
    want = st.session_state.pop("_goto_tab", None)
    if want:
        html_frame(_goto_script(want), 1)
    if main.goto and st.button(f"Take me to {main.goto}", key="banner_goto"):
        st.session_state["_goto_tab"] = main.goto
        st.rerun()
