# modules/api.py
from __future__ import annotations
import re, time, json, math, io
from collections import Counter, defaultdict
import requests
import streamlit as st
from modules.config import ESEARCH, ESUMMARY
from modules.utils import clean_sig

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_uniprot(query):
    """
    Fetch UniProt entry — STRICTLY human only (organism_id:9606 / Homo sapiens).
    Validates organism on EVERY result before returning.
    Non-human proteins raise a clear ValueError with explanation.
    """
    base = "https://rest.uniprot.org/uniprotkb"
    HUMAN_TAXID = 9606

    NON_HUMAN_TERMS = {
        "ovalbumin":"chicken (Gallus gallus)",
        "beta keratin":"reptile/bird — no human equivalent",
        "beta-keratin":"reptile/bird — no human equivalent",
        "serum albumin bovine":"cow (Bos taurus)",
        "lysozyme hen":"chicken (Gallus gallus)",
        "insulin bovine":"cow (Bos taurus)",
        "hemoglobin horse":"horse (Equus caballus)",
        "cytochrome c horse":"horse (Equus caballus)",
        "green fluorescent protein":"jellyfish (Aequorea victoria)",
        "gfp":"jellyfish (Aequorea victoria) — use human fluorescent reporters",
        "luciferase":"firefly (Photinus pyralis)",
    }
    q_lower = query.lower().strip()
    for term, species in NON_HUMAN_TERMS.items():
        if term in q_lower:
            raise ValueError(
                f"⚠️ '{query}' is a non-human protein ({species}). "
                f"Protellect analyses human proteins only. "
                f"If you're looking for the human version, try searching for the human gene name or function instead."
            )

    def validate_human(entry):
        org = entry.get("organism", {})
        sci = org.get("scientificName", "")
        taxid = org.get("taxonId", 0)
        if "Homo sapiens" in sci or taxid == HUMAN_TAXID:
            return True
        common = org.get("commonName", sci)
        gene_n = entry.get("genes",[{}])[0].get("geneName",{}).get("value","this protein") if entry.get("genes") else "this protein"
        acc_n  = entry.get("primaryAccession","?")
        raise ValueError(
            f"⚠️ Non-human protein detected: '{query}' resolved to **{gene_n}** ({acc_n}) from "
            f"**{common}** ({sci}). "
            f"Protellect is human-only. This protein does not exist in the human genome. "
            f"If a human orthologue exists, search by the human gene symbol (e.g. KRT — human keratin). "
            f"Human proteins to try: TP53 · FLNC · BRCA1 · ACM2 · EGFR · P04637"
        )

    if re.match(r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$", query.strip(), re.I):
        r = requests.get(f"{base}/{query.strip().upper()}", headers={"Accept":"application/json"}, timeout=20)
        r.raise_for_status()
        entry = r.json()
        validate_human(entry)
        return entry

    human_queries = [
        f"gene:{query} AND reviewed:true AND organism_id:9606",
        f"gene_exact:{query} AND organism_id:9606",
        f"protein_name:{query} AND reviewed:true AND organism_id:9606",
        f"({query}) AND reviewed:true AND organism_id:9606",
    ]
    for qry in human_queries:
        try:
            r = requests.get(f"{base}/search",
                             params={"query": qry, "format": "json", "size": 3},
                             headers={"Accept": "application/json"}, timeout=20)
            r.raise_for_status()
            results = r.json().get("results", [])
            for candidate in results:
                org = candidate.get("organism", {})
                sci = org.get("scientificName","")
                taxid = org.get("taxonId", 0)
                if "Homo sapiens" not in sci and taxid != HUMAN_TAXID:
                    continue
                uid = candidate["primaryAccession"]
                r2 = requests.get(f"{base}/{uid}", headers={"Accept":"application/json"}, timeout=20)
                r2.raise_for_status()
                full_entry = r2.json()
                validate_human(full_entry)
                return full_entry
        except ValueError:
            raise
        except Exception:
            continue

    raise ValueError(
        f"⚠️ No human (Homo sapiens) protein found for '{query}'. "
        f"Protellect analyses human proteins only. "
        f"Possible reasons: (1) this protein doesn't exist in humans, "
        f"(2) you searched a non-human protein name, "
        f"(3) the gene symbol is different in humans. "
        f"Try: TP53 · FLNC · BRCA1 · EGFR · ACM2 · ARRB2 · P04637 (TP53 accession)"
    )

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_clinvar(gene, max_v=150):
    import time, re as re2
    ids = []
    for term in [f"{gene}[genesymbol]", f"{gene}[gene]", f"{gene}[gene_name]"]:
        try:
            r = requests.get(ESEARCH, params={"db":"clinvar","term":term,"retmax":max_v,"retmode":"json"}, timeout=30)
            r.raise_for_status()
            ids = r.json().get("esearchresult",{}).get("idlist",[])
            if ids: break
            time.sleep(0.4)
        except: continue
    if not ids: return {"variants":[],"summary":{}}
    variants=[]
    for i in range(0,len(ids),100):
        try:
            r2=requests.get(ESUMMARY,params={"db":"clinvar","id":",".join(ids[i:i+100]),"retmode":"json"},timeout=30)
            r2.raise_for_status(); data=r2.json().get("result",{})
            for uid in data.get("uids",[]):
                e=data.get(uid,{}); gc=e.get("germline_classification",{})
                sig_raw = str(gc.get("description","Not provided") or "Not provided")
                sig = clean_sig(sig_raw)
                sc  = globals()["SIG_SCORE"].get(sig_raw.lower().strip(), globals()["SIG_SCORE"].get(sig.lower().strip(), 0))
                traits=[t.get("trait_name","") for t in e.get("trait_set",{}).get("trait",[]) if t.get("trait_name")]
                locs=e.get("location_list",[{}]); vset=e.get("variation_set",[{}])
                var_name = vset[0].get("variation_name","") if vset else ""
                prot_pos = ""
                pm = re2.search(r"p\.([A-Za-z]+)(\d+)", var_name)
                if pm: prot_pos = pm.group(2)
                if not prot_pos:
                    cm = re2.search(r"c\.(\d+)", var_name)
                    if cm: prot_pos = str(int(cm.group(1))//3 + 1)
                origin_raw = e.get("origin",{})
                if isinstance(origin_raw, dict):
                    origin_str = origin_raw.get("origin", "")
                elif isinstance(origin_raw, str):
                    origin_str = origin_raw
                else:
                    origin_str = str(origin_raw)
                is_somatic = bool(e.get("somatic_classifications",{})) or "somatic" in origin_str.lower()
                is_germline = any(x in origin_str.lower() for x in ["germline","inherited","de novo","maternal","paternal","constitutional"]) or (not is_somatic and sc >= 3)
                variants.append({
                    "uid":uid,"title":e.get("title",""),
                    "variant_name": var_name,
                    "sig":sig,"score":sc,"condition":"; ".join(t for t in traits if t.strip()) if traits else "",
                    "origin": origin_str,
                    "review":gc.get("review_status",""),
                    "start": prot_pos,
                    "somatic": is_somatic,
                    "germline": is_germline,
                    "url":f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{e.get('variation_id',uid)}/",
                })
        except: pass
        time.sleep(0.1)
    variants.sort(key=lambda x:-x["score"])
    sigs=Counter(clean_sig(v["sig"]) if str(v["sig"]).strip().isdigit() else v["sig"] for v in variants)
    conds=Counter()
    for v in variants:
        for c in v["condition"].split(";"):
            c=c.strip()
            if c and c!="Not specified": conds[c]+=1
    return {"variants":variants,"summary":{"total":len(variants),"by_sig":dict(sigs.most_common(8)),
            "top_conds":dict(conds.most_common(10)),"pathogenic":sum(1 for v in variants if v["score"]>=4),
            "vus":sum(1 for v in variants if v["score"]==2)}}

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_disease_proteins(disease_name, max_genes=15):
    try:
        queries = [
            f'"{disease_name}"[dis] AND (pathogenic[clnsig] OR "likely pathogenic"[clnsig])',
            f'{disease_name}[dis] AND pathogenic[clnsig]',
            f'{disease_name}[condition] AND (pathogenic[clnsig] OR "likely pathogenic"[clnsig])',
        ]
        ids = []
        for query in queries:
            r=requests.get(ESEARCH,params={"db":"clinvar","term":query,"retmax":300,"retmode":"json"},timeout=25)
            r.raise_for_status()
            ids=r.json().get("esearchresult",{}).get("idlist",[])
            if ids: break
        if not ids: return []
        r2=requests.get(ESUMMARY,params={"db":"clinvar","id":",".join(ids[:200]),"retmode":"json"},timeout=30)
        r2.raise_for_status(); data=r2.json().get("result",{})
        gene_map=defaultdict(lambda:{"count":0,"conditions":set(),"sigs":[],"uid":""})
        for uid in data.get("uids",[]):
            e=data.get(uid,{}); gs=e.get("gene_sort","") or e.get("genes",{}).get("gene",{}).get("symbol","")
            if not gs:
                vset=e.get("variation_set",[{}])
                if vset: gs=vset[0].get("gene_id","")
            gc=e.get("germline_classification",{}); sig=gc.get("description","")
            traits=[t.get("trait_name","") for t in e.get("trait_set",{}).get("trait",[]) if t.get("trait_name")]
            gene_map[gs]["count"]+=1
            gene_map[gs]["sigs"].append(sig)
            gene_map[gs]["uid"]=uid
            for t in traits: gene_map[gs]["conditions"].add(t)
        results=[]
        for gene,info in sorted(gene_map.items(),key=lambda x:-x[1]["count"]):
            if not gene or gene=="0": continue
            results.append({"gene":gene,"n_pathogenic":info["count"],
                           "conditions":list(info["conditions"])[:3],
                           "sigs":list(set(info["sigs"]))[:3],
                           "clinvar_url":f"https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]+{disease_name}[disease]"})
        return results[:max_genes]
    except: return []

@st.cache_data(show_spinner=False, ttl=604800)
def fetch_pdb(uid):
    if not uid: return ""
    acc = uid.upper()
    try:
        r = requests.get(f"https://alphafold.ebi.ac.uk/api/prediction/{acc}",
                         timeout=20, headers={"Accept": "application/json"})
        if r.status_code == 200:
            entries = r.json()
            if entries:
                pdb_url = entries[0].get("pdbUrl", "")
                if pdb_url:
                    r2 = requests.get(pdb_url, timeout=35)
                    if r2.status_code == 200 and "ATOM" in r2.text and len(r2.text) > 500:
                        return r2.text
    except Exception:
        pass
    for url in [
        f"https://alphafold.ebi.ac.uk/files/AF-{acc}-F1-model_v4.pdb",
        f"https://alphafold.ebi.ac.uk/files/AF-{acc}-F1-model_v3.pdb",
        f"https://alphafold.ebi.ac.uk/files/AF-{acc}-F2-model_v4.pdb",
    ]:
        try:
            r = requests.get(url, timeout=35)
            if r.status_code == 200 and "ATOM" in r.text and len(r.text) > 500:
                return r.text
        except Exception:
            continue
    return ""

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_papers(gene, n=6):
    try:
        r=requests.get(ESEARCH,params={"db":"pubmed","term":gene,"retmax":n*2,"retmode":"json","sort":"relevance"},timeout=15)
        r.raise_for_status(); ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return []
        r2=requests.get(ESUMMARY,params={"db":"pubmed","id":",".join(ids),"retmode":"json"},timeout=15)
        r2.raise_for_status(); data=r2.json().get("result",{})
        papers=[]
        for uid in data.get("uids",[]):
            e=data.get(uid,{})
            authors=", ".join(a.get("name","") for a in e.get("authors",[])[:3])
            if len(e.get("authors",[]))>3: authors+=" et al."
            pt=[p2.get("value","").lower() for p2 in e.get("pubtype",[])]
            sc=(3 if "review" in pt else 0)+(2 if e.get("pubdate","")[:4]>="2020" else 0)
            papers.append({"pmid":uid,"title":e.get("title","No title"),"authors":authors,
                           "journal":e.get("source",""),"year":e.get("pubdate","")[:4],
                           "url":f"https://pubmed.ncbi.nlm.nih.gov/{uid}/","score":sc,"pt":pt})
        return sorted(papers,key=lambda x:-x["score"])[:n]
    except: return []

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_pubmed_abstracts(gene: str, n: int = 12) -> list:
    try:
        queries = [
            f"{gene}[gene] AND (experiment OR assay OR functional OR knockout OR knockin OR crystal OR cryo-em OR structure)[title/abstract]",
            f"{gene}[gene] AND humans[mesh]",
        ]
        ids = []
        for q in queries:
            r = requests.get(ESEARCH, params={"db":"pubmed","term":q,"retmax":20,"retmode":"json","sort":"relevance"}, timeout=15)
            r.raise_for_status()
            new_ids = r.json().get("esearchresult",{}).get("idlist",[])
            for i in new_ids:
                if i not in ids: ids.append(i)
            if len(ids) >= n*2: break
        if not ids: return []
        r2 = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                          params={"db":"pubmed","id":",".join(ids[:n*2]),"retmode":"xml","rettype":"abstract"}, timeout=20)
        r2.raise_for_status()
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r2.text)
        papers = []
        for article in root.findall(".//PubmedArticle")[:n]:
            try:
                pmid    = article.findtext(".//PMID","")
                title   = article.findtext(".//ArticleTitle","")
                year    = article.findtext(".//PubDate/Year","?")
                journal = article.findtext(".//Journal/Title","")
                abstract_parts = article.findall(".//AbstractText")
                abstract = " ".join((p.text or "") for p in abstract_parts)
                authors_nodes = article.findall(".//Author")[:3]
                authors = ", ".join(
                    (a.findtext("LastName","") + " " + (a.findtext("ForeName","")[:1] or "")).strip()
                    for a in authors_nodes
                )
                if len(authors_nodes) > 3: authors += " et al."
                papers.append({
                    "pmid": pmid, "title": title, "abstract": abstract[:800],
                    "year": year, "journal": journal, "authors": authors,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                })
            except: pass
        return papers
    except Exception as e:
        return []

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_string_interactions(gene: str, species: int = 9606, limit: int = 10) -> list:
    try:
        url = "https://string-db.org/api/json/interaction_partners"
        r = requests.get(url, params={
            "identifiers": gene, "species": species,
            "limit": limit, "required_score": 700
        }, timeout=15)
        r.raise_for_status()
        data = r.json()
        interactions = []
        for item in data[:limit]:
            interactions.append({
                "partner": item.get("preferredName_B", item.get("stringId_B","")),
                "score": round(item.get("score",0) * 1000),
                "experiments": round(item.get("escore",0) * 1000),
                "coexpression": round(item.get("coexpression",0) * 1000),
                "url": f"https://string-db.org/network/{item.get('stringId_A','')}"
            })
        return sorted(interactions, key=lambda x: -x["score"])
    except:
        return []

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_gnomad(gene: str) -> dict:
    try:
        query = """
        { gene(gene_symbol: "%s", reference_genome: GRCh38) {
            gnomad_constraint { oe_lof oe_lof_upper oe_mis oe_mis_upper pLI pRec }
            pext { mean_proportion }
        } }
        """ % gene
        r = requests.post("https://gnomad.broadinstitute.org/api",
                         json={"query": query}, timeout=15,
                         headers={"Content-Type":"application/json"})
        r.raise_for_status()
        data = r.json()
        constraint = data.get("data",{}).get("gene",{}).get("gnomad_constraint",{}) or {}
        return {
            "pLI":   round(constraint.get("pLI",0) or 0, 3),
            "oe_lof": round(constraint.get("oe_lof",1) or 1, 3),
            "oe_mis": round(constraint.get("oe_mis",1) or 1, 3),
            "url": f"https://gnomad.broadinstitute.org/gene/{gene}?dataset=gnomad_r4",
            "intolerant": (constraint.get("pLI",0) or 0) > 0.9,
            "mis_intolerant": (constraint.get("oe_mis",1) or 1) < 0.6,
        }
    except:
        return {}

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_clinical_trials(gene: str, condition: str = "") -> list:
    try:
        query = gene if not condition else f"{gene} {condition}"
        r = requests.get(
            "https://clinicaltrials.gov/api/v2/studies",
            params={"query.term": query, "pageSize": 8, "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING"},
            timeout=15
        )
        r.raise_for_status()
        studies = r.json().get("studies",[])
        trials = []
        for s in studies:
            proto = s.get("protocolSection",{})
            ident = proto.get("identificationModule",{})
            status = proto.get("statusModule",{})
            design = proto.get("designModule",{})
            trials.append({
                "nct_id": ident.get("nctId",""),
                "title": ident.get("briefTitle","")[:120],
                "status": status.get("overallStatus",""),
                "phase": design.get("phases",["?"])[0] if design.get("phases") else "?",
                "url": f"https://clinicaltrials.gov/study/{ident.get('nctId','')}",
            })
        return trials
    except:
        return []

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_dgidb(gene: str) -> list:
    try:
        r = requests.get(f"https://www.dgidb.org/api/v2/interactions.json?genes={gene}", timeout=15)
        r.raise_for_status()
        interactions = r.json().get("matchedTerms",[{}])[0].get("interactions",[])
        drugs = []
        seen = set()
        for d in interactions[:15]:
            drug_name = d.get("drugName","")
            if drug_name and drug_name not in seen:
                seen.add(drug_name)
                drugs.append({
                    "drug": drug_name,
                    "type": d.get("interactionTypes",["unknown"])[0] if d.get("interactionTypes") else "unknown",
                    "sources": ", ".join(d.get("sources",[])[:2]),
                    "url": f"https://www.dgidb.org/genes/{gene}#interactions",
                })
        return drugs
    except:
        return []

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_ncbi_gene(symbol):
    try:
        r=requests.get(ESEARCH,params={"db":"gene","term":f"{symbol}[gene name] AND Homo sapiens[organism] AND alive[property]","retmax":1,"retmode":"json"},timeout=15)
        r.raise_for_status(); ids=r.json().get("esearchresult",{}).get("idlist",[])
        if not ids: return {}
        gid=ids[0]
        r2=requests.get(ESUMMARY,params={"db":"gene","id":gid,"retmode":"json"},timeout=15)
        r2.raise_for_status(); e=r2.json().get("result",{}).get(gid,{})
        gi=e.get("genomicinfo",[{}])[0] if e.get("genomicinfo") else {}
        return {"id":gid,"chr":e.get("chromosome",""),"map":e.get("maplocation",""),
                "summary":e.get("summary",""),"start":gi.get("chrstart",""),
                "stop":gi.get("chrstop",""),"exons":gi.get("exoncount",""),
                "link":f"https://www.ncbi.nlm.nih.gov/gene/{gid}"}
    except: return {}

@st.cache_data(show_spinner=False, ttl=86400)
def fetch_alphamissense(uniprot_id: str) -> dict:
    try:
        urls_to_try = [
            f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-aa-substitutions.csv",
        ]
        r = None
        for url in urls_to_try[:1]:
            try:
                r = requests.get(url, timeout=25, headers={"Accept": "text/csv,*/*"})
                if r.status_code == 200 and len(r.text) > 100: break
            except: pass
        if not r or r.status_code != 200 or len(r.text) < 100:
            return {}
        scores = {}
        lines_am = r.text.strip().splitlines()
        for line in lines_am[1:]:
            parts = line.split(",")
            if len(parts) < 3: continue
            try:
                variant = parts[0]
                pathogenicity = float(parts[1])
                am_class = parts[2].strip() if len(parts) > 2 else ""
                pos = int(variant[1:-1])
                alt = variant[-1]
                if pos not in scores: scores[pos] = {}
                scores[pos][alt] = {"score": round(pathogenicity, 3), "class": am_class}
            except: pass
        return scores
    except:
        return {}

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_opentargets(gene_symbol: str) -> dict:
    def _gene_to_ensembl(gene_symbol: str) -> str:
        try:
            r = requests.get(f"https://mygene.info/v3/query?q={gene_symbol}&species=human&fields=ensembl.gene&size=1", timeout=10)
            r.raise_for_status()
            hits = r.json().get("hits", [])
            if not hits: return ""
            ensembl = hits[0].get("ensembl", {})
            if isinstance(ensembl, list): ensembl = ensembl[0]
            return ensembl.get("gene", "")
        except:
            return ""

    try:
        query = """
        query TargetQuery($ensgId: String!) {
          target(ensemblId: $ensgId) {
            id approvedSymbol approvedName
            tractability {
              label modality value
            }
            safety { effects { direction dosing } }
            expressions { tissue { label } rna { value } }
            knownDrugs(size: 10) {
              count rows {
                drug { name id maximumClinicalTrialPhase }
                indication { name }
                mechanismOfAction
              }
            }
            associatedDiseases(size: 10) {
              rows {
                disease { name id }
                score
                datatypes { id score }
              }
            }
          }
        }
        """
        ensembl_id = _gene_to_ensembl(gene_symbol)
        if not ensembl_id: return {}
        r = requests.post(
            "https://api.platform.opentargets.org/api/v4/graphql",
            json={"query": query, "variables": {"ensgId": ensembl_id}},
            headers={"Content-Type": "application/json"}, timeout=20
        )
        r.raise_for_status()
        data = r.json().get("data", {}).get("target", {})
        if not data: return {}
        tractability = {}
        for t in (data.get("tractability") or []):
            if t.get("value"):
                cat = t.get("modality","?")
                tractability[cat] = tractability.get(cat,[]) + [t.get("label","")]
        drugs = []
        for row in (data.get("knownDrugs",{}).get("rows") or []):
            drugs.append({
                "name": row.get("drug",{}).get("name",""),
                "phase": row.get("drug",{}).get("maximumClinicalTrialPhase",0),
                "indication": row.get("indication",{}).get("name",""),
                "mechanism": row.get("mechanismOfAction",""),
                "url": f"https://platform.opentargets.org/drug/{row.get('drug',{}).get('id','')}",
            })
        disease_assoc = []
        for row in (data.get("associatedDiseases",{}).get("rows") or []):
            disease_assoc.append({
                "disease": row.get("disease",{}).get("name",""),
                "score": round(row.get("score",0), 3),
                "url": f"https://platform.opentargets.org/disease/{row.get('disease',{}).get('id','')}/associations",
            })
        expressions = sorted(
            [(e.get("tissue",{}).get("label",""), e.get("rna",{}).get("value",0))
             for e in (data.get("expressions") or []) if e.get("rna",{}).get("value",0) > 0],
            key=lambda x: -x[1]
        )[:10]
        return {
            "ensembl_id": ensembl_id,
            "tractability": tractability,
            "known_drugs": drugs,
            "disease_associations": disease_assoc,
            "top_tissues": expressions,
            "drug_count": data.get("knownDrugs",{}).get("count",0),
            "url": f"https://platform.opentargets.org/target/{ensembl_id}",
        }
    except Exception:
        return {}

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_isoforms(uniprot_id: str) -> list:
    try:
        r = requests.get(f"https://rest.uniprot.org/uniprotkb/{uniprot_id}",
                        headers={"Accept":"application/json"}, timeout=15)
        r.raise_for_status(); data = r.json()
        isoforms = []
        for comment in data.get("comments",[]):
            if comment.get("commentType") == "ALTERNATIVE SEQUENCE":
                for iso in comment.get("isoforms",[]):
                    name = iso.get("name",{}).get("value","")
                    ids  = iso.get("isoformIds",[])
                    note = iso.get("note",{}).get("texts",[{}])[0].get("value","") if iso.get("note") else ""
                    isoforms.append({"name":name,"ids":ids,"note":note,
                                     "disease_relevant":"disease" in note.lower() or "pathogenic" in note.lower()})
        return isoforms
    except: return []
