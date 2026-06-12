from __future__ import annotations
import hashlib, json, time
from datetime import datetime
import streamlit as st
from modules.config import PLAN_LIMITS, STRIPE_LINKS

def _hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def _get_credentials():
    if "_credentials" not in st.session_state:
        st.session_state["_credentials"] = {
            "demo@protellect.com": {"name":"Demo User", "pw":_hash("protellect2024"), "plan":"free", "searches_left":5},
            "pro@protellect.com": {"name":"Pro User", "pw":_hash("pro2024"), "plan":"pro", "searches_left":999},
            "enterprise@protellect.com": {"name":"Enterprise", "pw":_hash("ent2024"), "plan":"enterprise","searches_left":9999},
        }
    return st.session_state["_credentials"]

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
            email = st.text_input("Email", placeholder="you@lab.com", key="li_email")
            password = st.text_input("Password", type="password", key="li_pw")
            if st.button("Sign in", use_container_width=True, type="primary", key="li_btn"):
                user = _get_credentials().get(email)
                if user and user["pw"] == _hash(password):
                    st.session_state["auth_user"] = email
                    st.session_state["auth_name"] = user["name"]
                    st.session_state["auth_plan"] = user["plan"]
                    st.session_state["auth_searches_left"] = user["searches_left"]
                    st.success(f"Welcome back, {user['name']}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Use demo@protellect.com / protellect2024 to try.")
            st.markdown(
                "<div style='color:#2a5060;font-size:.8rem;margin-top:.5rem;'>Demo: demo@protellect.com / protellect2024</div>",
                unsafe_allow_html=True,
            )

        with tab_up:
            st.markdown("<div style='color:#5a8090;font-size:.86rem;margin-bottom:.6rem;'>Create an account to get 5 free protein analyses. Upgrade anytime.</div>", unsafe_allow_html=True)
            new_name = st.text_input("Full name", key="reg_name")
            new_email = st.text_input("Email", key="reg_email")
            new_pw = st.text_input("Password", type="password", key="reg_pw")
            new_pw2 = st.text_input("Confirm password", type="password", key="reg_pw2")
            if st.button("Create free account", use_container_width=True, type="primary", key="reg_btn"):
                if not new_name or not new_email or not new_pw:
                    st.error("All fields required.")
                elif new_pw != new_pw2:
                    st.error("Passwords do not match.")
                elif "@" not in new_email:
                    st.error("Enter a valid email address.")
                else:
                    _get_credentials()[new_email] = {
                        "name": new_name, "pw": _hash(new_pw),
                        "plan": "free", "searches_left": 5,
                    }
                    st.session_state["auth_user"] = new_email
                    st.session_state["auth_name"] = new_name
                    st.session_state["auth_plan"] = "free"
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
    existing = [i for i,w in enumerate(ws) if w.get("gene") == gene]
    if existing:
        ws.pop(existing[0])
    ws.insert(0, {
        "gene": gene,
        "uid": pdata.get("primaryAccession",""),
        "name": pdata.get("protein",{}).get("recommendedName",{}).get("fullName",{}).get("value","") or gene,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "verdict": gi.get("pursue",""),
        "n_path": gi.get("n_pathogenic",0),
        "n_total": gi.get("n_total",0),
        "density": round(gi.get("density",0)*100,2),
        "diseases": [d["name"] for d in diseases[:4]],
        "scored_top": [(v.get("variant_name","")[:30], v.get("ml_rank","")) for v in scored[:5]],
    })
    st.session_state["workspace"] = ws[:limit]

def check_search_limit():
    """Returns True if user can search, False if limit exceeded."""
    plan = st.session_state.get("auth_plan","free")
    if plan in ("pro","enterprise"):
        return True
    left = st.session_state.get("auth_searches_left", 0)
    return left > 0

def decrement_search():
    """Use one search credit."""
    plan = st.session_state.get("auth_plan","free")
    if plan == "free":
        st.session_state["auth_searches_left"] = max(0, st.session_state.get("auth_searches_left",0) - 1)
