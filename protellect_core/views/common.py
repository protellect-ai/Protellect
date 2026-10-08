"""Shared Streamlit rendering: claims with proof and ML validation, the data audit, secrets, cached engine."""
from __future__ import annotations

import os
from typing import Iterable, List, Optional

import streamlit as st

from ..evidence import Claim, truth_gate
from ..validation import validate

COLOR = {"holds up": "green", "weakened": "orange", "contested": "red", "unchecked": "gray"}
KIND = {"data": "", "rule": " · rule applied to data", "inference": " · inference"}
LEVEL_COLOR = {"PRIORITIZE": "#22c55e", "INVESTIGATE": "#38bdf8", "DEPRIORITIZE": "#94a3b8", "DATA GAP": "#f59e0b", "INFO": "#64748b"}


def secret(name: str):
    try:
        v = st.secrets.get(name)
        if v:
            return v
    except Exception:
        pass
    return os.environ.get(name)


@st.cache_resource(show_spinner=False)
def _engine_cached(registry_csv: str = "", outcomes_json: str = ""):
    import json
    from ..engine import HypothesisEngine
    from ..engine.cases import cases_from_outcomes, load_cases
    from ..engine.registry import load_registry_text
    base = load_cases()
    extra, _ = cases_from_outcomes(json.loads(outcomes_json) if outcomes_json else [], [c.id for c in base])
    return HypothesisEngine(cases=base + extra, registry=load_registry_text(registry_csv) if registry_csv else None)


def get_engine():
    """The engine. The model retrains instantly whenever outcomes are recorded this session (they are part of the cache key)."""
    return _engine_cached(st.session_state.get("hyp_registry_csv", ""), st.session_state.get("outcomes_json", ""))


def claim_card(c: Claim, key: str, bundle=None, how_label: str = "How to go about it") -> None:
    chip = f":{COLOR.get(c.verdict, 'gray')}[ML validation: {c.verdict}]"
    st.markdown(f"**{c.text}**  \n{chip}{KIND.get(c.kind, '')}")
    flag = c.tags.get("context_flag")
    if flag:
        st.caption(f"Tailored to your microenvironment: {flag}")
    if c.how:
        with st.expander(f"{how_label} ({len(c.how)} step{'s' if len(c.how) != 1 else ''})"):
            for i, h in enumerate(c.how, 1):
                st.markdown(f"{i}. {h}")
    with st.popover(f"Proof and ML validation ({len(c.proofs)} source{'s' if len(c.proofs) != 1 else ''})", key=f"pf_{key}") if _popover_has_key() else st.popover(f"Proof and ML validation ({len(c.proofs)})"):
        for p in c.proofs:
            line = f"- **{p.source}**: {p.detail}"
            st.markdown(line + (f" ([link]({p.url}))" if p.url.startswith("http") else ""))
        if c.basis:
            st.markdown(f"**Basis ({c.kind}):** {c.basis}")
        if c.counters:
            st.markdown("**Counter-arguments from ML validation**")
            for x in c.counters:
                st.markdown(f"- [{x['severity']}] {x['text']}")
        else:
            st.markdown("No counter-arguments were raised.")


def _popover_has_key() -> bool:
    import inspect
    try:
        return "key" in inspect.signature(st.popover).parameters
    except (TypeError, ValueError):
        return False


def render_claims(claims: Iterable[Claim], b, prefix: str, limit: Optional[int] = None, empty: str = "Nothing with proof to show here.", how_label: str = "How to go about it") -> List[Claim]:
    """Validate every claim, drop any without proof (counting them), and show the rest."""
    claims = list(claims)
    for c in claims:
        if c.verdict == "unchecked":
            validate(c, b)
    shown, withheld = truth_gate(claims)
    if not shown:
        st.info(empty)
    for i, c in enumerate(shown[:limit] if limit else shown):
        claim_card(c, f"{prefix}_{i}", b, how_label)
        st.divider()
    if limit and len(shown) > limit:
        st.caption(f"{len(shown) - limit} more not shown.")
    if withheld:
        st.caption(f"{len(withheld)} statement(s) were withheld because they could not be backed by a source.")
    return shown


def data_audit(b) -> None:
    n = st.session_state.get("_audit_n", 0) + 1
    st.session_state["_audit_n"] = n
    try:
        import protellect_data as _pd
        errs = dict(getattr(_pd, "FETCH_ERRORS", {}))
    except Exception:
        _pd, errs = None, {}
    errs.update(b.source_errors)
    with st.expander("Data audit: what each source returned for this protein"):
        st.caption("Empty rows usually mean a failed fetch, not a negative finding. Sections that depend on them say so instead of guessing.")
        st.dataframe([{"Source": a.name, "Records": a.n, "Note": a.note} for a in b.audit], hide_index=True)
        if errs:
            st.warning("Fetch problems since the app started:")
            st.dataframe([{"Source": k, "Last error": v} for k, v in errs.items()], hide_index=True)
        if _pd is not None and hasattr(_pd, "source_diagnostics"):
            if st.button("Check data sources now", key=f"diag_{n}"):
                with st.spinner("Calling each source from the server..."):
                    st.session_state["_diag_rows"] = _pd.source_diagnostics(b.gene or "TP53", b.uid or "P04637")
            if st.session_state.get("_diag_rows"):
                st.dataframe([{"Source": r["source"], "OK": "yes" if r["ok"] else "NO", "HTTP": r["http"], "ms": r["ms"], "Detail": r["detail"]} for r in st.session_state["_diag_rows"]], hide_index=True)
