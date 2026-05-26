from __future__ import annotations
# ═══════════════════════════════════════════════════════════════════
#  Protellect v6 — single-file, no local imports
#  All new: pursue banner · disease→proteins · GPCR detail ·
#           genomic visual · mutation cascade · source links ·
#           plain-language terms · CSV standalone · fixed empty sections
# ═══════════════════════════════════════════════════════════════════

import re, time, json, math, io
from collections import Counter, defaultdict

import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ─── Authentication & Workspace Configuration ──────────────────────────────────
import hashlib, json, time
from datetime import datetime

# Simple built-in auth (no external library needed — avoids import errors)
def _hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# Default credentials — in production, move to st.secrets
# Credentials stored in session state so registered users persist across reruns
def _get_credentials():
    if "_credentials" not in st.session_state:
        st.session_state["_credentials"] = {
            "demo@protellect.com":    {"name":"Demo User",    "pw":_hash("protellect2024"), "plan":"free",    "searches_left":5},
            "pro@protellect.com":     {"name":"Pro User",     "pw":_hash("pro2024"),        "plan":"pro",     "searches_left":999},
            "enterprise@protellect.com":{"name":"Enterprise", "pw":_hash("ent2024"),        "plan":"enterprise","searches_left":9999},
        }
    return st.session_state["_credentials"]
CREDENTIALS = None  # always call _get_credentials() instead

PLAN_LIMITS = {
    "free":       {"searches": 5,    "history": 5,   "excel": False, "ai_report": False, "price_id": None},
    "pro":        {"searches": 200,  "history": 100, "excel": True,  "ai_report": True,  "price_id": "price_pro_monthly"},
    "enterprise": {"searches": 9999, "history": 999, "excel": True,  "ai_report": True,  "price_id": "price_ent_monthly"},
}

STRIPE_LINKS = {
    "pro":        "https://buy.stripe.com/test_pro_placeholder",  # Replace with real Stripe payment link
    "enterprise": "https://buy.stripe.com/test_ent_placeholder",  # Replace with real Stripe payment link
}

def auth_init():
    defaults = {
        "auth_user": None, "auth_name": None, "auth_plan": None,
        "auth_searches_left": 0, "workspace": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def login_page():
    """Full-page login/signup UI."""
    st.markdown("""
    <style>
    .login-wrap{max-width:420px;margin:60px auto 0;padding:2rem 2.5rem;
      background:#020810;border:1px solid #0d2545;border-radius:16px;}
    .login-logo{text-align:center;margin-bottom:1.4rem;}
    .login-title{color:#00e5ff;font-size:1.6rem;font-weight:800;text-align:center;margin-bottom:.3rem;}
    .login-sub{color:#3a6080;font-size:.88rem;text-align:center;margin-bottom:1.4rem;}
    .plan-card{background:#030d1a;border:1px solid #0d2545;border-radius:10px;padding:.9rem;margin:.5rem 0;cursor:pointer;transition:all .2s;}
    .plan-card:hover{border-color:#00e5ff44;}
    .plan-free{border-left:3px solid #3a6080;}
    .plan-pro{border-left:3px solid #00e5ff;}
    .plan-ent{border-left:3px solid #a855f7;}
    </style>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1,2,1])
    with col_m:
        st.markdown("<div class='login-title'>Protellect</div>", unsafe_allow_html=True)
        st.markdown("<div class='login-sub'>Genetics-first protein intelligence</div>", unsafe_allow_html=True)

        tab_in, tab_up, tab_plans = st.tabs(["Sign in", "Register", "Plans & Pricing"])

        with tab_in:
            email    = st.text_input("Email", placeholder="you@lab.com", key="li_email")
            password = st.text_input("Password", type="password", key="li_pw")
            if st.button("Sign in", use_container_width=True, type="primary", key="li_btn"):
                user = _get_credentials().get(email)
                if user and user["pw"] == _hash(password):
                    st.session_state["auth_user"] = email
                    st.session_state["auth_name"] = user["name"]
                    # Give registered users full pro access
                    st.session_state["auth_plan"] = "pro"
                    st.session_state["auth_searches_left"] = 999999
                    st.success(f"Welcome back, {user['name']}! You have full Pro access.")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Use demo@protellect.com / protellect2024 to try.")
            st.markdown(
                "<div style='color:#2a5060;font-size:.8rem;margin-top:.5rem;'>Demo: demo@protellect.com / protellect2024</div>",
                unsafe_allow_html=True,
            )
            st.markdown("<div style='margin:.8rem 0;text-align:center;color:#1e4060;font-size:.75rem;'>── or ──</div>", unsafe_allow_html=True)
            if st.button("Continue as Guest (5 free analyses)", use_container_width=True, key="guest_btn"):
                st.session_state["auth_user"]          = "guest"
                st.session_state["auth_name"]          = "Guest Researcher"
                st.session_state["auth_plan"]          = "free"
                st.session_state["auth_searches_left"] = 5
                st.rerun()

        with tab_up:
            st.markdown("<div style='color:#5a8090;font-size:.86rem;margin-bottom:.6rem;'>Create an account to get 5 free protein analyses. Upgrade anytime.</div>", unsafe_allow_html=True)
            new_name  = st.text_input("Full name", key="reg_name")
            new_email = st.text_input("Email", key="reg_email")
            new_pw    = st.text_input("Password", type="password", key="reg_pw")
            new_pw2   = st.text_input("Confirm password", type="password", key="reg_pw2")
            if st.button("Create free account", use_container_width=True, type="primary", key="reg_btn"):
                if not new_name or not new_email or not new_pw:
                    st.error("All fields required.")
                elif new_pw != new_pw2:
                    st.error("Passwords do not match.")
                elif "@" not in new_email:
                    st.error("Enter a valid email address.")
                else:
                    # In production: write to database. Here: add to session.
                    _get_credentials()[new_email] = {
                        "name": new_name, "pw": _hash(new_pw),
                        "plan": "free", "searches_left": 5,
                    }
                    st.session_state["auth_user"]  = new_email
                    st.session_state["auth_name"]  = new_name
                    st.session_state["auth_plan"]  = "free"
                    st.session_state["auth_searches_left"] = 5
                    st.success("Account created! 5 free analyses included.")
                    st.rerun()

        with tab_plans:
            st.markdown(
                "<div style='background:#030d1a;border:1px solid #0d2545;border-radius:10px;padding:.9rem;margin:.4rem 0;border-left:3px solid #3a6080;'>"
                "<div style='color:#8ab8cc;font-weight:700;'>Free</div>"
                "<div style='color:#00e5ff;font-size:1.4rem;font-weight:800;'>$0</div>"
                "<div style='color:#3a6080;font-size:.82rem;'>5 protein analyses · 5 saved · Basic triage · ClinVar + UniProt</div>"
                "</div>"
                "<div style='background:#030d1a;border:1px solid #00e5ff33;border-radius:10px;padding:.9rem;margin:.4rem 0;border-left:3px solid #00e5ff;'>"
                "<div style='color:#00e5ff;font-weight:700;'>Pro <span style='color:#ffd60a;font-size:.72rem;'>MOST POPULAR</span></div>"
                "<div style='color:#00e5ff;font-size:1.4rem;font-weight:800;'>$49<span style='color:#3a6080;font-size:.9rem;'>/month</span></div>"
                "<div style='color:#3a6080;font-size:.82rem;'>200 analyses/month · Full history · Excel export · AI report · gnomAD + OpenTargets + AlphaMissense + STRING</div>"
                f"<a href='{STRIPE_LINKS['pro']}' target='_blank' style='display:inline-block;margin-top:.5rem;background:#00e5ff;color:#000;font-weight:700;padding:4px 18px;border-radius:8px;font-size:.82rem;text-decoration:none;'>Upgrade to Pro</a>"
                "</div>"
                "<div style='background:#030d1a;border:1px solid #a855f733;border-radius:10px;padding:.9rem;margin:.4rem 0;border-left:3px solid #a855f7;'>"
                "<div style='color:#a855f7;font-weight:700;'>Enterprise</div>"
                "<div style='color:#a855f7;font-size:1.4rem;font-weight:800;'>$299<span style='color:#3a6080;font-size:.9rem;'>/month</span></div>"
                "<div style='color:#3a6080;font-size:.82rem;'>Unlimited analyses · Team workspace · Private deployment · API access · Dedicated support</div>"
                f"<a href='{STRIPE_LINKS['enterprise']}' target='_blank' style='display:inline-block;margin-top:.5rem;background:#a855f7;color:#fff;font-weight:700;padding:4px 18px;border-radius:8px;font-size:.82rem;text-decoration:none;'>Upgrade to Enterprise</a>"
                "</div>",
                unsafe_allow_html=True,
            )

    st.stop()

def save_to_workspace(gene, pdata, gi, diseases, scored):
    """Save current analysis to workspace history."""
    if not st.session_state.get("auth_user"):
        return
    plan = st.session_state.get("auth_plan","free")
    limit = PLAN_LIMITS[plan]["history"]
    ws = st.session_state.get("workspace",[])
    # Avoid duplicates
    existing = [i for i,w in enumerate(ws) if w.get("gene") == gene]
    if existing:
        ws.pop(existing[0])
    ws.insert(0, {
        "gene":        gene,
        "uid":         pdata.get("primaryAccession",""),
        "name":        pdata.get("protein",{}).get("recommendedName",{}).get("fullName",{}).get("value","") or gene,
        "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M"),
        "verdict":     gi.get("pursue",""),
        "n_path":      gi.get("n_pathogenic",0),
        "n_total":     gi.get("n_total",0),
        "density":     round(gi.get("density",0)*100,2),
        "diseases":    [d["name"] for d in diseases[:4]],
        "scored_top":  [(v.get("variant_name","")[:30], v.get("ml_rank","")) for v in scored[:5]],
    })
    st.session_state["workspace"] = ws[:limit]

def check_search_limit():
    """Always returns True — Protellect is open access."""
    return True

def decrement_search():
    """Open access — no search credits to decrement."""
    pass


st.set_page_config(page_title="Protellect", page_icon="🔬",
                   layout="wide", initial_sidebar_state="expanded")

LOGO_B64 = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyMDAgMjAwIiB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCI+CiAgPGRlZnM+CiAgICA8cmFkaWFsR3JhZGllbnQgaWQ9ImJnIiBjeD0iNTAlIiBjeT0iNTAlIiByPSI1MCUiPgogICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjMDAxYTJlIiBzdG9wLW9wYWNpdHk9IjAuNiIvPgogICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiMwMDA1MDgiIHN0b3Atb3BhY2l0eT0iMCIvPgogICAgPC9yYWRpYWxHcmFkaWVudD4KICAgIDxmaWx0ZXIgaWQ9Imdsb3ciIHg9Ii01MCUiIHk9Ii01MCUiIHdpZHRoPSIyMDAlIiBoZWlnaHQ9IjIwMCUiPgogICAgICA8ZmVHYXVzc2lhbkJsdXIgc3RkRGV2aWF0aW9uPSIyLjUiIHJlc3VsdD0iYmx1ciIvPgogICAgICA8ZmVNZXJnZT48ZmVNZXJnZU5vZGUgaW49ImJsdXIiLz48ZmVNZXJnZU5vZGUgaW49IlNvdXJjZUdyYXBoaWMiLz48L2ZlTWVyZ2U+CiAgICA8L2ZpbHRlcj4KICAgIDxmaWx0ZXIgaWQ9InNvZnRnbG93Ij4KICAgICAgPGZlR2F1c3NpYW5CbHVyIHN0ZERldmlhdGlvbj0iMS41IiByZXN1bHQ9ImJsdXIiLz4KICAgICAgPGZlTWVyZ2U+PGZlTWVyZ2VOb2RlIGluPSJibHVyIi8+PGZlTWVyZ2VOb2RlIGluPSJTb3VyY2VHcmFwaGljIi8+PC9mZU1lcmdlPgogICAgPC9maWx0ZXI+CiAgICA8bGluZWFyR3JhZGllbnQgaWQ9ImhlbGl4MSIgeDE9IjAlIiB5MT0iMCUiIHgyPSIwJSIgeTI9IjEwMCUiPgogICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjMDBmZmVlIi8+CiAgICAgIDxzdG9wIG9mZnNldD0iNDAlIiBzdG9wLWNvbG9yPSIjMDBlNWZmIi8+CiAgICAgIDxzdG9wIG9mZnNldD0iMTAwJSIgc3RvcC1jb2xvcj0iIzAwNTVjYyIvPgogICAgPC9saW5lYXJHcmFkaWVudD4KICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iaGVsaXgyIiB4MT0iMCUiIHkxPSIxMDAlIiB4Mj0iMCUiIHkyPSIwJSI+CiAgICAgIDxzdG9wIG9mZnNldD0iMCUiIHN0b3AtY29sb3I9IiMwMGZmZWUiLz4KICAgICAgPHN0b3Agb2Zmc2V0PSI0MCUiIHN0b3AtY29sb3I9IiMwMGM4ZmYiLz4KICAgICAgPHN0b3Agb2Zmc2V0PSIxMDAlIiBzdG9wLWNvbG9yPSIjMDA0NGFhIi8+CiAgICA8L2xpbmVhckdyYWRpZW50PgogICAgPGxpbmVhckdyYWRpZW50IGlkPSJub2RlR3JhZCIgeDE9IjAlIiB5MT0iMCUiIHgyPSIxMDAlIiB5Mj0iMTAwJSI+CiAgICAgIDxzdG9wIG9mZnNldD0iMCUiIHN0b3AtY29sb3I9IiNmZmZmZmYiLz4KICAgICAgPHN0b3Agb2Zmc2V0PSIxMDAlIiBzdG9wLWNvbG9yPSIjMDBlNWZmIi8+CiAgICA8L2xpbmVhckdyYWRpZW50PgogIDwvZGVmcz4KCiAgPCEtLSBPdXRlciByaW5nIC0tPgogIDxjaXJjbGUgY3g9IjEwMCIgY3k9IjEwMCIgcj0iOTAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzAwZTVmZiIgc3Ryb2tlLXdpZHRoPSIwLjYiIG9wYWNpdHk9IjAuMTUiLz4KICA8Y2lyY2xlIGN4PSIxMDAiIGN5PSIxMDAiIHI9Ijc1IiBmaWxsPSJub25lIiBzdHJva2U9IiMwMGU1ZmYiIHN0cm9rZS13aWR0aD0iMC40IiBvcGFjaXR5PSIwLjEiLz4KICA8Y2lyY2xlIGN4PSIxMDAiIGN5PSIxMDAiIHI9IjkyIiBmaWxsPSJ1cmwoI2JnKSIvPgoKICA8IS0tIFRpY2sgbWFya3Mgb24gb3V0ZXIgcmluZyAtLT4KICA8ZyBzdHJva2U9IiMwMGU1ZmYiIHN0cm9rZS13aWR0aD0iMC44IiBvcGFjaXR5PSIwLjI1Ij4KICAgIDxsaW5lIHgxPSIxMDAiIHkxPSIxMCIgeDI9IjEwMCIgeTI9IjE4Ii8+CiAgICA8bGluZSB4MT0iMTAwIiB5MT0iMTgyIiB4Mj0iMTAwIiB5Mj0iMTkwIi8+CiAgICA8bGluZSB4MT0iMTAiIHkxPSIxMDAiIHgyPSIxOCIgeTI9IjEwMCIvPgogICAgPGxpbmUgeDE9IjE4MiIgeTE9IjEwMCIgeDI9IjE5MCIgeTI9IjEwMCIvPgogICAgPGxpbmUgeDE9IjM2IiB5MT0iMzYiIHgyPSI0MSIgeTI9IjQxIi8+CiAgICA8bGluZSB4MT0iMTU5IiB5MT0iMzYiIHgyPSIxNjQiIHkyPSI0MSIvPgogICAgPGxpbmUgeDE9IjM2IiB5MT0iMTY0IiB4Mj0iNDEiIHkyPSIxNTkiLz4KICAgIDxsaW5lIHgxPSIxNTkiIHkxPSIxNjQiIHgyPSIxNjQiIHkyPSIxNTkiLz4KICA8L2c+CgogIDwhLS0gRE5BIHN0cmFuZCBBIOKAlCBzaW51c29pZGFsIHBhdGggbGVmdCAtLT4KICA8cGF0aCBkPSJNIDgyIDIyIEMgNjAgNDAsIDY4IDU4LCA4NiA3MiBDIDEwNCA4NiwgMTEyIDEwNCwgOTIgMTIwIEMgNzIgMTM2LCA3NiAxNTYsIDg4IDE3NCIKICAgICAgICBmaWxsPSJub25lIiBzdHJva2U9InVybCgjaGVsaXgxKSIgc3Ryb2tlLXdpZHRoPSIzLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIKICAgICAgICBmaWx0ZXI9InVybCgjZ2xvdykiIG9wYWNpdHk9IjAuOTUiLz4KCiAgPCEtLSBETkEgc3RyYW5kIEIg4oCUIG9wcG9zaXRlIHBoYXNlIC0tPgogIDxwYXRoIGQ9Ik0gMTEyIDIyIEMgMTM0IDQwLCAxMjYgNTgsIDEwOCA3MiBDIDkwIDg2LCA4MiAxMDQsIDEwMiAxMjAgQyAxMjIgMTM2LCAxMTggMTU2LCAxMDYgMTc0IgogICAgICAgIGZpbGw9Im5vbmUiIHN0cm9rZT0idXJsKCNoZWxpeDIpIiBzdHJva2Utd2lkdGg9IjMuNSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogICAgICAgIGZpbHRlcj0idXJsKCNnbG93KSIgb3BhY2l0eT0iMC45NSIvPgoKICA8IS0tIFJ1bmdzIOKAlCBwcmVjaXNlIGF0IHdhdmUgaW50ZXJzZWN0aW9ucyAtLT4KICA8ZyBmaWx0ZXI9InVybCgjc29mdGdsb3cpIiBvcGFjaXR5PSIwLjkiPgogICAgPGxpbmUgeDE9IjgyIiB5MT0iMzAiIHgyPSIxMTIiIHkyPSIzMCIgc3Ryb2tlPSIjMDBmZmVlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgogICAgPGxpbmUgeDE9Ijc0IiB5MT0iNDgiIHgyPSIxMTgiIHkyPSI0OCIgc3Ryb2tlPSIjMDBlNWZmIiBzdHJva2Utd2lkdGg9IjEuOCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBvcGFjaXR5PSIwLjciLz4KICAgIDxsaW5lIHgxPSI3MCIgeTE9IjY2IiB4Mj0iMTIyIiB5Mj0iNjYiIHN0cm9rZT0iIzAwZmZlZSIgc3Ryb2tlLXdpZHRoPSIyLjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgogICAgPGxpbmUgeDE9Ijc0IiB5MT0iODQiIHgyPSIxMTgiIHkyPSI4NCIgc3Ryb2tlPSIjMDBlNWZmIiBzdHJva2Utd2lkdGg9IjEuOCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBvcGFjaXR5PSIwLjciLz4KICAgIDxsaW5lIHgxPSI4NCIgeTE9IjEwMiIgeDI9IjExMCIgeTI9IjEwMiIgc3Ryb2tlPSIjMDBmZmVlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgogICAgPGxpbmUgeDE9Ijg2IiB5MT0iMTIwIiB4Mj0iMTA4IiB5Mj0iMTIwIiBzdHJva2U9IiMwMGU1ZmYiIHN0cm9rZS13aWR0aD0iMS44IiBzdHJva2UtbGluZWNhcD0icm91bmQiIG9wYWNpdHk9IjAuNyIvPgogICAgPGxpbmUgeDE9Ijg0IiB5MT0iMTM4IiB4Mj0iMTA4IiB5Mj0iMTM4IiBzdHJva2U9IiMwMGZmZWUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+CiAgICA8bGluZSB4MT0iODgiIHkxPSIxNTYiIHgyPSIxMDYiIHkyPSIxNTYiIHN0cm9rZT0iIzAwZTVmZiIgc3Ryb2tlLXdpZHRoPSIxLjgiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgb3BhY2l0eT0iMC43Ii8+CiAgPC9nPgoKICA8IS0tIFJ1bmcgZW5kcG9pbnRzIOKAlCBsaXQgbm9kZXMgLS0+CiAgPGcgZmlsdGVyPSJ1cmwoI2dsb3cpIj4KICAgIDxjaXJjbGUgY3g9IjgyIiBjeT0iMzAiIHI9IjIuOCIgZmlsbD0iIzAwZmZlZSIgb3BhY2l0eT0iMC45NSIvPgogICAgPGNpcmNsZSBjeD0iMTEyIiBjeT0iMzAiIHI9IjIuOCIgZmlsbD0iIzAwZTVmZiIgb3BhY2l0eT0iMC45NSIvPgogICAgPGNpcmNsZSBjeD0iNzAiIGN5PSI2NiIgcj0iMy4yIiBmaWxsPSIjMDBmZmVlIi8+CiAgICA8Y2lyY2xlIGN4PSIxMjIiIGN5PSI2NiIgcj0iMy4yIiBmaWxsPSIjMDBlNWZmIi8+CiAgICA8Y2lyY2xlIGN4PSI4NCIgY3k9IjEwMiIgcj0iMi44IiBmaWxsPSIjMDBmZmVlIiBvcGFjaXR5PSIwLjk1Ii8+CiAgICA8Y2lyY2xlIGN4PSIxMTAiIGN5PSIxMDIiIHI9IjIuOCIgZmlsbD0iIzAwZTVmZiIgb3BhY2l0eT0iMC45NSIvPgogICAgPGNpcmNsZSBjeD0iODQiIGN5PSIxMzgiIHI9IjIuOCIgZmlsbD0iIzAwZmZlZSIgb3BhY2l0eT0iMC45Ii8+CiAgICA8Y2lyY2xlIGN4PSIxMDgiIGN5PSIxMzgiIHI9IjIuOCIgZmlsbD0iIzAwZTVmZiIgb3BhY2l0eT0iMC45Ii8+CiAgPC9nPgoKICA8IS0tIE5ldXJhbCBjaXJjdWl0IOKAlCBicmFuY2hlcyBmcm9tIHJ1bmcgbm9kZXMgLS0+CiAgPCEtLSBUb3AgcmlnaHQgY2x1c3RlciAtLT4KICA8ZyBzdHJva2U9IiMwMGU1ZmYiIGZpbGw9Im5vbmUiIG9wYWNpdHk9IjAuNiIgZmlsdGVyPSJ1cmwoI3NvZnRnbG93KSI+CiAgICA8bGluZSB4MT0iMTIyIiB5MT0iNjYiIHgyPSIxNTIiIHkyPSI1MiIgc3Ryb2tlLXdpZHRoPSIxLjQiLz4KICAgIDxsaW5lIHgxPSIxNTIiIHkxPSI1MiIgeDI9IjE3MiIgeTI9IjYyIiBzdHJva2Utd2lkdGg9IjEuMSIvPgogICAgPGxpbmUgeDE9IjE1MiIgeTE9IjUyIiB4Mj0iMTYwIiB5Mj0iMzgiIHN0cm9rZS13aWR0aD0iMS4xIi8+CiAgICA8Y2lyY2xlIGN4PSIxNTIiIGN5PSI1MiIgcj0iMy41IiBmaWxsPSIjMDBlNWZmIiBvcGFjaXR5PSIwLjg1Ii8+CiAgICA8Y2lyY2xlIGN4PSIxNzIiIGN5PSI2MiIgcj0iMi4yIiBmaWxsPSIjMDBlNWZmIiBvcGFjaXR5PSIwLjciLz4KICAgIDxjaXJjbGUgY3g9IjE2MCIgY3k9IjM4IiByPSIyIiBmaWxsPSIjMDBmZmVlIiBvcGFjaXR5PSIwLjY1Ii8+CiAgICA8bGluZSB4MT0iMTcyIiB5MT0iNjIiIHgyPSIxODQiIHkyPSI1NCIgc3Ryb2tlLXdpZHRoPSIwLjgiIG9wYWNpdHk9IjAuNCIvPgogICAgPGNpcmNsZSBjeD0iMTg0IiBjeT0iNTQiIHI9IjEuNSIgZmlsbD0iIzAwZTVmZiIgb3BhY2l0eT0iMC41Ii8+CiAgPC9nPgoKICA8IS0tIFRvcCBsZWZ0IGNsdXN0ZXIgLS0+CiAgPGcgc3Ryb2tlPSIjMDBlNWZmIiBmaWxsPSJub25lIiBvcGFjaXR5PSIwLjU1IiBmaWx0ZXI9InVybCgjc29mdGdsb3cpIj4KICAgIDxsaW5lIHgxPSI3MCIgeTE9IjY2IiB4Mj0iNDIiIHkyPSI1MiIgc3Ryb2tlLXdpZHRoPSIxLjQiLz4KICAgIDxsaW5lIHgxPSI0MiIgeTE9IjUyIiB4Mj0iMjQiIHkyPSI2MiIgc3Ryb2tlLXdpZHRoPSIxLjEiLz4KICAgIDxsaW5lIHgxPSI0MiIgeTE9IjUyIiB4Mj0iMzQiIHkyPSIzNiIgc3Ryb2tlLXdpZHRoPSIxLjEiLz4KICAgIDxjaXJjbGUgY3g9IjQyIiBjeT0iNTIiIHI9IjMuNSIgZmlsbD0iIzAwZTVmZiIgb3BhY2l0eT0iMC44NSIvPgogICAgPGNpcmNsZSBjeD0iMjQiIGN5PSI2MiIgcj0iMi4yIiBmaWxsPSIjMDBmZmVlIiBvcGFjaXR5PSIwLjciLz4KICAgIDxjaXJjbGUgY3g9IjM0IiBjeT0iMzYiIHI9IjIiIGZpbGw9IiMwMGU1ZmYiIG9wYWNpdHk9IjAuNjUiLz4KICA8L2c+CgogIDwhLS0gQm90dG9tIHJpZ2h0IGNsdXN0ZXIgLS0+CiAgPGcgc3Ryb2tlPSIjMDBlNWZmIiBmaWxsPSJub25lIiBvcGFjaXR5PSIwLjUiIGZpbHRlcj0idXJsKCNzb2Z0Z2xvdykiPgogICAgPGxpbmUgeDE9IjEwOCIgeTE9IjEzOCIgeDI9IjE0MCIgeTI9IjE1MiIgc3Ryb2tlLXdpZHRoPSIxLjQiLz4KICAgIDxsaW5lIHgxPSIxNDAiIHkxPSIxNTIiIHgyPSIxNTgiIHkyPSIxNDQiIHN0cm9rZS13aWR0aD0iMS4xIi8+CiAgICA8bGluZSB4MT0iMTQwIiB5MT0iMTUyIiB4Mj0iMTQ4IiB5Mj0iMTY4IiBzdHJva2Utd2lkdGg9IjEuMSIvPgogICAgPGNpcmNsZSBjeD0iMTQwIiBjeT0iMTUyIiByPSIzLjUiIGZpbGw9IiMwMGU1ZmYiIG9wYWNpdHk9IjAuOCIvPgogICAgPGNpcmNsZSBjeD0iMTU4IiBjeT0iMTQ0IiByPSIyLjIiIGZpbGw9IiMwMGZmZWUiIG9wYWNpdHk9IjAuNjUiLz4KICAgIDxjaXJjbGUgY3g9IjE0OCIgY3k9IjE2OCIgcj0iMiIgZmlsbD0iIzAwZTVmZiIgb3BhY2l0eT0iMC42Ii8+CiAgPC9nPgoKICA8IS0tIEJvdHRvbSBsZWZ0IGNsdXN0ZXIgLS0+CiAgPGcgc3Ryb2tlPSIjMDBlNWZmIiBmaWxsPSJub25lIiBvcGFjaXR5PSIwLjUiIGZpbHRlcj0idXJsKCNzb2Z0Z2xvdykiPgogICAgPGxpbmUgeDE9Ijg0IiB5MT0iMTM4IiB4Mj0iNTQiIHkyPSIxNTIiIHN0cm9rZS13aWR0aD0iMS40Ii8+CiAgICA8bGluZSB4MT0iNTQiIHkxPSIxNTIiIHgyPSIzNiIgeTI9IjE0NCIgc3Ryb2tlLXdpZHRoPSIxLjEiLz4KICAgIDxjaXJjbGUgY3g9IjU0IiBjeT0iMTUyIiByPSIzLjUiIGZpbGw9IiMwMGU1ZmYiIG9wYWNpdHk9IjAuOCIvPgogICAgPGNpcmNsZSBjeD0iMzYiIGN5PSIxNDQiIHI9IjIuMiIgZmlsbD0iIzAwZmZlZSIgb3BhY2l0eT0iMC42NSIvPgogIDwvZz4KCiAgPCEtLSBDZW50cmFsIHB1bHNlIOKAlCBpbnRlbGxpZ2VuY2UgY29yZSAtLT4KICA8Y2lyY2xlIGN4PSI5NyIgY3k9Ijk2IiByPSIxMCIgZmlsbD0iIzAwZTVmZiIgb3BhY2l0eT0iMC4wNiIvPgogIDxjaXJjbGUgY3g9Ijk3IiBjeT0iOTYiIHI9IjYiICBmaWxsPSIjMDBmZmVlIiBvcGFjaXR5PSIwLjE1Ii8+CiAgPGNpcmNsZSBjeD0iOTciIGN5PSI5NiIgcj0iMyIgIGZpbGw9IiNmZmZmZmYiIG9wYWNpdHk9IjAuODUiIGZpbHRlcj0idXJsKCNnbG93KSIvPgoKICA8IS0tIENyb3NzaGFpciBhdCBjZW50cmUgLS0+CiAgPGcgc3Ryb2tlPSIjMDBlNWZmIiBzdHJva2Utd2lkdGg9IjAuNiIgb3BhY2l0eT0iMC4zIj4KICAgIDxsaW5lIHgxPSI5NyIgeTE9Ijg4IiB4Mj0iOTciIHkyPSI5MiIvPgogICAgPGxpbmUgeDE9Ijk3IiB5MT0iMTAwIiB4Mj0iOTciIHkyPSIxMDQiLz4KICAgIDxsaW5lIHgxPSI4OSIgeTE9Ijk2IiB4Mj0iOTMiIHkyPSI5NiIvPgogICAgPGxpbmUgeDE9IjEwMSIgeTE9Ijk2IiB4Mj0iMTA1IiB5Mj0iOTYiLz4KICA8L2c+Cjwvc3ZnPg=="
LOGO_MIME = "image/svg+xml"
LOGO_SVG_RAW = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <radialGradient id="bg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#001a2e" stop-opacity="0.6"/>
      <stop offset="100%" stop-color="#000508" stop-opacity="0"/>
    </radialGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="2.5" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="softglow">
      <feGaussianBlur stdDeviation="1.5" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <linearGradient id="helix1" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#00ffee"/>
      <stop offset="40%" stop-color="#00e5ff"/>
      <stop offset="100%" stop-color="#0055cc"/>
    </linearGradient>
    <linearGradient id="helix2" x1="0%" y1="100%" x2="0%" y2="0%">
      <stop offset="0%" stop-color="#00ffee"/>
      <stop offset="40%" stop-color="#00c8ff"/>
      <stop offset="100%" stop-color="#0044aa"/>
    </linearGradient>
    <linearGradient id="nodeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="100%" stop-color="#00e5ff"/>
    </linearGradient>
  </defs>

  <!-- Outer ring -->
  <circle cx="100" cy="100" r="90" fill="none" stroke="#00e5ff" stroke-width="0.6" opacity="0.15"/>
  <circle cx="100" cy="100" r="75" fill="none" stroke="#00e5ff" stroke-width="0.4" opacity="0.1"/>
  <circle cx="100" cy="100" r="92" fill="url(#bg)"/>

  <!-- Tick marks on outer ring -->
  <g stroke="#00e5ff" stroke-width="0.8" opacity="0.25">
    <line x1="100" y1="10" x2="100" y2="18"/>
    <line x1="100" y1="182" x2="100" y2="190"/>
    <line x1="10" y1="100" x2="18" y2="100"/>
    <line x1="182" y1="100" x2="190" y2="100"/>
    <line x1="36" y1="36" x2="41" y2="41"/>
    <line x1="159" y1="36" x2="164" y2="41"/>
    <line x1="36" y1="164" x2="41" y2="159"/>
    <line x1="159" y1="164" x2="164" y2="159"/>
  </g>

  <!-- DNA strand A — sinusoidal path left -->
  <path d="M 82 22 C 60 40, 68 58, 86 72 C 104 86, 112 104, 92 120 C 72 136, 76 156, 88 174"
        fill="none" stroke="url(#helix1)" stroke-width="3.5" stroke-linecap="round"
        filter="url(#glow)" opacity="0.95"/>

  <!-- DNA strand B — opposite phase -->
  <path d="M 112 22 C 134 40, 126 58, 108 72 C 90 86, 82 104, 102 120 C 122 136, 118 156, 106 174"
        fill="none" stroke="url(#helix2)" stroke-width="3.5" stroke-linecap="round"
        filter="url(#glow)" opacity="0.95"/>

  <!-- Rungs — precise at wave intersections -->
  <g filter="url(#softglow)" opacity="0.9">
    <line x1="82" y1="30" x2="112" y2="30" stroke="#00ffee" stroke-width="2" stroke-linecap="round"/>
    <line x1="74" y1="48" x2="118" y2="48" stroke="#00e5ff" stroke-width="1.8" stroke-linecap="round" opacity="0.7"/>
    <line x1="70" y1="66" x2="122" y2="66" stroke="#00ffee" stroke-width="2.2" stroke-linecap="round"/>
    <line x1="74" y1="84" x2="118" y2="84" stroke="#00e5ff" stroke-width="1.8" stroke-linecap="round" opacity="0.7"/>
    <line x1="84" y1="102" x2="110" y2="102" stroke="#00ffee" stroke-width="2" stroke-linecap="round"/>
    <line x1="86" y1="120" x2="108" y2="120" stroke="#00e5ff" stroke-width="1.8" stroke-linecap="round" opacity="0.7"/>
    <line x1="84" y1="138" x2="108" y2="138" stroke="#00ffee" stroke-width="2" stroke-linecap="round"/>
    <line x1="88" y1="156" x2="106" y2="156" stroke="#00e5ff" stroke-width="1.8" stroke-linecap="round" opacity="0.7"/>
  </g>

  <!-- Rung endpoints — lit nodes -->
  <g filter="url(#glow)">
    <circle cx="82" cy="30" r="2.8" fill="#00ffee" opacity="0.95"/>
    <circle cx="112" cy="30" r="2.8" fill="#00e5ff" opacity="0.95"/>
    <circle cx="70" cy="66" r="3.2" fill="#00ffee"/>
    <circle cx="122" cy="66" r="3.2" fill="#00e5ff"/>
    <circle cx="84" cy="102" r="2.8" fill="#00ffee" opacity="0.95"/>
    <circle cx="110" cy="102" r="2.8" fill="#00e5ff" opacity="0.95"/>
    <circle cx="84" cy="138" r="2.8" fill="#00ffee" opacity="0.9"/>
    <circle cx="108" cy="138" r="2.8" fill="#00e5ff" opacity="0.9"/>
  </g>

  <!-- Neural circuit — branches from rung nodes -->
  <!-- Top right cluster -->
  <g stroke="#00e5ff" fill="none" opacity="0.6" filter="url(#softglow)">
    <line x1="122" y1="66" x2="152" y2="52" stroke-width="1.4"/>
    <line x1="152" y1="52" x2="172" y2="62" stroke-width="1.1"/>
    <line x1="152" y1="52" x2="160" y2="38" stroke-width="1.1"/>
    <circle cx="152" cy="52" r="3.5" fill="#00e5ff" opacity="0.85"/>
    <circle cx="172" cy="62" r="2.2" fill="#00e5ff" opacity="0.7"/>
    <circle cx="160" cy="38" r="2" fill="#00ffee" opacity="0.65"/>
    <line x1="172" y1="62" x2="184" y2="54" stroke-width="0.8" opacity="0.4"/>
    <circle cx="184" cy="54" r="1.5" fill="#00e5ff" opacity="0.5"/>
  </g>

  <!-- Top left cluster -->
  <g stroke="#00e5ff" fill="none" opacity="0.55" filter="url(#softglow)">
    <line x1="70" y1="66" x2="42" y2="52" stroke-width="1.4"/>
    <line x1="42" y1="52" x2="24" y2="62" stroke-width="1.1"/>
    <line x1="42" y1="52" x2="34" y2="36" stroke-width="1.1"/>
    <circle cx="42" cy="52" r="3.5" fill="#00e5ff" opacity="0.85"/>
    <circle cx="24" cy="62" r="2.2" fill="#00ffee" opacity="0.7"/>
    <circle cx="34" cy="36" r="2" fill="#00e5ff" opacity="0.65"/>
  </g>

  <!-- Bottom right cluster -->
  <g stroke="#00e5ff" fill="none" opacity="0.5" filter="url(#softglow)">
    <line x1="108" y1="138" x2="140" y2="152" stroke-width="1.4"/>
    <line x1="140" y1="152" x2="158" y2="144" stroke-width="1.1"/>
    <line x1="140" y1="152" x2="148" y2="168" stroke-width="1.1"/>
    <circle cx="140" cy="152" r="3.5" fill="#00e5ff" opacity="0.8"/>
    <circle cx="158" cy="144" r="2.2" fill="#00ffee" opacity="0.65"/>
    <circle cx="148" cy="168" r="2" fill="#00e5ff" opacity="0.6"/>
  </g>

  <!-- Bottom left cluster -->
  <g stroke="#00e5ff" fill="none" opacity="0.5" filter="url(#softglow)">
    <line x1="84" y1="138" x2="54" y2="152" stroke-width="1.4"/>
    <line x1="54" y1="152" x2="36" y2="144" stroke-width="1.1"/>
    <circle cx="54" cy="152" r="3.5" fill="#00e5ff" opacity="0.8"/>
    <circle cx="36" cy="144" r="2.2" fill="#00ffee" opacity="0.65"/>
  </g>

  <!-- Central pulse — intelligence core -->
  <circle cx="97" cy="96" r="10" fill="#00e5ff" opacity="0.06"/>
  <circle cx="97" cy="96" r="6"  fill="#00ffee" opacity="0.15"/>
  <circle cx="97" cy="96" r="3"  fill="#ffffff" opacity="0.85" filter="url(#glow)"/>

  <!-- Crosshair at centre -->
  <g stroke="#00e5ff" stroke-width="0.6" opacity="0.3">
    <line x1="97" y1="88" x2="97" y2="92"/>
    <line x1="97" y1="100" x2="97" y2="104"/>
    <line x1="89" y1="96" x2="93" y2="96"/>
    <line x1="101" y1="96" x2="105" y2="96"/>
  </g>
</svg>"""

_logo_src = f"data:image/svg+xml;base64,{LOGO_B64}"

# ─── CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:wght@400;500&display=swap');

/* ── Root tokens ─────────────────────────────────────────────── */
:root {
  --bg:      #080c12;
  --bg2:     #0d1219;
  --bg3:     #111720;
  --surface: #141b25;
  --border:  #1e2d3f;
  --border2: #243448;
  --text:    #dce8f5;
  --text2:   #8da8bf;
  --text3:   #4a6478;
  --cyan:    #00d4e8;
  --cyan2:   #38e8f8;
  --green:   #1db87a;
  --rose:    #f0385a;
  --amber:   #e8a020;
  --violet:  #8b6cf7;
  --r:       10px;
}

/* ── Base ────────────────────────────────────────────────────── */
html,body,[class*="css"] {
  font-family: 'DM Sans', system-ui, sans-serif !important;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text) !important;
}
.stApp { background: var(--bg) !important; }

/* ── Sidebar ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: var(--bg2) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text2) !important; }
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stTextArea textarea {
  background: var(--bg3) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: 8px !important;
  font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
  background: var(--bg3) !important;
  border-color: var(--border) !important;
  color: var(--text) !important;
}

/* ── Header bar ──────────────────────────────────────────────── */
.ph {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: .9rem 1.5rem .8rem;
  margin-bottom: .6rem;
  display: flex; align-items: center; gap: 14px;
}
.ph::after { display:none; }
.pt {
  font-size: 1.5rem; font-weight: 700; letter-spacing: -.4px; margin: 0;
  color: var(--text);
  background: none; -webkit-text-fill-color: unset;
  animation: none;
}
.pt span { color: var(--cyan); }
.ps { color: var(--text3); font-size: .82rem; margin: 1px 0 0; }

/* ── Verdict banners ─────────────────────────────────────────── */
.pursue-yes {
  background: rgba(240,56,90,.06);
  border: 1.5px solid rgba(240,56,90,.35);
  border-radius: var(--r); padding: 1rem 1.3rem;
  margin-bottom: .7rem; display: flex; gap: 12px; align-items: flex-start;
}
.pursue-no {
  background: rgba(30,45,63,.3);
  border: 1.5px dashed var(--border2);
  border-radius: var(--r); padding: 1rem 1.3rem;
  margin-bottom: .7rem; display: flex; gap: 12px; align-items: flex-start;
}
.pursue-caution {
  background: rgba(232,160,32,.06);
  border: 1.5px solid rgba(232,160,32,.35);
  border-radius: var(--r); padding: 1rem 1.3rem;
  margin-bottom: .7rem; display: flex; gap: 12px; align-items: flex-start;
}

/* ── Metric cards ────────────────────────────────────────────── */
.mc {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r); padding: .9rem 1rem; text-align: center;
  position: relative; overflow: hidden; transition: border-color .2s, transform .2s;
}
.mc::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; background: var(--acc, var(--cyan)); }
.mc:hover { border-color: var(--border2); transform: translateY(-2px); }
.mv { font-size: 1.75rem; font-weight: 700; line-height: 1.1; color: var(--clr, var(--cyan)); font-family: 'DM Mono', monospace; }
.ml2 { font-size: .68rem; color: var(--text3); margin-top: 3px; text-transform: uppercase; letter-spacing: .8px; font-weight: 500; }

/* ── Cards ───────────────────────────────────────────────────── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r); padding: 1rem 1.3rem; margin-bottom: .6rem;
}
.card h4 { color: var(--cyan); font-size: .92rem; font-weight: 600; margin: 0 0 .4rem; }
.card p { color: var(--text2); font-size: .84rem; line-height: 1.65; margin: 0; }

/* ── Badges ──────────────────────────────────────────────────── */
.badge { display:inline-block; padding:2px 9px; border-radius:5px; font-size:.72rem; font-weight:700; font-family:'DM Mono',monospace; }
.bC { background:rgba(240,56,90,.12); color:#f0385a; border:1px solid rgba(240,56,90,.3); }
.bH { background:rgba(232,160,32,.1);  color:#e8a020; border:1px solid rgba(232,160,32,.3); }
.bM { background:rgba(232,160,32,.07); color:#c89020; border:1px solid rgba(232,160,32,.2); }
.bN { background:rgba(74,100,120,.15); color:var(--text3); border:1px solid var(--border); }

/* ── Tabs ────────────────────────────────────────────────────── */
.stTabs { position: sticky; top: 0; z-index: 100; background: var(--bg); padding-top: 2px; }
.stTabs [data-baseweb="tab-list"] {
  background: var(--bg) !important;
  gap: 2px; border-bottom: 1px solid var(--border);
  overflow: hidden !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent; border-radius: 6px 6px 0 0;
  padding: 6px 14px; color: var(--text3) !important;
  font-weight: 500; font-size: .82rem;
  letter-spacing: .01em;
}
.stTabs [aria-selected="true"] {
  background: var(--bg2) !important;
  color: var(--cyan) !important;
  border-bottom: 2px solid var(--cyan) !important;
  font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-highlight"] { transition: none !important; }

/* ── Section headers ─────────────────────────────────────────── */
.sh2 {
  display: flex; align-items: center; gap: 8px;
  margin: 0 0 .7rem; padding-bottom: 5px;
  border-bottom: 1px solid var(--border);
}
.sh2 h3 { color: var(--text); font-size: .92rem; font-weight: 600; margin: 0; }

/* ── Dividers / utilities ────────────────────────────────────── */
.dv { border: none; border-top: 1px solid var(--border); margin: 1rem 0; }
.cite { border-left: 2px solid rgba(0,212,232,.2); padding:5px 10px; margin:3px 0; background:var(--bg3); border-radius:0 6px 6px 0; }
.cite a { color: var(--text3); text-decoration: none; font-size: .84rem; }
.cite a:hover { color: var(--cyan); }
.cm { color: var(--text3); font-size: .84rem; margin-top: 1px; }
.src-badge {
  display:inline-block; background:var(--bg3); border:1px solid var(--border2);
  color: var(--text3); padding:1px 8px; border-radius:5px;
  font-size:.75rem; margin-left:5px; text-decoration:none; font-family:'DM Mono',monospace;
}
.src-badge:hover { border-color: var(--cyan); color: var(--cyan); }
.plain { color: var(--text3); font-size: .84rem; font-style: italic; }

/* ── Table ───────────────────────────────────────────────────── */
.pt2 { width:100%; border-collapse:collapse; font-size:.82rem; }
.pt2 thead tr { background: var(--bg2); }
.pt2 th { color: var(--text3); padding:8px 12px; text-align:left; font-size:.72rem; font-weight:600; text-transform:uppercase; letter-spacing:.8px; border-bottom:1px solid var(--border); }
.pt2 td { padding:8px 12px; border-bottom:1px solid var(--border); color:var(--text2); vertical-align:middle; }
.pt2 tr:hover td { background: var(--bg3); }

/* ── Sidebar labels ──────────────────────────────────────────── */
.sb-t {
  font-size:.68rem; font-weight:600; color:var(--text3);
  text-transform:uppercase; letter-spacing:1px;
  margin:.8rem 0 .3rem; padding-bottom:3px; border-bottom:1px solid var(--border);
}

/* ── Inputs ──────────────────────────────────────────────────── */
.stTextInput input, .stTextArea textarea {
  background: var(--bg3) !important; border:1px solid var(--border) !important;
  color: var(--text) !important; border-radius:8px !important;
  font-family:'DM Sans',sans-serif !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--cyan) !important; outline: none !important;
  box-shadow: 0 0 0 2px rgba(0,212,232,.1) !important;
}
details { border:1px solid var(--border) !important; border-radius:8px !important; background:var(--bg3) !important; }

/* ── GI verdict classes ──────────────────────────────────────── */
.gi-critical  { background:rgba(240,56,90,.05); border:1.5px solid rgba(240,56,90,.3); border-radius:var(--r); padding:1rem 1.3rem; margin-bottom:.6rem; }
.gi-moderate  { background:rgba(232,160,32,.05); border:1.5px solid rgba(232,160,32,.3); border-radius:var(--r); padding:1rem 1.3rem; margin-bottom:.6rem; }
.gi-redundant { background:var(--bg3); border:1px dashed var(--border2); border-radius:var(--r); padding:1rem 1.3rem; margin-bottom:.6rem; }
.gi-unknown   { background:var(--bg3); border:1px solid var(--border); border-radius:var(--r); padding:1rem 1.3rem; margin-bottom:.6rem; }
.gi-stat { display:inline-block; background:var(--bg3); border:1px solid var(--border); border-radius:6px; padding:3px 9px; margin:2px; font-size:.75rem; color:var(--text2); font-family:'DM Mono',monospace; }

/* ── Misc cards ──────────────────────────────────────────────── */
.dis-row { display:flex; align-items:flex-start; gap:10px; background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:9px 12px; margin:3px 0; }
.dis-name { color:var(--text); font-size:.84rem; font-weight:600; }
.dis-desc { color:var(--text2); font-size:.8rem; margin-top:2px; line-height:1.5; }
.gpcr-box { background:var(--bg3); border:1px solid rgba(0,212,232,.2); border-radius:var(--r); padding:1rem 1.3rem; color:var(--text2); }
.cascade-stage { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:.8rem 1rem; margin:.4rem 0; }
.cascade-stage h5 { color:var(--cyan); font-size:.82rem; font-weight:600; margin:0 0 3px; }
.cascade-stage p { color:var(--text2); font-size:.8rem; margin:0; line-height:1.5; }
.bias-warn { background:var(--bg3); border:1px solid rgba(240,56,90,.2); border-radius:8px; padding:.8rem 1.1rem; margin:.6rem 0; }
.bias-warn p { color:var(--text2); font-size:.8rem; margin:0; line-height:1.6; }
.dis-protein-row { display:flex; align-items:center; gap:10px; background:var(--surface); border:1px solid var(--border); border-radius:7px; padding:7px 12px; margin:3px 0; transition:border-color .2s; }
.dis-protein-row:hover { border-color: var(--border2); }

/* ── Buttons ─────────────────────────────────────────────────── */
.stButton > button {
  background: var(--bg3) !important;
  color: var(--cyan) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 7px !important;
  font-weight: 600 !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: .82rem !important;
  transition: all .18s !important;
}
.stButton > button:hover {
  border-color: var(--cyan) !important;
  background: rgba(0,212,232,.06) !important;
  box-shadow: 0 2px 12px rgba(0,212,232,.1) !important;
}
.stButton > button[kind="primary"] {
  background: rgba(0,212,232,.08) !important;
  border-color: rgba(0,212,232,.4) !important;
}
.stDownloadButton > button {
  background: rgba(29,184,122,.08) !important;
  color: var(--green) !important;
  border: 1px solid rgba(29,184,122,.3) !important;
  border-radius: 7px !important; font-weight: 600 !important;
}
.stDownloadButton > button:hover { box-shadow: 0 2px 12px rgba(29,184,122,.15) !important; }

/* ── Logo ────────────────────────────────────────────────────── */
.proto-logo { display:block; margin:0 auto 4px; width:48px; height:48px; object-fit:contain; }
.proto-logo-sm { display:inline-block; width:24px; height:24px; object-fit:contain; vertical-align:middle; margin-right:7px; }
.proto-logo-header { display:inline-block; width:40px; height:40px; object-fit:contain; vertical-align:middle; margin-right:10px; }

/* ── Tutorial ────────────────────────────────────────────────── */
.tutorial-overlay { background:var(--bg2); border:1px solid var(--border); border-radius:var(--r); padding:1.4rem 1.8rem; }
.tut-step { background:var(--bg3); border:1px solid var(--border); border-radius:8px; padding:.8rem 1rem; margin:.4rem 0; }
.tut-step h4 { color:var(--cyan); font-size:.9rem; margin:0 0 .25rem; font-weight:600; }
.tut-step p { color:var(--text2); font-size:.82rem; margin:0; line-height:1.5; }
.tut-num { display:inline-flex; align-items:center; justify-content:center; background:var(--cyan); color:var(--bg); border-radius:50%; width:20px; height:20px; font-weight:700; font-size:.75rem; margin-right:8px; flex-shrink:0; }

/* ── Animations ──────────────────────────────────────────────── */
@keyframes fadeInUp { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
@keyframes slideInLeft { from{opacity:0;transform:translateX(-12px)} to{opacity:1;transform:translateX(0)} }
@keyframes pulseGlow { 0%,100%{box-shadow:0 0 0 rgba(0,212,232,0)} 50%{box-shadow:0 0 16px rgba(0,212,232,.15)} }
.mc { animation: fadeInUp .45s ease both; }
.mc:nth-child(1){animation-delay:.04s} .mc:nth-child(2){animation-delay:.08s}
.mc:nth-child(3){animation-delay:.12s} .mc:nth-child(4){animation-delay:.16s}
.mc:nth-child(5){animation-delay:.20s} .mc:nth-child(6){animation-delay:.24s}
.dis-row { animation: fadeInUp .3s ease both; }
.card { animation: fadeInUp .35s ease both; }
.sh2 { animation: slideInLeft .3s ease both; }

/* ── Domain selection cards ──────────────────────────────────── */
[data-testid="stHorizontalBlock"] .stButton > button {
  white-space: pre-line !important;
  min-height: 80px !important; height: auto !important;
  text-align: left !important; padding: 13px 16px !important;
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  font-size: .82rem !important; line-height: 1.55 !important;
  font-weight: 500 !important; transition: all .2s ease !important;
  width: 100% !important; color: var(--text2) !important;
}
[data-testid="stHorizontalBlock"] .stButton > button:hover {
  border-color: rgba(0,212,232,.35) !important;
  background: var(--bg3) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 4px 20px rgba(0,212,232,.07) !important;
  color: var(--text) !important;
}

</style>
""", unsafe_allow_html=True)

# ─── Constants ─────────────────────────────────────────────────────
SIG_SCORE = {
    "pathogenic":5,"likely pathogenic":4,"pathogenic/likely pathogenic":4,
    "risk factor":3,"uncertain significance":2,"conflicting interpretations":2,
    "conflicting interpretations of pathogenicity":2,"likely benign":1,
    "benign":0,"benign/likely benign":0,"not provided":-1,"not classified":-1,
    # ClinVar numeric codes (internal API values)
    "4":5,"3":4,"3/4":4,"5":3,"2":2,"1":1,"0":0,
}

# Human-readable labels for chart display
SIG_LABEL = {
    "pathogenic":                              "Disease-causing (Pathogenic)",
    "likely pathogenic":                       "Likely Disease-causing",
    "pathogenic/likely pathogenic":            "Pathogenic / Likely Path.",
    "risk factor":                             "Risk Factor",
    "uncertain significance":                  "Unknown Significance (VUS)",
    "conflicting interpretations":             "Conflicting Evidence",
    "conflicting interpretations of pathogenicity": "Conflicting Evidence",
    "likely benign":                           "Likely Harmless (Likely Benign)",
    "benign":                                  "Harmless (Benign)",
    "benign/likely benign":                    "Benign / Likely Benign",
    "not provided":                            "Not Classified",
    "not classified":                          "Not Classified",
    # Numeric code fallbacks
    "4":"Likely Disease-causing","3/4":"Pathogenic/LP","5":"Risk Factor",
    "2":"Unknown Significance","1":"Likely Harmless","0":"Harmless",
}

def clean_sig(raw):
    """Normalise raw ClinVar significance string."""
    s = str(raw).strip()
    return SIG_LABEL.get(s.lower(), s.title() if len(s) > 2 else "Not Classified")
AA_HYDRO  = {"A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,"G":-0.4,
             "H":-3.2,"I":4.5,"L":3.8,"K":-3.9,"M":1.9,"F":2.8,"P":-1.6,"S":-0.8,
             "T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2,"*":-10}
AA_CHG    = {"R":1,"K":1,"H":.5,"D":-1,"E":-1}
AA_NAMES  = {"A":"Alanine","R":"Arginine","N":"Asparagine","D":"Aspartate","C":"Cysteine",
             "Q":"Glutamine","E":"Glutamate","G":"Glycine","H":"Histidine","I":"Isoleucine",
             "L":"Leucine","K":"Lysine","M":"Methionine","F":"Phenylalanine","P":"Proline",
             "S":"Serine","T":"Threonine","W":"Tryptophan","Y":"Tyrosine","V":"Valine"}
RANK_CLR  = {"CRITICAL":"#ff2d55","HIGH":"#ff8c42","MEDIUM":"#ffd60a","NEUTRAL":"#3a5a7a"}
RANK_CSS  = {"CRITICAL":"bC","HIGH":"bH","MEDIUM":"bM","NEUTRAL":"bN"}
ESEARCH   = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# Plain-language term pairs
PLAIN = {
    "apoptosis":"cell death (apoptosis)","phosphorylation":"chemical tagging (phosphorylation)",
    "haploinsufficiency":"half-dose shortage (haploinsufficiency)",
    "missense":"letter-swap mutation (missense)","nonsense":"early-stop mutation (stop-gain)",
    "frameshift":"reading-frame shift (frameshift)","splice":"splice-site disruption",
    "dominant negative":"protein blocker (dominant-negative)","gain of function":"hyperactive mutation (gain-of-function)",
    "loss of function":"broken gene (loss-of-function)","germline":"heritable / born-with (germline)",
    "somatic":"acquired / developed (somatic)","heterozygous":"one-copy affected (heterozygous)",
    "homozygous":"both-copies affected (homozygous)","GPCR":"cell-surface signal receiver (GPCR)",
    "second messenger":"internal signal relay (second messenger)","G-protein":"signal relay switch (G-protein)",
    "kinase":"protein tagger/activator (kinase)","phenotype":"observable trait (phenotype)",
    "pathogenic":"disease-causing (pathogenic)","benign":"harmless variant (benign)",
    "VUS":"unknown-significance variant (VUS)","variant":"DNA spelling change (variant)",
}

GOAL_OPTIONS = ["🎯 Identify therapeutic targets","🔬 Understand disease mechanism",
                "💊 Drug discovery & development","📊 Biomarker identification",
                "🧬 Basic research / functional characterisation",
                "🧪 Experimental pathway prioritisation","📋 Clinical variant interpretation",
                "✏️ Custom goal (type below)"]

def p(term): return PLAIN.get(term, term)
def badge(rank): return f"<span class='badge {RANK_CSS.get(rank,'bN')}'>{rank}</span>"
def sh(icon, title): st.markdown(f"<div class='sh2'><span style='font-size:1.1rem'>{icon}</span><h3>{title}</h3></div>", unsafe_allow_html=True)
def mc(val, label, clr="#00e5ff", acc=None):
    a = acc or f"linear-gradient(90deg,{clr},{clr}88)"
    return f"<div class='mc' style='--clr:{clr};--acc:{a};'><div class='mv'>{val}</div><div class='ml2'>{label}</div></div>"
def src_link(label, url): return f"<a class='src-badge' style='color:#6ab8d0;' href='{url}' target='_blank'>↗ {label}</a>"
def score_rank(s, sens=50):
    shift=(sens-50)/100
    if s>=5: return "CRITICAL"
    if s>=4-shift: return "HIGH"
    if s>=2-shift: return "MEDIUM"
    return "NEUTRAL"
# ── Protellect M
