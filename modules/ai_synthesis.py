# modules/ai_synthesis.py
from __future__ import annotations
import requests
import json
import re

def ai_synthesize(
    gene: str, pdata: dict, cv: dict, gi: dict,
    papers: list, abstracts: list, string_data: list,
    gnomad: dict, trials: list, drugs: list,
    scored: list, gpcr_assessment: dict, goal: str,
    assay_text: str = ""
) -> dict:
    """
    Use Claude API to synthesize ALL fetched data into intelligent insights.
    """
    from modules.data_processing import g_diseases, g_name, g_func

    diseases_summary = "; ".join(d.get("name", "") for d in g_diseases(pdata)[:8]) or "None found"
    top_variants = [
        f"{v.get('variant_name', v.get('title', ''))[:50]} ({v.get('sig', '?')}, ML={v.get('ml', 0):.2f})"
        for v in scored[:10]
    ]
    paper_summaries = [
        f"[{classify_experiment_type(p.get('abstract', ''), p.get('title', ''))}] "
        f"{p.get('authors', '')} ({p.get('year', '')}): {p.get('title', '')[:100]}. "
        f"Abstract: {p.get('abstract', '')[:400]}"
        for p in abstracts[:8]
    ]
    string_summary = ", ".join(f"{i['partner']} (score={i['score']})" for i in string_data[:8]) if string_data else "No interaction data"

    context = f"""
You are a biomedical research intelligence engine. You have been given ALL of the following factual data about the protein {gene}. Your job is to reason about this data and produce structured insights. You MUST NOT invent any information not present in the data below.

=== PROTEIN DATA ===
Gene: {gene}
UniProt: {pdata.get('primaryAccession', '')}
Name: {g_name(pdata)}
Function: {g_func(pdata)[:600]}
Length: {pdata.get('sequence', {}).get('length', '')} amino acids
Organism: {pdata.get('organism', {}).get('scientificName', '')}

=== DISEASE ASSOCIATIONS (UniProt) ===
{diseases_summary}

=== CLINVAR DATA ===
Total variants: {cv.get('summary', {}).get('total', 0)}
Pathogenic/LP: {gi.get('n_pathogenic', 0)}
VUS: {gi.get('n_vus', 0)}
Benign: {gi.get('n_benign', 0)}
Genomic integrity verdict: {gi.get('verdict', '')}
Pathogenic density: {gi.get('density', 0) * 100:.2f}%
GPCR assessment: {gpcr_assessment.get('type', '')} — {gpcr_assessment.get('label', '')}

=== TOP PATHOGENIC VARIANTS ===
{chr(10).join(top_variants) if top_variants else 'None'}

=== POPULATION GENETICS (gnomAD) ===
pLI (loss-of-function intolerance): {gnomad.get('pLI', 'not available')}
o/e LoF: {gnomad.get('oe_lof', 'not available')}
o/e Missense: {gnomad.get('oe_mis', 'not available')}

=== PROTEIN INTERACTIONS (STRING, score>700) ===
{string_summary}

=== PUBLISHED EXPERIMENTS (from PubMed abstracts) ===
{chr(10).join(paper_summaries) if paper_summaries else 'No abstracts available'}

=== DRUG-GENE INTERACTIONS (DGIdb) ===
{', '.join(d['drug'] + ' (' + d['type'] + ')' for d in drugs[:8]) if drugs else 'None found'}

=== ACTIVE CLINICAL TRIALS ===
{chr(10).join(t['title'][:80] + ' [' + t['status'] + ']' for t in trials[:5]) if trials else 'None found'}

=== RESEARCHER GOAL ===
{goal or 'General research'}

=== WET LAB ASSAY DATA (if provided) ===
{assay_text or 'None provided'}

=== YOUR TASK ===
Based on the above data AND your knowledge of current biomedical literature, produce a JSON response:

{{
  "one_line_verdict": "One sentence: pursue or not, and why, based on genetics",
  "executive_summary": "3-4 sentences for a VC/investor audience. Plain language.",
  "organism_note": "State clearly: human or non-human protein, and implications",
  "experiments_done": [
    {{"type": "category", "finding": "what was found", "gap": "what was not tested", "pmid": "if available"}}
  ],
  "experiments_to_do": [
    {{"priority": "HIGH/MEDIUM/LOW", "name": "experiment name", "rationale": "why", "hypothesis": "testable prediction", "cost": "estimate", "timeline": "estimate"}}
  ],
  "interaction_insights": "What do the STRING interactions tell us about pathway context?",
  "population_genetics_interpretation": "What does pLI/gnomAD tell us about essentiality?",
  "drug_opportunity": "Based on DGIdb and disease data, what is the therapeutic opportunity?",
  "clinical_translation": "What do clinical trials suggest?",
  "assay_interpretation": "If assay data provided, what does it suggest?",
  "key_unknowns": ["unknown1", "unknown2"],
  "confidence": "HIGH/MEDIUM/LOW",
  "warning_flags": ["any red flags in the data"],
  "cure_hypotheses": [
    {{
      "disease": "specific disease name",
      "approach": "specific therapeutic modality",
      "mechanism": "molecular mechanism grounded in variant data",
      "key_experiment": "decisive experiment to test this",
      "prediction": "expected result if hypothesis correct",
      "citation_basis": "published precedent"
    }}
  ],
  "literature_precedents": [
    {{"finding": "what was shown", "relevance": "why it matters", "source": "author/journal/year"}}
  ]
}}
"""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": st.secrets.get("ANTHROPIC_API_KEY", "")},
            json={
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": context}],
            },
            timeout=60
        )
        if response.status_code == 200:
            content_blocks = response.json().get("content", [])
            raw_parts = []
            for block in content_blocks:
                if block.get("type") == "text":
                    raw_parts.append(block["text"])
            raw = " ".join(raw_parts)
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except Exception:
                    pass
            return {"executive_summary": raw[:800] if raw else "Analysis complete.", "confidence": "MEDIUM"}
        else:
            return {"executive_summary": f"AI synthesis unavailable (API error). All other data is available above.", "confidence": "N/A"}
    except Exception as e:
        return {"executive_summary": f"AI synthesis unavailable: {str(e)[:100]}.", "confidence": "N/A"}


def classify_experiment_type(abstract: str, title: str) -> str:
    text = (title + " " + abstract).lower()
    if any(k in text for k in ["cryo-em", "crystal structure", "x-ray", "nmr structure", "alphafold", "structural"]):
        return "🏗️ Structural"
    if any(k in text for k in ["crispr", "knockout", "knock-in", "knockdown", "sirna", "shrna"]):
        return "🔬 CRISPR/Genetic"
    if any(k in text for k in ["mouse", "rat", "zebrafish", "in vivo", "xenograft", "animal model"]):
        return "🐭 In Vivo"
    if any(k in text for k in ["clinical trial", "patient", "cohort", "clinical study", "human subject"]):
        return "👥 Clinical"
    return "📄 Other"
