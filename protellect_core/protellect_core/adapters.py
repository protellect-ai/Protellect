"""Raw session data -> typed, defensively parsed records, plus an audit of what was (and was not) found.

This is the ONLY module that knows the raw shapes of what protellect_data returns. Every view reads Bundle, so if a
shape assumption is wrong it is fixed here, and the audit table shows the mismatch instead of the app crashing or,
worse, silently showing nothing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

STAR_RULES = [("practice guideline", 4), ("reviewed by expert panel", 3), ("multiple submitters, no conflicts", 2),
              ("criteria provided, single submitter", 1), ("conflicting", 1), ("no assertion", 0), ("no classification", 0)]
LOF_TYPES = {"nonsense", "frameshift", "splice"}
PLP = ("pathogenic", "likely pathogenic")


def stars_from_review(review: str) -> int:
    r = (review or "").lower()
    for key, n in STAR_RULES:
        if key in r:
            return n
    return 0


def norm_sig(sig: str, score=None) -> str:
    s = (sig or "").lower()
    if "conflict" in s:
        return "conflicting"
    has_lp, has_p = "likely pathogenic" in s, "pathogenic" in s
    if has_lp and "pathogenic" in s.replace("likely pathogenic", ""):
        return "pathogenic"
    if has_lp:
        return "likely pathogenic"
    if has_p:
        return "pathogenic"
    if "uncertain" in s or "vus" in s:
        return "uncertain"
    if "likely benign" in s and "benign" in s.replace("likely benign", ""):
        return "benign"
    if "likely benign" in s:
        return "likely benign"
    if "benign" in s:
        return "benign"
    if isinstance(score, (int, float)):            # the app's ClinVar score: >=5 P, 4 LP, 2 VUS, <=0 benign
        return {5: "pathogenic", 4: "likely pathogenic", 2: "uncertain"}.get(int(score), "benign" if score <= 0 else "other")
    return "other"


def parse_position(v: Mapping) -> Optional[int]:
    for k in ("start", "position", "pos"):
        try:
            if v.get(k) not in (None, ""):
                return int(float(v[k]))
        except (TypeError, ValueError):
            pass
    for k in ("title", "variant_name", "name"):
        m = re.search(r"p\.\(?[A-Za-z]{1,3}(\d+)", str(v.get(k, ""))) or re.search(r"\b[A-Z](\d+)[A-Z*]\b", str(v.get(k, "")))
        if m:
            return int(m.group(1))
    return None


def parse_consequence(v: Mapping) -> str:
    c = str(v.get("consequence") or v.get("mutation_type") or "").lower()
    t = " ".join(str(v.get(k, "")) for k in ("title", "variant_name", "name")).lower()
    blob = c + " " + t
    if "nonsense" in blob or "ter)" in blob or re.search(r"p\.\(?\w+\d+(ter|\*)", blob) or "stop_gained" in blob:
        return "nonsense"
    if "frameshift" in blob or "fs" in re.findall(r"[a-z]+", t) or re.search(r"fs\*?\d*\)?", t):
        return "frameshift"
    if "splice" in blob or re.search(r"c\.\d+[+-][12]\b", t):
        return "splice"
    if "synonymous" in blob or re.search(r"p\.\(?\w+\d+=\)?", t):
        return "synonymous"
    if re.search(r"p\.\(?\w+\d+\w+\)?", t) or "missense" in blob:
        return "missense"
    if "del" in blob or "dup" in blob or "ins" in blob:
        return "inframe indel"
    return "other"


@dataclass
class Variant:
    name: str
    pos: Optional[int]
    significance: str
    stars: int
    review: str
    condition: str
    consequence: str
    url: str
    ml_rank: str = ""
    ml_score: Optional[float] = None
    am_score: Optional[float] = None
    am_class: str = ""
    somatic: bool = False

    @property
    def is_plp(self) -> bool:
        return self.significance in PLP


@dataclass
class Disease:
    name: str
    inheritance: str = ""
    omim: str = ""
    desc: str = ""
    source: str = "UniProt"


@dataclass
class Partner:
    name: str
    score: float
    url: str = ""


@dataclass
class Drug:
    name: str
    kind: str = ""
    phase: str = ""
    mechanism: str = ""
    indication: str = ""
    url: str = ""
    source: str = ""


@dataclass
class Hotspot:
    start: int
    end: int
    count: int
    fold: float


@dataclass
class DatasetStatus:
    name: str
    n: int
    note: str = ""


@dataclass
class Bundle:
    gene: str = ""
    uid: str = ""
    name: str = ""
    length: int = 0
    is_gpcr: bool = False
    gpcr_class: str = ""
    variants: List[Variant] = field(default_factory=list)
    diseases: List[Disease] = field(default_factory=list)
    partners: List[Partner] = field(default_factory=list)
    drugs: List[Drug] = field(default_factory=list)
    n_known_drugs: int = 0
    trials: List[dict] = field(default_factory=list)
    hotspots: List[Hotspot] = field(default_factory=list)
    constraint: Dict[str, Optional[float]] = field(default_factory=dict)
    tractability: Dict[str, bool] = field(default_factory=dict)
    clingen: str = ""
    am: Dict[int, Dict[str, dict]] = field(default_factory=dict)
    tissue_text: str = ""
    subcellular: List[str] = field(default_factory=list)
    domains: List[dict] = field(default_factory=list)
    pdb: str = ""
    sites: List[dict] = field(default_factory=list)
    sequence: str = ""
    aliases: List[str] = field(default_factory=list)
    query: str = ""
    papers: List[dict] = field(default_factory=list)
    audit: List[DatasetStatus] = field(default_factory=list)
    source_errors: Dict[str, str] = field(default_factory=dict)

    @property
    def plp(self) -> List[Variant]:
        return [v for v in self.variants if v.is_plp and not v.somatic]

    @property
    def loaded(self) -> bool:
        return bool(self.gene)

    def domain_at(self, pos: Optional[int]) -> str:
        if pos is None:
            return ""
        best = ""
        for d in self.domains:
            if d["start"] <= pos <= d["end"] and (not best or (d["end"] - d["start"]) < best[1]):
                best = (d["desc"] or d["type"], d["end"] - d["start"])
        return best[0] if best else ""


def _as_list(x) -> list:
    return list(x) if isinstance(x, (list, tuple)) else []


def _num(x) -> Optional[float]:
    try:
        return None if x is None or x == "" else float(x)
    except (TypeError, ValueError):
        return None


def mean_plddt(pdb: str) -> Optional[float]:
    """Mean AlphaFold pLDDT = mean B-factor of CA atoms (a real computation on the structure file)."""
    vals = []
    for line in (pdb or "").splitlines():
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            try:
                vals.append(float(line[60:66]))
            except ValueError:
                pass
    return sum(vals) / len(vals) if vals else None


def plddt_at(pdb: str, pos: Optional[int]) -> Optional[float]:
    if pos is None:
        return None
    for line in (pdb or "").splitlines():
        if line.startswith("ATOM") and line[12:16].strip() == "CA" and line[22:26].strip() == str(pos):
            try:
                return float(line[60:66])
            except ValueError:
                return None
    return None


def uniprot_diseases(pdata: Mapping) -> List[Disease]:
    out = []
    for c in _as_list((pdata or {}).get("comments")):
        if c.get("commentType") == "DISEASE" and isinstance(c.get("disease"), dict):
            d = c["disease"]
            mim = ""
            ref = d.get("diseaseCrossReference") or {}
            if isinstance(ref, dict) and ref.get("database") == "MIM":
                mim = str(ref.get("id", ""))
            desc = str(d.get("description", ""))
            inh = ""
            for kw in ("autosomal dominant", "autosomal recessive", "x-linked", "mitochondrial"):
                if kw in desc.lower():
                    inh = kw.title() if kw != "x-linked" else "X-linked"
                    break
            out.append(Disease(name=str(d.get("diseaseId") or d.get("diseaseAcronym") or ""), inheritance=inh, omim=mim, desc=desc[:300]))
    return [d for d in out if d.name]


def build_bundle(ss: Mapping, *, diseases=None, is_gpcr: Optional[bool] = None, gpcr_class: str = "") -> Bundle:
    """Build a Bundle from st.session_state. `diseases` may be the app's own g_diseases(pdata) result."""
    g = lambda k, d=None: ss.get(k, d) if hasattr(ss, "get") else d
    b = Bundle(gene=str(g("gene", "") or ""), uid=str(g("uid", "") or ""))
    pdata = g("pdata") or {}
    if not b.gene or not pdata:
        return b
    b.name = str((((pdata.get("proteinDescription") or {}).get("recommendedName") or {}).get("fullName") or {}).get("value", ""))
    b.length = int(((pdata.get("sequence") or {}).get("length")) or 0)
    b.is_gpcr = bool(is_gpcr) if is_gpcr is not None else any("g-protein coupled" in str(k.get("name", "")).lower() for k in _as_list(pdata.get("keywords")))
    b.gpcr_class = gpcr_class
    b.pdb = str(g("pdb", "") or "")
    b.sequence = str((pdata.get("sequence") or {}).get("value", "") or "")
    syn = []
    for gn in _as_list(pdata.get("genes")):
        syn += [str(x.get("value", "")) for x in _as_list(gn.get("synonyms"))]
    pd_ = pdata.get("proteinDescription") or {}
    syn += [str((x.get("fullName") or {}).get("value", "")) for x in _as_list(pd_.get("alternativeNames"))]
    b.aliases = list(dict.fromkeys(x for x in syn if x and x.upper() != b.gene.upper()))
    b.query = str(g("last", "") or "")

    # ClinVar variants + the app's ML scoring (merged by name)
    cv = g("cv") or {}
    scored = {str(v.get("variant_name") or v.get("title") or ""): v for v in _as_list(g("scored"))}
    for v in _as_list(cv.get("variants") if isinstance(cv, dict) else []):
        key = str(v.get("variant_name") or v.get("title") or "")
        s = scored.get(key, {})
        sig = norm_sig(str(v.get("sig") or v.get("clinical_significance") or v.get("significance") or ""), v.get("score"))
        review = str(v.get("review") or "")
        b.variants.append(Variant(
            name=key, pos=parse_position(v), significance=sig,
            stars=stars_from_review(review) if review else int(v.get("stars") or 0), review=review,
            condition=str(v.get("condition") or ""), consequence=parse_consequence(v), url=str(v.get("url") or ""),
            ml_rank=str(s.get("ml_rank") or ""), ml_score=_num(s.get("ml")), somatic=bool(v.get("somatic", False))))
    # AlphaMissense: position -> aa -> {score, class}
    am = g("am") or {}
    if isinstance(am, dict):
        for pos, aas in am.items():
            if isinstance(aas, dict):
                try:
                    b.am[int(pos)] = {a: d for a, d in aas.items() if isinstance(d, dict) and _num(d.get("score")) is not None}
                except (TypeError, ValueError):
                    continue
    for v in b.variants:                                   # per-position AM: worst-case substitution at that residue
        cand = b.am.get(v.pos or -1, {})
        if cand:
            top = max(cand.values(), key=lambda d: d["score"])
            v.am_score, v.am_class = float(top["score"]), str(top.get("class", ""))

    b.diseases = [Disease(name=str(d.get("name", "")), inheritance=str(d.get("inheritance", "")), omim=str(d.get("omim", "") or ""),
                          desc=str(d.get("desc", ""))[:300], source=str(d.get("source", "UniProt")))
                  for d in _as_list(diseases) if isinstance(d, dict) and d.get("name")] or uniprot_diseases(pdata)
    for p in _as_list(g("string")):
        if isinstance(p, dict) and p.get("partner"):
            b.partners.append(Partner(str(p["partner"]), _num(p.get("score")) or 0.0, str(p.get("url") or "")))
    for d in _as_list(g("drugs")):
        if isinstance(d, dict) and d.get("drug"):
            b.drugs.append(Drug(name=str(d["drug"]), kind=str(d.get("type") or ""), url=str(d.get("url") or ""), source=str(d.get("sources") or "DGIdb")))
    ot = g("ot") or {}
    kd = ot.get("known_drugs", 0) if isinstance(ot, dict) else 0
    if isinstance(kd, list):                               # the app treats this as a list in one place and a count in another
        b.n_known_drugs = len(kd)
        for d in kd:
            if isinstance(d, dict) and d.get("name"):
                b.drugs.append(Drug(name=str(d["name"]), phase=str(d.get("phase", "")), mechanism=str(d.get("mechanism", "")),
                                    indication=str(d.get("indication", "")), url=str(d.get("url", "")), source="Open Targets"))
    else:
        b.n_known_drugs = int(kd) if isinstance(kd, (int, float)) else 0
    tr = ot.get("tractability", {}) if isinstance(ot, dict) else {}
    if isinstance(ot, dict) and isinstance(ot.get("_errors"), dict):
        b.source_errors = {f"Open Targets / {k}": str(v) for k, v in ot["_errors"].items()}
    # only count tractability as "available" if Open Targets actually returned some (an empty reply is a failed fetch, not "not druggable")
    b.tractability = {k: bool(tr.get(k)) for k in ("Small molecule", "Antibody", "PROTAC")} if isinstance(tr, dict) and tr else {}
    b.trials = [t for t in _as_list(g("trials")) if isinstance(t, dict)]
    b.hotspots = [Hotspot(int(h.get("start", 0)), int(h.get("end", 0)), int(h.get("count", 0)), float(h.get("fold_enrichment", 0) or 0))
                  for h in _as_list(g("hotspots")) if isinstance(h, dict)]
    gn = g("gnomad") or {}
    b.constraint = {k: _num(gn.get(k)) for k in ("pLI", "oe_lof", "oe_lof_upper", "mis_z")} if isinstance(gn, dict) else {}
    cg = g("clingen") or {}
    b.clingen = str(cg.get("classification", "")) if isinstance(cg, dict) else ""
    b.papers = [p for p in (_as_list(g("abstracts")) + _as_list(g("papers"))) if isinstance(p, dict)]
    for c in _as_list(pdata.get("comments")):
        if c.get("commentType") == "TISSUE SPECIFICITY":
            texts = _as_list(c.get("texts"))
            b.tissue_text = str(texts[0].get("value", "")) if texts else ""
        if c.get("commentType") == "SUBCELLULAR LOCATION":
            b.subcellular += [str((x.get("location") or {}).get("value", "")) for x in _as_list(c.get("subcellularLocations"))]
    for f in _as_list(pdata.get("features")):
        loc = f.get("location") or {}
        try:
            s, e = int((loc.get("start") or {}).get("value")), int((loc.get("end") or {}).get("value"))
        except (TypeError, ValueError):
            continue
        if f.get("type") in ("Domain", "Region", "Transmembrane", "Topological domain", "Motif", "Repeat", "Zinc finger", "DNA binding"):
            b.domains.append({"start": s, "end": e, "type": str(f.get("type")), "desc": str(f.get("description", ""))})
        if f.get("type") in ("Binding site", "Active site", "Site"):
            b.sites.append({"start": s, "end": e, "type": str(f.get("type")), "desc": str(f.get("description", ""))})

    n_plp = len(b.plp)
    b.audit = [
        DatasetStatus("UniProt entry", 1, "" if b.name else "no protein name found"),
        DatasetStatus("ClinVar variants", len(b.variants), "" if b.variants else "returned nothing: not in ClinVar, or the fetch failed"),
        DatasetStatus("  of which pathogenic / likely pathogenic", n_plp, ""),
        DatasetStatus("  with a position", sum(v.pos is not None for v in b.variants), "variants without a position cannot be placed on the structure"
                      if b.variants and not any(v.pos for v in b.variants) else ""),
        DatasetStatus("AlphaMissense positions", len(b.am), "" if b.am else "no AlphaMissense data"),
        DatasetStatus("gnomAD constraint", sum(v is not None for v in b.constraint.values()), "" if any(v is not None for v in b.constraint.values()) else "no constraint metrics"),
        DatasetStatus("Disease annotations", len(b.diseases), "" if b.diseases else "none found in UniProt"),
        DatasetStatus("ClinGen validity", int(bool(b.clingen)), "" if b.clingen else "no ClinGen classification"),
        DatasetStatus("Interaction partners (STRING)", len(b.partners), "" if b.partners else "no partners returned"),
        DatasetStatus("Drug-gene interactions", len(b.drugs), "" if b.drugs else "none returned"),
        DatasetStatus("Open Targets tractability", sum(b.tractability.values()), "" if b.tractability else "no tractability data (fetch may have failed)"),
        DatasetStatus("Clinical trials", len(b.trials), ""),
        DatasetStatus("Literature records", len(b.papers), ""),
        DatasetStatus("AlphaFold structure", int(len(b.pdb) > 100), "" if len(b.pdb) > 100 else "no structure file loaded"),
    ]
    return b
