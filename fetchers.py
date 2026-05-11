"""
fetchers.py — All external API calls for Protellect
Sources: UniProt, ClinVar, AlphaFold, AlphaMissense, PubMed, gnomAD, STRING, OpenTargets, DGIdb, ClinicalTrials
"""
import streamlit as st
import requests
import time
import json
import re

HEADERS = {"User-Agent": "Protellect/2.0 (research-platform)"}

# ── UniProt ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_uniprot(gene: str) -> dict:
    """Fetch full UniProt entry for a human gene symbol or accession."""
    gene = gene.strip().upper()
    # Accession pattern
    if re.match(r'^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$', gene):
        return _fetch_uniprot_by_accession(gene)
    return _fetch_uniprot_by_gene(gene)

def _fetch_uniprot_by_gene(gene: str) -> dict:
    try:
        r = requests.get("https://rest.uniprot.org/uniprotkb/search",
                         params={"query": f"gene:{gene} AND organism_id:9606 AND reviewed:true",
                                 "format": "json", "size": 1,
                                 "fields": "accession,gene_names,protein_name,organism_name,sequence,comments,features,keywords,genes"},
                         headers=HEADERS, timeout=15)
        results = r.json().get("results", [])
        if results:
            return _fetch_uniprot_by_accession(results[0]["primaryAccession"])
        # Try broader search
        r2 = requests.get("https://rest.uniprot.org/uniprotkb/search",
                          params={"query": f"({gene}) AND organism_id:9606 AND reviewed:true",
                                  "format": "json", "size": 1},
                          headers=HEADERS, timeout=15)
        results2 = r2.json().get("results", [])
        if results2:
            return _fetch_uniprot_by_accession(results2[0]["primaryAccession"])
        return {}
    except Exception:
        return {}

@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_uniprot_by_accession(acc: str) -> dict:
    try:
        r = requests.get(f"https://rest.uniprot.org/uniprotkb/{acc.upper()}.json",
                         headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

def parse_uniprot(entry: dict) -> dict:
    """Extract structured data from a UniProt JSON entry."""
    if not entry:
        return {}
    seq = entry.get("sequence", {}).get("value", "")
    genes = []
    for g in entry.get("genes", []):
        n = g.get("geneName", {}).get("value", "")
        if n: genes.append(n)
    diseases = []
    tissues = []
    functions = []
    subcellular = []
    ptms = []
    for c in entry.get("comments", []):
        ct = c.get("commentType", "")
        if ct == "DISEASE":
            d = c.get("disease", {})
            diseases.append({"name": d.get("diseaseName", "?"), "desc": d.get("description", "")[:200]})
        elif ct == "TISSUE SPECIFICITY":
            for t in c.get("texts", []): tissues.append(t.get("value", "")[:200])
        elif ct == "FUNCTION":
            for t in c.get("texts", []): functions.append(t.get("value", "")[:300])
        elif ct == "SUBCELLULAR LOCATION":
            for loc in c.get("subcellularLocations", []):
                v = loc.get("location", {}).get("value", "")
                if v: subcellular.append(v)
        elif ct == "PTM":
            for t in c.get("texts", []): ptms.append(t.get("value", "")[:200])
    domains = []
    variants = []
    for f in entry.get("features", []):
        ft = f.get("type", "")
        loc = f.get("location", {})
        s = loc.get("start", {}).get("value", "?")
        e2 = loc.get("end", {}).get("value", "?")
        if ft in ("DOMAIN", "REGION", "MOTIF", "DNA_BIND", "ACT_SITE", "ZN_FING", "BINDING"):
            domains.append({"type": ft, "name": f.get("description", ft), "start": s, "end": e2})
        elif ft in ("VARIANT", "MUTAGEN"):
            desc = f.get("description", "")
            alts = f.get("alternativeSequence", {})
            variants.append({"pos": s, "original": alts.get("originalSequence", ""),
                              "mutated": ", ".join(alts.get("alternativeSequences", [])),
                              "desc": desc[:150]})
    kws = [k.get("name", "") for k in entry.get("keywords", [])]
    is_gpcr = any("g protein-coupled" in k.lower() or "gpcr" in k.lower() or "seven-transmembrane" in k.lower()
                  for k in kws + [str(entry.get("proteinDescription", "")).lower()])
    org = entry.get("organism", {})
    taxon_id = org.get("taxonId", 0)
    return {
        "accession": entry.get("primaryAccession", ""),
        "gene": genes[0] if genes else "",
        "gene_synonyms": genes[1:5],
        "protein_name": entry.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", ""),
        "organism": org.get("scientificName", ""),
        "taxon_id": taxon_id,
        "is_human": taxon_id == 9606,
        "sequence": seq,
        "seq_len": len(seq),
        "diseases": diseases,
        "tissues": tissues,
        "functions": functions,
        "subcellular": list(set(subcellular)),
        "domains": domains,
        "variants": variants,
        "ptms": ptms,
        "keywords": kws,
        "is_gpcr": is_gpcr,
        "mw_kda": round(len(seq) * 110 / 1000, 1),
    }

# ── ClinVar ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_clinvar(gene: str, max_r: int = 50) -> list:
    """Fetch ClinVar variants for a gene with ML scoring."""
    try:
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                         params={"db": "clinvar", "term": f"{gene}[gene] AND homo sapiens[organism]",
                                 "retmax": max_r, "retmode": "json"},
                         headers=HEADERS, timeout=15)
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids: return []
        time.sleep(0.35)
        r2 = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                          params={"db": "clinvar", "id": ",".join(ids[:50]), "retmode": "json"},
                          headers=HEADERS, timeout=20)
        result = r2.json().get("result", {})
        variants = []
        for uid in result.get("uids", []):
            v = result.get(uid, {})
            sig = v.get("clinical_significance", {}).get("description", "Unknown")
            review = v.get("review_status", "")
            conditions = [c.get("trait_name", "") for c in v.get("trait_set", [])]
            protein_change = v.get("protein_change", "")
            # Extract numeric position
            pos = 0
            m = re.search(r'(\d+)', protein_change)
            if m: pos = int(m.group(1))
            # ML score
            ml_score, ml_class, ml_color = _score_variant(sig, review)
            # Stars
            stars = {"no assertion": 0, "criteria provided, single": 1,
                     "criteria provided, multiple": 2, "reviewed by expert": 4}.get(
                review.lower()[:30], 0) if review else 0
            variants.append({
                "id": uid, "title": v.get("title", ""),
                "significance": sig, "review_status": review,
                "protein_change": protein_change,
                "position": pos,
                "conditions": conditions,
                "ml_score": ml_score, "ml_class": ml_class, "ml_color": ml_color,
                "stars": stars,
                "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/",
                "is_germline": _is_germline(sig, v.get("origin", "")),
            })
        return sorted(variants, key=lambda x: x["ml_score"], reverse=True)
    except Exception:
        return []

def _score_variant(sig: str, review: str) -> tuple:
    sl = sig.lower()
    if "pathogenic" in sl and "likely" not in sl: base = 5
    elif "likely pathogenic" in sl: base = 4
    elif "uncertain" in sl or "vus" in sl: base = 2
    elif "likely benign" in sl: base = 1
    elif "benign" in sl: base = 0
    else: base = 2
    # Review bonus
    if "expert" in review.lower(): base += 1
    if "multiple" in review.lower(): base += 0.5
    if base >= 5:   return base, "CRITICAL",  "#ff2d55"
    if base >= 4:   return base, "HIGH",       "#ff8c42"
    if base >= 2:   return base, "MODERATE",  "#ffd60a"
    return base,          "LOW",        "#64748b"

def _is_germline(sig: str, origin) -> bool:
    o = str(origin).lower() if origin else ""
    return "germline" in o or "hereditary" in o or not ("somatic" in o)

# ── AlphaFold ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=604800, show_spinner=False)
def fetch_alphafold_pdb(accession: str) -> str:
    try:
        r = requests.get(f"https://alphafold.ebi.ac.uk/files/AF-{accession.upper()}-F1-model_v4.pdb",
                         headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception:
        return ""

def parse_plddt(pdb_text: str) -> dict:
    d = {}
    for line in (pdb_text or "").splitlines():
        if line.startswith("ATOM"):
            try:
                resi = int(line[22:26].strip())
                b = float(line[60:66].strip())
                if resi not in d: d[resi] = b
            except: pass
    return d

# ── AlphaMissense ──────────────────────────────────────────────────────────
@st.cache_data(ttl=604800, show_spinner=False)
def fetch_alphamissense(accession: str) -> list:
    """Fetch per-residue AlphaMissense pathogenicity scores."""
    try:
        url = f"https://alphafold.ebi.ac.uk/files/AF-{accession.upper()}-F1-aa-substitutions.csv"
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200: return []
        lines = r.text.strip().splitlines()
        results = []
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) >= 4:
                try:
                    pos = int(parts[0])
                    ref = parts[1]
                    alt = parts[2]
                    score = float(parts[3])
                    cls = "pathogenic" if score >= 0.564 else "benign"
                    results.append({"position": pos, "ref": ref, "alt": alt, "score": score, "class": cls})
                except: pass
        return results
    except Exception:
        return []

# ── PubMed ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_pubmed(gene: str, n: int = 20) -> list:
    """Multi-query PubMed fetch with evidence tier classification."""
    queries = [
        f"{gene}[gene] pathogenic variant clinical 2020:2025[pdat]",
        f"{gene} functional assay CRISPR 2020:2025[pdat]",
        f"{gene} therapy treatment clinical trial 2020:2025[pdat]",
        f"{gene} disease mechanism phenotype 2020:2025[pdat]",
    ]
    all_papers = []
    seen_ids = set()
    for q in queries:
        try:
            r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                             params={"db": "pubmed", "term": q, "retmax": 6, "retmode": "json"},
                             headers=HEADERS, timeout=12)
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            new_ids = [i for i in ids if i not in seen_ids]
            if not new_ids: continue
            seen_ids.update(new_ids)
            time.sleep(0.35)
            r2 = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                              params={"db": "pubmed", "id": ",".join(new_ids), "retmode": "json"},
                              headers=HEADERS, timeout=15)
            result = r2.json().get("result", {})
            for pid in new_ids:
                p = result.get(pid, {})
                authors = p.get("authors", [])
                fa = authors[0].get("name", "") if authors else ""
                title = p.get("title", "")
                tier = _classify_paper_tier(title)
                all_papers.append({
                    "pmid": pid, "title": title, "year": p.get("pubdate", "")[:4],
                    "authors": f"{fa} et al." if len(authors) > 1 else fa,
                    "journal": p.get("source", ""),
                    "doi": p.get("elocationid", "").replace("doi: ", ""),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                    "tier": tier,
                    "tier_label": _tier_label(tier),
                    "tier_color": _tier_color(tier),
                })
        except Exception:
            continue
    return sorted(all_papers, key=lambda x: x["tier"])[:n]

def _classify_paper_tier(title: str) -> int:
    t = title.lower()
    if any(k in t for k in ["randomised", "randomized", "rct", "placebo-controlled"]): return 1
    if any(k in t for k in ["cohort", "prospective", "retrospective", "case-control"]): return 2
    if any(k in t for k in ["crispr", "knock-in", "western blot", "functional assay", "patch-clamp"]): return 3
    if any(k in t for k in ["cryo-em", "nmr", "x-ray", "spr", "itc", "alphafold", "crystal"]): return 4
    if any(k in t for k in ["mouse model", "zebrafish", "xenograft", "in vivo"]): return 5
    if any(k in t for k in ["in silico", "machine learning", "computational", "algorithm"]): return 6
    if any(k in t for k in ["case report", "case series"]): return 7
    if any(k in t for k in ["review", "meta-analysis", "systematic"]): return 8
    if any(k in t for k in ["preprint", "biorxiv", "medrxiv"]): return 9
    return 5

def _tier_label(t: int) -> str:
    return {1: "RCT", 2: "Cohort", 3: "Functional", 4: "Structural", 5: "Animal",
            6: "Computational", 7: "Case Report", 8: "Review", 9: "Preprint"}.get(t, "Study")

def _tier_color(t: int) -> str:
    return {1: "#00e5ff", 2: "#4ade80", 3: "#818cf8", 4: "#f97316",
            5: "#fbbf24", 6: "#94a3b8", 7: "#64748b", 8: "#475569", 9: "#334155"}.get(t, "#64748b")

# ── gnomAD ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_gnomad(gene: str) -> dict:
    """Fetch gnomAD constraint metrics via GraphQL."""
    query = """
    query GnomadGene($geneId: String!) {
      gene(gene_symbol: $geneId, reference_genome: GRCh38) {
        pLI: gnomad_constraint { pLI lof { oe } missense { oe } }
        gnomad_constraint { pLI lof { oe obs exp } missense { oe obs exp } }
      }
    }
    """
    try:
        r = requests.post("https://gnomad.broadinstitute.org/api",
                          json={"query": query, "variables": {"geneId": gene}},
                          headers={**HEADERS, "Content-Type": "application/json"},
                          timeout=20)
        data = r.json().get("data", {}).get("gene", {})
        constraint = data.get("gnomad_constraint", {}) or {}
        pLI = constraint.get("pLI", 0) or 0
        lof_oe = (constraint.get("lof", {}) or {}).get("oe", None)
        mis_oe = (constraint.get("missense", {}) or {}).get("oe", None)
        return {
            "pLI": round(float(pLI), 3) if pLI else None,
            "lof_oe": round(float(lof_oe), 3) if lof_oe else None,
            "missense_oe": round(float(mis_oe), 3) if mis_oe else None,
            "lof_constrained": float(lof_oe) < 0.35 if lof_oe else False,
            "essential": float(pLI) > 0.9 if pLI else False,
        }
    except Exception:
        return {}

# ── STRING ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_string(gene: str, limit: int = 15) -> list:
    try:
        r = requests.get("https://string-db.org/api/json/get_string_ids",
                         params={"identifiers": gene, "species": 9606, "limit": 1, "caller_identity": "protellect"},
                         headers=HEADERS, timeout=12)
        data = r.json()
        if not data: return []
        sid = data[0].get("stringId", "")
        r2 = requests.get("https://string-db.org/api/json/interaction_partners",
                          params={"identifiers": sid, "species": 9606, "limit": limit,
                                  "required_score": 700, "caller_identity": "protellect"},
                          headers=HEADERS, timeout=15)
        return [{"partner": i.get("preferredName_B", ""), "score": round(i.get("score", 0), 3),
                 "experimental": round(i.get("experimentally_determined_interaction", 0), 3),
                 "coexpression": round(i.get("coexpression", 0), 3)}
                for i in r2.json()]
    except Exception:
        return []

# ── OpenTargets ────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_opentargets(gene: str) -> dict:
    # Resolve to Ensembl ID
    try:
        r = requests.get(f"https://mygene.info/v3/query?q={gene}&species=human&fields=ensembl.gene",
                         headers=HEADERS, timeout=10)
        hits = r.json().get("hits", [])
        if not hits: return {}
        eid = hits[0].get("ensembl", {}).get("gene", "")
        if isinstance(eid, list): eid = eid[0]
        if not eid: return {}
    except Exception:
        return {}

    query = """
    query OT($ensgId: String!) {
      target(ensemblId: $ensgId) {
        tractability {
          smallMolecule { value label }
          antibody { value label }
        }
        knownDrugs { count rows { drug { name mechanismsOfAction { rows { actionType } } } phase status } }
        associatedDiseases(page: {index: 0, size: 10}) {
          rows { score disease { id name } }
        }
      }
    }
    """
    try:
        r = requests.post("https://api.platform.opentargets.org/api/v4/graphql",
                          json={"query": query, "variables": {"ensgId": eid}},
                          headers={**HEADERS, "Content-Type": "application/json"},
                          timeout=20)
        target = r.json().get("data", {}).get("target", {}) or {}
        tract = target.get("tractability", {}) or {}
        drugs_data = target.get("knownDrugs", {}) or {}
        assoc = target.get("associatedDiseases", {}).get("rows", [])
        return {
            "sm_tractable": any(t.get("value") for t in (tract.get("smallMolecule") or [{}])),
            "ab_tractable": any(t.get("value") for t in (tract.get("antibody") or [{}])),
            "known_drugs_count": drugs_data.get("count", 0),
            "known_drugs": [r.get("drug", {}).get("name", "") for r in (drugs_data.get("rows") or [])[:6]],
            "disease_associations": [{"name": a["disease"]["name"], "score": a["score"]}
                                      for a in assoc if a.get("disease")],
        }
    except Exception:
        return {}

# ── DGIdb ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_dgidb(gene: str) -> list:
    try:
        r = requests.get(f"https://dgidb.org/api/v2/interactions.json",
                         params={"genes": gene}, headers=HEADERS, timeout=12)
        matches = r.json().get("matchedTerms", [])
        drugs = []
        for m in matches:
            for iact in m.get("interactions", [])[:8]:
                drug = iact.get("drugName", "")
                if drug: drugs.append({"drug": drug, "type": iact.get("interactionTypes", ["?"])[0] if iact.get("interactionTypes") else "?",
                                        "source": iact.get("sources", [{}])[0].get("sourceName", "") if iact.get("sources") else ""})
        return drugs[:10]
    except Exception:
        return []

# ── ClinicalTrials.gov ─────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_trials(gene: str) -> list:
    try:
        r = requests.get("https://clinicaltrials.gov/api/v2/studies",
                         params={"query.term": gene, "filter.status": "RECRUITING", "pageSize": 8},
                         headers=HEADERS, timeout=15)
        studies = r.json().get("studies", [])
        trials = []
        for s in studies:
            mod = s.get("protocolSection", {})
            id_mod = mod.get("identificationModule", {})
            status_mod = mod.get("statusModule", {})
            design_mod = mod.get("designModule", {})
            trials.append({
                "nct_id": id_mod.get("nctId", ""),
                "title": id_mod.get("briefTitle", "")[:100],
                "status": status_mod.get("overallStatus", ""),
                "phase": design_mod.get("phases", ["?"])[0] if design_mod.get("phases") else "?",
                "url": f"https://clinicaltrials.gov/study/{id_mod.get('nctId','')}",
            })
        return trials
    except Exception:
        return []

# ── GTEx ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_gtex(gene: str) -> dict:
    try:
        r = requests.get("https://gtexportal.org/api/v2/expression/medianGeneExpression",
                         params={"geneId": gene, "datasetId": "gtex_v8", "format": "json"},
                         headers=HEADERS, timeout=20)
        items = r.json().get("medianGeneExpression", [])
        return {i.get("tissueSiteDetailId", "").replace("_", " "): i.get("median", 0) for i in items}
    except Exception:
        return {}

# ── KEGG ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_kegg_pathways(gene: str) -> list:
    try:
        r = requests.get(f"https://rest.kegg.jp/find/hsa/{gene}", headers=HEADERS, timeout=10)
        lines = r.text.strip().splitlines()
        if not lines: return []
        gid = lines[0].split("\t")[0].strip()
        r2 = requests.get(f"https://rest.kegg.jp/link/pathway/{gid}", headers=HEADERS, timeout=10)
        pids = [l.split("\t")[1].strip() for l in r2.text.strip().splitlines() if "\t" in l][:8]
        if not pids: return []
        r3 = requests.get(f"https://rest.kegg.jp/list/{'+'.join(pids)}", headers=HEADERS, timeout=10)
        pathways = []
        for line in r3.text.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                pathways.append({"id": parts[0].strip(), "name": parts[1].strip(),
                                  "url": f"https://www.kegg.jp/pathway/{parts[0].strip()}"})
        return pathways
    except Exception:
        return []

# ── AI synthesis (Claude) ──────────────────────────────────────────────────
def fetch_ai_report(gene: str, protein_data: dict, clinvar_data: list,
                    gnomad_data: dict, string_data: list, api_key: str = "") -> str:
    if not api_key:
        return ""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        path_count = sum(1 for v in clinvar_data if v.get("ml_class") in ("CRITICAL","HIGH"))
        conditions = list({c for v in clinvar_data for c in v.get("conditions",[]) if c})[:5]
        partners = [p["partner"] for p in string_data[:5]]
        prompt = f"""You are a specialist molecular biologist analysing {gene} for drug target potential.

PROTEIN DATA:
- Gene: {gene}
- Protein: {protein_data.get('protein_name','')}
- ClinVar pathogenic variants: {path_count}
- Conditions: {', '.join(conditions) or 'None identified'}
- gnomAD pLI: {gnomad_data.get('pLI','Unknown')} (>0.9 = essential)
- STRING top partners: {', '.join(partners) or 'Unknown'}
- Disease associations from UniProt: {len(protein_data.get('diseases',[]))} entries

TASK: Generate a comprehensive analysis covering:
1. VERDICT — PURSUE / PROCEED / SELECTIVE / DEPRIORITISE with clear justification from genetics
2. MECHANISM — specific molecular mechanism of disease causation
3. INHERITANCE — autosomal dominant/recessive/X-linked/de novo (infer from variant data)
4. THERAPEUTIC HYPOTHESES — 3 specific drug development approaches with rationale
5. KEY UNKNOWNS — what experiments would resolve the key uncertainties
6. ACTIVE RESEARCH — what is currently being studied (use web search if available)

RULES:
- Every factual claim MUST cite: Author, Journal, Year, PMID
- Never say "unknown" — say what experiment would resolve it
- Be specific about variant positions (e.g. p.Arg175His not just "missense")
- If this is a GPCR: note Filamin Ser2152-P assay as the receptor-proximal readout
- If this is ARRB1/ARRB2: immediately note DEPRIORITISE — <5 Mendelian disease variants

Respond in structured markdown with clear headers."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}]
        )
        # Extract text from content blocks
        text_parts = [b.text for b in message.content if hasattr(b, "text") and b.text]
        return "\n".join(text_parts)
    except Exception as e:
        return f"AI synthesis unavailable: {str(e)}"
