"""
auth.py — Authentication, quota management, user accounts
Free: 5 searches/month | Pro: $49/mo, 200 searches | Enterprise: $299/mo, unlimited
Dev bypass: protellect@gmail.com / dev@protellect
"""
import hashlib
import streamlit as st

# ── Account database ───────────────────────────────────────
def _h(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

ACCOUNTS = {
    "protellect@gmail.com": {
        "password_hash": _h("dev@protellect"),
        "tier": "enterprise",
        "name": "Protellect Dev",
        "quota": 999999,
        "dev": True,
    },
    "demo@protellect.io": {
        "password_hash": _h("demo2025"),
        "tier": "free",
        "name": "Demo User",
        "quota": 5,
        "dev": False,
    },
}

TIER_CONFIG = {
    "free":       {"label": "Free",       "quota": 5,      "color": "#64748b", "stripe": None},
    "pro":        {"label": "Pro",        "quota": 200,    "color": "#00e5ff", "stripe": "https://buy.stripe.com/protellect_pro"},
    "enterprise": {"label": "Enterprise", "quota": 999999, "color": "#f97316", "stripe": None},
}

# ── Session helpers ────────────────────────────────────────

def is_authenticated() -> bool:
    return st.session_state.get("auth_user") is not None

def current_user() -> dict:
    return st.session_state.get("auth_user", {})

def get_searches_used() -> int:
    return st.session_state.get("searches_used", 0)

def get_quota() -> int:
    u = current_user()
    return u.get("quota", 5)

def can_search() -> bool:
    u = current_user()
    if u.get("dev") or u.get("tier") == "enterprise":
        return True
    return get_searches_used() < get_quota()

def record_search():
    if not current_user().get("dev"):
        st.session_state.searches_used = get_searches_used() + 1

def logout():
    for k in ["auth_user","searches_used","workspace","search_history","current_protein"]:
        if k in st.session_state:
            del st.session_state[k]

# ── Login UI ───────────────────────────────────────────────

def render_login():
    """Full-screen login / signup page."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    *{font-family:'Inter',sans-serif!important}
    #MainMenu,footer,header{visibility:hidden}
    .block-container{padding:0!important;max-width:100%!important}
    .stApp{background:linear-gradient(135deg,#010306 0%,#070d1a 50%,#010918 100%)}
    </style>""", unsafe_allow_html=True)

    # Centre the login card
    _, card_col, _ = st.columns([1, 1.2, 1])
    with card_col:
        st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)

        # Logo
        st.markdown("""
        <div style="text-align:center;margin-bottom:32px">
          <div style="font-size:3rem;margin-bottom:8px">🔬</div>
          <div style="font-size:2.2rem;font-weight:800;background:linear-gradient(90deg,#00e5ff,#7c3aed);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-1px">
            Protellect
          </div>
          <div style="color:#4a7090;font-size:.95rem;margin-top:4px;letter-spacing:.05em">
            GENETICS-FIRST PROTEIN INTELLIGENCE
          </div>
        </div>""", unsafe_allow_html=True)

        # Login card
        st.markdown("""
        <div style="background:rgba(7,13,26,0.9);border:1px solid rgba(0,229,255,0.15);
             border-radius:16px;padding:36px;backdrop-filter:blur(10px)">
        """, unsafe_allow_html=True)

        tab_login, tab_demo = st.tabs(["Sign In", "Try Demo"])

        with tab_login:
            email = st.text_input("Email", placeholder="you@example.com", key="login_email")
            password = st.text_input("Password", type="password", placeholder="Password", key="login_pw")
            if st.button("Sign In →", type="primary", use_container_width=True, key="signin_btn"):
                _do_login(email, password)

        with tab_demo:
            st.markdown("""<div style="color:#4a7090;font-size:.88rem;margin-bottom:16px">
            Try Protellect with 5 free searches. No credit card required.</div>""", unsafe_allow_html=True)
            demo_email = st.text_input("Your email", placeholder="you@lab.edu", key="demo_email")
            demo_name  = st.text_input("Your name", placeholder="Dr. Smith", key="demo_name")
            goal = st.selectbox("Research goal", [
                "Drug target identification",
                "Disease mechanism understanding",
                "Protein function characterisation",
                "Variant pathogenicity assessment",
                "Therapeutic hypothesis generation",
                "Microbiome pathway annotation",
            ], key="demo_goal")
            if st.button("Start Free Trial →", type="primary", use_container_width=True, key="demo_btn"):
                if demo_email and demo_name:
                    st.session_state.auth_user = {
                        "email": demo_email,
                        "name": demo_name,
                        "tier": "free",
                        "quota": 5,
                        "dev": False,
                        "research_goal": goal,
                    }
                    st.session_state.searches_used = 0
                    st.session_state.workspace = []
                    st.rerun()
                else:
                    st.warning("Please enter your email and name.")

        st.markdown("</div>", unsafe_allow_html=True)

        # Pricing pills
        st.markdown("""
        <div style="display:flex;gap:12px;margin-top:24px;justify-content:center">
          <div style="background:rgba(7,13,26,0.8);border:1px solid #1e3a5f;border-radius:10px;padding:14px 20px;flex:1;text-align:center">
            <div style="color:#64748b;font-size:.78rem;font-weight:600;letter-spacing:.08em">FREE</div>
            <div style="color:#d0e8ff;font-size:1.3rem;font-weight:700;margin:4px 0">$0</div>
            <div style="color:#4a7090;font-size:.78rem">5 searches/month</div>
          </div>
          <div style="background:rgba(0,229,255,0.06);border:1px solid rgba(0,229,255,0.3);border-radius:10px;padding:14px 20px;flex:1;text-align:center">
            <div style="color:#00e5ff;font-size:.78rem;font-weight:600;letter-spacing:.08em">PRO</div>
            <div style="color:#d0e8ff;font-size:1.3rem;font-weight:700;margin:4px 0">$49<span style="font-size:.8rem;color:#4a7090">/mo</span></div>
            <div style="color:#4a7090;font-size:.78rem">200 searches</div>
          </div>
          <div style="background:rgba(249,115,22,0.06);border:1px solid rgba(249,115,22,0.3);border-radius:10px;padding:14px 20px;flex:1;text-align:center">
            <div style="color:#f97316;font-size:.78rem;font-weight:600;letter-spacing:.08em">ENTERPRISE</div>
            <div style="color:#d0e8ff;font-size:1.3rem;font-weight:700;margin:4px 0">$299<span style="font-size:.8rem;color:#4a7090">/mo</span></div>
            <div style="color:#4a7090;font-size:.78rem">Unlimited + API</div>
          </div>
        </div>""", unsafe_allow_html=True)

        # Quote
        st.markdown("""
        <div style="text-align:center;margin-top:28px;color:#2a4060;font-size:.82rem;font-style:italic">
        "The only platform that tells you which proteins to abandon<br>before you spend the money."
        </div>""", unsafe_allow_html=True)


def _do_login(email: str, password: str):
    email = email.strip().lower()
    account = ACCOUNTS.get(email)
    if account and account["password_hash"] == _h(password):
        st.session_state.auth_user = {
            "email": email,
            "name": account["name"],
            "tier": account["tier"],
            "quota": account["quota"],
            "dev": account.get("dev", False),
        }
        st.session_state.searches_used = 0
        st.session_state.workspace = []
        st.rerun()
    else:
        st.error("Invalid email or password.")


def render_quota_banner():
    """Small quota indicator shown in main app."""
    u = current_user()
    used = get_searches_used()
    quota = get_quota()
    tier = u.get("tier","free")
    tc = TIER_CONFIG[tier]

    if u.get("dev"):
        label = "Dev Account — Unlimited"
        color = "#f97316"
    elif tier == "enterprise":
        label = "Enterprise — Unlimited"
        color = "#f97316"
    else:
        remaining = quota - used
        label = f"{remaining} searches remaining ({tc['label']})"
        color = tc["color"]
        if remaining <= 0:
            label = "Quota exhausted — Upgrade to continue"
            color = "#ef4444"

    st.markdown(f"""
    <div style="background:rgba(0,229,255,0.05);border:1px solid rgba(0,229,255,0.1);
         border-radius:8px;padding:6px 14px;display:inline-block;font-size:.78rem;color:{color};margin-bottom:8px">
    {label}
    </div>""", unsafe_allow_html=True)
