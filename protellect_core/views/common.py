"""Shared Streamlit rendering: claims with proof and ML validation, the data audit, secrets, cached engine."""
from __future__ import annotations

import os
from typing import Iterable, List, Optional

import streamlit as st

from ..evidence import Claim, truth_gate
from ..validation import validate
from .tables import install as _install_tables

_install_tables()

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


IUPHAR_URL = "https://www.guidetopharmacology.org/DATA/targets_and_families.csv"


@st.cache_data(ttl=7 * 86400, show_spinner=False)
def _fetch_iuphar() -> str:
    """The full receptor list from the IUPHAR/BPS Guide to PHARMACOLOGY, cached for a week. Raises on failure so a failure is never cached."""
    import requests
    from ..engine.registry import convert_iuphar_bytes
    r = requests.get(IUPHAR_URL, timeout=45, headers={"User-Agent": "Protellect/2.0 (research tool)"})
    r.raise_for_status()
    return convert_iuphar_bytes(r.content)


def registry_text():
    """(csv text, label). The user's or the example's registry wins; else the full IUPHAR list; else the small built-in seed, with the reason."""
    ss = st.session_state
    if ss.get("hyp_registry_csv"):
        return ss["hyp_registry_csv"], "uploaded or example registry"
    try:
        txt = _fetch_iuphar()
        ss.pop("_registry_error", None)
        return txt, "IUPHAR/BPS Guide to PHARMACOLOGY (loaded automatically)"
    except Exception as e:  # noqa: BLE001
        ss["_registry_error"] = f"{type(e).__name__}: {e}"[:200]
        return "", "built-in 14-receptor seed (the full list could not be loaded)"


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
    txt, label = registry_text()
    st.session_state["_registry_label"] = label
    return _engine_cached(txt, st.session_state.get("outcomes_json", ""))


@st.cache_data(show_spinner=False, max_entries=8)
def pockets_cached(pdb_text: str, segs_key: str, segs: tuple):
    """Candidate pockets for a structure; segs is ((name, kind, start, end), ...) so the cache key is hashable."""
    try:
        from ..pockets import find_pockets, annotate
        pk = find_pockets(pdb_text)
        class _S:
            def __init__(self, n, k, a, b): self.name, self.kind, self.start, self.end = n, k, a, b
        return annotate(pk, [_S(*x) for x in segs], pdb_text)
    except Exception:
        return []


def get_pockets(b):
    from ..topology import topology as _topo
    if not getattr(b, "pdb", None):
        return []
    segs = _topo(b) or []
    key = tuple((s.name, s.kind, s.start, s.end) for s in segs)
    return pockets_cached(b.pdb, str(hash(key)), key)


def focus_picker(a) -> None:
    """Choose which protein from the experiment to show details for. The list itself is always shown; details follow this one protein."""
    if not a.focus_options:
        return
    opts = ["(none)"] + list(a.focus_options)
    cur = st.session_state.get("focus_gene")
    if cur not in a.focus_options:
        st.session_state["focus_gene"] = "(none)"
    st.selectbox("Show details for", opts, key="focus_gene",
                 help="Details (what your data says, what it might mean, the experiments to run) are shown for one protein at a time. Searching a protein in the sidebar selects it here.")


def experiment_protein_list(a) -> None:
    """Just the proteins found in the uploaded experiment, with the signal each one shows. No per-protein analysis."""
    if a.summary is None or not a.summary.n_orphan:
        return
    from ..engine.report import results_table
    t = results_table(a.summary)[["Receptor", "Your signal"]].rename(columns={"Receptor": "Protein"})
    st.dataframe(t, hide_index=True)


def svg(markup: str) -> None:
    """Inline SVG in the page (no iframe, so the page keeps scrolling normally over it)."""
    if markup:
        st.markdown(markup, unsafe_allow_html=True)


_RULE_NOTE = "This follows from a rule applied to data"


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
    ak = c.tags.get("assay")
    if ak:
        from ..assays import render_assay
        render_assay(st, ak)
    with st.popover(f"Proof and ML validation ({len(c.proofs)} source{'s' if len(c.proofs) != 1 else ''})", key=f"pf_{key}") if _popover_has_key() else st.popover(f"Proof and ML validation ({len(c.proofs)})"):
        for p in c.proofs:
            line = f"- **{p.source}**: {p.detail}"
            st.markdown(line + (f" ([link]({p.url}))" if p.url.startswith("http") else ""))
        if c.basis:
            st.markdown(f"**Basis ({c.kind}):** {c.basis}")
        if c.counters:
            st.markdown("**Counter-arguments from ML validation**")
            shown_c = [x for x in c.counters if not x["text"].startswith(_RULE_NOTE)]
            for x in shown_c:
                st.markdown(f"- [{x['severity']}] {x['text']}")
            if not shown_c:
                st.markdown("No counter-arguments were raised.")
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
    if any(c.kind == "rule" for c in shown):
        st.caption("Statements marked 'rule' follow from a rule applied to data and were not measured directly for this protein; each one names its basis in the proof box.")
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
        se = st.session_state.get("_step_errors") or {}
        if se:
            st.warning("Analysis steps that failed on this protein (the rest of the analysis still ran):")
            st.dataframe([{"Step": k, "Error": v} for k, v in se.items()], hide_index=True)
        if errs:
            st.warning("Fetch problems since the app started:")
            st.dataframe([{"Source": k, "Last error": v} for k, v in errs.items()], hide_index=True)
        if _pd is not None and hasattr(_pd, "source_diagnostics"):
            if st.button("Check data sources now", key=f"diag_{n}"):
                with st.spinner("Calling each source from the server..."):
                    st.session_state["_diag_rows"] = _pd.source_diagnostics(b.gene or "TP53", b.uid or "P04637")
            if st.session_state.get("_diag_rows"):
                st.dataframe([{"Source": r["source"], "OK": "yes" if r["ok"] else "NO", "HTTP": r["http"], "ms": r["ms"], "Detail": r["detail"]} for r in st.session_state["_diag_rows"]], hide_index=True)
