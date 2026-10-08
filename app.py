from __future__ import annotations
# ═══════════════════════════════════════════════════════════════════
#  Protellect v6 — single-file, no local imports
#  All new: pursue banner · disease→proteins · GPCR detail ·
#           genomic visual · mutation cascade · source links ·
#           plain-language terms · CSV standalone · fixed empty sections
# ═══════════════════════════════════════════════════════════════════

import os, re, time, json, math, io
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
# ── Protellect modules (extracted for modularity) ──
from protellect_data import *  # all fetch_* data-source functions
from protellect_citations import PROTELLECT_CITATIONS, cite
from protellect_icons import SVG_ICONS, svg_icon, _auto_icon_name

import streamlit.components.v1 as components

# ─── Authentication & Workspace Configuration ──────────────────────────────────
import hashlib, json, time
from datetime import datetime

# Simple built-in auth (no external library needed — avoids import errors)
def _hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# Credentials resolver — reads from st.secrets in production, falls back to a
# single demo account for local/preview use. NEVER hardcode real passwords here.
#
# To set production credentials, add a [credentials] block to Streamlit secrets:
#   [credentials]
#   "protellect@gmail.com" = "your-new-strong-password"
#   "demo@protellect.com"  = "some-demo-password"
# (plus optional [credential_plans] mapping email -> "free"/"pro"/"enterprise")
def _get_credentials():
    if "_credentials" not in st.session_state:
        creds = {}
        # 1) Load from st.secrets if present
        try:
            if hasattr(st, "secrets") and "credentials" in st.secrets:
                _plans = {}
                try:
                    _plans = dict(st.secrets.get("credential_plans", {}) or {})
                except Exception:
                    _plans = {}
                for email, pw in dict(st.secrets["credentials"]).items():
                    plan = _plans.get(email, "pro")
                    limit = {"free":5,"pro":200,"enterprise":9999}.get(plan, 200)
                    creds[email.lower()] = {
                        "name": email.split("@")[0].title(),
                        "pw": _hash(str(pw)),
                        "plan": plan,
                        "searches_left": limit,
                    }
        except Exception:
            pass
        # 2) Fallback: a single demo account ONLY if no secrets configured.
        #    This is intentionally weak and free-tier; it grants no sensitive access.
        if not creds:
            creds = {
                "demo@protellect.com": {
                    "name": "Demo User", "pw": _hash("protellect-demo"),
                    "plan": "free", "searches_left": 5,
                },
            }
        st.session_state["_credentials"] = creds
    return st.session_state["_credentials"]

PLAN_LIMITS = {
    "free":       {"searches": 5,    "history": 5,   "excel": False, "ai_report": False, "price_id": None},
    "pro":        {"searches": 200,  "history": 100, "excel": True,  "ai_report": True,  "price_id": "price_pro_monthly"},
    "enterprise": {"searches": 9999, "history": 999, "excel": True,  "ai_report": True,  "price_id": "price_ent_monthly"},
}

STRIPE_LINKS = {
    "pro":        "https://buy.stripe.com/test_pro_placeholder",  # Replace with real Stripe payment link
    "enterprise": "https://buy.stripe.com/test_ent_placeholder",  # Replace with real Stripe payment link
}


def login_page():
    """Full-page login/signup UI."""
    st.markdown("""
    <style>
    .login-wrap{max-width:420px;margin:60px auto 0;padding:2rem 2.5rem;
      background:#020617;border:1px solid #0d2545;border-radius:16px;}
    .login-logo{text-align:center;margin-bottom:1.4rem;}
    .login-title{color:#38bdf8;font-size:1.6rem;font-weight:800;text-align:center;margin-bottom:.3rem;}
    .login-sub{color:#3a6080;font-size:.88rem;text-align:center;margin-bottom:1.4rem;}
    .plan-card{background:#030d1a;border:1px solid #0d2545;border-radius:10px;padding:.9rem;margin:.5rem 0;cursor:pointer;transition:all .2s;}
    .plan-card:hover{border-color:#38bdf844;}
    .plan-free{border-left:3px solid #3a6080;}
    .plan-pro{border-left:3px solid #38bdf8;}
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
                    st.error("Invalid credentials. You can also continue as a guest below.")
            st.markdown(
                "<div style='color:#2a5060;font-size:.8rem;margin-top:.5rem;'>"
                "No account? Use guest access below, or register for a free account.</div>",
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
                "<div style='color:#38bdf8;font-size:1.4rem;font-weight:800;'>$0</div>"
                "<div style='color:#3a6080;font-size:.82rem;'>5 protein analyses · 5 saved · Basic triage · ClinVar + UniProt</div>"
                "</div>"
                "<div style='background:#030d1a;border:1px solid #38bdf833;border-radius:10px;padding:.9rem;margin:.4rem 0;border-left:3px solid #38bdf8;'>"
                "<div style='color:#38bdf8;font-weight:700;'>Pro <span style='color:#ffd60a;font-size:.72rem;'>MOST POPULAR</span></div>"
                "<div style='color:#38bdf8;font-size:1.4rem;font-weight:800;'>$49<span style='color:#3a6080;font-size:.9rem;'>/month</span></div>"
                "<div style='color:#3a6080;font-size:.82rem;'>200 analyses/month · Full history · Excel export · AI report · gnomAD + OpenTargets + AlphaMissense + STRING</div>"
                f"<a href='{STRIPE_LINKS['pro']}' target='_blank' style='display:inline-block;margin-top:.5rem;background:#38bdf8;color:#000;font-weight:700;padding:4px 18px;border-radius:8px;font-size:.82rem;text-decoration:none;'>Upgrade to Pro</a>"
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
    ws = (st.session_state.get("workspace") or [])
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


import base64 as _b64_pre
import io as _io_pre
try:
    from PIL import Image as _PIL_pre
except Exception:
    _PIL_pre = None

# Logo for favicon — actual full base64 lives at LOGO_B64 below; we need a
# minimal copy here because set_page_config MUST be the first Streamlit call.
# We import the full base64 string by re-reading this file's source.
_PAGE_ICON = "🧬"  # fallback emoji
try:
    if _PIL_pre is not None:
        # Pull LOGO_B64 from the source file itself (it's defined later in this file).
        import os as _os_pre
        _this_file = __file__ if "__file__" in dir() else None
        if _this_file and _os_pre.path.exists(_this_file):
            with open(_this_file, "r", encoding="utf-8", errors="ignore") as _fh:
                _src = _fh.read()
            import re as _re_pre
            _m_logo = _re_pre.search(r'^LOGO_B64\s*=\s*"([^"]+)"', _src, _re_pre.MULTILINE)
            if _m_logo:
                _bytes = _b64_pre.b64decode(_m_logo.group(1))
                _PAGE_ICON = _PIL_pre.open(_io_pre.BytesIO(_bytes))
except Exception:
    _PAGE_ICON = "🧬"

st.set_page_config(page_title="Protellect", page_icon=_PAGE_ICON,
                   layout="wide", initial_sidebar_state="expanded")

# ── protellect_core: version guard + imports (a clear message instead of a cryptic ImportError) ──────────────────
_PC_NEED = "2"
_PC_OK, _PC_ERR = True, ""
try:
    import protellect_core as _pc
    if str(_pc.__version__).split(".")[0] != _PC_NEED:
        raise ImportError(f"found version {_pc.__version__}, need {_PC_NEED}.x")
    from protellect_core.views.shell import build_analysis as _build_analysis
    from protellect_core.views.banner import render_priority_banner as _render_priority_banner
    from protellect_core.views.sidebar import render_context_sidebar as _render_context_sidebar
    from protellect_core.views.overview import render_overview as _render_overview
    from protellect_core.views.triage import render_triage as _render_triage
    from protellect_core.views.hotspots import render_hotspots as _render_hotspots
    from protellect_core.views.genetics import render_genetics as _render_genetics
    from protellect_core.views.casestudy import render_casestudy as _render_casestudy
    from protellect_core.views.experiments import render_experiments as _render_experiments
    from protellect_core.views.tutorial import tutorial_dialog as _tutorial_dialog
except Exception as _pc_exc:
    _PC_OK, _PC_ERR = False, f"{type(_pc_exc).__name__}: {_pc_exc}"
if not _PC_OK:
    st.error("Protellect cannot start: the `protellect_core` folder is missing or out of date (" + _PC_ERR + "). "
             "Upload the whole `protellect_core` folder from the latest zip next to app.py, replacing any older copy, then reboot the app.")
    st.stop()


def _safe(fn, *args):
    """Run one tab's renderer; a bug in one tab shows a message there and never takes the rest of the app down."""
    try:
        fn(*args)
    except Exception as _e:  # noqa: BLE001
        st.error(f"This section could not be displayed: {type(_e).__name__}: {_e}")


def _am_flat(am):
    """Flatten AlphaMissense data (position -> aa -> {score, class}) to a list of scores."""
    out = []
    for pos in (am or {}).values():
        for a in (pos.values() if isinstance(pos, dict) else [pos]):
            v = a.get("score") if isinstance(a, dict) else a
            if isinstance(v, (int, float)):
                out.append(float(v))
    return out


# ── BUILD BADGE — visible at top-right so we know which version is running ──
# Bright on purpose. Helps verify deploys actually went through.
_BUILD = "2026.05.28-o"
st.markdown(
    f"<div style='position:fixed;top:8px;right:160px;z-index:9999;"
    f"background:#38bdf822;border:1px solid #38bdf8;color:#38bdf8;"
    f"padding:3px 10px;border-radius:6px;font-family:monospace;font-size:.75rem;"
    f"font-weight:700;pointer-events:none;'>build {_BUILD}</div>",
    unsafe_allow_html=True,
)


LOGO_B64 = "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"

_logo_src = f"data:image/png;base64,{LOGO_B64}"

# ─── CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=DM+Mono:wght@400;500&display=swap');

/* ── Root tokens ─────────────────────────────────────────────── */
:root {
  --bg:      #020617;
  --bg2:     #050d24;
  --bg3:     #0a1530;
  --surface: #0f1a36;
  --border:  #1e2a4a;
  --border2: #2a3a5e;
  --text:    #e6edf7;
  --text2:   #94a3b8;
  --text3:   #5b6b80;
  --cyan:    #38bdf8;
  --cyan2:   #7dd3fc;
  --green:   #34d399;
  --rose:    #fb7185;
  --amber:   #fbbf24;
  --violet:  #a78bfa;
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
.bC { background:rgba(240,56,90,.12); color:#fb7185; border:1px solid rgba(240,56,90,.3); }
.bH { background:rgba(232,160,32,.1);  color:#fbbf24; border:1px solid rgba(232,160,32,.3); }
.bM { background:rgba(232,160,32,.07); color:#c89020; border:1px solid rgba(232,160,32,.2); }
.bN { background:rgba(74,100,120,.15); color:var(--text3); border:1px solid var(--border); }

/* ── Tabs ────────────────────────────────────────────────────── */
.stTabs { background: transparent; }
.stTabs [data-baseweb="tab-list"] {
  background: var(--bg) !important;
  gap: 2px; border-bottom: 1px solid var(--border);
  overflow-x: auto;
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

/* ── Scroll: let the app scroll vertically, never trap it ───────────────── */
/* Do NOT force height:auto on stMain — that fights Streamlit's scroll container.
   Only ensure vertical scrolling is allowed and horizontal overflow is clipped. */
html, body {
  overflow-x: hidden;          /* clip sideways bleed */
  overflow-y: auto;            /* but always allow vertical scroll */
  max-width: 100%;
  overscroll-behavior-y: auto; /* don't let any child lock the document scroll */
}
[data-testid="stAppViewContainer"] {
  overflow-x: hidden;
  max-width: 100vw;
}
section[data-testid="stMain"] {
  overflow-y: auto !important; /* the main column scrolls */
  overscroll-behavior-y: auto;
}
/* Zero-height helper iframes must not reserve space or grab the wheel */
iframe[height="0"], iframe[height="0px"] { display: none !important; }
.block-container {
  max-width: 100% !important;
  padding-left: clamp(1rem, 3vw, 3rem) !important;
  padding-right: clamp(1rem, 3vw, 3rem) !important;
  overflow: visible !important;
  padding-bottom: 4rem !important;  /* room past Streamlit "Manage app" badge so last items aren't hidden */
}
/* Long unbreakable strings (DNA sequences, formulas) wrap instead of widening page */
[data-testid="stMarkdownContainer"] div,
[data-testid="stMarkdownContainer"] p {
  overflow-wrap: anywhere;
  word-break: break-word;
}
/* Wide tables get their own scroll, never push the page wide */
[data-testid="stMarkdownContainer"] table { display: block; overflow-x: auto; max-width: 100%; }
/* Component iframes shouldn't trap wheel events when scrolling over them.
   pointer-events:none would also disable clicks, so instead we make sure
   iframes don't reserve more height than declared and don't lock overscroll. */
iframe {
  max-width: 100% !important;
  overscroll-behavior: auto;   /* 'contain' stopped the page scrolling whenever the cursor was over an embedded view */
}
/* st.expander content should expand naturally without an inner scroll container
   that competes with the page scroll on long tabs (Chemistry, Pharma). */
[data-testid="stExpander"] [data-testid="stExpanderDetails"] { overflow: visible !important; }
[data-testid="stExpander"] { overflow: visible !important; }
/* Plotly charts should not lock wheel events (their internal scroll-zoom on hover
   is what makes the page feel "stuck"). */
.js-plotly-plot, .plot-container { overscroll-behavior: auto; }


</style>
""", unsafe_allow_html=True)



AA_HYDRO  = {"A":1.8,"R":-4.5,"N":-3.5,"D":-3.5,"C":2.5,"Q":-3.5,"E":-3.5,"G":-0.4,
             "H":-3.2,"I":4.5,"L":3.8,"K":-3.9,"M":1.9,"F":2.8,"P":-1.6,"S":-0.8,
             "T":-0.7,"W":-0.9,"Y":-1.3,"V":4.2,"*":-10}
AA_CHG    = {"R":1,"K":1,"H":.5,"D":-1,"E":-1}
RANK_CSS  = {"CRITICAL":"bC","HIGH":"bH","MEDIUM":"bM","NEUTRAL":"bN"}

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

GOAL_OPTIONS = [" Identify therapeutic targets"," Understand disease mechanism",
                " Drug discovery & development"," Biomarker identification",
                " Basic research / functional characterisation",
                " Experimental pathway prioritisation"," Clinical variant interpretation",
                " Custom goal (type below)"]

def p(term): return PLAIN.get(term, term)
def badge(rank): return f"<span class='badge {RANK_CSS.get(rank,'bN')}'>{rank}</span>"

# ── Inline SVG icon system (Lucide-style) ────────────────────────────────────



def mc(val, label, clr="#38bdf8", acc=None):
    a = acc or f"linear-gradient(90deg,{clr},{clr}88)"
    return f"<div class='mc' style='--clr:{clr};--acc:{a};'><div class='mv'>{val}</div><div class='ml2'>{label}</div></div>"
def src_link(label, url): return f"<a class='src-badge' style='color:#6ab8d0;' href='{url}' target='_blank'>↗ {label}</a>"
def score_rank(s, sens=50):
    shift=(sens-50)/100
    if s>=5: return "CRITICAL"
    if s>=4-shift: return "HIGH"
    if s>=2-shift: return "MEDIUM"
    return "NEUTRAL"
# ── Protellect ML model (lazy-loaded) ─────────────────────────────────────
import sys as _sys, os as _os
_ML_PACK = None
def _load_ml_model():
    global _ML_PACK
    if _ML_PACK is not None:
        return _ML_PACK
    # Try to load trained model from several possible paths
    import joblib
    for path in [
        _os.path.join(_os.path.dirname(_os.path.abspath(__file__ if "__file__" in dir() else ".")), "protellect_ml", "models", "protellect_variant_clf.pkl"),
        "/mount/src/protellect/protellect_ml/models/protellect_variant_clf.pkl",
        _os.path.join(_os.getcwd(), "protellect_ml", "models", "protellect_variant_clf.pkl"),
    ]:
        if _os.path.exists(path):
            try:
                _ML_PACK = joblib.load(path)
                return _ML_PACK
            except Exception:
                pass
    return None

def score_variant_ml(
    consequence: str = "missense",
    clinvar_stars: int = 0,
    pli: float = 0.5,
    cv_density: float = 0.0,
    gnomad_af: float = 0.0,
    am_score: float = 0.0,
    plddt: float = 50.0,
    gene_total_cv: int = 0,
    gene_plp_count: int = 0,
    oe_lof_upper: float = 1.0,
    mis_z: float = 0.0,
    n_submitters: int = 1,
) -> dict:
    """
    ML-backed variant scoring. Returns probability + tier + explanation.
    Falls back to rule-based if model not available.
    """
    CONS_MAP = {"nonsense":5,"stop_gained":5,"frameshift":4,"splice":3,"splice_site":3,
                "missense":2,"deletion":2,"insertion":2,"synonymous":0,"other":1}
    cons_score = CONS_MAP.get(consequence.lower().replace(" ","_"),
                  CONS_MAP.get(consequence.lower(), 1))
    is_lof = int(cons_score >= 3)
    pli = 0.5 if pli is None else pli
    oe_lof_upper = 1.0 if oe_lof_upper is None else oe_lof_upper
    is_lof_intol = int(pli >= 0.9)
    is_constrained = int(oe_lof_upper < 0.35)
    pvs1 = int(is_lof and is_lof_intol)
    mis_z_tier = min(4, max(0, int(max(0, mis_z) // 1)))
    multi_ev = min(20, clinvar_stars*2 + is_lof_intol*3 + cons_score + int(cv_density>5)*2 + pvs1*3)

    X = [float(clinvar_stars), float(n_submitters), float(1 if is_lof else 2),
         float(cons_score), float(is_lof), float(pli),
         float(max(0.01, oe_lof_upper*0.85)), float(oe_lof_upper),
         float(mis_z), float(is_lof_intol), float(is_constrained),
         float(cv_density), float(gene_total_cv), float(gene_plp_count),
         float(pvs1), float(multi_ev), float(mis_z_tier)]

    pack = _load_ml_model()
    if pack is not None:
        try:
            import numpy as _np
            arr = _np.array(X, dtype=_np.float32).reshape(1, -1)
            prob = float(pack["model"].predict_proba(arr)[0, 1])
            source = "ml_model"
        except Exception:
            prob = None; source = "rule_based"
    else:
        prob = None; source = "rule_based"

    if prob is None:
        # Rule-based fallback — strengthened so ClinVar P/LP can reach CRITICAL
        # without requiring gnomAD constraint (which often fails in production).
        # Major sources of evidence (each contributes substantially to the final score):
        #   - ClinVar review-star quality (multiplied by 2.5 — was 2)
        #   - ClinVar P/LP status itself contributes (was implicit, now explicit +5)
        #     This is the key fix: a ClinVar Pathogenic missense in a known
        #     oncogene shouldn't lose CRITICAL ranking just because gnomAD 403'd.
        #   - LoF intolerance from gnomAD (+3 if available, but optional)
        #   - Consequence severity (LoF heavy-weighted)
        #   - Variant rarity (rare variants more likely pathogenic)
        #   - AlphaMissense (+3 if confidently pathogenic, was +2)
        #   - Mutational density at the position
        # The cv_density signal is reinterpreted as "evidence weight" rather than
        # being capped at 2 — TP53/EGFR-class genes routinely have >50 P/LP variants.
        # The is_clinvar_plp signal is set externally via `clinvar_stars >= 2` since
        # the scorer doesn't receive cv_class directly. ClinVar reviewed-by-expert
        # status (2+ stars) is treated as strong evidence on its own.
        is_clinvar_reviewed = int(clinvar_stars >= 2)
        score = (
            clinvar_stars * 2.5                                     # max 10 (4-star expert review)
            + is_clinvar_reviewed * 5                               # +5 if ClinVar reviewed (replaces gnomAD as primary evidence)
            + is_lof_intol * 3                                      # +3 if gnomAD available AND constrained
            + cons_score                                            # 5 (nonsense), 4 (FS), 3 (splice), 2 (missense)
            + (2 if gnomad_af == 0 else 1.5 if gnomad_af < 0.0001 else 0)  # rare = pathogenic-leaning
            + (3 if am_score >= 0.7 and "missense" in consequence.lower() else 0)  # AM strong: +3
            + (1 if plddt >= 70 else 0)                             # structured region
            + (3 if cv_density > 20 else 2 if cv_density > 10 else 1 if cv_density > 5 else 0)  # density carries more weight
        )
        # Normalise against new max (~25 for an expert-reviewed nonsense in a hotspot)
        prob = min(0.99, max(0.01, score / 22.0))

    tier = 1 if prob>=0.75 else 2 if prob>=0.50 else 3 if prob>=0.25 else 4
    return {"probability": round(prob,4), "tier": tier, "source": source,
            "cons_score": cons_score, "is_lof": is_lof, "pvs1": pvs1, "multi_ev": multi_ev}

def ml_rank_fn(ml, sens=50, clinvar_score=None):
    """
    Rank variant by ML score, capped by ClinVar evidence.
    Uses ML-model probability when available.
    """
    shift = (sens - 50) / 200
    raw_rank = ("CRITICAL" if ml >= .85 - shift else
                "HIGH"     if ml >= .65 - shift else
                "MEDIUM"   if ml >= .40 - shift else "NEUTRAL")
    if clinvar_score is None:
        return raw_rank
    if clinvar_score >= 4:   return raw_rank
    elif clinvar_score == 3: return "HIGH" if raw_rank == "CRITICAL" else raw_rank
    elif clinvar_score == 2: return "MEDIUM" if raw_rank in ("CRITICAL", "HIGH") else raw_rank
    elif clinvar_score == 1: return "NEUTRAL"
    else:                    return "NEUTRAL"
def score_domain_context(pdata, cv_variants, am_scores_dict=None):
    """
    Map ClinVar P/LP variants onto protein domains to identify mutational hotspots.
    Returns per-domain pathogenic density and top hotspot residues.
    """
    if not pdata: return {}

    # Get UniProt domains
    features = pdata.get("features", [])
    domains = [f for f in features if f.get("type","") in
               ("Domain", "Region", "Active site", "Binding site",
                "Modified residue", "Natural variant", "Transmembrane", "Zinc finger")]

    seq_len = len(pdata.get("sequence",{}).get("value","") or "")
    if seq_len == 0: return {}

    # Map P/LP variants to positions
    plp_positions = set()
    for v in (cv_variants or []):
        if v.get("cv_class") in (1,2):
            pos = v.get("position") or 0
            if pos: plp_positions.add(int(pos))

    # Score each domain
    domain_scores = []
    for dom in domains:
        loc = dom.get("location",{})
        start = int(loc.get("start",{}).get("value",0) or 0)
        end = int(loc.get("end",{}).get("value",0) or 0)
        if end <= start: continue
        dom_len = end - start + 1
        plp_in_domain = len([p for p in plp_positions if start <= p <= end])
        density = plp_in_domain / dom_len * 100 if dom_len > 0 else 0

        # AlphaMissense score in domain region
        am_in_domain = []
        if am_scores_dict:
            am_in_domain = [am_scores_dict.get(str(p),0) or 0 for p in range(start, end+1)
                           if str(p) in am_scores_dict]
        mean_am = sum(am_in_domain)/len(am_in_domain) if am_in_domain else 0

        domain_scores.append({
            "name": dom.get("description","") or dom.get("type","Unknown"),
            "type": dom.get("type",""),
            "start": start, "end": end, "length": dom_len,
            "plp_count": plp_in_domain,
            "density": round(density, 2),
            "mean_am": round(mean_am, 3),
            "hotspot_score": round(density * 0.6 + mean_am * 100 * 0.4, 1),
            "is_hotspot": density >= 5 or (plp_in_domain >= 3 and dom_len < 50),
        })

    domain_scores.sort(key=lambda x: x["hotspot_score"], reverse=True)

    # Identify specific hotspot residues (positions with ≥2 independent P/LP)
    from collections import Counter
    pos_counts = Counter()
    for v in (cv_variants or []):
        if v.get("cv_class") in (1,2):
            pos = v.get("position") or 0
            if pos: pos_counts[int(pos)] += 1
    hotspot_residues = [(pos, count) for pos, count in pos_counts.most_common(10) if count >= 2]

    # Genomic integrity score — this is Protellect's core metric
    total_cv = len(cv_variants or [])
    plp_cv = len(plp_positions)
    gi_score = round(plp_cv / max(seq_len, 1) * 100, 2)
    gi_class = ("DISEASE-CRITICAL" if gi_score >= 10 else
                "DISEASE-ASSOCIATED" if gi_score >= 5 else
                "MODERATE" if gi_score >= 2 else
                "LOW-EVIDENCE" if gi_score >= 0.5 else "MINIMAL")

    return {
        "domains": domain_scores[:10],
        "hotspot_residues": hotspot_residues,
        "gi_score": gi_score,
        "gi_class": gi_class,
        "plp_count": plp_cv,
        "total_cv": total_cv,
        "seq_len": seq_len,
        "top_hotspot_domain": domain_scores[0] if domain_scores else None,
    }


def score_conflict_detection(cv_data, gnomad_data, am_data=None):
    """
    Detect conflicts between databases that indicate data quality issues or
    reclassification candidates.
    Returns list of conflict flags with explanations.
    """
    flags = []
    variants = cv_data.get("variants", []) or []
    gn_variants = gnomad_data.get("variants", {}) or {}

    # Flag 1: ClinVar P/LP but high population AF
    for v in variants:
        if v.get("cv_class") in (1,2):
            vid = v.get("variant_id","") or ""
            af = gn_variants.get(vid, {}).get("af", 0) or 0
            if af > 0.001:
                flags.append({
                    "type": "AF_CONFLICT",
                    "severity": "HIGH",
                    "message": f"Variant classified P/LP in ClinVar but AF={af:.4%} in gnomAD — may warrant reclassification",
                    "variant": v.get("name",""),
                    "color": "#ff2d55",
                })

    # Flag 2: Many VUS vs few P/LP → poorly characterised gene
    plp = sum(1 for v in variants if v.get("cv_class") in (1,2))
    vus = sum(1 for v in variants if v.get("cv_class") == 3)
    if vus > plp * 5 and vus >= 20:
        flags.append({
            "type": "VUS_BURDEN",
            "severity": "MEDIUM",
            "message": f"High VUS burden: {vus} VUS vs {plp} P/LP — gene is poorly characterised. Functional data critical before any wet-lab commitment.",
            "color": "#ffd60a",
        })

    # Flag 3: Conflicting interpretations in ClinVar
    conf = sum(1 for v in variants if "conflict" in (v.get("review_status","") or "").lower())
    if conf >= 3:
        flags.append({
            "type": "CONFLICTING_INTERP",
            "severity": "MEDIUM",
            "message": f"{conf} variants have conflicting interpretations in ClinVar — independent functional validation mandatory before use as biomarker.",
            "color": "#ff8c42",
        })

    # Flag 4: No gnomAD constraint data
    if not gnomad_data.get("pLI") and not gnomad_data.get("oe_lof"):
        flags.append({
            "type": "NO_CONSTRAINT",
            "severity": "LOW",
            "message": "No gnomAD constraint data — gene may be too small to score, or non-coding. Check OMIM for disease mechanism.",
            "color": "#3a6080",
        })

    return flags


def auto_acmg_criteria(pdata, cv_data, gnomad_data, am_data=None):
    """
    Automatically evaluate ACMG/AMP 2015 criteria from fetched data.
    Returns dict of {criterion: (met, strength, evidence_string)}.
    """
    criteria = {}
    if not pdata: return criteria

    pli = gnomad_data.get("pLI", 0) or 0
    oe_lof_upper = gnomad_data.get("oe_lof_upper", 1) or 1
    seq_len = len(pdata.get("sequence", {}).get("value", "") or "")

    variants = cv_data.get("variants", []) or []
    plp_vars = [v for v in variants if v.get("cv_class") in (1, 2)]
    blb_vars = [v for v in variants if v.get("cv_class") in (4, 5)]
    total_vars = len(variants)
    plp_count = len(plp_vars)
    blb_count = len(blb_vars)

    # ── Pathogenic criteria ────────────────────────────────────────────────
    # PVS1: LoF in LoF-intolerant gene
    gene_name = pdata.get("gene_names", [{}])[0].get("gene", {}).get("geneName", {}).get("value", "") if pdata.get("gene_names") else ""
    lof_gene = pli >= 0.9 or oe_lof_upper < 0.35
    if lof_gene and plp_count >= 3:
        criteria["PVS1"] = (True, "very_strong",
            f"Gene is LoF-intolerant (pLI={pli:.2f}, oe_lof_upper={oe_lof_upper:.2f}) with {plp_count} confirmed P/LP LoF variants in ClinVar")
    elif lof_gene:
        criteria["PVS1"] = (False, "very_strong",
            f"Gene is LoF-intolerant (pLI={pli:.2f}) — PVS1 applicable if variant is null (nonsense/frameshift/canonical splice)")

    # PM2: Absent from population controls
    gn_variants = gnomad_data.get("variants", {})
    n_gnomad = len(gn_variants)
    if n_gnomad < 5:
        criteria["PM2"] = (True, "moderate",
            f"Gene has {n_gnomad} variants in gnomAD — absent from population controls. PM2 applicable.")
    else:
        criteria["PM2"] = (False, "moderate",
            f"Gene has {n_gnomad} population variants in gnomAD — check specific variant AF (<0.001% = PM2)")

    # PS1/PM5: Same position as known pathogenic
    hotspot_positions = {}
    for v in plp_vars:
        pos = v.get("position") or 0
        if pos:
            hotspot_positions[pos] = hotspot_positions.get(pos, 0) + 1
    hotspot_count = sum(1 for c in hotspot_positions.values() if c >= 2)
    if hotspot_count >= 3:
        criteria["PM1"] = (True, "moderate",
            f"{hotspot_count} mutational hotspot positions identified (≥2 independent P/LP variants at same residue). PM1 applicable.")
    elif hotspot_count >= 1:
        criteria["PM1"] = (False, "moderate",
            f"{hotspot_count} potential hotspot position — check if new variant is at same amino acid as known P/LP")

    # PP2: Gene with low rate of benign missense
    mis_z = gnomad_data.get("mis_z", 0) or 0
    if mis_z >= 3.09:
        criteria["PP2"] = (True, "supporting",
            f"Gene has very low rate of benign missense variants (mis_z={mis_z:.2f} > 3.09 threshold). PP2 applicable for missense.")
    elif mis_z >= 2.0:
        criteria["PP2"] = (False, "supporting",
            f"Gene has elevated missense constraint (mis_z={mis_z:.2f}) — PP2 may apply depending on specific variant")

    # PP3: Computational evidence. ACMG applies this PER VARIANT, so no gene-level PP3 is asserted here.
    if am_data:
        _am_vals = _am_flat(am_data) if isinstance(am_data, dict) else []
        if _am_vals:
            _n_hi = sum(1 for s in _am_vals if s > 0.564)
            criteria["PP3"] = (False, "supporting",
                f"PP3 is judged per variant, not per gene. {_n_hi} of {len(_am_vals)} AlphaMissense substitution scores exceed 0.564 (likely pathogenic, Cheng 2023); a specific variant needs its own score.")


    # ── Benign criteria ────────────────────────────────────────────────────
    # BA1: Common in population
    # (variant-level — can't auto-populate without specific variant AF)

    # BS1: Allele frequency greater than expected for disorder
    # Handled per-variant in the app

    # BP1: Missense in gene where only truncating cause disease
    lof_only_gene = plp_count >= 5 and blb_count == 0 and sum(
        1 for v in plp_vars if any(k in (v.get("consequence","") or "").lower()
            for k in ["frameshift","nonsense","stop","splice"])
    ) / max(plp_count, 1) >= 0.85
    if lof_only_gene:
        criteria["BP1"] = (True, "supporting",
            f"≥85% of {plp_count} P/LP variants in this gene are truncating — missense variants may receive BP1 benign evidence")

    # Summary score
    n_met = sum(1 for met, _, _ in criteria.values() if met)
    criteria["_summary"] = {
        "n_criteria_met": n_met,
        "n_criteria_assessed": len([c for c in criteria if not c.startswith("_")]),
        "genomic_integrity_pct": round(plp_count / max(total_vars, 1) * 100, 1),
        "plp_count": plp_count,
        "total_vars": total_vars,
        "hotspot_positions": hotspot_count,
        "lof_intolerant": lof_gene,
    }
    return criteria




def parse_aa(name):
    aa3={"Ala":"A","Arg":"R","Asn":"N","Asp":"D","Cys":"C","Gln":"Q","Glu":"E","Gly":"G",
         "His":"H","Ile":"I","Leu":"L","Lys":"K","Met":"M","Phe":"F","Pro":"P","Ser":"S",
         "Thr":"T","Trp":"W","Tyr":"Y","Val":"V","Ter":"*","Xaa":"X"}
    m=re.search(r"p\.([A-Z][a-z]{2})\d+([A-Z][a-z]{2}|Ter|\*)",name or "")
    return (aa3.get(m.group(1),"?"),aa3.get(m.group(2),"?")) if m else ("?","?")

# ─── API functions ─────────────────────────────────────────────────

def _is_ambiguous_search(query: str, result_gene: str, result_name: str) -> str | None:
    """
    Returns a warning string if the search term is ambiguous/generic and
    the top result may not be what the user intended.
    Returns None if the match looks direct and unambiguous.
    """
    q = query.strip().lower()
    g = result_gene.strip().lower()
    n = result_name.strip().lower()

    # If the query matches the gene symbol exactly → no warning
    if q == g: return None
    # If the query is a UniProt accession → no warning
    import re as _re
    if _re.match(r"^[A-Z][0-9][A-Z0-9]{3}[0-9]$", query.strip(), _re.I): return None

    # Common ambiguous/generic food/substance terms that hit protein names
    AMBIGUOUS_TERMS = {
        "gelatin":  ("ADIPOQ (Adiponectin)", "Adiponectin was historically called 'Gelatin-Binding Protein 28' (GBP28) in early literature — it is NOT related to dietary gelatin. If you meant: search the human gene symbol directly, e.g. ADIPOQ, COL1A1 (collagen/gelatin source), or MMP2 (gelatinase A)."),
        "albumin":  ("ALB (Serum albumin)", "Albumin matches human serum albumin (ALB). If you meant a different protein, search by gene symbol."),
        "fibrin":   ("FGB/FGA/FGG", "Fibrin is a fibrinogen cleavage product. Search FGB, FGA, or FGG for fibrinogen chains."),
        "collagen": ("COL1A1 (top hit)", "Multiple collagen genes exist (COL1A1–COL28A1). Search the specific collagen by number (e.g. COL4A1) for precision."),
        "keratin":  ("KRT1 (top hit)", "Multiple keratin genes exist (KRT1–KRT86). Search the specific keratin number for precision."),
        "actin":    ("ACTB/ACTA1", "Multiple actin genes exist. ACTB = cytoplasmic beta-actin, ACTA1 = skeletal muscle alpha-actin."),
        "myosin":   ("MYH7 (top hit)", "Multiple myosin heavy/light chain genes exist. Search the specific myosin (e.g. MYH7, MYL2) for precision."),
        "hemoglobin":("HBB (top hit)", "Multiple haemoglobin subunit genes: HBA1, HBA2 (alpha), HBB (beta), HBD (delta)."),
        "elastin":  ("ELN", "ELN = human elastin — correct match."),
        "casein":   (None, "Casein is a milk protein — no direct human gene equivalent. Try CSNK (casein kinase) if you meant casein kinase."),
    }

    for term, (likely_hit, explanation) in AMBIGUOUS_TERMS.items():
        if term in q and g not in q:
            return (f" <b>Search disambiguation:</b> '{query}' matched <b>{result_gene}</b> "
                    f"because its protein name contains this term. "
                    f"Top result: {likely_hit}. {explanation}")

    # Generic check: query not in gene name and not in first word of protein name
    gene_words = g.split()
    protein_first_word = n.split()[0] if n else ""
    if q not in gene_words and q != protein_first_word and len(q) > 4:
        return (f" <b>Search note:</b> '{query}' is not the gene symbol for <b>{result_gene}</b> — "
                f"it matched the protein description. If this is not the protein you intended, "
                f"search by gene symbol (e.g. {result_gene.upper()}) or UniProt accession for a precise match.")

    return None








# ─── Additional data sources ───────────────────────────────────────────────────





def _disease_evidence_tier(source: str, n_clinvar_stars: int = 0,
                            clingen_class: str = "") -> dict:
    """
    Assign an evidence tier to a disease association.
    Tier 1 = UniProt manually curated (strongest)
    Tier 2 = ClinGen Definitive/Strong
    Tier 3 = ClinVar ≥2 stars / ClinGen Moderate
    Tier 4 = ClinVar 1 star / ClinGen Limited
    Tier 5 = OpenTargets GWAS/expression only (correlation, not causation)
    """
    CLINGEN_TIERS = {
        "Definitive": 2, "Strong": 2, "Moderate": 3,
        "Limited": 4, "No Reported Evidence": 5,
        "Disputed": 5, "Refuted": 5,
    }
    tier = 5
    if source == "uniprot": tier = 1
    elif clingen_class in CLINGEN_TIERS: tier = CLINGEN_TIERS[clingen_class]
    elif n_clinvar_stars >= 2: tier = 3
    elif n_clinvar_stars == 1: tier = 4
    tier_labels = {
        1: ("Tier 1", "#22c55e", "UniProt manually curated — highest confidence causal evidence"),
        2: ("Tier 2", "#4a90d9", "ClinGen Definitive/Strong — expert-curated gene-disease validity"),
        3: ("Tier 3", "#ffd60a", "ClinVar ≥2 stars / ClinGen Moderate — good evidence, peer reviewed"),
        4: ("Tier 4", "#ff8c42", "ClinVar 1 star / ClinGen Limited — single submitter, use cautiously"),
        5: ("Tier 5", "#3a6080", "Statistical association only — not causal Mendelian evidence"),
    }
    label, color, desc = tier_labels[tier]
    return {"tier": tier, "label": label, "color": color, "description": desc}


@st.cache_data(show_spinner=False, ttl=3600)

def classify_organism(pdata: dict) -> dict:
    """Classify whether this protein is human or non-human."""
    org = pdata.get("organism",{})
    sci_name = org.get("scientificName","")
    common   = org.get("commonName","")
    tax_id   = org.get("taxonId",0)
    is_human = ("Homo sapiens" in sci_name) or (tax_id == 9606)
    return {
        "is_human": is_human,
        "scientific_name": sci_name,
        "common_name": common or sci_name,
        "tax_id": tax_id,
        "warning": "" if is_human else (
            f" Non-human protein: {sci_name} ({common}). "
            f"ClinVar and disease data apply to human proteins only. "
            f"This protein may have a human orthologue — search by gene symbol instead."
        )
    }

def classify_experiment_type(abstract: str, title: str) -> str:
    """Classify what type of experiment was done based on paper abstract."""
    text = (title + " " + abstract).lower()
    if any(k in text for k in ["cryo-em","crystal structure","x-ray","nmr structure","alphafold","structural"]): return " Structural"
    if any(k in text for k in ["crispr","knockout","knock-in","knockdown","sirna","shrna"]): return " CRISPR/Genetic"
    if any(k in text for k in ["mouse","rat","zebrafish","in vivo","xenograft","animal model"]): return " In Vivo"
    if any(k in text for k in ["clinical trial","patient","cohort","clinical study","human subject"]): return " Clinical"
    if any(k in text for k in ["binding","affinity","kinetics","spr","biacore","itc","pull-down","co-ip"]): return " Binding/Interaction"
    if any(k in text for k in ["phosphorylation","kinase activity","enzyme","substrate","biochemical"]): return " Biochemical"
    if any(k in text for k in ["western blot","immunofluorescence","flow cytometry","facs","cell viability","proliferation"]): return " Cell-Based"
    if any(k in text for k in ["whole genome","sequencing","gwas","variant","mutation","polymorphism"]): return " Genomics"
    if any(k in text for k in ["drug","inhibitor","compound","therapeutic","treatment","clinical"]): return " Drug/Therapeutic"
    return " Other"



def ml_score_variants(variants, sens=50):
    out=[]
    for v in variants:
        name=v.get("variant_name","") or v.get("title","")
        orig,alt=parse_aa(name)
        hd=abs(AA_HYDRO.get(orig,0)-AA_HYDRO.get(alt,0))
        cd=abs(AA_CHG.get(orig,0)-AA_CHG.get(alt,0))
        stop=float(alt=="*"); frame=float("frame" in name.lower())
        stars={"practice guideline":1,"reviewed by expert panel":.9,
               "criteria provided, multiple submitters":.7,"criteria provided, single submitter":.5}.get(v.get("review","").lower(),.2)
        base=v.get("score",0)/5.0
        ml=min(1.0,base*.5+stop*.25+frame*.15+(hd/10)*.05+cd*.03+stars*.02)
        vc=dict(v); vc["ml"]=round(float(ml),3); vc["ml_rank"]=ml_rank_fn(ml, sens, v.get("score", None))
        vc["rank"]=score_rank(v.get("score",0),sens)
        out.append(vc)
    return sorted(out,key=lambda x:-x["ml"])

# UniProt helpers
def g_gene(p):
    try: return p["genes"][0]["geneName"]["value"]
    except: return p.get("primaryAccession","?")
def g_name(p):
    try: return p["proteinDescription"]["recommendedName"]["fullName"]["value"]
    except: return "Unknown protein"
def g_seq(p): return p.get("sequence",{}).get("value","")
def g_diseases(p):
    """
    Extract ALL disease associations from UniProt — comments + features + cross-refs.
    Extracts inheritance, mutation type, OMIM ID, and clinical note for every disease.
    """
    out = []
    seen = set()
    if not isinstance(p, dict):
        return out  # nothing to extract from a missing / malformed protein record

    # Detect the gene's chromosome so we can infer X/Y-linked inheritance when a
    # specific disease note doesn't state it. FLNA, for example, is on the X
    # chromosome, so ALL its diseases are X-linked even if only some notes say so.
    _gene_chromosome = ""
    try:
        for xref in p.get("uniProtKBCrossReferences", []):
            if xref.get("database") == "Proteomes":
                for prop in xref.get("properties", []):
                    if prop.get("key") == "Component":
                        _comp = prop.get("value", "")
                        if "chromosome x" in _comp.lower(): _gene_chromosome = "X"
                        elif "chromosome y" in _comp.lower(): _gene_chromosome = "Y"
                        elif "mitochond" in _comp.lower(): _gene_chromosome = "MT"
        # Fallback: scan gene-level keywords/comments for X-linked mentions
        if not _gene_chromosome:
            _all_text = json.dumps(p.get("comments", []))[:5000].lower()
            if "x-linked" in _all_text:
                _gene_chromosome = "X"
    except Exception:
        _gene_chromosome = ""

    # 1. Disease comments (primary and most reliable source)
    for c in p.get("comments", []):
        if c.get("commentType") != "DISEASE": continue
        d = c.get("disease", {})
        name = d.get("diseaseId", d.get("diseaseAcronym",""))
        if not name or name in seen: continue
        seen.add(name)
        
        # Get mutation note
        note = ""
        if c.get("note"):
            texts = c.get("note", {}).get("texts", [])
            note = texts[0].get("value", "") if texts else ""
        
        # Get OMIM cross-reference from disease entry
        omim_id = ""
        # Handle both "diseaseCrossReferences" (plural) and "diseaseCrossReference" (singular) across UniProt API versions
        xrefs_raw = d.get("diseaseCrossReferences") or d.get("diseaseCrossReference") or []
        if isinstance(xrefs_raw, dict): xrefs_raw = [xrefs_raw]
        for xref in xrefs_raw:
            if xref.get("database") == "MIM":
                omim_id = xref.get("id","")
                break
        
        desc = d.get("description","")
        
        # Extract inheritance — try multiple text sources
        inh_text = " ".join([note, desc, name])
        inheritance = _extract_inheritance(inh_text)
        
        # If still empty, infer from chromosome first (most reliable), then conventions
        if not inheritance:
            name_lower = name.lower()
            if _gene_chromosome == "X":
                inheritance = "X-linked"      # gene is on X → disease is X-linked
            elif _gene_chromosome == "Y":
                inheritance = "Y-linked"
            elif _gene_chromosome == "MT":
                inheritance = "Mitochondrial"
            elif "cardiomyopathy" in name_lower:
                inheritance = "Autosomal Dominant (AD)"  # most cardiomyopathies are AD
            elif "deficiency" in name_lower:
                inheritance = "Autosomal Recessive (AR)"
            # Note: removed the unreliable "type 1 / syndrome 1 → AD" guess —
            # a trailing number says nothing about inheritance mode.
        
        # Extract mutation type from note
        mut_type = _extract_mutation_type(note)
        if not mut_type:
            mut_type = _extract_mutation_type(desc)
        
        _ev_tier = _disease_evidence_tier("uniprot")
        out.append({
            "_evidence_tier": _ev_tier,
            "name": name,
            "desc": desc,
            "note": note,
            "omim": omim_id,
            "inheritance": inheritance,
            "mutation_type": mut_type,
        })
    
    # 2. Extract from variant features that mention disease
    for f in p.get("features", []):
        if f.get("type") in ("Natural variant", "VARIANT"):
            desc = f.get("description", "")
            if any(k in desc.lower() for k in ["disease", "cancer", "carcinoma", "syndrome", "disorder", "deficiency"]):
                # Extract disease name from description
                loc = f.get("location", {})
                pos = loc.get("start", {}).get("value", "?")
                orig = f.get("alternativeSequence", {}).get("originalSequence", "")
                alts = f.get("alternativeSequence", {}).get("alternativeSequences", [])
                alt = alts[0] if alts else ""
                # Try to extract condition from "in X; " pattern
                import re as re2
                matches = re2.findall(r"[Ii]n ([A-Z][^;.]+?)(?:;|\.|$)", desc)
                for m in matches[:2]:
                    m = m.strip()
                    if len(m) > 5 and m not in seen:
                        seen.add(m)
                        out.append({
                            "name": m,
                            "desc": f"Variant at position {pos}: {orig}→{alt or '?'}",
                            "note": desc[:200],
                            "omim": "",
                            "inheritance": _extract_inheritance(desc),
                            "mutation_type": f"p.{orig}{pos}{alt}" if orig and alt else desc[:40],
                        })
    return out[:20]  # cap at 20

def _extract_inheritance(text):
    """Extract inheritance pattern from ANY available text including OMIM notation."""
    if not text: return ""
    t = text.lower()
    # Most specific first
    if "autosomal dominant" in t or "ad inheritance" in t: return "Autosomal Dominant (AD)"
    if "autosomal recessive" in t or "ar inheritance" in t: return "Autosomal Recessive (AR)"
    if "x-linked dominant" in t: return "X-linked Dominant"
    if "x-linked recessive" in t: return "X-linked Recessive"
    if "x-linked" in t: return "X-linked"
    if "y-linked" in t: return "Y-linked"
    if "mitochondrial" in t or "maternal" in t: return "Mitochondrial"
    if "digenic" in t: return "Digenic"
    if "semidominant" in t or "semi-dominant" in t: return "Semidominant"
    # Broader
    if "dominant" in t: return "Autosomal Dominant (AD)"
    if "recessive" in t: return "Autosomal Recessive (AR)"
    if "somatic" in t: return "Somatic (acquired — not heritable)"
    if "de novo" in t: return "De novo (new mutation)"
    if "sporadic" in t: return "Sporadic"
    return ""


def _extract_mutation_type(text):
    """Extract mutation type from text including HGVS notation."""
    if not text: return ""
    t = text.lower()
    if "missense" in t or "p." in t and ">" not in t: return "Missense (letter-swap mutation)"
    if "frameshift" in t or "frame shift" in t or "fs" in text: return "Frameshift (reading-frame shift)"
    if "nonsense" in t or "stop gained" in t or "ter" in t.lower(): return "Stop-gain (early termination)"
    if "splice" in t and "donor" in t: return "Splice-donor disruption"
    if "splice" in t and "acceptor" in t: return "Splice-acceptor disruption"
    if "splice" in t: return "Splice-site disruption"
    if "large deletion" in t or "exon deletion" in t: return "Large deletion"
    if "deletion" in t and "in-frame" in t: return "In-frame deletion"
    if "deletion" in t: return "Deletion"
    if "duplication" in t: return "Duplication"
    if "insertion" in t: return "Insertion"
    if "inversion" in t: return "Inversion"
    if "translocation" in t: return "Translocation"
    if "copy number" in t or "cnv" in t: return "Copy number variant (CNV)"
    if "promoter" in t: return "Promoter variant"
    if "5'utr" in t or "5 utr" in t: return "5' UTR variant"
    if "3'utr" in t or "3 utr" in t: return "3' UTR variant"
    return ""

def g_func(p):
    for c in p.get("comments",[]):
        if c.get("commentType")=="FUNCTION":
            t=c.get("texts",[])
            if t: return t[0].get("value","")
    return ""

@st.cache_data(show_spinner=False, ttl=86400)

def _check_h8_helix(seq: str) -> dict:
    """
    Check for H8 (helix 8) Filamin-Binding Motif in GPCR C-terminus.
    The H8 motif is a conserved hydrophobic helix after TM7 in Class A GPCRs.
    Consensus: [FILV]x[FILV]x[FILV] within last 60 aa.
    Returns dict with has_h8, position, and sequence.
    """
    if not seq or len(seq) < 30:
        return {"has_h8": False}
    tail = seq[-60:]
    import re as _re
    # H8 consensus: amphipathic helix with hydrophobic residues at i, i+2, i+4
    hydro = set("FILMVWY")
    h8_hits = []
    for i in range(len(tail)-8):
        window = tail[i:i+9]
        # Count hydrophobic at positions 0, 2, 4 (characteristic of amphipathic helix)
        score = sum(1 for pos in [0,2,4,6] if pos < len(window) and window[pos] in hydro)
        if score >= 3:
            h8_hits.append((i + len(seq) - 60 + 1, window))
    if h8_hits:
        best_pos, best_seq = h8_hits[0]
        return {
            "has_h8": True,
            "position": best_pos,
            "sequence": best_seq,
            "note": f"H8 motif at position {best_pos} — PKA/Filamin piggyback assay applicable (PMID:26124276)"
        }
    return {"has_h8": False, "note": "No H8 motif detected — standard GPCR assays apply (cAMP/IP3/β-arrestin)"}

def g_gpcr(p):
    kws=[k.get("value","").lower() for k in p.get("keywords",[])]
    kws_str = " ".join(kws)
    fn = g_func(p).lower()
    is_structural = any(x in kws_str for x in ["filamin","actin-binding","cytoskeleton","scaffold protein","focal adhesion","sarcomere"])
    if is_structural: return False
    has_gpcr_kw = any(x in kws_str for x in ["gpcr","g protein-coupled receptor","7-transmembrane","rhodopsin","adrenergic receptor","muscarinic","serotonin receptor","dopamine receptor","chemokine receptor","opioid receptor"])
    has_gpcr_fn = any(x in fn for x in ["g protein-coupled","g-protein-coupled","seven-transmembrane","7-transmembrane receptor"])
    return has_gpcr_kw or has_gpcr_fn

def g_gpcr_full(p, gene: str = "") -> dict:
    """
    Full GPCR classification: UniProt + GPCRdb + H8 helix check.
    Returns unified dict with confirmed class, subfamily, coupling, H8 status.
    """
    is_gpcr_uniprot = g_gpcr(p)
    gpcrdb = {}
    if gene and (is_gpcr_uniprot or any(x in g_func(p).lower() for x in ["receptor","gpcr"])):
        gpcrdb = fetch_gpcrdb(gene)
    confirmed = is_gpcr_uniprot or gpcrdb.get("confirmed_gpcr", False)
    seq = g_seq(p) if callable(g_seq) else ""
    h8 = _check_h8_helix(seq) if confirmed and seq else {"has_h8": False}
    # Subfamily classification
    GPCR_CLASSES = {
        "Class A (Rhodopsin)": ["rhodopsin","adrenergic","muscarinic","dopamine","serotonin","opioid","chemokine","cannabinoid","histamine","adenosine","purinergic"],
        "Class B1 (Secretin)": ["secretin","glucagon","glp","gip","pth","crf","vip","pacap","calcitonin"],
        "Class B2 (Adhesion)": ["adhesion","celsr","etl","emr","htr","latrophilin"],
        "Class C (Glutamate)": ["metabotropic","grm","gaba-b","gabab","calcium-sensing","taste"],
        "Class F (Frizzled)": ["frizzled","fzd","smoothened"],
    }
    detected_class = gpcrdb.get("receptor_class","")
    if not detected_class:
        fn_lower = g_func(p).lower()
        kws_lower = " ".join(k.get("value","").lower() for k in p.get("keywords",[]))
        for cls, keywords in GPCR_CLASSES.items():
            if any(kw in fn_lower or kw in kws_lower for kw in keywords):
                detected_class = cls
                break
        if not detected_class and confirmed:
            detected_class = "Class A (Rhodopsin) — presumed"
    return {
        "is_gpcr": confirmed,
        "receptor_class": detected_class,
        "subfamily": gpcrdb.get("subfamily",""),
        "family": gpcrdb.get("family",""),
        "h8": h8,
        "couplings": gpcrdb.get("couplings",{}),
        "gpcrdb_confirmed": gpcrdb.get("confirmed_gpcr", False),
        "source": "GPCRdb + UniProt" if gpcrdb else "UniProt only",
    }


def g_ptype(p):
    kws=[k.get("value","").lower() for k in p.get("keywords",[])]
    kw=" ".join(kws); fn=g_func(p).lower()
    if any(x in kw for x in ["kinase","phosphotransferase"]): return "kinase"
    if any(x in kw for x in ["transcription factor","dna-binding","zinc finger","homeodomain"]): return "transcription_factor"
    if g_gpcr(p): return "gpcr"
    if any(x in kw for x in ["ion channel","voltage-gated","ligand-gated"]): return "ion_channel"
    if any(x in kw for x in ["receptor tyrosine","growth factor receptor","egfr","erbb"]): return "receptor_tyrosine_kinase"
    if any(x in kw for x in ["nuclear receptor","steroid","thyroid hormone receptor"]): return "nuclear_receptor"
    if any(x in kw for x in ["e3 ubiquitin","ubiquitin ligase","cullin"]): return "ubiquitin_system"
    if any(x in kw for x in ["structural","cytoskeletal","actin-binding","filamin","collagen","laminin"]): return "structural"
    if any(x in kw for x in ["chaperone","heat shock protein","hsp"]): return "chaperone"
    if any(x in kw for x in ["receptor"]): return "receptor"
    return "general"



def classify_entity(p):
    """Classify protein entity type and derive drug class, first assay, and tailored description."""
    ptype = g_ptype(p)
    DRUG_CLASS = {
        "kinase": "ATP-competitive or allosteric kinase inhibitor",
        "gpcr":   "Biased agonist, antagonist, PAM, or NAM",
        "receptor_tyrosine_kinase": "Monoclonal antibody or small molecule TKI",
        "ion_channel": "Pore blocker or gating modifier",
        "nuclear_receptor": "Ligand (agonist/antagonist) or co-activator disruptor",
        "transcription_factor": "PPI inhibitor, PROTAC, or upstream kinase target",
        "structural": "Stabiliser, splice modulator — direct drugging very difficult",
        "enzyme": "Active site inhibitor or allosteric modulator",
        "ubiquitin_system": "PROTAC substrate ligand or E3 ligase inhibitor",
        "chaperone": "HSP90 co-chaperone client or allosteric modulator",
    }
    FIRST_ASSAY = {
        "kinase":  "ADP-Glo kinase activity assay — direct measure of catalytic function loss",
        "gpcr":    "cAMP HTRF (Gs/Gi) + beta-arrestin BRET — biased agonism screen",
        "receptor_tyrosine_kinase": "pY1068/pERK western blot — autophosphorylation readout",
        "ion_channel": "Whole-cell patch clamp or thallium flux assay",
        "nuclear_receptor": "GAL4-UAS luciferase reporter + LanthaScreen TR-FRET",
        "transcription_factor": "EMSA + ChIP-qPCR on known target gene promoter",
        "structural": "Negative-stain EM of mutant vs WT + hydrogen-deuterium exchange (HDX-MS)",
        "enzyme":  "Substrate conversion fluorescence assay — kinetic Km/Vmax",
        "ubiquitin_system": "In vitro ubiquitination cascade assay",
        "chaperone": "Refolding protection assay + client protein western",
    }
    return {
        "ptype": ptype,
        "drug_class": DRUG_CLASS.get(ptype, "Small molecule or biologic — assess tractability first"),
        "first_assay": FIRST_ASSAY.get(ptype, "Variant biochemical activity assay — compare WT vs P/LP variant"),
        "is_enzyme": ptype in ("kinase","enzyme","ubiquitin_system"),
        "is_receptor": ptype in ("gpcr","receptor","receptor_tyrosine_kinase","ion_channel","nuclear_receptor"),
        "is_druggable_class": ptype in ("kinase","gpcr","receptor_tyrosine_kinase","ion_channel","nuclear_receptor"),
    }

# ── Research goal configuration ────────────────────────────────────────────
GOAL_CONFIG = {
    "Identify therapeutic targets": {
        "emphasis": ["druggability","tractability","hotspots","patient_population","clinical_trials"],
        "experiment_priority": ["Variant biochemical activity assay (WT vs P/LP)","CRISPR isogenic knock-in","AP-MS interactome mapping"],
        "banner": "Therapeutic target mode: OpenTargets tractability + drug landscape + FDA pathways prioritised.",
        "sidebar_tip": "Cross-reference with OpenTargets tractability — only proceed to HTS if small molecule tractable.",
    },
    "Understand disease mechanism": {
        "emphasis": ["variant_cascade","pathway","somatic_germline","interactions"],
        "experiment_priority": ["CRISPR isogenic knock-in (PS3 evidence)","AP-MS unbiased interactome mapping","Bulk RNA-seq transcriptional response"],
        "banner": "Mechanism mode: variant cascade, pathway disruption, and somatic vs germline split emphasised.",
        "sidebar_tip": "CRISPR knock-in of the top pathogenic variant is the gold-standard PS3 mechanistic evidence.",
    },
    "Drug discovery & development": {
        "emphasis": ["binding","ic50","ADMET","selectivity","SAR"],
        "experiment_priority": ["SPR binding kinetics (kon/koff)","HTS biochemical primary assay","ADMET panel (CYP3A4, hERG, plasma binding)"],
        "banner": "Drug development mode: binding kinetics, ChEMBL scaffolds, and selectivity panel emphasised.",
        "sidebar_tip": "Sequence: AlphaFold binding pocket → fpocket druggability → SPR primary screen → ITC for thermodynamics.",
    },
    "Biomarker identification": {
        "emphasis": ["expression","tissue","population_genetics","allele_frequency"],
        "experiment_priority": ["qPCR validation","Proteomics (LFQ)","ELISA development"],
        "banner": "Biomarker mode: tissue expression, gnomAD allele frequency, and patient vs healthy cohort comparison emphasised.",
        "sidebar_tip": "Variants at MAF < 0.01% in gnomAD + pathogenic ClinVar = strong diagnostic biomarker candidate.",
    },
    "Basic research": {
        "emphasis": ["function","interactions","structure","evolution"],
        "experiment_priority": ["Cryo-EM single-particle analysis","HDX-MS conformational dynamics","BioLayer Interferometry (BLI) binding kinetics"],
        "banner": "Basic research mode: full data shown without commercial or clinical filtering.",
        "sidebar_tip": "Check PDB for existing structures before committing to cryo-EM — may already be solved.",
    },
    "Experimental pathway prioritisation": {
        "emphasis": ["roi_calculator","cost","timeline","p_success"],
        "experiment_priority": ["AlphaMissense pathogenicity landscape (free)","Variant co-occurrence analysis (gnomAD)","Structural pocket scoring (fpocket — free)"],
        "banner": "Experiment prioritisation mode: ROI calculator shown first. Zero-cost computational screens always before wet-lab.",
        "sidebar_tip": "Never spend on CRISPR until TSA + viability confirm dysfunction. ROI = p(success) × value / (cost × time).",
    },
    "Clinical variant interpretation": {
        "emphasis": ["clinvar_stars","reclassification","inheritance","ps3_bs3"],
        "experiment_priority": ["CRISPR knock-in (PS3 evidence)","Splicing reporter assay","Protein stability (BS3 evidence)"],
        "banner": "Clinical variant mode: ACMG/AMP classification criteria, ClinGen PS3/BS3 evidence, and reclassification plan emphasised.",
        "sidebar_tip": "VUS reclassification requires: AlphaMissense ≥0.564 (PP3) + CRISPR functional effect (PS3) + segregation in family (PP1).",
    },
}

def get_goal_config(gl):
    for k in GOAL_CONFIG:
        if k.lower() in gl.lower() or gl.lower() in k.lower():
            return GOAL_CONFIG[k]
    return GOAL_CONFIG.get("Basic research", {})

# ─── Genomic integrity ─────────────────────────────────────────────
def compute_gi(cv, protein_length):
    variants=cv.get("variants",[]); total=len(variants)
    germline=[v for v in variants if not v.get("somatic",False)]
    pathogenic=[v for v in germline if v.get("score",0)>=4]
    vus=[v for v in germline if v.get("score",0)==2]
    benign=[v for v in germline if v.get("score",0)<=0]
    n_p=len(pathogenic); n_g=max(len(germline),1); length=max(protein_length or 1,1)
    density=n_p/n_g; per100=(n_p/length)*100
    if total==0:
        return dict(verdict="NO CLINVAR DATA",label="No ClinVar variants found — API fetch may have failed",
                    css="gi-unknown",color="#1e6080",icon="",pursue="neutral",density=0,per100=0,
                    n_pathogenic=0,n_vus=0,n_benign=0,n_total=0,n_germline=0,
                    explanation="ClinVar returned no variants. This may be a network/API issue or the gene is not in ClinVar. Try searching by exact gene symbol (e.g. FLNA, not 'filamin a').",
                    pathogenic_list=[])
    elif total<5:
        return dict(verdict="UNDERSTUDIED",label=f"Only {total} ClinVar entries — protein may be understudied",
                    css="gi-unknown",color="#1e6080",icon="",pursue="neutral",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation=f"Only {total} ClinVar entries. Cannot make a confident genetics-based recommendation. Check OMIM and literature for disease evidence.",
                    pathogenic_list=pathogenic)
    elif n_p==0:
        return dict(verdict="NO DISEASE VARIANTS",label="Zero pathogenic / likely-pathogenic germline variants in ClinVar",
                    css="gi-redundant",color="#3a5a7a",icon="",pursue="deprioritise",density=0,per100=0,
                    n_pathogenic=0,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation=f"No germline pathogenic or likely-pathogenic variants among {total} ClinVar entries. ClinVar reflects what has been submitted, so this does not show the gene is redundant or unimportant.",
                    pathogenic_list=[])
    elif density<0.01 and n_p<5:
        return dict(verdict="VERY LOW DISEASE BURDEN",label=f"Only {n_p} of {len(germline)} germline variants are disease-causing",
                    css="gi-redundant",color="#4a6a30",icon="",pursue="caution",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation="Few of the submitted germline variants are pathogenic or likely pathogenic.",
                    pathogenic_list=pathogenic)
    elif per100>=1 or (n_p>=20 and density>=0.05):
        return dict(verdict="DISEASE-CRITICAL",label=f"{n_p} disease-causing variants · {per100:.1f} per 100 aa",
                    css="gi-critical",color="#ff2d55",icon="",pursue="prioritise",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation=f"{n_p} germline pathogenic or likely-pathogenic variants ({per100:.1f} per 100 residues) among {total} ClinVar entries.",
                    pathogenic_list=pathogenic)
    elif density>=0.05 or per100>=0.5:
        return dict(verdict="DISEASE-ASSOCIATED",label=f"{n_p} disease-causing variants ({density*100:.1f}% of total)",
                    css="gi-moderate",color="#ff8c42",icon="",pursue="proceed",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation="Meaningful disease association. Focus on confirmed P/LP variants only.",
                    pathogenic_list=pathogenic)
    else:
        return dict(verdict="MODERATE",label=f"{n_p} disease-causing variants ({density*100:.1f}%)",
                    css="gi-moderate",color="#ffd60a",icon="",pursue="selective",density=density,per100=per100,
                    n_pathogenic=n_p,n_vus=len(vus),n_benign=len(benign),n_total=total,n_germline=len(germline),
                    explanation="Some association but low density. Do not extrapolate to nearby benign entries.",
                    pathogenic_list=pathogenic)

# ─── CSV processing ─────────────────────────────────────────────────
def detect_csv_type(df):
    cols = " ".join(c.lower() for c in df.columns)
    vals = " ".join(str(v) for v in df.iloc[0].values if v)[:200].lower() if len(df) > 0 else ""
    
    # DMS (Deep Mutational Scanning) — specific detection
    if any(k in cols for k in ["effect_score","fitness","dms","ddg","stability","enrich"]):
        return "dms"
    if ("mutation" in cols or "variant" in cols) and ("effect" in cols or "score" in cols or "fitness" in cols):
        return "dms"
    # Check values for amino acid notation like G12D, A42V
    import re as _re
    if _re.search(r"[A-Z][0-9]+[A-Z*]", vals):
        return "dms"
    if any(k in cols for k in ["fold","logfc","log2","fpkm","rpkm","tpm","count","expr","deseq","edger"]): return "expression"
    if any(k in cols for k in ["chrom","chr","ref","alt","rsid","vcf","gnomad","af_","allele_freq"]): return "vcf_variants"
    if any(k in cols for k in ["accession","grch","protein change","protein_change","clinicalsignificance","clinical significance","condition","geneidsymbol","gene(s)","variationid"]): return "clinical_variants"
    if any(k in cols for k in ["variant","mutation","hgvs","clinvar","pathogen","classification"]): return "clinical_variants"
    if any(k in cols for k in ["protein","abundance","intensity","peptide","spectral","lfq","tmt"]): return "proteomics"
    if any(k in cols for k in ["pvalue","p_val","padj","fdr","qvalue","z_score","beta","odds_ratio"]): return "stats"
    if any(k in cols for k in ["cell","viability","ic50","ec50","apoptosis","proliferation","caspase"]): return "cell_assay"
    if any(k in cols for k in ["binding","kd","kon","koff","spr","itc","affinity","tm","shift"]): return "binding_assay"
    return "generic"

def summarise_assay(df, csv_type):
    n_rows,n_cols=len(df),len(df.columns)
    summaries={"expression":f"Gene expression dataset: {n_rows:,} genes/transcripts across {n_cols} columns. "
                             "Likely contains fold-change or normalised counts from RNA-seq, microarray, or qPCR.",
               "variants":f"Variant dataset: {n_rows:,} genetic variants across {n_cols} columns. "
                          "May include genomic positions, reference/alt alleles, or clinical classifications.",
               "proteomics":f"Proteomics dataset: {n_rows:,} proteins/peptides. "
                            "May include mass-spectrometry intensity values or protein abundance ratios.",
               "stats":f"Statistical results table: {n_rows:,} entries. "
                       "Contains p-values or adjusted significance scores — likely from a differential analysis.",
               "generic":f"Dataset: {n_rows:,} rows × {n_cols} columns. Column headers: {', '.join(df.columns[:6].tolist())}."}
    return summaries.get(csv_type, summaries["generic"])

# ─────────────────────────────────────────────────────────────────────────────
# CSV-driven workspace helpers — used by EVERY tab to render CSV-tailored content
# when a CSV is loaded. The CSV is the experiment; the protein search is a cue.
# ─────────────────────────────────────────────────────────────────────────────
def csv_extract_candidates(df, csv_type, max_n=15):
    if df is None or len(df) == 0: return []
    import re as _rex
    cols_l = {c: c.lower() for c in df.columns}
    gene_col = next((c for c, l in cols_l.items() if any(k == l or k+"s" == l or l.startswith(k+"_") or l.endswith("_"+k)
                     for k in ("gene","symbol","name","geneid","gene_id"))), None)
    fc_col   = next((c for c, l in cols_l.items() if any(k in l for k in ("fold","logfc","log2fc","log2_fold","lfc"))), None)
    eff_col  = next((c for c, l in cols_l.items() if any(k in l for k in ("effect","score","fitness","ddg","stability","enrich","activity","ic50","ki","kd"))), None)
    p_col    = next((c for c, l in cols_l.items() if any(k in l for k in ("pvalue","p_val","padj","fdr","qvalue","p.value","p-value"))), None)
    pos_col  = next((c for c, l in cols_l.items() if any(k in l for k in ("residue","position","resi","aa_pos","site"))), None)
    mut_col  = next((c for c, l in cols_l.items() if any(k in l for k in ("mutation","variant","change","substitution","hgvs","mut"))), None)
    primary_score = fc_col or eff_col
    if not primary_score:
        for c in df.columns:
            try:
                if df[c].dtype.kind in "fi": primary_score = c; break
            except Exception: pass
    if not primary_score: return []
    try:
        _w = df.copy()
        _w["_abs_score"] = _w[primary_score].astype(float).abs()
        if p_col:
            try: _w = _w[_w[p_col].astype(float) < 0.05]
            except Exception: pass
        _w = _w.sort_values("_abs_score", ascending=False).head(max_n)
        cands = []
        for i, (_, row) in enumerate(_w.iterrows(), 1):
            try:    score = float(row[primary_score])
            except: score = 0.0
            try:    pval = float(row[p_col]) if p_col else None
            except: pval = None
            g = ""
            if gene_col: g = str(row.get(gene_col, "")).strip()
            elif mut_col and pos_col is None:
                m = _rex.match(r"([A-Za-z*])([0-9]+)([A-Za-z*])", str(row.get(mut_col, "")))
                if m: g = f"pos {m.group(2)}"
            elif pos_col: g = f"pos {row.get(pos_col, '?')}"
            if not g: g = f"row {i}"
            label_units = "log₂FC" if (fc_col and primary_score == fc_col) else "effect"
            arrow = "↑" if score > 0 else ("↓" if score < 0 else "·")
            cands.append({"gene": g, "rank": i, "score": score, "abs_score": abs(score),
                          "score_label": f"{label_units} = {score:+.2f}", "arrow": arrow,
                          "p_value": pval, "raw_row": row.to_dict()})
        return cands
    except Exception: return []

def csv_section_header(title, sub=""):
    return (f"<div style='background:linear-gradient(90deg,rgba(56,189,248,.10),transparent);"
            f"border-left:3px solid #38bdf8;border-radius:6px;padding:.55rem .9rem;margin:1rem 0 .8rem;'>"
            f"<div style='color:#38bdf8;font-weight:800;font-size:.9rem;'>{title}</div>"
            + (f"<div style='color:var(--text2);font-size:.78rem;margin-top:2px;'>{sub}</div>" if sub else "")
            + "</div>")


def csv_is_active():
    return bool(st.session_state.get("csv_triage_active") and st.session_state.get("csv_df") is not None)

def csv_context():
    if not csv_is_active(): return None, None, []
    df = st.session_state.get("csv_df")
    ct = st.session_state.get("csv_type", "generic")
    cands = csv_extract_candidates(df, ct, max_n=15)
    return df, ct, cands



def render_csv_triage_tab(df, csv_type, cands):
    st.markdown(csv_section_header(" CSV Triage — Per-Candidate Ranking", "Each candidate scored against effect, significance, and variant context."), unsafe_allow_html=True)
    if not cands:
        st.info("No ranked candidates extractable from this CSV. Try a CSV with gene symbols + effect/fold-change columns.")
        return
    import pandas as _pd
    rows = []
    for c in cands:
        rows.append({"Rank": c['rank'], "Gene": c['gene'], "Direction": c['arrow'],
                     "Effect": f"{c['score']:+.2f}", "|Effect|": f"{c['abs_score']:.2f}",
                     "p-value": f"{c['p_value']:.2g}" if c.get('p_value') is not None else "—",
                     "Tier": ("Tier 1" if c['rank']<=3 else "Tier 2" if c['rank']<=8 else "Tier 3")})
    st.dataframe(_pd.DataFrame(rows), use_container_width=True, hide_index=True)



def render_csv_experiments_tab(df, csv_type, cands):
    st.markdown(csv_section_header(" Recommended Wet-Lab Experiments", "Based on signal type in your CSV."), unsafe_allow_html=True)
    if not cands:
        st.info("Upload a CSV with ranked signals to get experiment recommendations.")
        return
    top3 = [c['gene'] for c in cands[:3]]
    recipes = {
        "expression": [
            ("qPCR validation", f"Validate top hits ({', '.join(top3)}) by qPCR in 3 biological replicates. Use GAPDH/ACTB as housekeepers (verify they're stable in your condition first)."),
            ("Western blot", f"Confirm mRNA changes translate to protein for {top3[0]}. Use total protein normalization (Stain-Free or REVERT)."),
            ("Pathway enrichment", f"Run GSEA on the {len(df):,}-gene ranked list. MSigDB Hallmarks + GO BP. Look for enrichment in the relevant tissue's pathways."),
            ("Knockdown validation", f"siRNA/CRISPRi knockdown of {top3[0]} in the relevant cell line, then re-profile to confirm the dependency."),
        ],
        "dms": [
            ("Confirmatory single-variant", "Clone the top 3 deleterious positions individually. Validate by the same functional readout."),
            ("Structural inspection", "Map top-effect positions onto AlphaFold structure. Active site, interface, or core? That predicts mechanism."),
            ("Rescue experiment", "Co-express WT + deleterious mutant to test dominant-negative behaviour."),
        ],
        "clinical_variants": [
            ("ACMG re-classification", "Run each VUS through ACMG criteria. Focus on low gnomAD AF + high AlphaMissense."),
            ("Family segregation", "Request additional family members' genotypes — segregation is strong evidence (PP1/BS4)."),
            ("Functional assay", "For highest-suspicion VUS: minigene splicing or yeast complementation."),
        ],
        "binding_assay": [
            ("Counterscreen", f"Run top {len(top3)} hits against the closest off-target to assess selectivity."),
            ("Dose-response", "Move to 8–10 point dose-response in triplicate. Fit IC50/Ki properly."),
            ("Orthogonal assay", "Confirm hits in a mechanistically different assay to weed out artefacts."),
        ],
        "cell_assay": [
            ("Replicate + dose-response", f"Run top hits ({', '.join(top3)}) in dose-response, 3 biological replicates. IC50 with 95% CI."),
            ("Mechanism panel", "Apoptosis (Annexin V/PI), proliferation (Ki-67/EdU), cell-cycle (PI)."),
        ],
    }
    chosen = recipes.get(csv_type, [
        ("Replicate", f"Confirm top signals ({', '.join(top3)}) in biological replicates with a different operator."),
        ("Cross-reference", "Cross-check top genes against ClinVar pathogenic variants and gnomAD pLI > 0.9."),
        ("Orthogonal validation", "Use a mechanistically independent readout for the strongest effect."),
    ])
    for title, body in chosen:
        st.markdown(f"<div class='card'><h4>{title}</h4><p>{body}</p></div>", unsafe_allow_html=True)







def analyse_csv_standalone(df, csv_type, goal,
                           gene="", scored=None, variants=None,
                           am_scores=None, protein_length=1):
    """
    Full analysis of any uploaded CSV.
    Cross-references with ClinVar, AlphaMissense, and protein data where available.
    Returns list of (title, body, plotly_fig_or_None) tuples.
    """
    import re as _re2
    import numpy as _np2
    findings = []
    scored   = scored   or []
    variants = variants or []
    am_scores= am_scores or {}
    
    # ── Column detection ────────────────────────────────────────────────────────
    col_l   = {c: c.lower() for c in df.columns}
    pos_col = next((c for c,l in col_l.items() if any(k in l for k in
                    ["residue","position","pos","resi","aa_pos","site"])), None)
    mut_col = next((c for c,l in col_l.items() if any(k in l for k in
                    ["mutation","variant","change","substitution","hgvs","mut"])), None)
    eff_col = next((c for c,l in col_l.items() if any(k in l for k in
                    ["effect","score","fitness","ddg","stability","enrich",
                     "pathogenicity","functional","activity","log_ratio"])), None)
    fc_col  = next((c for c,l in col_l.items() if any(k in l for k in
                    ["fold","logfc","log2fc","log2_fold","lfc"])), None)
    p_col   = next((c for c,l in col_l.items() if any(k in l for k in
                    ["pvalue","p_val","padj","fdr","qvalue","p.value","p-value"])), None)
    gene_col= next((c for c,l in col_l.items() if any(k in l for k in
                    ["gene","symbol","name","geneid","gene_name","gene_id"])), None)
    int_col = next((c for c,l in col_l.items() if any(k in l for k in
                    ["intensity","abundance","lfq","tmt","count","area","peptide"])), None)
    exp_col = next((c for c,l in col_l.items() if any(k in l for k in
                    ["experiment","type","assay","condition","class"])), None)
    
    findings.append((" Dataset",
        f"**{csv_type.replace('_',' ').title()}** · {len(df):,} rows · {len(df.columns)} columns · "
        f"Columns: {', '.join(df.columns.tolist()[:8])}"))
    
    # ════════════════════════════════════════════════════════════════
    # DMS (Deep Mutational Scanning) — full cross-referenced analysis
    # ════════════════════════════════════════════════════════════════
    if csv_type == "dms":
        findings.append((" Assay type identified",
            "**Deep Mutational Scanning (DMS)** — measures the functional effect of every possible "
            "amino acid substitution in a protein. Effect score near 1.0 = highly deleterious. "
            "Near 0.0 = neutral/tolerated. Cross-referencing positions against ClinVar and AlphaMissense now."))
        
        # Parse mutations into structured data
        mutations = []
        for _, row in df.iterrows():
            pos    = None
            aa_wt  = None
            aa_alt = None
            # Get position
            if pos_col and _re2.match(r"\d+", str(row.get(pos_col,""))):
                try: pos = int(float(str(row[pos_col]).split(".")[0]))
                except: pass
            # Get mutation string
            mut_str = str(row.get(mut_col, "")) if mut_col else ""
            m = _re2.match(r"([A-Za-z*])([0-9]+)([A-Za-z*])", mut_str)
            if m:
                aa_wt  = m.group(1).upper()
                if pos is None: pos = int(m.group(2))
                aa_alt = m.group(3).upper()
            # Get effect score
            eff = None
            if eff_col:
                try: eff = float(row[eff_col])
                except: pass
            mutations.append({
                "pos": pos, "wt": aa_wt, "alt": aa_alt,
                "mut_str": mut_str, "eff": eff,
                "row": row.to_dict()
            })
        
        valid_muts = [m for m in mutations if m["pos"] is not None and m["eff"] is not None]
        
        if valid_muts:
            effs   = [m["eff"] for m in valid_muts]
            n_high = sum(1 for e in effs if e >= 0.7)
            n_med  = sum(1 for e in effs if 0.3 <= e < 0.7)
            n_low  = sum(1 for e in effs if e < 0.3)
            top5   = sorted(valid_muts, key=lambda x: -x["eff"])[:5]
            
            findings.append((" Effect score distribution",
                f"**{n_high}** highly deleterious (≥0.7) · **{n_med}** moderate (0.3–0.7) · "
                f"**{n_low}** tolerated (<0.3) · Mean score: **{sum(effs)/len(effs):.3f}**"))
            
            top5_text = " · ".join(
                f"{m['mut_str']} ({m['eff']:.2f})" for m in top5
            )
            findings.append((" Most deleterious mutations", top5_text))
            
            # ── ClinVar cross-reference ────────────────────────────────────
            if variants:
                cv_by_pos = {}
                for v in variants:
                    try: cv_by_pos[int(v.get("start",""))] = v
                    except: pass
                
                matched_cv = []
                for m in valid_muts:
                    if m["pos"] in cv_by_pos:
                        cv = cv_by_pos[m["pos"]]
                        matched_cv.append({
                            "mut": m["mut_str"],
                            "eff": m["eff"],
                            "cv_sig": cv.get("sig",""),
                            "cv_score": cv.get("score",0),
                            "cv_cond": cv.get("condition","")[:50],
                            "cv_url": cv.get("url",""),
                        })
                
                if matched_cv:
                    # Sort by combined score
                    matched_cv.sort(key=lambda x: -(x["eff"]*0.5 + x["cv_score"]/10))
                    agreement = sum(1 for x in matched_cv if
                                    (x["eff"]>=0.5 and x["cv_score"]>=3) or
                                    (x["eff"]<0.3 and x["cv_score"]<=1))
                    findings.append((" ClinVar cross-reference",
                        f"**{len(matched_cv)}** DMS positions match ClinVar variant positions. "
                        f"**{agreement}** show agreement between DMS effect score and ClinVar classification. "
                        f"Top concordant: " +
                        " · ".join(f"{x['mut']} (DMS={x['eff']:.2f}, ClinVar={x['cv_sig'][:20]})"
                                   for x in matched_cv[:3])))
                else:
                    findings.append(("ClinVar cross-reference",
                        f"No direct position overlap with ClinVar variants for {gene}. "
                        "This may indicate these are novel positions not yet in ClinVar — "
                        "high-scoring DMS positions are prime candidates for ClinVar submission."))
            
            # ── AlphaMissense cross-reference ──────────────────────────────
            if am_scores:
                am_concordant = []
                am_discordant = []
                for m in valid_muts:
                    pos_am = am_scores.get(m["pos"], {})
                    alt_am = pos_am.get(m["alt"], {}) if m["alt"] else {}
                    am_score = alt_am.get("score") if isinstance(alt_am, dict) else None
                    am_class = alt_am.get("class","") if isinstance(alt_am, dict) else ""
                    if am_score is not None:
                        dms_path = m["eff"] >= 0.5
                        am_path  = am_score >= 0.564
                        if dms_path == am_path:
                            am_concordant.append((m["mut_str"], m["eff"], am_score))
                        else:
                            am_discordant.append((m["mut_str"], m["eff"], am_score))
                
                if am_concordant or am_discordant:
                    findings.append((" AlphaMissense AI vs DMS agreement",
                        f"**{len(am_concordant)}** mutations where DMS functional data agrees with "
                        f"AlphaMissense AI prediction · **{len(am_discordant)}** discordant (investigate these — "
                        f"may reflect cell-type-specific effects not captured by structure-based AI). "
                        f"Concordant examples: " +
                        " · ".join(f"{t[0]} (DMS={t[1]:.2f}, AM={t[2]:.2f})"
                                   for t in am_concordant[:3])))
            
            # ── Hotspot analysis from DMS ──────────────────────────────────
            pos_effs = {}
            for m in valid_muts:
                if m["pos"] not in pos_effs:
                    pos_effs[m["pos"]] = []
                pos_effs[m["pos"]].append(m["eff"])
            pos_avg = {p: sum(e)/len(e) for p,e in pos_effs.items()}
            
            hot_positions = sorted(
                [(p, avg) for p, avg in pos_avg.items() if avg >= 0.65],
                key=lambda x: -x[1]
            )
            if hot_positions:
                findings.append((" DMS hotspot positions",
                    f"**{len(hot_positions)}** positions where the majority of substitutions are deleterious (avg effect ≥0.65) — "
                    f"these are structurally or functionally critical residues. "
                    f"Top positions: " +
                    ", ".join(f"pos {p} (avg={a:.2f})" for p,a in hot_positions[:8])))
            
            # ── Experimental triage from DMS ───────────────────────────────
            findings.append((" Recommended next experiments",
                f"**1. Validate top {min(5,n_high)} deleterious mutations biochemically** — "
                f"Express {', '.join(m['mut_str'] for m in top5[:3])} as recombinant protein and measure activity vs wild-type (thermal shift, enzyme assay). "
                f"**2. Cross-reference with patient data** — submit high-effect positions to ClinVar search; "
                f"check if any patient carries these variants. "
                f"**3. Structure-guided targeting** — map deleterious hotspot positions onto AlphaFold structure "
                f"to identify whether they cluster in a druggable pocket. "
                f"**4. CRISPR knock-in** — introduce top 3 high-effect mutations into endogenous locus "
                f"and measure cellular phenotype (viability, morphology, signalling)."))
    
    # ════════════════════════════════════════════════════════════════
    # EXPRESSION (RNA-seq / microarray / qPCR)
    # ════════════════════════════════════════════════════════════════
    elif csv_type == "expression":
        # ── CSV-first: surface the data's own top candidates BEFORE any cross-ref ──
        if fc_col and gene_col and df[fc_col].dtype in [float, 'float64', int, 'int64']:
            try:
                # Rank by absolute fold-change, optionally filtered by significance
                _df_rank = df.copy()
                _df_rank["_abs_fc"] = _df_rank[fc_col].abs()
                if p_col and df[p_col].dtype in [float, 'float64']:
                    _df_rank = _df_rank[_df_rank[p_col] < 0.05]
                _df_rank = _df_rank.sort_values("_abs_fc", ascending=False).head(10)
                if len(_df_rank) > 0:
                    _lines = []
                    for _, _r in _df_rank.iterrows():
                        _g = str(_r[gene_col])
                        _f = float(_r[fc_col])
                        _arrow = "↑" if _f > 0 else "↓"
                        _p_str = f" · p={float(_r[p_col]):.2g}" if p_col else ""
                        _lines.append(f"**{_g}** {_arrow} log₂FC = {_f:+.2f}{_p_str}")
                    findings.append((" Top candidates from your CSV",
                        "Strongest signals in this dataset, ranked by |log₂FC|" +
                        (" (filtered to p < 0.05)" if p_col else "") + ":<br>" +
                        "<br>".join(_lines) +
                        "<br><br><i>Search any of these in the protein box above to drill into its ClinVar/gnomAD/structural profile.</i>"))
            except Exception: pass

        # ── Now the standard summary stats ───────────────────────────────────────
        if fc_col and df[fc_col].dtype in [float, 'float64', int, 'int64']:
            up   = (df[fc_col] > 1).sum()
            dn   = (df[fc_col] < -1).sum()
            neut = len(df) - up - dn
            findings.append((" Differential expression",
                f"**{up:,}** upregulated (log₂FC > 1) · **{dn:,}** downregulated (log₂FC < −1) · "
                f"**{neut:,}** unchanged · Mean |FC|: {df[fc_col].abs().mean():.2f}"))
        if p_col and df[p_col].dtype in [float, 'float64']:
            sig = (df[p_col] < 0.05).sum()
            sig01 = (df[p_col] < 0.01).sum()
            findings.append((" Statistical significance",
                f"**{sig:,}** significant at p < 0.05 · **{sig01:,}** at p < 0.01 out of {len(df):,} total. "
                f"Multiple testing correction applied? Check for 'padj' or 'FDR' column."))
        # ── Only NOW cross-reference with the searched protein, if there is one ───
        if fc_col and p_col and gene_col:
            try:
                sig_mask = (df[p_col] < 0.05) & (df[fc_col].abs() > 1)
                sig_genes = df.loc[sig_mask, gene_col].dropna().astype(str).tolist()
                if sig_genes:
                    findings.append((" All significantly changed genes",
                        f"{', '.join(sig_genes[:20])}{f' … (+{len(sig_genes)-20} more)' if len(sig_genes)>20 else ''} "
                        f"— {len(sig_genes)} total"))
                if gene and any(str(gene).upper() == g.upper() for g in sig_genes):
                    fc_val = df.loc[df[gene_col].astype(str).str.upper()==gene.upper(), fc_col].values[0]
                    findings.append((f" Cross-reference: {gene} is in this CSV",
                        f"**{gene}** is significantly differentially expressed — log₂FC = {fc_val:.2f}. "
                        f"This functional signal aligns with the protein you're analysing. "
                        f"Cross-reference: does expression change in the disease tissue where ClinVar variants are found?"))
            except: pass
        findings.append((" Recommended next experiments",
            "**1. Pathway enrichment** — run GSEA or ORA on significantly changed genes using MSigDB hallmarks. "
            "**2. ClinVar intersection** — which significantly changed genes also carry ClinVar pathogenic variants? These are highest-priority. "
            "**3. Validation** — qPCR validate top 5–10 hits in independent samples before protein-level follow-up. "
            "**4. Protein level** — run western blot or proteomics to confirm mRNA changes translate to protein abundance changes."))
    
    # ════════════════════════════════════════════════════════════════
    # CLINICAL VARIANTS / VCF
    # ════════════════════════════════════════════════════════════════
    elif csv_type in ("clinical_variants", "vcf_variants"):
        import re as _re3
        import plotly.graph_objects as _go2

        # ── Detect real ClinVar export columns ──────────────────────────────
        # Standard ClinVar download columns: Name, Gene(s), Protein change,
        # Condition(s), Clinical significance (Last reviewed), Accession, etc.
        gene_col2   = next((c for c in df.columns if c.lower() in
                           ["gene(s)","gene","genes","gene_symbol","symbol"]), None)
        sig_col2    = next((c for c in df.columns if any(k in c.lower() for k in
                           ["significance","classification","clinical sig","clinsig","pathogen"])), None)
        cond_col    = next((c for c in df.columns if any(k in c.lower() for k in
                           ["condition","disease","phenotype","trait"])), None)
        prot_col    = next((c for c in df.columns if any(k in c.lower() for k in
                           ["protein change","protein_change","hgvsp","p.","amino"])), None)
        acc_col     = next((c for c in df.columns if any(k in c.lower() for k in
                           ["accession","rcv","vcv","id"])), None)
        chrom_col   = next((c for c in df.columns if any(k in c.lower() for k in
                           ["chromosome","chr","grch38chrom","grch37chrom"])), None)
        loc_col     = next((c for c in df.columns if any(k in c.lower() for k in
                           ["location","position","start","grch38loc","grch37loc"])), None)
        review_col  = next((c for c in df.columns if any(k in c.lower() for k in
                           ["review","star","status","last reviewed"])), None)
        name_col    = next((c for c in df.columns if c.lower() in ["name","variant name","title"]), None)

        # ── Classification parsing ───────────────────────────────────────────
        PATH_KEYS  = ["pathogenic","likely pathogenic","pathogenic/likely pathogenic"]
        VUS_KEYS   = ["uncertain significance","conflicting","vus"]
        BENIGN_KEYS= ["benign","likely benign","benign/likely benign"]

        def classify_sig(s):
            s = str(s).lower().strip()
            if any(k in s for k in PATH_KEYS):  return "Pathogenic/LP"
            if any(k in s for k in VUS_KEYS):    return "VUS"
            if any(k in s for k in BENIGN_KEYS): return "Benign/LB"
            return "Other"

        if sig_col2:
            df["_sig_class"] = df[sig_col2].apply(classify_sig)
        else:
            df["_sig_class"] = "Other"

        n_path  = (df["_sig_class"]=="Pathogenic/LP").sum()
        n_vus   = (df["_sig_class"]=="VUS").sum()
        n_ben   = (df["_sig_class"]=="Benign/LB").sum()
        n_other = (df["_sig_class"]=="Other").sum()
        total   = len(df)

        findings.append((" Classification breakdown",
            f"**{n_path:,}** disease-causing (Pathogenic/LP) · **{n_vus:,}** unknown significance (VUS) · "
            f"**{n_ben:,}** harmless (Benign/LB) · **{n_other:,}** other · **{total:,}** total. "
            f"Pathogenic rate: **{n_path/max(total,1)*100:.1f}%**. "
            f"A high VUS fraction ({n_vus/max(total,1)*100:.0f}%) means functional studies are needed "
            f"to reclassify variants — this is where DMS or CRISPR knock-in adds the most value."))

        # ── Gene breakdown ───────────────────────────────────────────────────
        if gene_col2:
            gene_path_counts = {}
            gene_vus_counts  = {}
            for _, row in df.iterrows():
                raw_genes = str(row.get(gene_col2,""))
                for g2 in _re3.split(r"[;,|/]", raw_genes):
                    g2 = g2.strip()
                    if not g2 or g2.lower() in ("nan","","none","-"): continue
                    sc = row.get("_sig_class","Other")
                    if sc == "Pathogenic/LP":
                        gene_path_counts[g2] = gene_path_counts.get(g2,0)+1
                    elif sc == "VUS":
                        gene_vus_counts[g2]  = gene_vus_counts.get(g2,0)+1

            top_path_genes = sorted(gene_path_counts.items(), key=lambda x:-x[1])[:15]
            top_vus_genes  = sorted(gene_vus_counts.items(),  key=lambda x:-x[1])[:10]

            if top_path_genes:
                findings.append((" Top genes by confirmed disease-causing variants",
                    "Ranked by pathogenic/likely pathogenic variant count — these are the highest-priority targets. "
                    "Source: ClinVar. Top 10: " +
                    " · ".join(f"**{g}** ({n})" for g,n in top_path_genes[:10])))
                findings.append((" Primary therapeutic target from this dataset",
                    f"**{top_path_genes[0][0]}** leads with {top_path_genes[0][1]} confirmed disease-causing variants. "
                    f"**Hypothesis:** Variants in {top_path_genes[0][0]} are most likely to be causally linked to the associated diseases. "
                    f"This gene should be the first target for functional validation. "
                    f"Cross-reference against genomic integrity score in Protellect by searching {top_path_genes[0][0]} above. "
                    f"Compare with runner-up {top_path_genes[1][0]} ({top_path_genes[1][1]} variants) to assess whether a shared pathway exists."))

            # Check if searched protein is in this dataset
            if gene and gene_path_counts.get(gene,0) > 0:
                findings.append((f" {gene} found in this dataset",
                    f"**{gene}** has {gene_path_counts[gene]} pathogenic variants and "
                    f"{gene_vus_counts.get(gene,0)} VUS in this dataset. "
                    f"This is consistent with the ClinVar genomic integrity profile shown above. "
                    f"These variants should be cross-referenced with the Protellect triage table for position-specific analysis."))

        # ── Condition / disease breakdown ────────────────────────────────────
        if cond_col:
            cond_counts2 = {}
            for val in df[cond_col].dropna().astype(str):
                for c2 in _re3.split(r"[;|]", val):
                    c2 = c2.strip()
                    if c2 and c2.lower() not in ("not provided","not specified","","nan","-"):
                        cond_counts2[c2] = cond_counts2.get(c2,0)+1
            top_conds = sorted(cond_counts2.items(), key=lambda x:-x[1])[:12]
            if top_conds:
                findings.append((" Top associated diseases in this dataset",
                    f"**{len(cond_counts2)}** unique disease/condition terms. Most common: " +
                    " · ".join(f"**{c}** ({n})" for c,n in top_conds[:8])))

        # ── Protein change / variant type analysis ───────────────────────────
        if prot_col:
            mis_n   = df[prot_col].astype(str).str.contains(r"[A-Za-z][0-9]+[A-Za-z]", regex=True, na=False).sum()
            stop_n  = df[prot_col].astype(str).str.contains(r"Ter|\*|Stop", regex=True, na=False).sum()
            fs_n    = df[prot_col].astype(str).str.contains(r"fs|frameshift", case=False, regex=True, na=False).sum()
            del_n   = df[prot_col].astype(str).str.contains(r"del", case=False, regex=True, na=False).sum()
            dup_n   = df[prot_col].astype(str).str.contains(r"dup", case=False, regex=True, na=False).sum()
            spl_n   = df[prot_col].astype(str).str.contains(r"splice|IVS", case=False, regex=True, na=False).sum()

            findings.append((" Variant type breakdown (from protein change notation)",
                f"**{mis_n:,}** missense (letter-swap) · **{stop_n:,}** stop-gain (early termination) · "
                f"**{fs_n:,}** frameshift (reading-frame shift) · **{del_n:,}** deletions · "
                f"**{dup_n:,}** duplications · **{spl_n:,}** splice-site disruptions. "
                f"**Clinical relevance:** Stop-gain and frameshift variants cause complete protein loss (LoF) — "
                f"these are typically the most severe. Missense variants may be gain- or loss-of-function depending on position."))

        # ── Review star quality ──────────────────────────────────────────────
        if review_col:
            star_map = {
                "practice guideline": 4,
                "reviewed by expert panel": 4,
                "criteria provided, multiple submitters": 3,
                "criteria provided, single submitter": 2,
                "no assertion criteria provided": 1,
                "no classification provided": 0,
            }
            star_counts = {}
            for val in df[review_col].dropna().astype(str):
                matched = next((v for k,v in star_map.items() if k in val.lower()), 0)
                star_counts[matched] = star_counts.get(matched,0)+1
            high_conf = star_counts.get(3,0)+star_counts.get(4,0)
            low_conf  = star_counts.get(0,0)+star_counts.get(1,0)
            findings.append((" Evidence quality (ClinVar review status)",
                f"**{high_conf:,}** high-confidence (≥2 submitters / expert reviewed) · "
                f"**{low_conf:,}** low-confidence (single submitter or no criteria). "
                f"Only the high-confidence pathogenic variants should drive experimental decisions. "
                f"Low-confidence variants require independent functional validation before acting on them."))

        # ── Chromosome / locus distribution ─────────────────────────────────
        if chrom_col:
            chrom_counts = df[chrom_col].astype(str).value_counts().head(10)
            if len(chrom_counts) > 1:
                findings.append((" Chromosomal distribution",
                    "Variants span chromosomes: " +
                    " · ".join(f"Chr{c}: {n}" for c,n in chrom_counts.items()
                               if c.lower() not in ("nan","")) +
                    ". Multi-chromosomal distribution suggests this is a pan-disease or multi-gene panel dataset."))

        # ── Actionable triage: P/LP with no functional evidence ─────────────
        if n_path > 0:
            findings.append((" Actionable finding — variants requiring functional validation",
                f"**{n_path:,} pathogenic/likely pathogenic variants** identified. Of these, the majority "
                f"lack functional experimental evidence (typical for ClinVar submissions). "
                f"**Priority action:** Cross-reference each P/LP variant with: "
                f"(1) AlphaMissense score ≥0.564 (AI pathogenicity), "
                f"(2) Presence in gnomAD at <0.001% allele frequency (population rarity), "
                f"(3) Located in a known functional domain (≥5Å from active site = lower priority). "
                f"Variants passing all 3 filters are highest-priority for CRISPR knock-in validation."))

        # ── VUS reclassification opportunity ────────────────────────────────
        if n_vus > 50:
            findings.append((" VUS reclassification opportunity",
                f"**{n_vus:,} variants of uncertain significance** — these represent significant scientific and "
                f"clinical value if reclassified. **Strategy:** Run deep mutational scan (DMS) on the proteins "
                f"with the most VUS to generate functional scores for every substitution. "
                f"VUS at positions where DMS effect score ≥0.7 AND AlphaMissense ≥0.564 should be upgraded to "
                f"Likely Pathogenic (LP) and submitted to ClinVar. "
                f"This is one of the highest-impact contributions a research group can make to the field."))

        # ── Recommended experiments ──────────────────────────────────────────
        findings.append((" Experimental triage — what to do with this dataset",
            f"**Step 1 (Free, 1 day):** Import this file into Protellect's protein search for each top gene "
            f"({', '.join(g for g,_ in top_path_genes[:3]) if gene_col2 and top_path_genes else 'top genes'}). "
            f"The triage tab will map each P/LP variant onto the 3D AlphaFold structure. "
            f"**Step 2 (Free, 2 days):** Cross-reference P/LP variants with AlphaMissense scores — "
            f"concordant high-scoring variants are highest confidence. "
            f"**Step 3 ($2K–5K, 1–2 weeks):** Biochemical activity assay on recombinant WT vs top 5 P/LP variants "
            f"to confirm destabilisation. "
            f"**Step 4 ($25K, 8–10 weeks):** CRISPR knock-in of top 3 variants — if phenotype confirmed, "
            f"you have gold-standard ClinGen PS3 functional evidence for ClinVar reclassification."))


    elif csv_type == "proteomics":
        # ── Full proteomics analysis ────────────────────────────────────────
        import re as _re_p
        gene_col_p  = next((c for c in df.columns if any(k in c.lower() for k in
                           ["gene","protein","symbol","accession","uniprot","entry","majority"])),None)
        int_cols_p  = [c for c in df.columns if any(k in c.lower() for k in
                       ["intensity","lfq","tmt","abundance","area","ibaq","ms/ms"])]
        pep_col     = next((c for c in df.columns if "peptide" in c.lower()),None)
        ratio_col   = next((c for c in df.columns if any(k in c.lower() for k in
                           ["ratio","fold","log2","log fc","lfc"])),None)
        pval_col_p  = next((c for c in df.columns if any(k in c.lower() for k in
                           ["pvalue","p_val","padj","fdr","q value","significance"])),None)
        seq_col     = next((c for c in df.columns if any(k in c.lower() for k in
                           ["sequence","peptide sequence","modified sequence"])),None)

        n_proteins  = len(df)
        n_with_int  = int((df[int_cols_p[0]] > 0).sum()) if int_cols_p and df[int_cols_p[0]].dtype in [float,"float64"] else 0
        n_samples   = len(int_cols_p)

        findings.append((" Proteomics dataset",
            f"**{n_proteins:,}** proteins/peptides · **{n_samples}** quantification channel(s) detected · "
            f"**{n_with_int:,}** with valid intensity values. "
            f"{'MaxQuant-style output detected (LFQ/iBAQ columns present).' if any('lfq' in c.lower() or 'ibaq' in c.lower() for c in int_cols_p) else ''} "
            f"{'TMT/iTRAQ multiplexed experiment detected.' if any('tmt' in c.lower() or 'reporter' in c.lower() for c in int_cols_p) else ''} "
            f"Quantification: {', '.join(int_cols_p[:4])}{'...' if len(int_cols_p)>4 else ''}"))

        if int_cols_p:
            ic = int_cols_p[0]
            vals = df[ic].dropna()
            if vals.dtype in [float,"float64"] and len(vals)>0:
                nonzero = vals[vals>0]
                dynamic_range = nonzero.max()/nonzero.min() if len(nonzero)>1 and nonzero.min()>0 else 0
                findings.append((" Intensity statistics",
                    f"Range: {vals.min():.2e} – {vals.max():.2e} · "
                    f"Median: {vals.median():.2e} · "
                    f"Dynamic range: {dynamic_range:.0f}× · "
                    f"Missing values: {(vals==0).sum() + vals.isna().sum():,} ({(vals==0).sum()+vals.isna().sum()}/{len(vals)*100:.0f}%). "
                    f"**Interpretation:** Dynamic range >10,000× is expected for good LC-MS data. "
                    f"High missing values (>30%) indicate the experiment may need imputation before statistical analysis."))

        if ratio_col and df[ratio_col].dtype in [float,"float64"]:
            up2  = (df[ratio_col]>1).sum()
            dn2  = (df[ratio_col]<-1).sum()
            neut2= len(df)-up2-dn2
            findings.append((" Differential protein abundance",
                f"**{up2:,}** upregulated (log₂ratio > 1) · **{dn2:,}** downregulated (log₂ratio < −1) · "
                f"**{neut2:,}** unchanged. Mean ratio: {df[ratio_col].mean():.2f}. "
                f"Upregulated proteins are candidates for inhibition targets (if causally linked to disease). "
                f"Downregulated proteins may indicate loss-of-function or degradation — cross-reference with ClinVar LoF variants."))

        if pval_col_p and df[pval_col_p].dtype in [float,"float64"]:
            sig_p = (df[pval_col_p]<0.05).sum()
            sig_p01 = (df[pval_col_p]<0.01).sum()
            findings.append((" Statistical significance",
                f"**{sig_p:,}** significant at p<0.05 · **{sig_p01:,}** at p<0.01. "
                f"For proteomics, use BH-corrected FDR (padj) rather than raw p-values — "
                f"multiple testing correction is critical with {n_proteins:,} proteins tested simultaneously."))

        if gene_col_p and gene:
            matches = df[df[gene_col_p].astype(str).str.upper().str.contains(gene.upper(),na=False)]
            if not matches.empty:
                int_val = f"{matches.iloc[0][int_cols_p[0]]:.2e}" if int_cols_p else "N/A"
                ratio_val = f"{matches.iloc[0][ratio_col]:.2f}" if ratio_col and ratio_col in matches.columns else "N/A"
                findings.append((f" {gene} detected in this proteomics dataset",
                    f"**{gene}** found — intensity: {int_val} · ratio: {ratio_val}. "
                    f"Compare this abundance with the disease tissue expression data shown in the Case Study tab. "
                    f"If {gene} is downregulated AND carries ClinVar LoF variants, this supports haploinsufficiency as the disease mechanism. "
                    f"If upregulated AND has GoF variants, supports gain-of-function oncogenic mechanism."))

        if pep_col:
            pep_vals = df[pep_col].dropna()
            findings.append((" Peptide coverage",
                f"Peptide column detected ({pep_col}) · {len(pep_vals):,} peptide entries. "
                f"Ensure ≥2 unique peptides per protein for confident identification (standard proteomics QC threshold)."))

        findings.append((" Recommended experiments",
            f"**1. Normalisation check (free):** Verify TIC, iBAQ, or LFQ normalisation was applied. "
            f"Plot intensity distributions across samples — they should overlap after normalisation. "
            f"**2. Missing value imputation ($0, 1 day):** Use Perseus MinProb or DreamAI imputation for proteins missing in >30% of samples. "
            f"**3. Statistical testing ($0, 1 day):** Use MSstats (R/Bioconductor) for rigorous protein-level differential analysis with proper variance modelling. "
            f"**4. Pathway enrichment ($0, 2 days):** STRING network enrichment on {up2 if ratio_col else 'significant'} upregulated proteins to identify dysregulated pathways. "
            f"**5. PTM analysis ($8K, 3 weeks):** Run phosphoproteomics on same samples — cross-reference phosphosites with PhosphoSitePlus and your protein's functional domains. "
            f"**6. Interaction confirmation ($20K, 6 weeks):** For top hits, AP-MS pulldown to confirm physical interaction with {gene if gene else 'target protein'}."))

    elif csv_type == "cell_assay":
        # ── Full cell viability / phenotypic assay analysis ─────────────────
        via_col  = next((c for c in df.columns if any(k in c.lower() for k in
                        ["viability","survival","growth","proliferation","confluency"])),None)
        ic50_col = next((c for c in df.columns if any(k in c.lower() for k in
                        ["ic50","ec50","cc50","ki","potency","ac50"])),None)
        apo_col  = next((c for c in df.columns if any(k in c.lower() for k in
                        ["apoptosis","caspase","annexin","dead","death"])),None)
        treat_col= next((c for c in df.columns if any(k in c.lower() for k in
                        ["treatment","compound","drug","condition","sample","inhibitor"])),None)
        conc_col = next((c for c in df.columns if any(k in c.lower() for k in
                        ["conc","concentration","dose","µm","um","nm","molar"])),None)
        time_col = next((c for c in df.columns if any(k in c.lower() for k in
                        ["time","hour","day","h","timepoint"])),None)
        cell_col = next((c for c in df.columns if any(k in c.lower() for k in
                        ["cell","line","model","cellline"])),None)

        n_rows_c  = len(df)
        n_treats  = df[treat_col].nunique() if treat_col else "?"
        n_cells   = df[cell_col].nunique() if cell_col else "?"

        findings.append((" Cell assay dataset",
            f"**{n_rows_c:,}** measurements · **{n_treats}** treatment conditions · "
            f"**{n_cells}** cell line(s). "
            f"Columns detected: viability={'' if via_col else ''} · IC50={'' if ic50_col else ''} · "
            f"apoptosis={'' if apo_col else ''} · treatment={'' if treat_col else ''} · "
            f"concentration={'' if conc_col else ''}."))

        if via_col and df[via_col].dtype in [float,"float64"]:
            mean_v = df[via_col].mean()
            min_v  = df[via_col].min()
            max_v  = df[via_col].max()
            n_low  = (df[via_col] < 70).sum()
            n_dead = (df[via_col] < 30).sum()
            findings.append((" Viability summary",
                f"Mean: **{mean_v:.1f}%** · Range: {min_v:.1f}%–{max_v:.1f}%. "
                f"**{n_low}** measurements below 70% viability (cytotoxic threshold). "
                f"**{n_dead}** below 30% (severe toxicity / cell death). "
                f"**Interpretation:** Viability <70% triggers investigation of mechanism — "
                f"is this apoptosis (programmed), necrosis (uncontrolled), or autophagy?"))

        if treat_col and via_col and df[via_col].dtype in [float,"float64"]:
            treat_means = df.groupby(treat_col)[via_col].mean().sort_values()
            if len(treat_means) > 1:
                worst = treat_means.index[0]
                best  = treat_means.index[-1]
                findings.append((" Most vs least cytotoxic conditions",
                    f"Most cytotoxic: **{worst}** (mean viability {treat_means.iloc[0]:.1f}%) · "
                    f"Least: **{best}** ({treat_means.iloc[-1]:.1f}%). "
                    f"**Hypothesis:** If {worst} targets {gene if gene else 'your protein'}, "
                    f"the viability reduction is consistent with on-target activity. "
                    f"Rescue experiment required: re-introduce wild-type protein to confirm specificity."))

        if ic50_col and df[ic50_col].dtype in [float,"float64"]:
            ic50_vals = df[ic50_col].dropna()
            findings.append((" IC50 / potency values",
                f"Range: {ic50_vals.min():.3e} – {ic50_vals.max():.3e}. "
                f"Median IC50: {ic50_vals.median():.3e}. "
                f"**Interpretation:** IC50 <100nM = drug-like potency. "
                f"IC50 >10µM = high concentration needed, selectivity likely poor — may need scaffold optimisation. "
                f"Compare against therapeutic index (IC50 tumour vs IC50 normal cells)."))

        if apo_col and df[apo_col].dtype in [float,"float64"]:
            mean_apo = df[apo_col].mean()
            findings.append((" Apoptosis / cell death readout",
                f"Mean apoptosis signal: **{mean_apo:.1f}%**. "
                f"**Mechanism interpretation:** "
                f"{'High apoptosis suggests caspase-dependent programmed cell death — validate with caspase 3/7 activity assay and Annexin V staining.' if mean_apo>30 else 'Low apoptosis signal — cell death may be via necrosis or autophagy. Run LDH release assay and LC3 immunofluorescence to distinguish.'}"))

        if n_cells != "?" and n_cells > 1:
            findings.append((" Multi-cell-line data — selectivity check required",
                f"Data spans {n_cells} cell lines. "
                f"**Critical check:** Does the effect vary across cell lines? "
                f"If effect is only in cancer lines but not normal cells — suggests on-target specificity. "
                f"If effect is in all lines equally — may be off-target toxicity, not a therapeutic mechanism. "
                f"Calculate selectivity index = IC50(normal) / IC50(cancer)."))

        findings.append((" Recommended next experiments",
            f"**1. Mechanistic validation ($2K, 1 week):** Western blot for cleaved caspase 3/7 (apoptosis), "
            f"LC3-II/LC3-I ratio (autophagy), γH2AX (DNA damage) to identify cell death mechanism. "
            f"**2. Rescue experiment ($3K, 2 weeks):** Re-express wild-type {gene if gene else 'target protein'} "
            f"in cells — if it rescues viability, the effect is on-target. "
            f"**3. Selectivity panel ($5K, 3 weeks):** Test in ≥3 cancer and ≥2 normal cell lines. "
            f"**4. In vivo validation ($80K, 12 weeks):** Only if rescue confirmed — "
            f"xenograft model using most sensitive cell line. "
            f"**5. Biomarker correlation:** Do cells with ClinVar pathogenic variants in {gene if gene else 'target'} "
            f"show greater sensitivity? This defines your precision medicine patient population."))

    elif csv_type == "binding_assay":
        # ── Full binding / biophysical assay analysis ────────────────────────
        kd_col   = next((c for c in df.columns if any(k in c.lower() for k in
                        ["kd","dissociation","affinity","koff/kon","equilibrium"])),None)
        kon_col  = next((c for c in df.columns if any(k in c.lower() for k in
                        ["kon","ka","association","on rate"])),None)
        koff_col = next((c for c in df.columns if any(k in c.lower() for k in
                        ["koff","kd_rate","dissociation rate","off rate"])),None)
        tm_col   = next((c for c in df.columns if any(k in c.lower() for k in
                        ["tm","melting","delta tm","shift","thermal"])),None)
        analyte_col = next((c for c in df.columns if any(k in c.lower() for k in
                           ["analyte","compound","ligand","drug","molecule","name","id"])),None)
        conc_col2= next((c for c in df.columns if any(k in c.lower() for k in
                        ["conc","concentration","µm","nm","molar"])),None)
        rmax_col = next((c for c in df.columns if any(k in c.lower() for k in ["rmax","rsp","response max"])),None)

        n_analytes = df[analyte_col].nunique() if analyte_col else len(df)
        assay_type = ("Surface Plasmon Resonance (SPR/Biacore)" if koff_col and kon_col else
                      "Thermal Shift Assay (TSA/DSF)" if tm_col else
                      "Equilibrium binding (ITC/FP/HTRF)" if kd_col else "Binding assay")

        findings.append((" Binding assay identified",
            f"**{assay_type}** · {n_analytes} analyte(s) tested · {len(df):,} data points. "
            f"Columns: KD={'' if kd_col else ''} · kon={'' if kon_col else ''} · "
            f"koff={'' if koff_col else ''} · Tm shift={'' if tm_col else ''}."))

        if kd_col and df[kd_col].dtype in [float,"float64"]:
            kd_vals = df[kd_col].dropna()
            best_kd  = kd_vals.min()
            worst_kd = kd_vals.max()
            n_potent = (kd_vals < 100e-9).sum()  # sub-100nM
            findings.append((" Binding affinity (KD) summary",
                f"Best KD: **{best_kd:.2e} M** · Weakest: {worst_kd:.2e} M · "
                f"**{n_potent}** analytes with KD < 100 nM (drug-like affinity range). "
                f"**Interpretation:** KD < 1 nM = very high affinity (antibody-like). "
                f"1–100 nM = drug-like. 100 nM–1 µM = moderate, may need optimisation. "
                f">1 µM = weak — likely not suitable as drug lead without significant improvement."))
            if analyte_col:
                best_row = df.loc[df[kd_col].idxmin()]
                best_name = str(best_row.get(analyte_col,"Unknown"))
                findings.append((f" Highest affinity binder",
                    f"**{best_name}** with KD = {best_kd:.2e} M. "
                    f"**Hypothesis:** If {best_name} binds the pathogenic hotspot region identified in Protellect's structure analysis, "
                    f"it may stabilise the wild-type conformation and rescue the pathogenic variant's functional deficit. "
                    f"Validate by testing whether binding is reduced for pathogenic variant protein vs wild-type."))

        if kon_col and koff_col and df[kon_col].dtype in [float,"float64"]:
            kon_mean  = df[kon_col].mean()
            koff_mean = df[koff_col].mean()
            findings.append((" Kinetics — on-rate / off-rate",
                f"Mean kon (association rate): {kon_mean:.2e} M⁻¹s⁻¹ · "
                f"Mean koff (dissociation rate): {koff_mean:.2e} s⁻¹. "
                f"**Interpretation:** Drug residence time = 1/koff = {1/koff_mean:.0f}s. "
                f"{'Long residence time (slow koff) — excellent for sustained target engagement in vivo.' if koff_mean < 0.001 else 'Short residence time — may need formulation strategy to maintain therapeutic exposure.'}"))

        if tm_col and df[tm_col].dtype in [float,"float64"]:
            tm_vals = df[tm_col].dropna()
            findings.append((" Thermal stability shift (ΔTm)",
                f"Range: {tm_vals.min():.1f}°C – {tm_vals.max():.1f}°C shift. "
                f"**{(tm_vals >= 1).sum()}** compounds shift Tm ≥1°C (significant stabilisation threshold). "
                f"**{(tm_vals >= 3).sum()}** shift ≥3°C (strong stabilisation — prioritise these). "
                f"Compounds with ΔTm ≥3°C are stabilising the protein fold — "
                f"directly relevant if pathogenic variants cause protein instability."))

        findings.append((" Recommended next experiments",
            f"**1. Validate binding site ($5K, 3 weeks):** Competitive displacement assay with known binder — "
            f"confirm top compound binds the hotspot pocket identified in Protellect's druggability map. "
            f"**2. Structural confirmation ($50K, 2–4 months):** Cryo-EM or X-ray co-crystal structure of protein + top binder — "
            f"confirms binding mode and guides medicinal chemistry. "
            f"**3. Cellular target engagement ($8K, 2 weeks):** NanoBRET or CETSA in cells — "
            f"confirms biophysical binding translates to cellular target engagement. "
            f"**4. Selectivity panel ($15K, 4 weeks):** Test top binder against closest homologs "
            f"to confirm selectivity. Off-target binding causes toxicity. "
            f"**5. SAR expansion ($30K, 3 months):** If lead confirmed, synthesise 20–30 analogs "
            f"to improve KD and selectivity simultaneously."))

    elif csv_type == "stats":
        # ── GWAS / statistical results ──────────────────────────────────────
        pval_col_s = next((c for c in df.columns if any(k in c.lower() for k in
                          ["pvalue","p_val","padj","fdr","p.value","p-value","p_lrt"])),None)
        eff_col_s  = next((c for c in df.columns if any(k in c.lower() for k in
                          ["beta","effect","or","odds_ratio","effect_size","b_ml","b"])),None)
        snp_col    = next((c for c in df.columns if any(k in c.lower() for k in
                          ["snp","rsid","rs","marker","variant_id","id"])),None)
        gene_col_s = next((c for c in df.columns if any(k in c.lower() for k in
                          ["gene","symbol","nearest","nearest_gene"])),None)
        chrom_col_s= next((c for c in df.columns if any(k in c.lower() for k in
                          ["chr","chrom","chromosome"])),None)
        af_col     = next((c for c in df.columns if any(k in c.lower() for k in
                          ["af","maf","freq","allele_freq","minor_allele"])),None)

        n_total_s = len(df)
        findings.append((" Statistical results dataset",
            f"**{n_total_s:,}** entries · columns: pvalue={'' if pval_col_s else ''} · "
            f"effect size={'' if eff_col_s else ''} · SNP/variant={'' if snp_col else ''} · "
            f"gene={'' if gene_col_s else ''} · allele freq={'' if af_col else ''}. "
            f"{'Likely GWAS summary statistics.' if snp_col and chrom_col_s else 'Likely differential analysis results.'}"))

        if pval_col_s and df[pval_col_s].dtype in [float,"float64"]:
            import numpy as _np_s
            pvals = df[pval_col_s].dropna()
            gwas_thresh = 5e-8
            nom_thresh  = 1e-5
            sig_gwas = (pvals < gwas_thresh).sum()
            sig_nom  = (pvals < nom_thresh).sum()
            sig_05   = (pvals < 0.05).sum()
            findings.append((" Significance thresholds",
                f"**{sig_gwas:,}** genome-wide significant (p < 5×10⁻⁸, GWAS standard) · "
                f"**{sig_nom:,}** nominally significant (p < 10⁻⁵) · "
                f"**{sig_05:,}** at p < 0.05. "
                f"**Interpretation:** Only genome-wide significant hits are robustly reproducible. "
                f"Nominal hits require independent replication before follow-up investment."))

        if eff_col_s and df[eff_col_s].dtype in [float,"float64"]:
            effs_s = df[eff_col_s].dropna()
            pos_eff = (effs_s > 0).sum()
            neg_eff = (effs_s < 0).sum()
            findings.append((" Effect size distribution",
                f"**{pos_eff}** positive effects (risk-increasing) · **{neg_eff}** protective. "
                f"Mean |effect|: {effs_s.abs().mean():.3f}. "
                f"Variants with large effect AND genome-wide significance = highest-priority functional follow-up."))

        if pval_col_s and gene_col_s and df[pval_col_s].dtype in [float,"float64"]:
            sig_mask_s = df[pval_col_s] < (gwas_thresh if snp_col else 0.01)
            sig_genes_s = df.loc[sig_mask_s, gene_col_s].dropna().astype(str).value_counts()
            if len(sig_genes_s) > 0:
                findings.append((" Genes with most significant associations",
                    f"Top genes: " + " · ".join(f"**{g}** ({n})" for g,n in sig_genes_s.head(10).items()) +
                    f". These should be cross-referenced with ClinVar pathogenic variants — "
                    f"statistical association alone does not confirm causality."))
                if gene and gene in sig_genes_s.index:
                    findings.append((f" {gene} in significant hits",
                        f"**{gene}** appears {sig_genes_s[gene]} times in significant results. "
                        f"Consistent with its ClinVar pathogenic variant profile. "
                        f"This statistical evidence SUPPORTS but does not CONFIRM causality — "
                        f"Mendelian randomisation or functional study needed."))

        if af_col and df[af_col].dtype in [float,"float64"]:
            afs = df[af_col].dropna()
            rare = (afs < 0.01).sum()
            findings.append((" Allele frequency distribution",
                f"**{rare:,}** rare variants (MAF < 1%) of {len(afs):,} total. "
                f"Rare variants with large effects are highest-priority — "
                f"they are more likely to be functional and causal than common variants with tiny effects."))

        findings.append((" Recommended experiments",
            f"**1. Mendelian randomisation (free, 1 week):** Use significant SNPs as instruments to test "
            f"causal effect of the trait on disease outcomes. Tools: TwoSampleMR (R). "
            f"**2. Colocalization ($0, 2 days):** Test whether GWAS signal colocalises with eQTL from GTEx "
            f"in the disease-relevant tissue — confirms the SNP acts through gene expression change. "
            f"**3. Fine-mapping ($0, 1 week):** Identify the likely causal variant within each GWAS locus "
            f"using SuSiE or FINEMAP. This narrows from locus to specific variant. "
            f"**4. Functional annotation ($0, 1 day):** Annotate significant variants with CADD, "
            f"RegulomeDB, and AlphaMissense to predict functional consequence. "
            f"**5. CRISPR screen ($80K, 12 weeks):** For top gene hits, genome-wide CRISPR knockout screen "
            f"to confirm essentiality in disease-relevant cell model."))

    else:
        # ── Generic table ────────────────────────────────────────────────────
        numeric_cols_g = df.select_dtypes(include=[float, int]).columns.tolist()
        str_cols_g     = df.select_dtypes(include=[object]).columns.tolist()
        
        findings.append((" Dataset overview",
            f"**{len(df):,}** rows · **{len(df.columns)}** columns · "
            f"**{len(numeric_cols_g)}** numeric · **{len(str_cols_g)}** text columns. "
            f"Column headers: {', '.join(df.columns.tolist()[:10])}{'...' if len(df.columns)>10 else ''}"))
        
        for nc in numeric_cols_g[:5]:
            col_data = df[nc].dropna()
            if len(col_data) > 0 and col_data.dtype in [float,"float64",int,"int64"]:
                findings.append((f" {nc}",
                    f"Range: {col_data.min():.4g} – {col_data.max():.4g} · "
                    f"Mean: {col_data.mean():.4g} · Median: {col_data.median():.4g} · "
                    f"Std: {col_data.std():.4g} · Missing: {col_data.isna().sum()}"))
        
        for sc in str_cols_g[:3]:
            n_unique = df[sc].nunique()
            top_vals = df[sc].value_counts().head(5)
            findings.append((f" {sc}",
                f"{n_unique} unique values. Most common: " +
                " · ".join(f"{v} ({c})" for v,c in top_vals.items())))
        
        findings.append((" Tip",
            "To get a full analysis, ensure your CSV has clear column names matching your data type: "
            "gene/fold/pvalue for expression · residue_position/effect_score/mutation for DMS · "
            "intensity/abundance for proteomics · kd/affinity for binding assays · "
            "significance/classification for variant tables."))

    # ── Goal-specific overlay (always appended) ──────────────────────────────
    goal_l = goal.lower()
    if "therapeutic" in goal_l or "drug" in goal_l:
        findings.append((" Therapeutic goal — prioritisation strategy",
            "Intersection rule: only genes/mutations scoring HIGH in **this assay** AND carrying "
            "ClinVar pathogenic variants are credible drug targets. Single-assay evidence alone is insufficient. "
            "Require: functional effect in this data + ClinVar genetic evidence + structural druggability."))
    if "biomarker" in goal_l:
        findings.append((" Biomarker goal — strategy",
            "Biomarker candidates must: (1) show significant change in this assay, "
            "(2) be detectable in an accessible biofluid (blood/urine/CSF), "
            "(3) correlate with disease severity in patient cohorts. "
            "Next step: cross-reference significant hits with Human Protein Atlas tissue expression data."))
    if "mechanism" in goal_l:
        findings.append((" Mechanistic goal — strategy",
            "Use this assay data to build a mechanistic model: which positions/genes "
            "are functionally sensitive? Map onto protein structure. Do they cluster in a "
            "known functional domain? Does the pattern match loss-of-function or gain-of-function?"))
    
    return findings




def variant_landscape_fig(variants, protein_length, scored):
    if not variants: return None
    sig_c={5:"#ff2d55",4:"#ff6b55",3:"#ff8c42",2:"#ffd60a",1:"#2a6040",0:"#0e2840",-1:"#060f18"}
    sig_l={5:"Disease-causing (pathogenic)",4:"Likely disease-causing",3:"Risk factor",
           2:"Unknown significance (VUS)",1:"Likely harmless (likely benign)",0:"Harmless (benign)",-1:"Not classified"}
    ml_map={v.get("uid",""):v.get("ml",0) for v in scored}
    positions,ys,colours,labels,urls=[],[],[],[],[]
    for v in variants:
        pos_int = None
        raw_start = v.get("start","")
        if raw_start:
            try: pos_int = int(raw_start)
            except: pass
        if pos_int is None:
            # Try to extract from variant name
            import re as _re2
            vn2 = v.get("variant_name","") or v.get("title","")
            pm2 = _re2.search(r"p\.(?:[A-Za-z]+)?(\d+)", vn2)
            if pm2:
                try: pos_int = int(pm2.group(1))
                except: pass
        if pos_int is None:
            continue
        sc=v.get("score",-1); ml2=ml_map.get(v.get("uid",""),0)
        name2=(v.get("variant_name") or v.get("title",""))[:40]; url=v.get("url","")
        positions.append(pos_int); ys.append(max(sc,0)+ml2*.4)
        colours.append(sig_c.get(sc,"#0e2840"))
        labels.append(f"{name2}<br>{sig_l.get(sc,'?')}<br>ML score: {ml2:.2f}<extra></extra>")
        urls.append(url)
    if not positions: return None
    fig=go.Figure()
    for x,y,c in zip(positions,ys,colours):
        fig.add_trace(go.Scatter(x=[x,x],y=[0,y],mode="lines",line=dict(color=c,width=1),showlegend=False,hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=positions,y=ys,mode="markers",
        marker=dict(color=colours,size=7,opacity=.85,line=dict(color="#020617",width=.5)),
        text=labels,hovertemplate="%{text}",showlegend=False))
    fig.add_hrect(y0=0,y1=.8,fillcolor="rgba(6,30,6,0.2)",line_width=0,annotation_text="Harmless zone",annotation_font_size=9,annotation_font_color="#1a4030")
    fig.add_hrect(y0=3.5,y1=6,fillcolor="rgba(80,0,20,0.15)",line_width=0,annotation_text="Disease-causing zone",annotation_font_size=9,annotation_font_color="#5a1020")
    maxpos=max(protein_length or 100,max(positions)+10)
    fig.update_layout(paper_bgcolor="#020617",plot_bgcolor="#020617",font_color="#1e4060",
        xaxis=dict(title="Position in protein chain (amino acid number)",range=[0,maxpos],gridcolor="#060f1c",color="#0e2840"),
        yaxis=dict(title="Disease severity score",range=[-0.1,6.2],
            tickvals=[0,2,4,5],ticktext=["Harmless","Unknown","Likely Disease","Disease-causing"],
            gridcolor="#060f1c",color="#0e2840"),
        height=270,margin=dict(t=8,b=30,l=90,r=8),hovermode="closest")
    return fig




# ═══════════════════════════════════════════════════════════════════
#  POWER FEATURES — what no other tool has
# ═══════════════════════════════════════════════════════════════════



@st.cache_data(show_spinner=False, ttl=3600)

def compute_hotspot_clusters(variants: list, protein_length: int) -> list:
    """
    Identify variant hotspot clusters — regions of the protein where
    pathogenic variants are significantly denser than expected by chance.
    Returns list of clusters with positions, density, and functional annotation.
    """
    if not variants or not protein_length: return []
    import math
    # Only pathogenic variants with positions
    path_vars = []
    for v in variants:
        if v.get("score",0) >= 3:
            try: path_vars.append(int(v.get("start",0)))
            except: pass
    if not path_vars: return []
    path_vars.sort()
    # Sliding window: window=20aa, step=5, flag if density > 3x genome-wide average
    global_density = len(path_vars) / max(protein_length, 1)
    window, step = 20, 5
    clusters = []
    i = 0
    while i < protein_length - window:
        in_window = [p for p in path_vars if i <= p < i+window]
        local_density = len(in_window) / window
        if local_density >= max(3, global_density * 4) and in_window:
            # Merge with adjacent clusters
            if clusters and clusters[-1]["end"] >= i:
                clusters[-1]["end"] = i + window
                clusters[-1]["count"] += len(in_window)
                clusters[-1]["positions"].extend(in_window)
            else:
                clusters.append({
                    "start": i, "end": i+window,
                    "count": len(in_window),
                    "positions": in_window,
                    "fold_enrichment": round(local_density / max(global_density, 0.001), 1),
                })
        i += step
    # Deduplicate positions in clusters
    for c in clusters:
        c["positions"] = sorted(set(c["positions"]))
        c["count"] = len(c["positions"])
    return sorted(clusters, key=lambda x: -x["fold_enrichment"])

def estimate_patient_population(diseases: list, cv: dict, gi: dict) -> dict:
    """Removed on purpose: hand-typed prevalence table with no source. Returns nothing rather than an unsourced number."""
    return {}

def compute_experiment_roi(scored: list, gi: dict, ptype: str, gnomad: dict, ot_data: dict) -> list:
    """Removed on purpose: the costs and success probabilities in the old table had no source. Next experiments are now ranked by evidence in the Experiments tab."""
    return []

def find_drugged_analogs(pdata: dict, string_data: list, ot_data: dict) -> list:
    """
    Find proteins with similar disease profiles that have been successfully drugged.
    'Closest drugged analog' — the most powerful drug discovery insight.
    """
    analogs = []
    # From OpenTargets known drugs on interaction partners
    for partner in string_data[:5]:
        gene = partner.get("partner","")
        if gene:
            analogs.append({
                "protein": gene,
                "relationship": "Interaction partner (STRING)",
                "score": partner.get("score",0),
                "implication": f"If {gene} is druggable, its interaction with the target protein may allow indirect targeting or combination therapy.",
                "string_url": partner.get("url",""),
            })
    # From OpenTargets disease associations
    for da in (ot_data.get("disease_associations",[]) if ot_data else [])[:3]:
        analogs.append({
            "protein": da.get("disease",""),
            "relationship": "Shared disease association (OpenTargets)",
            "score": int(da.get("score",0)*1000),
            "implication": "Other proteins in this disease module may serve as proxy targets with established drug precedent.",
            "ot_url": da.get("url",""),
        })
    return analogs

def regulatory_pathway_map(diseases: list, patient_data: dict, gi: dict) -> dict:
    """Removed on purpose: orphan-drug eligibility derived from that table. Returns nothing rather than an unsourced number."""
    return {}


# ─── Excel Export ─────────────────────────────────────────────────────────────
def generate_excel(gene, pdata, cv, scored, gi, gnomad, string_data,
                   drugs_data, trials_data, ot_data, diseases, papers,
                   patient_data, roi_data, am_scores, hotspots) -> bytes:
    """Generate a comprehensive multi-sheet Excel workbook with all protein data."""
    import io
    try:
        import openpyxl
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        from openpyxl.chart import BarChart, Reference
        from openpyxl.chart.series import DataPoint
    except ImportError:
        return b""

    wb = openpyxl.Workbook()

    # ── Colour palette ───────────────────────────────────────────────────────
    DARK    = "0D1117"
    BLUE    = "0066AA"
    CYAN    = "00E5FF"
    RED     = "FF2D55"
    ORANGE  = "FF8C42"
    YELLOW  = "FFD60A"
    GREEN   = "00C896"
    PURPLE  = "A855F7"
    WHITE   = "FFFFFF"
    LGREY   = "F0F4F8"
    MGREY   = "D0DCE8"

    def hdr(ws, row, col, text, bg=BLUE, fg=WHITE, bold=True, sz=11):
        cell = ws.cell(row=row, column=col, value=text)
        cell.fill  = PatternFill("solid", fgColor=bg)
        cell.font  = Font(bold=bold, color=fg, size=sz, name="Calibri")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        return cell

    def val(ws, row, col, text, bg=None, fg="111111", bold=False, sz=10, wrap=True):
        cell = ws.cell(row=row, column=col, value=text)
        if bg:
            cell.fill = PatternFill("solid", fgColor=bg)
        cell.font  = Font(bold=bold, color=fg, size=sz, name="Calibri")
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=wrap)
        return cell

    def section_hdr(ws, row, col, text, width=8):
        cell = ws.cell(row=row, column=col, value=text)
        cell.fill  = PatternFill("solid", fgColor=DARK)
        cell.font  = Font(bold=True, color=CYAN, size=12, name="Calibri")
        cell.alignment = Alignment(horizontal="left", vertical="center")
        if width > 1:
            ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=col+width-1)
        return cell

    def rank_colour(rank):
        return {"CRITICAL":RED,"HIGH":ORANGE,"MEDIUM":YELLOW,"NEUTRAL":"888888"}.get(rank, MGREY)

    # ════════════════════════════════════════════════════
    # SHEET 1: Executive Summary
    # ════════════════════════════════════════════════════
    ws1 = wb.active; ws1.title = " Summary"
    ws1.sheet_view.showGridLines = False
    ws1.column_dimensions["A"].width = 28
    ws1.column_dimensions["B"].width = 45
    ws1.column_dimensions["C"].width = 20
    ws1.column_dimensions["D"].width = 20

    section_hdr(ws1, 1, 1, f" PROTELLECT — {gene} Intelligence Report", 4)
    ws1.row_dimensions[1].height = 30
    val(ws1, 2, 1, f"Generated by Protellect | Data: UniProt, ClinVar, gnomAD, STRING, OpenTargets, PubMed", bg=LGREY, sz=9)
    ws1.merge_cells("A2:D2")

    row = 4
    fields = [
        ("Gene Symbol", gene),
        ("Protein Name", g_name(pdata)[:80]),
        ("UniProt ID", pdata.get("primaryAccession","")),
        ("Organism", pdata.get("organism",{}).get("scientificName","")),
        ("Protein Length", f"{pdata.get('sequence',{}).get('length','')} amino acids"),
        ("Genomic Integrity", gi.get("verdict","")),
        ("Invest Verdict", gi.get("pursue","").upper()),
        ("Pathogenic Variants", gi.get("n_pathogenic",0)),
        ("Total ClinVar Variants", gi.get("n_total",0)),
        ("Variant Density", f"{gi.get('density',0)*100:.2f}%"),
        ("pLI (LoF intolerance)", (gnomad.get("pLI") if gnomad and gnomad.get("pLI") is not None else "N/A")),
        ("o/e LoF", gnomad.get("oe_lof","N/A") if gnomad else "N/A"),
        ("Known drugs (DGIdb/OT)", len(drugs_data)),
        ("Active clinical trials", len(trials_data)),
        ("Estimated global patients", f"{patient_data.get('estimated_global_patients',0):,}" if patient_data else "N/A"),
        ("Orphan Drug eligible", "YES" if patient_data.get("orphan_eligible") else "NO"),
        ("GPCR / Piggyback", "YES" if g_gpcr(pdata) else "NO"),
    ]
    hdr(ws1,row,1,"Field",DARK,CYAN); hdr(ws1,row,2,"Value",DARK,CYAN)
    row += 1
    for k, v0 in fields:
        val(ws1,row,1,k,LGREY,bold=True)
        bg2 = None
        if "Verdict" in k:
            bg2 = {"prioritise":"C8F0E0","proceed":"FFE8CC","selective":"FFFACC","caution":"FFF0CC","deprioritise":"F0E0E8","neutral":LGREY}.get(gi.get("pursue",""),None)
        val(ws1,row,2,str(v0),bg2)
        row += 1

    # ════════════════════════════════════════════════════
    # SHEET 2: ClinVar Variants (ALL)
    # ════════════════════════════════════════════════════
    ws2 = wb.create_sheet(" ClinVar Variants")
    ws2.sheet_view.showGridLines = False
    for col, (name, w) in enumerate([("ML Rank",12),("Variant",40),("Protein Change",18),("Position",10),("ClinVar Sig.",22),("Disease / Condition",40),("ML Score",10),("Germline",10),("Somatic",10),("Review Status",22),("ClinVar URL",40)],1):
        ws2.column_dimensions[get_column_letter(col)].width = w
        hdr(ws2,1,col,name,DARK,CYAN)
    ws2.row_dimensions[1].height = 22

    for r_idx, v2 in enumerate(scored, 2):
        rk = v2.get("ml_rank","NEUTRAL")
        rk_clr = rank_colour(rk)
        cells_data = [
            (rk, rk_clr, WHITE, True),
            (v2.get("variant_name","")[:60], None, "111111", False),
            (v2.get("variant_name","")[:30], None, "111111", False),
            (v2.get("start",""), None, "111111", False),
            (v2.get("sig",""), None, "333333", False),
            (v2.get("condition","")[:80], None, "333333", False),
            (v2.get("ml",0), None, "111111", False),
            ("Yes" if v2.get("germline") else "No", "C8F0E0" if v2.get("germline") else None, "111111", False),
            ("Yes" if v2.get("somatic") else "No", "F0E0E8" if v2.get("somatic") else None, "111111", False),
            (v2.get("review","")[:30], None, "555555", False),
            (v2.get("url",""), None, "0066AA", False),
        ]
        for c_idx, (txt, bg, fg, bold) in enumerate(cells_data, 1):
            cell = val(ws2, r_idx, c_idx, txt, bg, fg, bold, 9)
            if c_idx == 11 and txt:
                cell.hyperlink = txt
                cell.style = "Hyperlink"
        ws2.row_dimensions[r_idx].height = 16

    # ════════════════════════════════════════════════════
    # SHEET 3: Disease Associations
    # ════════════════════════════════════════════════════
    ws3 = wb.create_sheet(" Diseases")
    ws3.sheet_view.showGridLines = False
    for col, (name, w) in enumerate([("Disease Name",40),("Inheritance",20),("Mutation Type",25),("ClinVar Variants",15),("Severity Est.",12),("Description",60)],1):
        ws3.column_dimensions[get_column_letter(col)].width = w
        hdr(ws3,1,col,name,DARK,CYAN)
    cond_counts_e = {}
    _variants_e = (cv or {}).get("variants", []) if cv else []
    for v2 in _variants_e:
        if v2.get("score",0)>=2:
            for c2 in v2.get("condition","").split(";"):
                c2=c2.strip()
                if c2: cond_counts_e[c2]=cond_counts_e.get(c2,0)+1
    for r_idx, d2 in enumerate(diseases, 2):
        nm2 = d2.get("name","")
        cv_cnt = max((v for k,v in cond_counts_e.items() if nm2.lower()[:15] in k.lower()), default=0)
        sev2 = min(95,20+cv_cnt*8+(20 if "dominant" in d2.get("inheritance","").lower() else 0))
        sev_bg = "FFD0D0" if sev2>70 else "FFE8CC" if sev2>40 else "FFFACC"
        val(ws3,r_idx,1,nm2,None,"111111",True,10)
        val(ws3,r_idx,2,d2.get("inheritance","Unknown"))
        val(ws3,r_idx,3,d2.get("mutation_type","Variant"))
        val(ws3,r_idx,4,cv_cnt)
        val(ws3,r_idx,5,f"{sev2}/100",sev_bg,"333333",True)
        val(ws3,r_idx,6,d2.get("desc","")[:200])
        ws3.row_dimensions[r_idx].height = 18

    # ════════════════════════════════════════════════════
    # SHEET 4: Experiment ROI Roadmap
    # ════════════════════════════════════════════════════
    ws4 = wb.create_sheet(" Experiment Roadmap")
    ws4.sheet_view.showGridLines = False
    for col, (name, w) in enumerate([("Priority Rank",10),("Experiment",40),("Category",18),("ROI Score",12),("ROI Label",14),("Est. Cost",14),("Timeline",12),("P(Success)",12),("Rationale",70)],1):
        ws4.column_dimensions[get_column_letter(col)].width = w
        hdr(ws4,1,col,name,DARK,CYAN)
    for r_idx, exp_e in enumerate(roi_data, 2):
        pri_bg = {" Excellent":"C8F0E0"," Good":"FFFACC"," Fair":"FFE8CC"," Low":"FFD0D0"}.get(exp_e.get("roi_label",""),"F5F5F5")
        val(ws4,r_idx,1,r_idx-1,None,"111111",True)
        val(ws4,r_idx,2,exp_e.get("name",""),None,"111111",True,10)
        val(ws4,r_idx,3,exp_e.get("category",""))
        val(ws4,r_idx,4,exp_e.get("roi",0),pri_bg,"111111",True)
        val(ws4,r_idx,5,exp_e.get("roi_label",""),pri_bg)
        val(ws4,r_idx,6,f"${exp_e.get('cost_usd',0):,}" if exp_e.get('cost_usd',0)>0 else "FREE")
        val(ws4,r_idx,7,f"{exp_e.get('time_weeks',0)} weeks")
        val(ws4,r_idx,8,f"{exp_e.get('p_success',0)*100:.0f}%")
        val(ws4,r_idx,9,exp_e.get("rationale","")[:300],sz=9)
        ws4.row_dimensions[r_idx].height = 36

    # ════════════════════════════════════════════════════
    # SHEET 5: Drug Landscape
    # ════════════════════════════════════════════════════
    ws5 = wb.create_sheet(" Drug Landscape")
    ws5.sheet_view.showGridLines = False
    for col, (name, w) in enumerate([("Drug / Compound",30),("Interaction Type",20),("Sources",30),("Database",12),("Link",40)],1):
        ws5.column_dimensions[get_column_letter(col)].width = w
        hdr(ws5,1,col,name,DARK,CYAN)
    row5 = 2
    for d_e in drugs_data:
        val(ws5,row5,1,d_e.get("drug",""),None,"111111",True)
        val(ws5,row5,2,d_e.get("type",""))
        val(ws5,row5,3,d_e.get("sources","")[:50])
        val(ws5,row5,4,"DGIdb")
        url_e = d_e.get("url","")
        cell_e = val(ws5,row5,5,url_e,None,"0066AA")
        if url_e: cell_e.hyperlink = url_e; cell_e.style = "Hyperlink"
        row5 += 1
    if ot_data:
        row5 += 1
        section_hdr(ws5,row5,1,"OpenTargets Known Drugs",5); row5 += 1
        for d_ot in ot_data.get("known_drugs",[]):
            val(ws5,row5,1,d_ot.get("name",""),None,"111111",True)
            val(ws5,row5,2,d_ot.get("mechanism","")[:40])
            val(ws5,row5,3,d_ot.get("indication","")[:50])
            val(ws5,row5,4,f"Phase {d_ot.get('phase',0)}")
            url_ot = d_ot.get("url","")
            cell_ot = val(ws5,row5,5,url_ot,None,"0066AA")
            if url_ot: cell_ot.hyperlink = url_ot; cell_ot.style = "Hyperlink"
            row5 += 1

    # ════════════════════════════════════════════════════
    # SHEET 6: Protein Interactions
    # ════════════════════════════════════════════════════
    ws6 = wb.create_sheet(" Interactions")
    ws6.sheet_view.showGridLines = False
    for col, (name, w) in enumerate([("Partner Protein",22),("Combined Score",16),("Experimental Score",18),("Co-expression",16),("STRING URL",40)],1):
        ws6.column_dimensions[get_column_letter(col)].width = w
        hdr(ws6,1,col,name,DARK,CYAN)
    for r_idx, si in enumerate(string_data, 2):
        bg_si = "C8F0E0" if si.get("score",0)>800 else "FFFACC" if si.get("score",0)>600 else None
        val(ws6,r_idx,1,si.get("partner",""),None,"111111",True)
        val(ws6,r_idx,2,si.get("score",0),bg_si,"111111",True)
        val(ws6,r_idx,3,si.get("experiments",0))
        val(ws6,r_idx,4,si.get("coexpression",0))
        url_si = si.get("url","")
        cell_si = val(ws6,r_idx,5,url_si,None,"0066AA")
        if url_si: cell_si.hyperlink = url_si; cell_si.style = "Hyperlink"

    # ════════════════════════════════════════════════════
    # SHEET 7: Clinical Trials
    # ════════════════════════════════════════════════════
    ws7 = wb.create_sheet(" Clinical Trials")
    ws7.sheet_view.showGridLines = False
    for col, (name, w) in enumerate([("NCT ID",15),("Title",80),("Status",22),("Phase",10),("ClinicalTrials.gov URL",50)],1):
        ws7.column_dimensions[get_column_letter(col)].width = w
        hdr(ws7,1,col,name,DARK,CYAN)
    for r_idx, t_e in enumerate(trials_data, 2):
        status_bg = "C8F0E0" if "RECRUIT" in t_e.get("status","") else "FFE8CC"
        val(ws7,r_idx,1,t_e.get("nct_id",""),None,"0066AA",True)
        val(ws7,r_idx,2,t_e.get("title","")[:150])
        val(ws7,r_idx,3,t_e.get("status",""),status_bg)
        val(ws7,r_idx,4,t_e.get("phase","?"))
        url_t = t_e.get("url","")
        cell_t = val(ws7,r_idx,5,url_t,None,"0066AA")
        if url_t: cell_t.hyperlink = url_t; cell_t.style = "Hyperlink"

    # ════════════════════════════════════════════════════
    # SHEET 8: Variant Hotspots
    # ════════════════════════════════════════════════════
    ws8 = wb.create_sheet(" Hotspots")
    ws8.sheet_view.showGridLines = False
    for col, (name, w) in enumerate([("Hotspot #",10),("Start Residue",14),("End Residue",14),("Pathogenic Count",16),("Fold Enrichment",16),("Positions",60)],1):
        ws8.column_dimensions[get_column_letter(col)].width = w
        hdr(ws8,1,col,name,DARK,CYAN)
    for r_idx, hs in enumerate(hotspots, 2):
        fe = hs.get("fold_enrichment",0)
        hs_bg = "FFD0D0" if fe>8 else "FFE8CC" if fe>4 else "FFFACC"
        val(ws8,r_idx,1,r_idx-1,hs_bg,"111111",True)
        val(ws8,r_idx,2,hs.get("start",0))
        val(ws8,r_idx,3,hs.get("end",0))
        val(ws8,r_idx,4,hs.get("count",0),hs_bg,"111111",True)
        val(ws8,r_idx,5,f"{fe}×",hs_bg,"111111",True)
        val(ws8,r_idx,6,", ".join(str(p) for p in hs.get("positions",[])[:30]),sz=9)

    # ════════════════════════════════════════════════════
    # SHEET 9: Literature / Papers
    # ════════════════════════════════════════════════════
    ws9 = wb.create_sheet(" Literature")
    ws9.sheet_view.showGridLines = False
    for col, (name, w) in enumerate([("PMID",12),("Title",80),("Authors",35),("Journal",30),("Year",8),("Experiment Type",22),("PubMed URL",40)],1):
        ws9.column_dimensions[get_column_letter(col)].width = w
        hdr(ws9,1,col,name,DARK,CYAN)
    all_papers_e = papers + [p2 for p2 in ((st.session_state.get("abstracts") or [])) if p2.get("pmid","") not in {p3.get("pmid","") for p3 in papers}]
    for r_idx, p_e in enumerate(all_papers_e, 2):
        val(ws9,r_idx,1,p_e.get("pmid",""),None,"0066AA",True)
        val(ws9,r_idx,2,p_e.get("title","")[:150])
        val(ws9,r_idx,3,p_e.get("authors","")[:60])
        val(ws9,r_idx,4,p_e.get("journal","")[:35])
        val(ws9,r_idx,5,p_e.get("year",""))
        val(ws9,r_idx,6,classify_experiment_type(p_e.get("abstract",""),p_e.get("title","")))
        url_p = p_e.get("url","")
        cell_p = val(ws9,r_idx,7,url_p,None,"0066AA")
        if url_p: cell_p.hyperlink = url_p; cell_p.style = "Hyperlink"

    # Save to bytes
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

# ─── CSV Type Guide ─────────────────────────────────────────────────────────────
CSV_GUIDE = {
    "expression": {
        "icon":"", "name":"Gene Expression (RNA-seq / Microarray / qPCR)",
        "required_cols":["gene/symbol", "fold_change OR log2FC", "p-value OR padj"],
        "optional_cols":["sample names", "RPKM/TPM/counts"],
        "produces":["Volcano plot","Up/downregulated gene lists","Pathway enrichment (if gene list)","Target prioritisation against ClinVar"],
        "example":"DESeq2 / edgeR output, GEO series matrix, qPCR Ct values",
        "tip":"Export from DESeq2 with gene symbol column named 'gene' and columns 'log2FoldChange' and 'padj'.",
    },
    "variants": {
        "icon":"", "name":"Variant / Mutation Table (VCF-derived / clinical)",
        "required_cols":["gene OR symbol", "variant (HGVS or rsID)", "clinical significance OR consequence"],
        "optional_cols":["chromosome","position","ref","alt","AF (allele frequency)"],
        "produces":["Variant pathogenicity ranking","ClinVar cross-reference","Hotspot mapping","Protein position annotation"],
        "example":"VCF annotated by ANNOVAR/VEP, clinical genetics lab report, gnomAD export",
        "tip":"Include a 'p.' notation column (protein change) for best positional mapping.",
    },
    "proteomics": {
        "icon":"", "name":"Proteomics (MS intensity / LFQ / TMT)",
        "required_cols":["protein/gene name", "intensity OR abundance OR LFQ"],
        "optional_cols":["fold-change","p-value","peptide count","sequence"],
        "produces":["Abundance comparison","Interaction network overlay","Post-translational modification mapping"],
        "example":"MaxQuant proteinGroups.txt, Perseus output, Spectronaut report",
        "tip":"Use 'LFQ intensity' columns from MaxQuant for best quantification.",
    },
    "stats": {
        "icon":"", "name":"Statistical Results (GWAS / differential analysis)",
        "required_cols":["identifier (gene/SNP/probe)", "p-value OR q-value"],
        "optional_cols":["effect size","beta","OR","confidence interval"],
        "produces":["Manhattan-style plot","Significant hit prioritisation","ClinVar comparison"],
        "example":"GWAS summary stats, PLINK output, limma/edgeR results",
        "tip":"Include rsID or gene symbol for cross-referencing ClinVar.",
    },
    "generic": {
        "icon":"", "name":"Generic tabular data",
        "required_cols":["Any structured columns"],
        "optional_cols":["gene names help link to protein data"],
        "produces":["Data summary","Column statistics","AI-powered interpretation"],
        "example":"Any CSV/TSV from your experiment",
        "tip":"Name columns clearly — gene, protein, sample, treatment, control.",
    },
}


# ═══════════════════════════════════════════════════════════════════
#  ANIMATION ENGINES — all data-driven, zero hallucination
# ═══════════════════════════════════════════════════════════════════


# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────



def show_tutorial_dialog():
    _tutorial_dialog()

# ─── Auth init + gate ─────────────────────────────────────────────────────

# ════════════════════════════════════════════════════════════════════════════
#  DOMAIN WORKSPACES — each with unique UI & interaction model
# ════════════════════════════════════════════════════════════════════════════










# ════════════════════════════════════════════════════════════════════════════
#  ONCOLOGY-SPECIFIC FEATURES
# ════════════════════════════════════════════════════════════════════════════








# ── Canonical citation library — used as footers on tabs to ground methodology ─











# ─── Sidebar ────────────────────────────────────────────────────────


# ── Authentication gate ──────────────────────────────────────────────────
# Show login page if not authenticated
# Users can sign in, register, or continue as guest (free plan)
if not st.session_state.get("auth_user"):
    login_page()  # shows login/register/plans UI and calls st.stop()

for k,v0 in {"pdata":None,"cv":None,"pdb":"","papers":[],"scored":[],"gene":"","uid":"",
             "assay":"","last":"","csv_df":None,"csv_type":"","goal_label":GOAL_OPTIONS[0],
             "goal_custom":"","sensitivity":50,"gi":None,"partner_query":"",
             "partner_cv":None,"partner_gi":None,"disease_search":"","disease_proteins":[],"csv_triage_active":False,"show_tutorial":True,"gnomad":{},"string":[],"trials":[],"drugs":[],"abstracts":[],"org":{},"ai_result":{},"ot":{},"am":{},"isoforms":[],"hotspots":[],"patients":{},"excel_bytes":None,"domain_ctx":{},"acmg_auto":{},"conflicts":[],"ml_result":{},"lab_configured":False,"lab_chat_open":False,"lab_setup_complete":False,"lab_name":"","lab_pi":"","lab_focus":"","lab_domain":"","lab_proteins":[],"lab_diseases":[],"lab_techniques":[],"lab_budget":"medium","lab_model_organism":"","lab_goal":"","lab_chat_history":[],"protein_query_val":"","ob_complete":True,"ob_step":1,"ob_papers":[],"clingen":{},"screener_results":[],"screener_genes_run":[],"screener_running":False,"screener_filters":{},"screener_history":[],
             }.items():
    if k not in st.session_state: st.session_state[k]=v0



# ════════════════════════════════════════════════════════════════════
#  RESEARCH DOMAIN SELECTION PAGE
# ════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════════
#  DOMAIN WORKSPACE FUNCTIONS — full tab-based workspaces per domain
#  Called when domain is selected but no protein loaded
# ════════════════════════════════════════════════════════════════════════════






# ══════════════════════════════════════════════════════════════════════════════
#  FEATURE 1 — SEMANTIC SCHOLAR PAPER FETCH
# ══════════════════════════════════════════════════════════════════════════════











# ══════════════════════════════════════════════════════════════════════════════
#  FEATURE 2 — ONBOARDING WIZARD
# ══════════════════════════════════════════════════════════════════════════════




# ══════════════════════════════════════════════════════════════════════════════
#  FEATURE 3 — EXPORT DOCUMENTATION
# ══════════════════════════════════════════════════════════════════════════════

def generate_export_report(pdata, cv, gi, gnomad_data, diseases,
                           scored, gene, uid, drugs_data, trials_data, ot_data) -> bytes:
    """
    Generate a comprehensive markdown documentation report for a protein analysis.
    Includes: executive summary, protein identity, disease table, variant table,
    gnomAD constraint, experiment roadmap (4 phases), drugs, trials, confidence notes.
    """
    from datetime import datetime as _dt
    now  = _dt.now().strftime("%Y-%m-%d %H:%M UTC")
    lab  = st.session_state.get("lab_name", "")
    pi   = st.session_state.get("lab_pi", "")
    sens = st.session_state.get("sensitivity", 50)

    L = []   # lines list

    # ── Cover ─────────────────────────────────────────────────────────────────
    L += [
        f"# Protellect Analysis — {gene}",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Gene | {gene} |",
        f"| UniProt | [{uid}](https://www.uniprot.org/uniprotkb/{uid}/entry) |",
        f"| Generated | {now} |",
    ]
    if lab: L.append(f"| Lab | {lab} |")
    if pi:  L.append(f"| PI  | {pi}  |")
    L.append(f"| Sensitivity | {sens} |")
    L += ["", "---", ""]

    # ── Executive summary ─────────────────────────────────────────────────────
    L.append("## Executive Summary")
    L.append("")
    if gi:
        density = gi.get("density", 0) * 100
        n_path  = gi.get("n_pathogenic", 0)
        n_total = gi.get("n_total", 0)
        verdict = gi.get("verdict", "")
        seq_len = pdata.get("sequence", {}).get("length", 0) if pdata else 0
        pli_val = gnomad_data.get("pLI", "N/A") if gnomad_data else "N/A"
        if pli_val is None: pli_val = "N/A"
        oe_lof  = gnomad_data.get("oe_lof_upper", "N/A") if gnomad_data else "N/A"
        mis_z   = gnomad_data.get("mis_z", "N/A") if gnomad_data else "N/A"
        L += [
            f"| Metric | Value | Interpretation |",
            f"|--------|-------|----------------|",
            f"| **Verdict** | {verdict} | |",
            f"| Genomic Integrity Score | {density:.1f}% | {n_path}/{n_total} P/LP variants · {seq_len} aa |",
            f"| gnomAD pLI | {pli_val} | {'Essential (>0.9)' if isinstance(pli_val, float) and pli_val > 0.9 else 'Tolerates LoF' if pli_val != 'N/A' else 'N/A'} |",
            f"| oe_lof_upper | {oe_lof} | {'Constrained (<0.35)' if isinstance(oe_lof, float) and oe_lof < 0.35 else 'Not constrained' if oe_lof != 'N/A' else 'N/A'} |",
            f"| mis_z | {mis_z} | {'Constrained missense' if isinstance(mis_z, float) and mis_z > 3.09 else 'Normal' if mis_z != 'N/A' else 'N/A'} |",
            f"| Associated diseases | {len(diseases)} | |",
            f"| Known drugs | {len(drugs_data) if drugs_data else 0} | |",
            f"| Active trials | {len(trials_data) if trials_data else 0} | |",
            "",
        ]
        expl = gi.get("explanation", "")
        if expl:
            L += [f"> **Interpretation:** {expl}", ""]
    L += ["---", ""]

    # ── Protein identity ──────────────────────────────────────────────────────
    if pdata:
        pname = (
            (pdata.get("proteinDescription", {}) or {})
            .get("recommendedName", {})
            .get("fullName", {})
            .get("value", "") or gene
        )
        func_text = ""
        for c in pdata.get("comments", []):
            if c.get("commentType") == "FUNCTION":
                for t in c.get("texts", []):
                    func_text = t.get("value", "")[:600]
                    break
            if func_text:
                break
        seq_val = pdata.get("sequence", {}).get("value", "") or ""
        L += [
            "## Protein Identity",
            "",
            f"**Full name:** {pname}  ",
            f"**Gene:** {gene} · **UniProt:** {uid}  ",
            f"**Length:** {len(seq_val) or pdata.get('sequence',{}).get('length',0)} aa  ",
            "",
            "**Function:**",
            f"> {func_text}" if func_text else "> See UniProt entry for full functional annotation.",
            "",
            "---",
            "",
        ]

    # ── Disease associations ──────────────────────────────────────────────────
    if diseases:
        L += ["## Disease Associations", ""]
        L += ["| Disease | Inheritance | ClinVar variants | Evidence tier |"]
        L += ["|---------|------------|-----------------|--------------|"]
        for d in diseases[:20]:
            ev_tier = d.get("_evidence_tier", {})
            ev_label = ev_tier.get("label", "UniProt") if isinstance(ev_tier, dict) else "UniProt"
            L.append(
                f"| {d.get('name','')} | {d.get('inheritance','')} "
                f"| {d.get('n_variants',0)} | {ev_label} |"
            )
        L += ["", "---", ""]

    # ── ClinVar pathogenic variants ───────────────────────────────────────────
    if cv and cv.get("variants"):
        plp = sorted(
            [v for v in cv["variants"] if v.get("score", 0) >= 4],
            key=lambda x: x.get("cv_stars", 0), reverse=True
        )
        L += [
            "## Confirmed Pathogenic Variants (ClinVar)",
            "",
            f"Showing {min(20, len(plp))} of {len(plp)} P/LP variants.",
            "",
            "| Variant | Classification | Condition | Stars | URL |",
            "|---------|---------------|-----------|-------|-----|",
        ]
        for v in plp[:20]:
            stars = "★" * v.get("cv_stars", 0) + "" * (4 - v.get("cv_stars", 0))
            url   = v.get("url", "")
            L.append(
                f"| {v.get('variant_name','')[:38]} | {v.get('sig','')} "
                f"| {v.get('condition','')[:28]} | {stars} "
                f"| {'[Link](' + url + ')' if url else ''} |"
            )
        L += ["", "---", ""]

    # ── gnomAD constraint ─────────────────────────────────────────────────────
    if gnomad_data:
        L += [
            "## Population Constraint (gnomAD v4)",
            "",
            "| Metric | Value | Interpretation |",
            "|--------|-------|----------------|",
            f"| pLI | {gnomad_data.get('pLI','N/A')} | LoF intolerance (>0.9 = essential) |",
            f"| oe_lof_upper | {gnomad_data.get('oe_lof_upper','N/A')} | Observed/expected LoF (CCRS <0.35 = constrained) |",
            f"| oe_lof | {gnomad_data.get('oe_lof','N/A')} | Observed/expected LoF ratio |",
            f"| mis_z | {gnomad_data.get('mis_z','N/A')} | Missense z-score (>3.09 = constrained) |",
            f"| oe_mis | {gnomad_data.get('oe_mis','N/A')} | Observed/expected missense ratio |",
            "",
            "---",
            "",
        ]

    # ── Experiments ───────────────────────────────────────────────────────────
    n_crit = sum(1 for v in (scored or []) if v.get("ml_rank") == "CRITICAL")
    n_high = sum(1 for v in (scored or []) if v.get("ml_rank") == "HIGH")
    top_names = ", ".join(
        v.get("variant_name", "")[:20]
        for v in (scored or [])[:3]
        if v.get("ml_rank") in ("CRITICAL","HIGH")
    ) or "—"
    dis0 = diseases[0]["name"][:40] if diseases else "associated condition"
    pli_v = (gnomad_data.get("pLI") or 0) if gnomad_data else 0

    L += [
        "## Recommended Experiment Roadmap",
        "",
        "Ordered by evidence-to-cost ratio. Each step's data informs the next.",
        "Do not skip phases — wet-lab budget should only follow computational triage.",
        "",
        "### Phase 0 — Computational (Free · 1–3 days)",
        "",
        f"1. **AlphaMissense triage** — Cross-reference {n_crit} CRITICAL + {n_high} HIGH ML-ranked variants "
        f"with AlphaMissense. Tier 1 criteria: ClinVar ≥4★ + AM ≥0.70 + gnomAD AF <0.001% + pLDDT ≥70. "
        f"Priority variants: {top_names}.",
        f"2. **gnomAD constraint review** — pLI = {pli_v}. "
        f"{'Essential gene — LoF-based therapeutics justified.' if (pli_v or 0) > 0.9 else 'Moderate constraint — confirm mechanism before LoF drug approach.'}",
        "3. **AlphaFold structural mapping** — Map variant positions onto pLDDT. pLDDT <50 = disordered; "
        "AM scores unreliable in these regions. Focus structural work on pLDDT >70 positions.",
        "",
        "### Phase 1 — Low-cost biochemical ($500–5K · 2–4 weeks)",
        "",
        "1. **Recombinant expression + Western blot** (~$500) — Express WT + top 3 variants "
        "in E. coli BL21 (soluble domains) or HEK293T (full-length). Anti-His/FLAG tag. "
        "Absent mutant band = degraded (LoF via NMD/proteasome confirmed).",
        "2. **Thermal shift assay / DSF** (~$1–2K) — WT vs each variant. "
        "ΔTm ≥1°C = structurally destabilising → directly actionable. "
        "ΔTm <1°C but pathogenic = functional mechanism, not stability.",
        f"3. **Cell viability assay** (~$3K) — Overexpress variants in {dis0}-relevant line. "
        "CellTiter-Glo at 72h. Rescue with WT co-expression to confirm on-target effect.",
        "",
        "### Phase 2 — Mechanistic ($15K–50K · 6–12 weeks)",
        "",
        "1. **iPSC or patient-derived cells** — Functional assay specific to protein class. "
        "Isogenic control (CRISPR-corrected) mandatory to distinguish variant effect from genetic background.",
        "2. **CRISPR knock-in** — Introduce top 2 variants into iPSC. Compare to isogenic WT. "
        "Protein-class-specific readout (e.g. electrophysiology for ion channels, immunofluorescence for structural).",
        "",
        "### Phase 3 — In vivo ($50K–200K · 3–6 months)",
        "",
        "1. **Zebrafish morpholino** — 5-day knockdown. WT mRNA rescue confirms specificity. "
        "Cost-effective first in-vivo screen.",
        "2. **Mouse germline knock-in** — Variant-specific model. Only after Phase 2 unambiguously confirms mechanism.",
        "",
        "### Phase 4 — Clinical translation ($1M+ · years)",
        "",
        "IND + regulatory strategy must be planned from Phase 2 data. "
        f"{'Orphan Drug Designation eligibility: check for <200,000 US patients.' if diseases else ''}",
        "",
        "---",
        "",
    ]

    # ── Known drugs ───────────────────────────────────────────────────────────
    if drugs_data:
        L += [
            "## Known Drugs and Compounds",
            "",
            "| Drug | Interaction type | Score | Source |",
            "|------|-----------------|-------|--------|",
        ]
        for d in (drugs_data or [])[:15]:
            L.append(
                f"| {d.get('drug','')} | {d.get('interaction_type','')} "
                f"| {d.get('score','')} | {d.get('source','')} |"
            )
        L += [""]

    # ── Active trials ─────────────────────────────────────────────────────────
    if trials_data:
        L += [
            "## Active Clinical Trials",
            "",
            "| Trial | Status | Phase | Condition |",
            "|-------|--------|-------|-----------|",
        ]
        for t in (trials_data or [])[:10]:
            L.append(
                f"| {t.get('title','')[:50]} | {t.get('status','')} "
                f"| {t.get('phase','')} | {t.get('condition','')[:30]} |"
            )
        L += [""]

    # ── Confidence notes ──────────────────────────────────────────────────────
    L += [
        "---",
        "",
        "## Data Confidence and Limitations",
        "",
        "- **ClinVar:** Variant classifications are submitter-reported. Single-submitter (1★) "
        "entries should be independently verified before any clinical or wet-lab commitment.",
        "- **gnomAD:** Population constraint scores are probabilistic, not deterministic. "
        "Small genes may be underpowered for constraint analysis.",
        "- **AlphaMissense:** AI-predicted pathogenicity. Threshold 0.70 recommended for Tier 1. "
        "Scores in disordered regions (pLDDT <50) are less reliable.",
        "- **This report does not constitute clinical advice.** All findings require "
        "validation in appropriate experimental models before any clinical application.",
        "",
        "---",
        f"",
        f"*Generated by [Protellect](https://protellect.streamlit.app) · {now}*",
    ]

    return "\n".join(L).encode("utf-8")


def render_export_button(pdata, cv, gi, gnomad_data, diseases,
                         scored, gene, uid, drugs_data, trials_data, ot_data):
    """Render export documentation buttons in sidebar."""
    if not (pdata and gene):
        return
    from datetime import datetime as _dt2
    st.sidebar.markdown("<div class='sb-t'>Export</div>", unsafe_allow_html=True)
    doc_bytes = generate_export_report(
        pdata, cv, gi, gnomad_data, diseases or [],
        scored or [], gene, uid,
        drugs_data or [], trials_data or [], ot_data or {}
    )
    fname = f"Protellect_{gene}_{_dt2.now().strftime('%Y%m%d')}.md"
    st.sidebar.download_button(
        "Download report (.md)",
        doc_bytes, file_name=fname,
        mime="text/markdown",
        key="exp_md_sb", use_container_width=True,
    )
    if st.session_state.get("excel_bytes"):
        st.sidebar.download_button(
            "Download spreadsheet (.xlsx)",
            st.session_state["excel_bytes"],
            file_name=f"Protellect_{gene}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="exp_xl_sb", use_container_width=True,
        )









with st.sidebar:
    st.markdown(
        f"<div style='text-align:center;padding:.3rem 0 .5rem;'>"
        f"<div style='display:flex;justify-content:center;margin-bottom:4px;'>{svg_icon('activity', size=22, color='#38bdf8')}</div>"
        f"<div style='color:#38bdf8;font-size:1.05rem;font-weight:800;'>Protellect</div>"
        f"<div style='color:#7dd3fc;font-size:.72rem;margin:.2rem 0;'>Orphan GPCR hypotheses</div>"
        f"</div><div style='border-top:1px solid #0c2040;margin-bottom:.5rem;'></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='sb-t'>Research Goal</div>", unsafe_allow_html=True)
    goal_label=st.selectbox("Goal",GOAL_OPTIONS,label_visibility="collapsed")
    goal_custom=""
    if "Custom" in goal_label:
        goal_custom=st.text_input("Describe your goal",placeholder="e.g. Find splice variants affecting exon 4…",label_visibility="collapsed")
    active_goal=goal_custom if "Custom" in goal_label else goal_label
    st.session_state["active_goal"] = active_goal

    _render_context_sidebar()

    st.markdown("<div class='sb-t'>Protein Search</div>", unsafe_allow_html=True)
    # If user clicked a Recent Work item, prefill + auto-trigger
    _pending_q = st.session_state.pop("_pending_search_query", None)
    if _pending_q:
        st.session_state["protein_query_val"] = _pending_q
        st.session_state["_auto_search_triggered"] = True
    query=st.text_input("Gene / UniProt ID",placeholder="TP53 · BRCA1 · P04637 · FLNC · ACM2",label_visibility="collapsed",value=st.session_state.get("protein_query_val",""),key="protein_query_box")
    _search_btn=st.button("Analyse Protein",use_container_width=True)
    # Auto-trigger search if a recent-work item was clicked
    search = _search_btn or st.session_state.pop("_auto_search_triggered", False)

    st.markdown("<div class='sb-t'>Disease → Proteins</div>", unsafe_allow_html=True)
    disease_q=st.text_input("Search by disease name",placeholder="e.g. dilated cardiomyopathy · Glanzmann",label_visibility="collapsed",key="dis_q_inp")
    dis_search=st.button("Find Disease Proteins",use_container_width=True,key="dis_btn")
    if dis_search:
        if disease_q and disease_q.strip():
            with st.spinner(f"Searching ClinVar for proteins linked to '{disease_q}'..."):
                dp=fetch_disease_proteins(disease_q.strip(),max_genes=20)
                st.session_state["disease_search"]=disease_q.strip()
                st.session_state["disease_proteins"]=dp
                if not dp:
                    st.session_state["disease_proteins"]=[]
                    st.warning(f"No ClinVar results for '{disease_q}'. Try a broader term like 'cardiomyopathy' or 'Glanzmann'.")
        else:
            st.warning("Enter a disease name first.")

    st.markdown("<div class='sb-t'>Wet-Lab Data (CSV)</div>", unsafe_allow_html=True)
    # Show CSV type guide in sidebar
    with st.expander(" What CSVs work best?", expanded=False):
        for ctype, cinfo in CSV_GUIDE.items():
            st.markdown(
                f"<div style='margin:.4rem 0;'><span style='color:#38bdf8;font-weight:700;font-size:.8rem;'>{cinfo['icon']} {cinfo['name']}</span>"
                f"<div style='color:#3a6080;font-size:.73rem;'>Needs: {', '.join(cinfo['required_cols'][:2])}</div>"
                f"<div style='color:#2a5060;font-size:.71rem;'>{cinfo['tip'][:70]}</div></div>",
                unsafe_allow_html=True,
            )
    uploaded_csv=st.file_uploader("Upload CSV (any format)",type=["csv","tsv","txt"],label_visibility="collapsed")
    if uploaded_csv:
        try:
            sep="\t" if uploaded_csv.name.endswith((".tsv",".txt")) else ","
            df=pd.read_csv(uploaded_csv,sep=sep,on_bad_lines="skip")
            csv_type=detect_csv_type(df)
            st.session_state["csv_df"]=df
            st.session_state["csv_type"]=csv_type
            st.session_state["csv_filename"]=uploaded_csv.name
            # Reset any manual override when a NEW file is uploaded
            if st.session_state.get("_csv_last_file") != uploaded_csv.name:
                st.session_state["_csv_last_file"] = uploaded_csv.name
                st.session_state["csv_type_override"] = None
                st.session_state["csv_edit_mode"] = False
                st.session_state["csv_user_description"] = ""
        except Exception as e:
            st.error(f"CSV error: {e}")
    # End sidebar CSV upload here — the full top-bar + edit UI is rendered in the main area
    # (below the empty-state banner / above the tabs) so it doesn't get cut off in the sidebar

    # Run Triage button for CSV-only analysis
    if st.session_state.get("csv_df") is not None:
        # Auto-activate on upload — no need for a separate click. The button below
        # still works as a manual re-trigger.
        if not st.session_state.get("csv_triage_active"):
            st.session_state["csv_triage_active"] = True
        run_csv_triage = st.button(" Re-run Wet-Lab Triage", use_container_width=True, key="csv_triage_btn",
                                    help="Re-analyse the uploaded CSV")
        if run_csv_triage:
            st.session_state["csv_triage_active"] = True
    
    st.markdown("<div class='sb-t'>Assay Notes</div>", unsafe_allow_html=True)
    assay_txt=st.text_area("Assay description",height=70,placeholder="e.g. Western blot shows 3× expression increase…",label_visibility="collapsed")

    # ── Export documentation ─────────────────────────────────────────────
    try:
        _ep = st.session_state.get("pdata")
        _eg = st.session_state.get("gene","")
        if _ep and _eg:
            render_export_button(
                _ep, (st.session_state.get("cv") or {}),
                (st.session_state.get("gi") or {}),
                (st.session_state.get("gnomad") or {}),
                (st.session_state.get("scored") or [])[:0],  # diseases pulled inside fn
                (st.session_state.get("scored") or []),
                _eg, st.session_state.get("uid",""),
                (st.session_state.get("drugs") or []),
                (st.session_state.get("trials") or []),
                (st.session_state.get("ot") or {}),
            )
    except Exception:
        pass

    # ── Export documentation ────────────────────────────────────────────────
    _exp_pdata = st.session_state.get("pdata")
    _exp_gene = st.session_state.get("gene","")
    if _exp_pdata and _exp_gene:
        try:
            render_export_button(
                _exp_pdata,
                (st.session_state.get("cv") or {}),
                (st.session_state.get("gi") or {}),
                (st.session_state.get("gnomad") or {}),
                [],  # diseases pulled inside
                (st.session_state.get("scored") or []),
                _exp_gene,
                st.session_state.get("uid",""),
                (st.session_state.get("drugs") or []),
                (st.session_state.get("trials") or []),
                (st.session_state.get("ot") or {}),
            )
        except Exception:
            pass


    # ── Plan display ───────────────────────────────────────────────────────
    _plan_sb = st.session_state.get("auth_plan","pro")
    _plan_label_sb = {"pro":"Pro · Unlimited","enterprise":"Enterprise","free":"Free (5 searches)"}.get(_plan_sb, _plan_sb.title())
    _plan_clr_sb = "#22c55e" if _plan_sb in ("pro","enterprise") else "#ffd60a"
    st.markdown(
        f"<div style='border-top:1px solid #071828;margin:.6rem 0 .3rem;padding-top:.5rem;"
        f"display:flex;justify-content:space-between;align-items:center;'>"
        f"<span style='color:#1e4060;font-size:.62rem;text-transform:uppercase;letter-spacing:.07em;'>Access</span>"
        f"<span style='background:{_plan_clr_sb}18;color:{_plan_clr_sb};border:1px solid {_plan_clr_sb}33;"
        f"padding:1px 8px;border-radius:4px;font-size:.62rem;font-weight:700;'>{_plan_label_sb}</span>"
        f"</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div class='sb-t'>Variant Triage Threshold</div>"
        "<div style='color:#3a6080;font-size:.75rem;margin-bottom:4px;'>Disease variants / total variants per 100 residues</div>",
        unsafe_allow_html=True,
    )
    sensitivity=st.slider("",0,100,st.session_state["sensitivity"],5,label_visibility="collapsed",
                          help="Controls how many variants per 100 residues are required before a variant is elevated to CRITICAL or HIGH. "
                               "Low (strict) = only variants with strong multi-submitter ClinVar evidence + structural disruption. "
                               "High (sensitive) = surfaces more candidates including single-submitter and moderate structural impact.")
    st.session_state["sensitivity"]=sensitivity
    # Compute real density label from current protein if loaded
    _gi_now = (st.session_state.get("gi") or {})
    _density_now = _gi_now.get("density",0)*100 if _gi_now else 0
    _plen_now = (st.session_state.get("pdata") or {}).get("sequence",{}).get("length",1) if st.session_state.get("pdata") else 1
    _path_now = _gi_now.get("n_pathogenic",0) if _gi_now else 0
    _total_now = _gi_now.get("n_total",1) if _gi_now else 1
    if _gi_now and _path_now > 0:
        _density_per100 = round(_path_now / max(_plen_now,1) * 100, 2)
        _ratio_pct = round(_path_now / max(_total_now,1) * 100, 1)
        sens_lbl = f"{_path_now} disease / {_total_now} total = {_density_per100}/100 residues"
        sens_clr = "#ff2d55" if _density_per100 > 5 else "#ff8c42" if _density_per100 > 1 else "#ffd60a"
    else:
        sens_lbl = "Strict  <————>  Sensitive"
        sens_clr = "#3a6080"
    st.markdown(
        f"<div style='color:{sens_clr};font-size:.78rem;margin-top:2px;font-weight:600;'>{sens_lbl}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='sb-t'>Compare Interaction Partner</div>", unsafe_allow_html=True)
    partner_q=st.text_input("Partner gene / UniProt ID",placeholder="e.g. ITGAL · FLNC · ARRB2",label_visibility="collapsed",key="partner_inp")
    fetch_partner=st.button("Compare Partner",use_container_width=True,key="partner_btn")
    if fetch_partner and partner_q:
        with st.spinner("Fetching partner data..."):
            try:
                p2=fetch_uniprot(partner_q); g2=g_gene(p2); uid2=p2.get("primaryAccession","")
                cv2=fetch_clinvar(g2,100); ln2=p2.get("sequence",{}).get("length",1)
                gi2=compute_gi(cv2,ln2)
                st.session_state["partner_query"]=partner_q
                st.session_state["partner_cv"]=cv2
                st.session_state["partner_gi"]={"gi":gi2,"gene":g2,"uid":uid2}
            except Exception as e: st.error(f"Partner: {e}")

    st.markdown("<div class='sb-t'>Data Depth</div>", unsafe_allow_html=True)
    depth=st.selectbox("Depth",["Standard (150 variants)","Deep (400 variants)"],label_visibility="collapsed")
    max_v=150 if "Standard" in depth else 400
    # Build version — bump on each deploy so you can confirm the live app is current
    st.markdown("<div style='color:#1e3050;font-size:.62rem;text-align:right;margin-top:.3rem;'>build 2026.05.28-n</div>", unsafe_allow_html=True)

    # Sidebar protein summary
    if st.session_state["pdata"]:
        p3=st.session_state["pdata"]; gene3=st.session_state["gene"]; uid3=st.session_state["uid"]
        scored3=st.session_state["scored"]; cv3=st.session_state["cv"]
        st.markdown(f"<div style='border-top:1px solid #0c2040;margin:.6rem 0 .3rem;'></div><div style='background:#050d24;border:1px solid #0c2040;border-radius:8px;padding:7px 9px;'><div style='color:#38bdf8;font-weight:700;font-size:.98rem;'>{gene3}</div><div style='color:#5a8090;font-size:.96rem;'>{uid3}</div></div>", unsafe_allow_html=True)
        gi3=st.session_state.get("gi"); ds_scores={}
        for sv in scored3:
            for c2 in sv.get("condition","").split(";"):
                c2=c2.strip()
                if c2: ds_scores[c2]=max(ds_scores.get(c2,0),sv.get("ml",0))
        diseases3=g_diseases(p3)
        all_names=list(dict.fromkeys([d["name"] for d in diseases3]+[c2 for sv in cv3.get("variants",[]) for c2 in sv.get("condition","").split(";") if c2.strip() and c2.strip()!="Not specified"]))
        if all_names:
            st.markdown("<div class='sb-t'>Disease Affiliations</div>", unsafe_allow_html=True)
            for name3 in all_names[:8]:
                score3=ds_scores.get(name3,.4); rk3="CRITICAL" if score3>=.85 else "HIGH" if score3>=.65 else "MEDIUM" if score3>=.40 else "NEUTRAL"
                if any(k in name3.lower() for k in ["cancer","carcinoma","leukemia","sarcoma"]) and rk3=="MEDIUM": rk3="HIGH"
                css3=RANK_CSS[rk3]
                st.markdown(f"<div style='display:flex;align-items:center;gap:6px;margin:3px 0;'><span class='badge {css3}'>{rk3}</span><span style='color:#5a8090;font-size:.81rem;'>{name3[:32]}</span></div>", unsafe_allow_html=True)
        _ent3 = classify_entity(p3)
        _gi3  = st.session_state.get("gi") or {}
        _n_crit3 = sum(1 for v in scored3 if v.get("ml_rank")=="CRITICAL")
        _n_lof3  = sum(1 for v in scored3 if any(k in v.get("variant_name","").lower() for k in ["del","ter","fs","stop","nonsense"]) and v.get("score",0)>=3)
        _gnomad3 = st.session_state.get("gnomad") or {}
        _pli3    = (_gnomad3.get("pLI") if isinstance(_gnomad3, dict) else 0) or 0
        _goal3   = get_goal_config(active_goal)
        # Generate protein-specific experiments from actual data
        _exps3 = []
        if _ent3["ptype"] == "kinase":
            _exps3 = [
                f"ADP-Glo kinase assay — test {min(3,_n_crit3)} CRITICAL variants vs WT",
                f"pERK/pAKT western — downstream signalling loss in mutant cells",
                f"{'HTS inhibitor screen (tractable)' if ((st.session_state.get('ot') or {}).get('tractability') or {}).get('Small molecule') else 'Allosteric site mapping by HDX-MS'}",
            ]
        elif _ent3["ptype"] == "gpcr":
            _exps3 = [
                "cAMP HTRF (Gs coupling) + beta-arrestin BRET (bias)",
                "Radioligand competition binding assay",
                "BRET2 proximity assay for G-protein selectivity",
            ]
        elif _ent3["ptype"] == "transcription_factor":
            _exps3 = [
                "EMSA — test DNA binding affinity of mutant vs WT",
                "ChIP-seq — identify lost target gene occupancy sites",
                "Luciferase reporter — quantify transactivation defect",
            ]
        elif _ent3["ptype"] == "ion_channel":
            _exps3 = [
                "Whole-cell patch clamp — current amplitude in mutant",
                "Tl+ flux assay (HTS-compatible) — channel permeability",
                "Confocal imaging — surface trafficking of mutant channel",
            ]
        elif _ent3["ptype"] == "structural":
            _exps3 = [
                "Negative-stain EM — confirm mutant folds correctly",
                "AP-MS (affinity purification + mass spec) — unbiased interactome in mutant vs WT cells",
                f"ASO splice modulation — {_n_lof3} LoF variants suggest splice correction viable",
            ]
        else:
            _exps3 = [
                f"Variant activity assay (ADP-Glo / HTRF) — {_n_crit3} CRITICAL variants vs WT",
                f"{'CRISPR knock-in (pLI=' + str(_pli3) + ' — strong phenotype expected)' if _pli3 > 0.8 else 'Cell viability panel — confirm loss-of-function phenotype first'}",
                f"{_goal3.get('experiment_priority',['Variant biochemical activity assay'])[0]}",
            ]
        st.markdown("<div class='sb-t'>Prioritised Experiments</div>", unsafe_allow_html=True)
        for s3 in _exps3:
            st.markdown(f"<div style='color:#7ab0c4;font-size:.82rem;margin:2px 0;'>▸ {s3}</div>", unsafe_allow_html=True)
        if _goal3.get("sidebar_tip"):
            st.markdown(
                f"<div style='background:#050d24;border:1px solid #38bdf822;border-radius:7px;padding:6px 9px;margin-top:5px;'>"
                f"<div style='color:#3a7090;font-size:.74rem;'><b style='color:#4a8090;'>Goal tip:</b> {_goal3['sidebar_tip']}</div></div>",
                unsafe_allow_html=True,
            )

        # Excel download button
        st.markdown("<div class='sb-t'>Export All Data</div>", unsafe_allow_html=True)
        if st.button(' Download Excel Report', use_container_width=True, key='xl_btn'):
            with st.spinner('Building Excel workbook (9 sheets)...'):
                xl_bytes = generate_excel(
                    gene3, p3, cv3, scored3,
                    (st.session_state.get('gi') or {}),
                    (st.session_state.get('gnomad') or {}),
                    (st.session_state.get('string') or []),
                    (st.session_state.get('drugs') or []),
                    (st.session_state.get('trials') or []),
                    (st.session_state.get('ot') or {}),
                    g_diseases(p3),
                    (st.session_state.get('papers') or []),
                    (st.session_state.get('patients') or {}),
                    compute_experiment_roi(scored3,(st.session_state.get('gi') or {}),g_ptype(p3),(st.session_state.get('gnomad') or {}),(st.session_state.get('ot') or {})),
                    (st.session_state.get('am') or {}),
                    (st.session_state.get('hotspots') or []),
                )
                if xl_bytes:
                    st.session_state['excel_bytes'] = xl_bytes
        if st.session_state.get('excel_bytes'):
            st.download_button(' Save Excel', st.session_state['excel_bytes'],
                file_name=f'Protellect_{gene3}_report.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True, key='xl_dl')




# ─── Handle click-to-analyse from workspace buttons ──────────────────
# These may be overridden below by the sidebar widgets — ensure defaults exist
if "search" not in dir(): search = False
if "query" not in dir(): query = ""
if st.session_state.get("_trigger_search"):
    _tq = st.session_state.pop("_trigger_search")
    if _tq and _tq != st.session_state.get("last",""):
        st.session_state["last"] = ""
        st.session_state["protein_query_val"] = _tq
        query = _tq
        search = True

# ─── Header ─────────────────────────────────────────────────────────
st.markdown(
    "<div class='ph'>"
    "<div style='display:flex;align-items:center;gap:14px;'>"
    f"<img src='{_logo_src}' style='width:52px;height:52px;object-fit:contain;filter:drop-shadow(0 0 14px #38bdf866);animation:spinDNA 12s linear infinite;'>"
    f"<div>"
    f"<div class='pt'>Protellect</div>"
    f"<div class='ps'>AI-powered protein triage · Genetics-first · Eliminate wasted experiments</div>"
    f"</div></div></div>",
    unsafe_allow_html=True,
)

# ─── Tutorial trigger ────────────────────────────────────────────────
if st.session_state.get("show_tutorial", True):
    st.session_state["show_tutorial"] = False   # open once; the sidebar button reopens it on demand
    show_tutorial_dialog()

# Persistent tutorial button in header area
with st.container():
    _, btn_col = st.columns([10, 1])
    with btn_col:
        if st.button("Tutorial", key="tut_btn", help="Open the tutorial"):
            st.session_state["show_tutorial"] = True
            st.rerun()

# ── Empty-state hint when no protein is loaded ────────────────────────────────
if not st.session_state.get("pdata") and not st.session_state.get("csv_triage_active"):
    _suggest = "GPR151"
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#050d24,#0a1530);"
        f"border:1px solid #38bdf833;border-left:4px solid #38bdf8;"
        f"border-radius:10px;padding:.95rem 1.2rem;margin:.4rem 0 1rem;display:flex;"
        f"align-items:center;gap:14px;'>"
        f"{svg_icon('search', size=28, color='#38bdf8')}"
        f"<div style='flex:1;'>"
        f"<div style='color:#e6edf7;font-weight:700;font-size:.95rem;margin-bottom:2px;'>"
        f"Search a protein to populate every tab</div>"
        f"<div style='color:#94a3b8;font-size:.8rem;line-height:1.5;'>"
        f"Use the sidebar search — gene symbol (GPR151, GPR88, TP53) or UniProt accession (P04637). "
        f"Try: <b style='color:#38bdf8;'>{_suggest}</b> to explore."
        f"</div></div></div>",
        unsafe_allow_html=True,
    )

# ── Tabs: one fixed, predictable order. The Hypotheses tab sits next to Summary. ──────────────────────────
ALL_TAB_NAMES = ["Overview","Triage","Druggable hotspots","Genetics","Case Study","Experiments"]
_visible_tab_names = ALL_TAB_NAMES




class _SinkTab:
    """Context manager that absorbs all Streamlit rendering inside it (used for unchecked tabs).
    The tab does NOT appear in the strip; if any `with tabN:` block tries to render content for it,
    that content goes into a placeholder which is immediately cleared on exit. No UI noise."""
    def __enter__(self):
        self._slot = st.empty()
        self._cm = self._slot.container()
        return self._cm.__enter__()
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._cm.__exit__(exc_type, exc_val, exc_tb)
        finally:
            try:
                self._slot.empty()
            except Exception:
                pass
        return False  # don't suppress exceptions


# ── CSV Detection Bar (visible when a wet-lab CSV is loaded) ─────────────────
_csv_df_top = st.session_state.get("csv_df")
if _csv_df_top is not None:
    _csv_name_top = st.session_state.get("csv_filename","uploaded.csv")
    _csv_type_top = st.session_state.get("csv_type_override") or st.session_state.get("csv_type","generic")
    _csv_user_desc = st.session_state.get("csv_user_description","")
    _csv_summary = _csv_user_desc.strip() if _csv_user_desc.strip() else summarise_assay(_csv_df_top, _csv_type_top)
    _type_pretty = _csv_type_top.replace("_"," ").title()
    _is_overridden = bool(st.session_state.get("csv_type_override")) or bool(_csv_user_desc.strip())

    if not st.session_state.get("csv_edit_mode"):
        # Display bar
        st.markdown(
            f"<div style='background:linear-gradient(90deg,rgba(56,189,248,.1),rgba(56,189,248,.02));"
            f"border:1px solid rgba(56,189,248,.32);border-left:4px solid #38bdf8;"
            f"border-radius:10px;padding:.7rem 1.1rem;margin:.5rem 0;'>"
            f"<div style='display:flex;align-items:center;gap:14px;'>"
            f"<div style='flex:1;'>"
            f"<div style='color:#94a3b8;font-size:.66rem;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px;'>"
            f"Wet-lab CSV loaded · {len(_csv_df_top):,} rows × {len(_csv_df_top.columns)} columns"
            f"</div>"
            f"<div style='color:#e6edf7;font-size:.86rem;font-weight:700;margin-bottom:3px;'>"
            f"{_csv_name_top} · <span style='color:#38bdf8;'>{_type_pretty}</span>"
            f"{' <span style=color:#34d399;font-size:.72rem;font-weight:600;>(manual override)</span>' if _is_overridden else ''}"
            f"</div>"
            f"<div style='color:#94a3b8;font-size:.75rem;line-height:1.5;'>{_csv_summary[:280]}</div>"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )
        _ec1, _ec2, _ec3 = st.columns([1,1,5])
        with _ec1:
            if st.button("Is this not right? Edit", key="csv_edit_btn"):
                st.session_state["csv_edit_mode"] = True
                st.rerun()
        with _ec2:
            if st.button("Run analysis from this CSV", key="csv_run_btn", type="primary"):
                st.session_state["csv_triage_active"] = True
                st.rerun()
    else:
        # Edit mode
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#050d24,#0a1530);"
            f"border:1px solid rgba(167,139,250,.4);border-left:4px solid #a78bfa;"
            f"border-radius:10px;padding:.9rem 1.2rem;margin:.5rem 0;'>"
            f"<div style='color:#a78bfa;font-weight:700;font-size:.9rem;margin-bottom:6px;'>"
            f"Correct the CSV interpretation</div>"
            f"<div style='color:#94a3b8;font-size:.74rem;line-height:1.6;'>"
            f"Override the auto-detected type and/or describe what this CSV actually contains. "
            f"All downstream analysis (Triage, Experiments) will use your description as the ground truth.</div></div>",
            unsafe_allow_html=True,
        )
        _CSV_TYPES = ["expression","variants","proteomics","stats","generic"]
        _CSV_LABELS = {
            "expression":  "Gene expression — RNA-seq / microarray / qPCR fold-changes",
            "variants":    "Variants — VCF-derived, ClinVar-style classifications",
            "proteomics":  "Proteomics — mass-spec intensities / abundance ratios",
            "stats":       "Statistical results — p-values, GWAS, differential analysis",
            "generic":     "Generic tabular data (let the AI infer from your description)",
        }
        _new_type = st.selectbox(
            "Actual CSV type",
            _CSV_TYPES,
            index=_CSV_TYPES.index(_csv_type_top) if _csv_type_top in _CSV_TYPES else 4,
            format_func=lambda x: _CSV_LABELS.get(x,x),
            key="csv_type_override_sel",
        )
        _new_desc = st.text_area(
            "Describe what this CSV is about (this becomes ground truth for all analysis)",
            value=_csv_user_desc,
            placeholder="e.g. Patient-derived iPSC western blot densitometry. 12 patient lines vs 4 healthy controls. Values are normalized to GAPDH. Variants tested: p.Arg175His, p.Gly12Asp...",
            height=110,
            key="csv_user_desc_input",
        )
        # Quick preview of first 5 rows
        with st.expander(f"Preview first 5 rows of {_csv_name_top}", expanded=False):
            st.dataframe(_csv_df_top.head(5), use_container_width=True)
        _sc1, _sc2 = st.columns([1,4])
        with _sc1:
            if st.button("Save & re-run", key="csv_save_override", type="primary"):
                st.session_state["csv_type_override"] = _new_type
                st.session_state["csv_user_description"] = _new_desc.strip()
                st.session_state["csv_edit_mode"] = False
                # If a protein is loaded, mark for re-analysis using the new description
                if st.session_state.get("pdata"):
                    st.session_state["csv_reanalyze_pending"] = True
                st.rerun()
        with _sc2:
            if st.button("Cancel", key="csv_cancel_override"):
                st.session_state["csv_edit_mode"] = False
                st.rerun()

# Logo strip directly above the tabs — keeps the brand visible at the workspace anchor
_subtitle = "Auditable orphan GPCR triage and hypotheses"
st.markdown(
    f"<div style='display:flex;align-items:center;gap:12px;margin:.6rem 0 .3rem;padding:.5rem .9rem;"
    f"background:linear-gradient(90deg,rgba(56,189,248,.06),rgba(56,189,248,0) 60%);"
    f"border-bottom:1px solid rgba(56,189,248,.18);border-radius:8px 8px 0 0;'>"
    f"<img src='{_logo_src}' style='width:36px;height:36px;object-fit:contain;flex-shrink:0;"
    f"filter:drop-shadow(0 0 6px rgba(56,189,248,.4));'>"
    f"<div style='flex:1;'>"
    f"<div style='color:#e6edf7;font-weight:800;font-size:1rem;letter-spacing:-.2px;'>Protellect</div>"
    f"<div style='color:#94a3b8;font-size:.72rem;'>{_subtitle}</div>"
    f"</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# Create only the visible tabs in the strip
# Banner slot: filled after the analysis exists, but shown ABOVE the tab strip
_banner_slot = st.container()
_visible_tab_objs = st.tabs(_visible_tab_names)
_tab_by_name = {n: _visible_tab_objs[i] for i, n in enumerate(_visible_tab_names)}

# Assign canonical tab0..tab9 — real tab if visible, sink if not.
# This keeps every `with tabN:` block working without indentation changes; hidden tabs just absorb their content.
tab0 = _tab_by_name.get("Overview",           _SinkTab())
tab1 = _tab_by_name.get("Triage",             _SinkTab())
tab2 = _tab_by_name.get("Case Study",         _SinkTab())
tab4 = _tab_by_name.get("Experiments",        _SinkTab())
tab7 = _tab_by_name.get("Genetics",           _SinkTab())
tab9 = _tab_by_name.get("Druggable hotspots", _SinkTab())

_pdata_f = st.session_state.get("pdata") or {}
_gene_f = st.session_state.get("gene","")


if search and query:
    # Search button was clicked. Always re-run analysis fully — this guarantees
    # the live scan trace appears every time and never re-uses stale state.
    if not check_search_limit():
        st.markdown(
            "<div style='background:#0a0300;border:2px solid #ffd60a;border-radius:10px;"
            "padding:.9rem 1.2rem;margin:.5rem 0;'>"
            "<div style='color:#ffd60a;font-weight:800;'>Search limit reached</div>"
            "<div style='color:#8a7040;font-size:.86rem;margin:.3rem 0;'>Free plan: 5 analyses included. Upgrade to Pro for 200/month.</div>"
            f"<a href='{STRIPE_LINKS['pro']}' target='_blank' style='background:#38bdf8;color:#000;font-weight:700;"
            "padding:4px 18px;border-radius:8px;font-size:.82rem;text-decoration:none;display:inline-block;margin-top:.3rem;'>"
            "Upgrade to Pro — $49/month</a></div>",
            unsafe_allow_html=True,
        )
        st.stop()
    decrement_search()

    # ── Clear stale disambiguation from any previous search ──────────────────
    st.session_state["_search_disambiguation"] = None

    # ── Pre-search: block generic/category names that return garbage data ─────
    _q_pre = query.strip().lower()
    _STOP_TERMS = {
        # Food / substance terms
        "gelatin":    ("ADIPOQ · COL1A1 · MMP2",      "Gelatin is denatured collagen — not a gene. Adiponectin (ADIPOQ) was nicknamed 'Gelatin-Binding Protein 28' in 1990s literature."),
        "sugar":      ("SLC2A1 · GCK · INS",           "Not a gene. Try: SLC2A1 (GLUT1), GCK (glucokinase), INS (insulin)."),
        "fat":        ("FASN · ADIPOQ · PPARG",         "Not a gene. Try: FASN (fatty acid synthase), ADIPOQ (adiponectin), PPARG (fat cell regulator)."),
        "calcium":    ("CACNA1S · CALM1 · ATP2A1",      "Calcium is an ion, not a gene. Try: CACNA1S (Ca²⁺ channel), CALM1 (calmodulin), ATP2A1 (SERCA pump)."),
        "vitamin":    ("VDR · RBP4 · SLC23A1",          "Not a gene. Try: VDR (vitamin D receptor), RBP4 (retinol-binding), SLC23A1 (vitamin C transporter)."),
        # Protein family names — UniProt can't resolve these to one gene
        "keratin":    ("KRT1 · KRT5 · KRT14 · KRT18",  "Keratin is a family of 54 genes. Clinically relevant: KRT5/14 (epidermolysis bullosa), KRT8/18 (liver disease), KRT1/10 (ichthyosis). Search the specific number."),
        "collagen":   ("COL1A1 · COL4A1 · COL2A1",     "Collagen is a family of 28 genes. Try: COL1A1/2 (OI, EDS), COL4A1 (HANAC syndrome), COL2A1 (spondyloepiphyseal dysplasia)."),
        "actin":      ("ACTB · ACTA1 · ACTA2",          "Actin is a family. Try: ACTB (cytoskeletal, ubiquitous), ACTA1 (skeletal muscle myopathy), ACTA2 (smooth muscle, aortic aneurysm)."),
        "myosin":     ("MYH7 · MYH9 · MYL2",            "Myosin is a family of >40 genes. Try: MYH7 (HCM), MYH9 (MYH9-related disease), MYL2 (cardiac light chain)."),
        "hemoglobin": ("HBB · HBA1 · HBA2",             "Try: HBB (sickle cell, beta-thalassaemia), HBA1/HBA2 (alpha-thalassaemia)."),
        "haemoglobin":("HBB · HBA1 · HBA2",             "Try: HBB (sickle cell, beta-thalassaemia), HBA1/HBA2 (alpha-thalassaemia)."),
        "tubulin":    ("TUBA1A · TUBB2B · TUBB3",       "Try: TUBA1A (lissencephaly), TUBB2B (pachygyria), TUBB3 (CFEOM congenital fibrosis)."),
        "fibrin":     ("FGB · FGA · FGG",                "Fibrin is a cleavage product. The fibrinogen genes are: FGA (alpha), FGB (beta), FGG (gamma)."),
        "albumin":    ("ALB",                            "Human serum albumin gene is ALB. Try: ALB (hypoalbuminaemia, liver function)."),
        "elastin":    ("ELN",                            "Human elastin gene is ELN. Mutations cause supravalvular aortic stenosis and Williams syndrome."),
        "laminin":    ("LAMA2 · LAMA4 · LAMB1",         "Laminin is a family. Try: LAMA2 (merosin-deficient CMD), LAMB2 (Pierson syndrome)."),
        "fibronectin":("FN1",                             "Fibronectin = FN1. Mutations cause glomerulopathy with fibronectin deposits."),
        "filamin":    ("FLNA · FLNB · FLNC",             "Filamin is a family of 3 genes. FLNA: X-linked periventricular heterotopia + GPCR piggyback assay (PMID:26124276). FLNB: Boomerang/Larsen dysplasia (skeletal). FLNC: Myofibrillar myopathy + dilated cardiomyopathy. Search by specific gene symbol."),
        "spectrin":   ("SPTA1 · SPTB · SPTAN1",          "Spectrin is a family. SPTA1/SPTB: hereditary spherocytosis/elliptocytosis. SPTAN1: early infantile epileptic encephalopathy."),
        "troponin":   ("TNNT2 · TNNI3 · TNNC1",          "Troponin has 3 cardiac subunits. TNNT2 (T): HCM/DCM. TNNI3 (I): HCM/RCM. TNNC1 (C): HCM. All cause inherited cardiomyopathy."),
        "titin":      ("TTN",                             "Titin gene = TTN. Largest human gene. Truncating variants (TTNtv) cause ~25% of familial DCM."),
        "dystrophin": ("DMD",                             "Dystrophin gene = DMD. Frameshift/nonsense = Duchenne MD. In-frame deletions = Becker MD."),
        "fibrinogen": ("FGA · FGB · FGG",                 "Fibrinogen has 3 chains: FGA (alpha), FGB (beta — most clinically important), FGG (gamma)."),
        # Fully generic terms
        "protein":    (None, "Too generic — matches thousands of entries. Search a specific gene (TP53, BRCA1, EGFR) or UniProt accession (P04637)."),
        "enzyme":     (None, "Too generic. Search a specific enzyme gene (LDH, GPT, ACE, PCSK9) or use an EC number."),
        "receptor":   (None, "Too generic. Search a specific receptor (EGFR, ADRB2, GRIA1, GABRA1, SCN1A)."),
        "channel":    (None, "Too generic. Search a specific channel gene (SCN1A, KCNQ2, CACNA1S, CFTR, PIEZO1)."),
        "antibody":   (None, "Antibodies target proteins. Search the antigen gene instead (EGFR, ERBB2=HER2, CD274=PD-L1, MS4A1=CD20)."),
        "hormone":    (None, "Too generic. Search a specific hormone gene (INS=insulin, GH1, TSHB, POMC, LEP=leptin, GHRH)."),
        "cytokine":   (None, "Too generic. Search a specific cytokine gene (TNF, IL6, IL1B, IFNG, IL10, TGFB1)."),
        "integrin":   (None, "Integrin is a family. Search the specific subunit (ITGB1, ITGA2B, ITGB3, ITGAV)."),
    }
    _stop_hit = None
    for _term, (_suggest, _explain) in _STOP_TERMS.items():
        if _q_pre == _term or _q_pre.startswith(_term + " ") or _q_pre.endswith(" " + _term):
            _stop_hit = (_term, _suggest, _explain)
            break

    if _stop_hit:
        _t, _s, _e = _stop_hit
        st.markdown(
            f"<div style='background:#030810;border:2px solid #ffd60a55;border-left:5px solid #ffd60a;"
            f"border-radius:0 14px 14px 0;padding:1.3rem 1.5rem;margin:.6rem 0;'>"
            f"<div style='color:#ffd60a;font-weight:800;font-size:1rem;margin-bottom:.6rem;'>"
            f" &nbsp;'{query}' is a protein family name, not a gene symbol</div>"
            f"<div style='color:#c0a840;font-size:.85rem;line-height:1.75;margin-bottom:.7rem;'>{_e}</div>"
            f"{'<div style=background:#050d24;border:1px solid #4a90d955;border-radius:9px;padding:8px 14px;><span style=color:#1e4060;font-size:.73rem;>Use one of these gene symbols: </span><br><span style=color:#38bdf8;font-size:.92rem;font-weight:700;>' + _s + '</span></div>' if _s else ''}"
            f"</div>",
            unsafe_allow_html=True
        )
        st.stop()  # Stop here — don't proceed with a search that returns garbage

    # Clear ALL stale protein data before each new search.
    # Clear each key to its CORRECT empty type so downstream .get(...) + attribute
    # access never hits a None (the cause of the recurring AttributeErrors).
    _dict_keys = {"pdata","cv","gi","gnomad","org","ai_result","ot","am","patients",
                  "domain_ctx","acmg_auto","ml_result","clingen","reg_paths"}
    _list_keys = {"string","trials","drugs","abstracts","isoforms","hotspots","scored",
                  "papers","analogs","roi_data","conflicts","analysis_trace"}
    _str_keys  = {"gene","uid","pdb","_search_disambiguation"}
    for _clr_key in (_dict_keys | _list_keys | _str_keys | {"excel_bytes"}):
        if _clr_key in _dict_keys:   st.session_state[_clr_key] = {}
        elif _clr_key in _list_keys: st.session_state[_clr_key] = []
        elif _clr_key in _str_keys:  st.session_state[_clr_key] = ""
        else:                        st.session_state[_clr_key] = None  # excel_bytes (binary)
    st.session_state["scored"] = []
    # Clear any per-protein workspace chat history so questions about prior proteins don't leak
    for _ws_k in [k for k in list(st.session_state.keys()) if isinstance(k,str) and k.startswith("ws_chat_") and k != "ws_active_chat_key"]:
        try: del st.session_state[_ws_k]
        except Exception: pass
    st.session_state["last"] = query
    # Clear cache so stale results never persist between searches
    fetch_uniprot.clear()

    # ── LIVE SCAN TRACE — dropdown showing every API call as it happens ─────
    # Prominent banner above the spinner so it's visible from the start
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#050d24,#0a1530);"
        f"border:1px solid rgba(56,189,248,.3);border-left:4px solid #38bdf8;"
        f"border-radius:10px;padding:.7rem 1.1rem;margin:.6rem 0;'>"
        f"<div style='color:#38bdf8;font-weight:700;font-size:.85rem;margin-bottom:2px;'>"
        f"Analysing <code style='color:#7dd3fc;background:rgba(56,189,248,.1);padding:1px 6px;border-radius:4px;'>{query}</code>"
        f"</div>"
        f"<div style='color:#94a3b8;font-size:.72rem;'>Live trace of all API calls below — expand to see exactly which databases are being queried.</div></div>",
        unsafe_allow_html=True,
    )

    _scan_steps = []
    _scan_box = st.empty()
    def _render_scan():
        """Re-render the scan trace dropdown from current _scan_steps state."""
        if not _scan_steps:
            _scan_box.empty()
            return
        _rows = []
        for s in _scan_steps:
            if s["status"] == "run":
                _icon, _clr = "→", "var(--cyan)"
            elif s["status"] == "ok":
                _icon, _clr = "✓", "var(--green)"
            elif s["status"] == "skip":
                _icon, _clr = "·", "var(--text3)"
            else:
                _icon, _clr = "✕", "var(--rose)"
            _rows.append(
                f"<div style='padding:4px 0;border-bottom:1px solid rgba(56,189,248,.06);'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<span style='color:{_clr};font-weight:700;font-size:.78rem;'>[{_icon}] {s['label']}</span>"
                f"</div>"
                f"<code style='color:var(--text3);font-size:.65rem;font-family:DM Mono,monospace;display:block;margin-top:1px;'>{s['code']}</code>"
                f"</div>"
            )
        _n_done = sum(1 for s in _scan_steps if s["status"]=="ok")
        _scan_box.markdown(
            f"<details open style='background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:.4rem .8rem;margin:.4rem 0;'>"
            f"<summary style='color:var(--text);font-weight:700;font-size:.84rem;cursor:pointer;padding:6px 0;'>"
            f"Analysis trace · {len(_scan_steps)} steps · {_n_done} complete</summary>"
            f"<div style='margin-top:.5rem;'>" + "".join(_rows) + "</div></details>",
            unsafe_allow_html=True,
        )

    def _scan(label, code_hint, status="run"):
        """Append a step to the live trace and re-render."""
        _scan_steps.append({"label":label,"code":code_hint,"status":status})
        _render_scan()

    def _scan_done(label, code_hint, n_results=None):
        """Mark a previously-started step as complete."""
        for s in _scan_steps:
            if s["label"] == label and s["status"] == "run":
                s["status"] = "ok"
                if n_results is not None:
                    s["code"] = code_hint + f"  → {n_results} results"
                break
        _render_scan()

    with st.spinner(" Fetching UniProt · ClinVar · AlphaFold · PubMed…"):
        try:
            _scan("UniProt", f"GET https://rest.uniprot.org/uniprotkb/search?query={query}")
            pdata=fetch_uniprot(query)
            _scan_done("UniProt", f"GET https://rest.uniprot.org/uniprotkb/search?query={query}", 1 if pdata else 0)
            # Final organism guard — reject anything not Homo sapiens
            _org_check = pdata.get("organism",{})
            _sci_name  = _org_check.get("scientificName","")
            _tax_id    = _org_check.get("taxonId",0)
            if "Homo sapiens" not in _sci_name and _tax_id != 9606:
                _common = _org_check.get("commonName", _sci_name)
                raise ValueError(
                    f"Non-human protein: '{query}' resolved to {_common} ({_sci_name}). "
                    f"Protellect only analyses human proteins. Try: TP53 · FLNC · BRCA1 · EGFR"
                )
            # ── Validate pdata has real content ───────────────────────────────
            _seq_check = pdata.get("sequence",{}).get("value","") if pdata else ""
            _gene_check = g_gene(pdata) if pdata else ""
            if not _seq_check or len(_seq_check) < 5 or _gene_check in ("?",""):
                raise ValueError(
                    f" '{query}' returned an incomplete protein record (no sequence data). "
                    f"This usually means the search matched a partial or deprecated entry. "
                    f"Try searching by exact gene symbol (e.g. FLNA for Filamin A, "
                    f"ACTB for beta-actin, MYH7 for cardiac myosin) or by UniProt accession."
                )
            st.session_state["pdata"]=pdata
            gene=g_gene(pdata); uid=pdata.get("primaryAccession","")
            st.session_state["gene"]=gene; st.session_state["uid"]=uid
            # ── Search confidence banner ──────────────────────────────────────
            _conf = pdata.get("_search_confidence","exact_gene_symbol")
            if _conf == "protein_name_match":
                try:
                    _pn = (pdata.get("proteinDescription",{}) or {}).get("recommendedName",{}).get("fullName",{}).get("value","") or ""
                    st.session_state["_search_disambiguation"] = _is_ambiguous_search(query, gene, _pn)
                except Exception:
                    st.session_state["_search_disambiguation"] = None
            elif not st.session_state.get("_search_disambiguation"):
                st.session_state["_search_disambiguation"] = None
            _scan("ClinVar (NCBI)", f"GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&term={gene}[gene]")
            cv=fetch_clinvar(gene,max_v); st.session_state["cv"]=cv
            _scan_done("ClinVar (NCBI)", f"GET clinvar?term={gene}[gene]", len((cv or {}).get("variants",[])))
            _scan("AlphaFold (EBI)", f"GET https://alphafold.ebi.ac.uk/files/AF-{uid}-F1-model_v4.pdb")
            pdb=fetch_pdb(uid); st.session_state["pdb"]=pdb
            _scan_done("AlphaFold (EBI)", f"GET alphafold AF-{uid}", 1 if pdb else 0)
            _scan("Europe PMC", f"GET europepmc.org/webservices/rest/search?query={gene}")
            papers=fetch_papers(gene); st.session_state["papers"]=papers
            _scan_done("Europe PMC", f"GET europepmc.org search query={gene}", len(papers or []))
            scored=ml_score_variants(cv.get("variants",[]),sensitivity)
            st.session_state["scored"]=scored
            protein_len=pdata.get("sequence",{}).get("length",1)
            gi=compute_gi(cv,protein_len); st.session_state["gi"]=gi
            # Save to workspace history
            save_to_workspace(g_gene(pdata), pdata, gi, g_diseases(pdata), [])
            st.session_state["assay"]=assay_txt; st.session_state["last"]=query
            # Extended data fetches
            with st.spinner(" Fetching interactions, population genetics & drug data..."):
                _scan("gnomAD v4", f"POST gnomad.broadinstitute.org/api  query={{ gene(symbol:{gene}) constraint }}")
                gnomad_data  = fetch_gnomad(gene)
                _scan_done("gnomAD v4", f"POST gnomad.broadinstitute.org/api {gene}", 1 if gnomad_data else 0)
                _scan("STRING-DB", f"GET string-db.org/api/json/network?identifiers={gene}")
                string_data  = fetch_string_interactions(gene)
                _scan_done("STRING-DB", f"GET string-db.org/api network={gene}", len(string_data or []))
                _scan("ClinicalTrials.gov", f"GET clinicaltrials.gov/api/v2/studies?query.term={gene}")
                trials_data  = fetch_clinical_trials(gene)
                _scan_done("ClinicalTrials.gov", f"GET clinicaltrials.gov  q={gene}", len(trials_data or []))
                _scan("DGIdb (drug)", f"POST dgidb.org/api/graphql  genes:[{gene}]")
                drugs_data   = fetch_dgidb(gene)
                _scan_done("DGIdb (drug)", f"POST dgidb.org/api {gene}", len(drugs_data or []))
                _scan("PubMed abstracts", f"GET eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={gene}")
                abstracts    = fetch_pubmed_abstracts(gene)
                _scan_done("PubMed abstracts", f"GET pubmed esearch {gene}", len(abstracts or []))
                org_class    = classify_organism(pdata)
                st.session_state["gnomad"]   = gnomad_data
                st.session_state["string"]   = string_data
                st.session_state["trials"]   = trials_data
                st.session_state["drugs"]    = drugs_data
                st.session_state["abstracts"]= abstracts
                st.session_state["org"]      = org_class
            # Power features
            with st.spinner(" Fetching OpenTargets, AlphaMissense & computing hotspots..."):
                _scan("OpenTargets Platform", f"POST api.platform.opentargets.org  query target({gene})")
                ot_data   = fetch_opentargets(gene)
                _scan_done("OpenTargets Platform", f"POST opentargets {gene}", 1 if ot_data else 0)
                _scan("AlphaMissense", f"GET https://alphamissense.hegelab.org/{uid}")
                am_scores = fetch_alphamissense(uid)
                _scan_done("AlphaMissense", f"GET alphamissense {uid}", len(am_scores or {}))
                _scan("UniProt isoforms", f"GET uniprot.org/uniprotkb/{uid}/isoforms")
                isoforms  = fetch_isoforms(uid)
                _scan_done("UniProt isoforms", f"GET uniprot {uid}/isoforms", len(isoforms or []))
                _scan("Hotspot clustering", f"compute_hotspot_clusters(variants={len(cv.get('variants',[]))}, L={protein_len})")
                hotspots  = compute_hotspot_clusters(cv.get("variants",[]), pdata.get("sequence",{}).get("length",1))
                _scan_done("Hotspot clustering", f"compute_hotspot_clusters L={protein_len}", len(hotspots or []))
                _scan("Patient population estimation", f"estimate_patient_population(diseases={len(g_diseases(pdata) or [])})")
                patient_d = estimate_patient_population(g_diseases(pdata), cv, compute_gi(cv, pdata.get("sequence",{}).get("length",1)))
                _scan_done("Patient population estimation", f"estimate_patient_population", 1 if patient_d else 0)
                # ── ClinGen gene-disease validity ─────────────────────────────
                _scan("ClinGen", f"GET search.clinicalgenome.org/kb/gene-validity?search={gene}")
                try:
                    clingen_data = fetch_clingen(gene)
                except Exception:
                    clingen_data = {"classifications": []}
                _scan_done("ClinGen", f"GET clinicalgenome.org/{gene}", len((clingen_data or {}).get("classifications",[])))
                st.session_state["clingen"]   = clingen_data
                st.session_state["ot"]        = ot_data
                st.session_state["am"]        = am_scores
                st.session_state["isoforms"]  = isoforms
                st.session_state["hotspots"]  = hotspots
                st.session_state["patients"]  = patient_d
                # ── NEW: ML scoring + domain hotspot + ACMG + conflict detection ──
                domain_ctx = score_domain_context(
                    pdata, cv.get("variants",[]),
                    am_scores if isinstance(am_scores, dict) else {}
                )
                acmg_auto  = auto_acmg_criteria(pdata, cv, gnomad_data, am_scores)
                conflicts  = score_conflict_detection(cv, gnomad_data, am_scores)
                # ML-backed variant re-scoring
                _pli_val   = gnomad_data.get("pLI", 0) or 0
                _oel_val   = gnomad_data.get("oe_lof_upper", 1) or 1
                _mz_val    = gnomad_data.get("mis_z", 0) or 0
                _gi_val    = domain_ctx.get("gi_score", gi.get("density",0) if gi else 0)
                _plp_val   = domain_ctx.get("plp_count", 0)
                _tot_val   = domain_ctx.get("total_cv", 0)
                ml_result  = score_variant_ml(
                    consequence="missense",
                    clinvar_stars=min(4, int(_plp_val / max(_tot_val,1) * 20)),
                    pli=_pli_val, cv_density=_gi_val,
                    gnomad_af=0.0,
                    am_score=0.5,
                    gene_total_cv=_tot_val, gene_plp_count=_plp_val,
                    oe_lof_upper=_oel_val, mis_z=_mz_val,
                )
                st.session_state["domain_ctx"]  = domain_ctx
                st.session_state["acmg_auto"]   = acmg_auto
                st.session_state["conflicts"]   = conflicts
                st.session_state["ml_result"]   = ml_result
                # ── NEW: compute regulatory pathways + drugged analogs ──
                try:
                    _reg_paths = regulatory_pathway_map(g_diseases(pdata), patient_d, gi)
                    _analogs   = find_drugged_analogs(pdata, string_data, ot_data)
                except Exception:
                    _reg_paths, _analogs = {}, []
                st.session_state["reg_paths"] = _reg_paths
                st.session_state["analogs"]   = _analogs
                # ── NEW: compute experiment ROI ranking ──
                try:
                    _roi_data = compute_experiment_roi(scored, gi, g_ptype(pdata), gnomad_data, ot_data)
                except Exception:
                    _roi_data = []
                st.session_state["roi_data"] = _roi_data
                # ── Analysis trace: record what ran so users can audit ──
                from datetime import datetime as _dt
                trace = []
                trace.append(("UniProt API",   f"Fetched {gene} ({pdata.get('primaryAccession','?')}) · {pdata.get('sequence',{}).get('length','?')} aa · {len(g_diseases(pdata) or [])} associated diseases"))
                trace.append(("ClinVar NCBI",  f"Retrieved {len((cv or {}).get('variants',[]))} variants · {gi.get('n_pathogenic',0)} P/LP"))
                trace.append(("gnomAD v4",     f"pLI={gnomad_data.get('pLI','—')} · oe_lof_upper={gnomad_data.get('oe_lof_upper','—')} · mis_z={gnomad_data.get('mis_z','—')}"))
                _am_all = _am_flat(am_scores)
                trace.append(("AlphaMissense", f"Scored {len(am_scores or {})} positions, {len(_am_all)} substitutions (mean={sum(_am_all)/len(_am_all):.3f})" if _am_all else "No AlphaMissense data available"))
                trace.append(("STRING-DB",     f"{len(string_data or [])} interaction partners"))
                trace.append(("OpenTargets",   f"Tractability: {ot_data.get('tractability',{}).get('small_molecule','—') if ot_data else '—'} · {len((ot_data or {}).get('drugs',[]))} known drugs"))
                trace.append(("DGIdb / drug",  f"{len(drugs_data or [])} drug-gene interactions retrieved"))
                trace.append(("PubMed",        f"{len(abstracts or [])} recent abstracts ({sum(1 for a in (abstracts or []) if a.get('year',0) >= 2020)} from 2020+)"))
                trace.append(("ClinGen",       f"Gene-disease validity: {(clingen_data or {}).get('classification','—')}"))
                trace.append(("ML model",      f"LightGBM scored {len(scored or [])} variants · {sum(1 for s in (scored or []) if s.get('ml_rank') in ('CRITICAL','HIGH'))} high-priority"))
                trace.append(("Domain analysis", f"{len(domain_ctx.get('domains',[]))} Pfam-like domains analysed · gi_score={domain_ctx.get('gi_score','—')}"))
                trace.append(("ACMG auto",     f"{len((acmg_auto or {}).get('criteria_triggered',[]))} ACMG criteria triggered · {len(conflicts or [])} conflicts"))
                trace.append(("Drugged analogs", f"{len(_analogs or [])} drugged analogs found"))
                st.session_state["analysis_trace"] = {
                    "ran_at": _dt.now().isoformat(timespec="seconds"),
                    "gene": gene,
                    "uniprot": pdata.get('primaryAccession',''),
                    "steps": trace,
                }
                # Update GI score from domain analysis
                # gi_score is already a percentage (×100); density is a fraction (0–1).
                # Divide by 100 so display × 100 yields the correct percentage.
                if domain_ctx.get("gi_score") is not None and gi:
                    gi["density"] = min(1.0, domain_ctx["gi_score"] / 100.0)
                    gi["gi_class"] = domain_ctx.get("gi_class","")
                    st.session_state["gi"] = gi
            st.rerun()
        except Exception as e:
            err_msg = str(e)
            # Show a clear, styled error — especially for non-human proteins
            if "non-human" in err_msg.lower() or "homo sapiens" in err_msg.lower() or "reptile" in err_msg.lower() or "bird" in err_msg.lower() or "chicken" in err_msg.lower() or "not in humans" in err_msg.lower():
                st.markdown(
                    "<div style='background:#0a0300;border:2px solid #ff8c42;border-radius:12px;"
                    "padding:1.1rem 1.4rem;margin:.5rem 0;'>"
                    "<div style='color:#ff8c42;font-weight:800;font-size:1rem;margin-bottom:5px;'>"
                    " Non-human protein detected — Protellect is human-only</div>"
                    f"<div style='color:#8a6040;font-size:.88rem;line-height:1.6;'>{err_msg}</div>"
                    "<div style='margin-top:.7rem;color:#5a4030;font-size:.82rem;'>"
                    "<b style='color:#7a6040;'>Try these human proteins instead:</b> "
                    "TP53 · FLNC · BRCA1 · EGFR · ACM2 · ARRB2 · KRT5 (human keratin) · INS (human insulin)"
                    "</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='background:#0a0100;border:2px solid #ff2d55;border-radius:12px;"
                    "padding:1rem 1.4rem;margin:.5rem 0;'>"
                    "<div style='color:#ff2d55;font-weight:800;font-size:.95rem;margin-bottom:4px;'> Search error</div>"
                    f"<div style='color:#804050;font-size:.86rem;'>{err_msg}</div>"
                    "</div>",
                    unsafe_allow_html=True,
                )


# Domain routing handled above

# ─── Main variables ──────────────────────────────────────────────────
pdata=st.session_state.get("pdata") or {}; cv=st.session_state.get("cv") or {}
pdb=st.session_state.get("pdb",""); papers=(st.session_state.get("papers") or [])
scored=(st.session_state.get("scored") or []); gene=st.session_state.get("gene","")
assay=st.session_state.get("assay",""); uid=st.session_state.get("uid","")
cv = cv or {}; summary=cv.get("summary",{}); variants=cv.get("variants",[])
diseases=g_diseases(pdata) if pdata else []
# Enrich diseases with ClinVar conditions not in UniProt
_cv_disease_names = set(d["name"] for d in diseases)
for _cond, _cnt in (cv.get("summary",{}).get("top_conds",{}) or {}).items():
    if _cond and _cond not in _cv_disease_names and len(_cond) > 4:
        # Find pathogenic variants for this condition
        _path_vars = [v for v in variants if _cond in v.get("condition","") and v.get("score",0)>=3]
        if _path_vars:
            _sig = _path_vars[0].get("sig","")
            diseases.append({
                "name": _cond,
                "desc": f"{len(_path_vars)} ClinVar variant(s) — {_sig}. Source: ClinVar.",
                "note": _path_vars[0].get("variant_name","")[:80] if _path_vars else "",
                "inheritance": "Unknown",
                "mutation_type": _path_vars[0].get("variant_name","")[:40] if _path_vars else "Variant",
            })
        _cv_disease_names.add(_cond)
protein_length = pdata.get("sequence",{}).get("length") or len(pdata.get("sequence",{}).get("value","")) or 0
gi=st.session_state.get("gi") or compute_gi(cv,protein_length)

# ── Conflict flags + ACMG badges + ML probability (shown in verdict area) ─
_conflicts_hook = (st.session_state.get("conflicts") or [])
_acmg_hook      = (st.session_state.get("acmg_auto") or {})
_dom_ctx        = (st.session_state.get("domain_ctx") or {})
_ml_res         = (st.session_state.get("ml_result") or {})

# ─── Chemical Structure helpers ────────────────────────────────────────────────










# ════════════════════════════════════════════════════════════════════════════
#  MICROBIOME ANNOTATION ENGINE — The PI's specific request
#  Vague annotation → Specific EC-numbered pathway annotation using LLM+rules
# ════════════════════════════════════════════════════════════════════════════













# ─── Session state ──────────────────────────────────────────────────

























# ── Research domain registry ─────────────────────────────────────────────────




# ─── CSV-only triage panel ────────────────────────────────────────────
if st.session_state.get("csv_triage_active") and st.session_state.get("csv_df") is not None:
    df_t = st.session_state["csv_df"]; ct_t = st.session_state["csv_type"]
    st.markdown(
        f"<div style='background:#020617;border:2px solid #38bdf833;border-radius:14px;"
        f"padding:1.2rem 1.5rem;margin-bottom:1rem;'>"
        f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:.8rem;'>"
        f"<img src='{_logo_src}' style='width:32px;height:32px;object-fit:contain;'>"
        f"<div style='color:#38bdf8;font-weight:800;font-size:1.1rem;'>Wet-Lab Triage Results</div>"
        f"<span style='background:#38bdf822;color:#38bdf8;border:1px solid #38bdf833;padding:2px 10px;border-radius:10px;font-size:.8rem;'>{ct_t.replace('_',' ').title()}</span>"
        f"</div></div>",
        unsafe_allow_html=True,
    )
    c_m1, c_m2, c_m3 = st.columns(3)
    with c_m1: st.markdown(mc(f"{len(df_t):,}", "Rows", "#38bdf8"), unsafe_allow_html=True)
    with c_m2: st.markdown(mc(len(df_t.columns), "Columns", "#4a90d9"), unsafe_allow_html=True)
    with c_m3: st.markdown(mc(ct_t.replace("_"," ").title(), "Type detected", "#00c896"), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    # Pull protein context from session if available; CSV-only triage may run before
    # any protein search, in which case we pass empty values and let the analyser
    # produce CSV-only insights without protein cross-referencing.
    _csv_gene     = st.session_state.get("gene", "") or ""
    _csv_scored   = st.session_state.get("scored") or []
    _csv_variants = (st.session_state.get("cv") or {}).get("variants", []) or []
    _csv_am       = st.session_state.get("am") or {}
    _csv_pdata    = st.session_state.get("pdata") or {}
    _csv_plen     = (_csv_pdata.get("sequence") or {}).get("length", 1) or 1

    # ── CSV ↔ searched-protein overlap check ─────────────────────────────────
    # If the user has searched a protein and the CSV contains a gene-symbol column,
    # warn when the searched protein is NOT in the CSV — the data is the experiment,
    # the search is just a cue. We don't want users to assume the analysis is "about"
    # their searched protein when the CSV is actually about something else.
    if _csv_gene and ct_t in ("expression","clinical_variants","vcf_variants","proteomics","stats","cell_assay"):
        _csv_gene_col = next((c for c in df_t.columns if c.lower() in
                              ("gene","gene_symbol","symbol","gene(s)","genes","gene_name","gene_id","geneid")), None)
        if _csv_gene_col is not None:
            try:
                _csv_gene_set = set(df_t[_csv_gene_col].dropna().astype(str).str.upper())
                _searched_in_csv = _csv_gene.upper() in _csv_gene_set
                if not _searched_in_csv:
                    # Suggest a couple of candidates from the CSV itself
                    _sample = sorted(_csv_gene_set)[:6]
                    st.markdown(
                        f"<div style='background:rgba(255,140,66,.08);border:1px solid #ff8c4266;"
                        f"border-left:4px solid #ff8c42;border-radius:10px;padding:.8rem 1.1rem;margin-bottom:1rem;'>"
                        f"<div style='color:#ff8c42;font-weight:800;font-size:.85rem;margin-bottom:.3rem;'>"
                        f"⚠ Searched protein not in this CSV</div>"
                        f"<div style='color:var(--text2);font-size:.82rem;line-height:1.5;'>"
                        f"You searched <b>{_csv_gene}</b>, but it's not present in the uploaded CSV "
                        f"({len(_csv_gene_set):,} unique genes). The analysis below is driven by the <b>CSV's own contents</b>, "
                        f"not your search. To cross-reference a specific protein, search one of the genes in the CSV — "
                        f"e.g. <i>{', '.join(_sample)}</i>.</div></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div style='background:rgba(34,197,94,.06);border:1px solid #22c55e44;"
                        f"border-left:4px solid #22c55e;border-radius:10px;padding:.6rem 1rem;margin-bottom:1rem;'>"
                        f"<span style='color:#22c55e;font-weight:700;font-size:.82rem;'>✓ {_csv_gene} found in this CSV</span> "
                        f"<span style='color:var(--text3);font-size:.78rem;margin-left:8px;'>— cross-referencing below</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            except Exception: pass

    for t_t, b_t in analyse_csv_standalone(df_t, ct_t, active_goal,
                                           gene=_csv_gene, scored=_csv_scored,
                                           variants=_csv_variants, am_scores=_csv_am,
                                           protein_length=_csv_plen):
        st.markdown(f"<div class='card'><h4>{t_t}</h4><p>{b_t}</p></div>", unsafe_allow_html=True)
    # Volcano plot
    import numpy as np
    fc_t = next((c for c in df_t.columns if any(k in c.lower() for k in ["fold","logfc","log2fc"])), None)
    p_t  = next((c for c in df_t.columns if any(k in c.lower() for k in ["pvalue","p_val","padj","fdr"])), None)
    if fc_t and p_t and df_t[fc_t].dtype in [float,'float64'] and df_t[p_t].dtype in [float,'float64']:
        neg_log_p = (-np.log10(df_t[p_t].clip(1e-300))).clip(0, 50)
        c_v = ["#ff2d55" if (f>1 and p<0.05) else "#1e4060" if (f<-1 and p<0.05) else "#2a4060"
               for f,p in zip(df_t[fc_t], df_t[p_t])]
        fig_vt = go.Figure(go.Scatter(x=df_t[fc_t], y=neg_log_p, mode="markers",
            marker=dict(color=c_v, size=4, opacity=.75),
            hovertemplate="FC: %{x:.2f}<br>-log10(p): %{y:.2f}<extra></extra>"))
        fig_vt.add_vline(x=1, line_color="rgba(255,45,85,0.27)", line_dash="dot")
        fig_vt.add_vline(x=-1, line_color="rgba(58,90,122,0.27)", line_dash="dot")
        fig_vt.add_hline(y=-np.log10(0.05), line_color="rgba(255,214,10,0.27)", line_dash="dot")
        fig_vt.update_layout(paper_bgcolor="#020617", plot_bgcolor="#020617", font_color="#1e4060",
            xaxis=dict(title="Fold change (log₂) — increased vs decreased expression", gridcolor="#050d24"),
            yaxis=dict(title="-log₁₀(p-value) — confidence in result", gridcolor="#050d24"),
            height=380, margin=dict(t=10, b=40, l=60, r=10),
            title=dict(text="Volcano plot —  significantly up ·  significantly down", font_color="#2a5070", font_size=12))
        st.plotly_chart(fig_vt, use_container_width=True, config={"displayModeBar":False})
    with st.expander(" Preview CSV data"):
        st.dataframe(df_t.head(20), use_container_width=True)
    if st.button("✕ Close triage panel", key="close_triage"):
        st.session_state["csv_triage_active"] = False
        st.rerun()
    st.markdown("<hr style='border-color:#050d24;margin:1rem 0;'>", unsafe_allow_html=True)

# ─── Disease proteins panel ─────────────────────────────────────────
if st.session_state["disease_proteins"]:
    dp_list=st.session_state["disease_proteins"]; dis_name=st.session_state["disease_search"]
    with st.expander(f" Disease → Proteins: '{dis_name}' — {len(dp_list)} genes found (ClinVar)", expanded=True):
        st.markdown(f"<div style='color:#1e4060;font-size:.96rem;margin-bottom:.6rem;'>All genes with <b>pathogenic / likely-pathogenic</b> (disease-causing) germline variants for <b>{dis_name}</b>, ranked by number of confirmed variants. Source: {src_link('ClinVar',f'https://www.ncbi.nlm.nih.gov/clinvar/?term={dis_name}[disease]')}</div>", unsafe_allow_html=True)
        for dp_idx, dp_row in enumerate(dp_list):
            gn=dp_row.get("gene","?"); np2=dp_row.get("n_pathogenic",0)
            conds=dp_row.get("conditions",[])
            cond_str="; ".join(conds)[:80]
            cv_url=dp_row.get("clinvar_url","")
            bar_w=min(100,int(np2/max(dp_list[0].get("n_pathogenic",1),1)*100))
            # Clickable row — launches full analysis
            dp_col_a, dp_col_b = st.columns([5,1], gap="small")
            with dp_col_a:
                with st.expander(
                    f"{np2} variants  ·  {gn}  ·  {cond_str[:50]}",
                    expanded=False,
                ):
                    ec1, ec2 = st.columns([3,2])
                    with ec1:
                        st.markdown(
                            f"<div style='margin-bottom:.5rem;'>"
                            f"<div style='color:#38bdf8;font-weight:800;font-size:1.1rem;'>{gn}</div>"
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
                            # Pre-fill the search box
                            st.session_state["protein_query_val"] = gn
                            st.session_state["_trigger_search"] = gn
                            st.rerun()
            with dp_col_b:
                if st.button(f"Analyse →", key=f"dp_btn_{dp_idx}_{gn}", use_container_width=True):
                    st.session_state["last"] = ""
                    st.session_state["_trigger_search"] = gn
                    st.rerun()

# [_trigger_search handler moved above routing]


# ── ONE analysis per run; every tab reads it, so they always agree ────────────────────────────────────────────────
_pdata_a = st.session_state.get("pdata") or {}
_gene_a = st.session_state.get("gene", "")
try:
    _gf = g_gpcr_full(_pdata_a, _gene_a) if _pdata_a else {}
except Exception:
    _gf = {}
try:
    _dis_a = g_diseases(_pdata_a) if _pdata_a else None
except Exception:
    _dis_a = None
try:
    _ana = _build_analysis(st.session_state, diseases=_dis_a, is_gpcr=(_gf.get("is_gpcr") if _gf else None),
                           gpcr_class=(_gf.get("receptor_class", "") if _gf else ""), couplings=(_gf.get("couplings") if _gf else None))
except Exception as _ana_e:  # noqa: BLE001
    _ana = None
    st.error(f"The analysis could not be built: {type(_ana_e).__name__}: {_ana_e}")
if _ana is not None:
    with _banner_slot:
        _safe(_render_priority_banner, _ana.priorities)
_helpers = {
    "render_csv": (lambda: render_csv_triage_tab(*csv_context())),
    "render_csv_experiments": (lambda: render_csv_experiments_tab(*csv_context())),
    "landscape": (lambda: variant_landscape_fig((st.session_state.get("cv") or {}).get("variants", []),
                                                ((st.session_state.get("pdata") or {}).get("sequence") or {}).get("length", 1),
                                                st.session_state.get("scored") or [])),
}
try:
    _ncbi = fetch_ncbi_gene(_gene_a) if _gene_a else {}
except Exception:
    _ncbi = {}


def _need_ana(fn, *args):
    if _ana is None:
        st.warning("Nothing to show: the analysis could not be built (see the error above).")
    else:
        _safe(fn, _ana, *args)

with tab0:
    _need_ana(_render_overview)

with tab1:
    _need_ana(_render_triage, _helpers)

with tab2:
    _need_ana(_render_casestudy, _ncbi)



with tab4:
    _need_ana(_render_experiments, _helpers)

pass  # removed tab block




pass  # removed tab block



with tab7:
    _need_ana(_render_genetics)

# ─── Footer ────────────────────────────────────────────────────────
st.markdown(
    f"<hr style='border-color:#050d24;margin:.8rem 0;'>"
    f"<div style='text-align:center;margin-bottom:6px;'>"
    f"<img src='data:image/png;base64,{LOGO_B64}' style='width:22px;height:22px;object-fit:contain;opacity:.4;vertical-align:middle;margin-right:6px;'>"
    f"<span style='color:#0a1e30;font-size:.8rem;font-weight:600;'>Protellect</span></div>"
    f"<p style='text-align:center;color:#060f1c;font-size:.75rem;'>"
    f"Protellect · Not a substitute for expert clinical judgment.</p>",
    unsafe_allow_html=True,
)

pass  # removed tab block

with tab9:
    _need_ana(_render_hotspots)
