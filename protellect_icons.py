"""Protellect SVG icon system."""

SVG_ICONS = {
    "microscope":"<path d='M6 18h8'/><path d='M3 22h18'/><path d='M14 22a7 7 0 1 0 0-14h-1'/><path d='M9 14h2'/><path d='M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z'/><path d='M12 6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3'/>",
    "dna":"<path d='M2 15c6.667-6 13.333 0 20-6'/><path d='M9 22c1.798-1.998 2.518-3.995 2.807-5.993'/><path d='M15 2c-1.798 1.998-2.518 3.995-2.807 5.993'/><path d='m17 6-2.5-2.5'/><path d='m14 8-1-1'/><path d='m7 18 2.5 2.5'/><path d='m3.5 14.5.5.5'/><path d='m20 9 .5.5'/><path d='m6.5 12.5 1 1'/><path d='m16.5 10.5 1 1'/><path d='m10 16 1.5 1.5'/>",
    "pill":"<path d='m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z'/><path d='m8.5 8.5 7 7'/>",
    "chart":"<line x1='12' y1='20' x2='12' y2='10'/><line x1='18' y1='20' x2='18' y2='4'/><line x1='6' y1='20' x2='6' y2='16'/>",
    "target":"<circle cx='12' cy='12' r='10'/><circle cx='12' cy='12' r='6'/><circle cx='12' cy='12' r='2'/>",
    "flask":"<path d='M9 3v6l-3.5 7a2 2 0 0 0 1.8 2.9h9.4a2 2 0 0 0 1.8-2.9L15 9V3'/><path d='M8 3h8'/>",
    "brain":"<path d='M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z'/><path d='M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z'/>",
    "search":"<circle cx='11' cy='11' r='7'/><line x1='21' y1='21' x2='16.65' y2='16.65'/>",
    "book":"<path d='M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z'/><path d='M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z'/>",
    "atom":"<circle cx='12' cy='12' r='1'/><path d='M20.2 20.2c2.04-2.03.02-7.36-4.5-11.9-4.54-4.52-9.87-6.54-11.9-4.5-2.04 2.03-.02 7.36 4.5 11.9 4.54 4.52 9.87 6.54 11.9 4.5Z'/><path d='M15.7 15.7c4.52-4.54 6.54-9.87 4.5-11.9-2.03-2.04-7.36-.02-11.9 4.5-4.52 4.54-6.54 9.87-4.5 11.9 2.03 2.04 7.36.02 11.9-4.5Z'/>",
    "warning":"<path d='m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z'/><line x1='12' y1='9' x2='12' y2='13'/><line x1='12' y1='17' x2='12.01' y2='17'/>",
    "network":"<circle cx='12' cy='12' r='2'/><circle cx='4' cy='4' r='2'/><circle cx='20' cy='4' r='2'/><circle cx='4' cy='20' r='2'/><circle cx='20' cy='20' r='2'/><path d='m5.5 5.5 5 5'/><path d='m18.5 5.5-5 5'/><path d='m5.5 18.5 5-5'/><path d='m18.5 18.5-5-5'/>",
    "globe":"<circle cx='12' cy='12' r='10'/><line x1='2' y1='12' x2='22' y2='12'/><path d='M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z'/>",
    "building":"<rect x='4' y='2' width='16' height='20' rx='2'/><path d='M9 22v-4h6v4'/><path d='M8 6h.01'/><path d='M16 6h.01'/><path d='M12 6h.01'/><path d='M12 10h.01'/><path d='M12 14h.01'/><path d='M16 10h.01'/><path d='M16 14h.01'/><path d='M8 10h.01'/><path d='M8 14h.01'/>",
    "zap":"<polygon points='13 2 3 14 12 14 11 22 21 10 12 10 13 2'/>",
    "activity":"<polyline points='22 12 18 12 15 21 9 3 6 12 2 12'/>",
    "clipboard":"<path d='M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2'/><rect x='8' y='2' width='8' height='4' rx='1'/>",
    "layers":"<polygon points='12 2 2 7 12 12 22 7 12 2'/><polyline points='2 17 12 22 22 17'/><polyline points='2 12 12 17 22 12'/>",
    "user":"<path d='M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2'/><circle cx='12' cy='7' r='4'/>",
    "shield":"<path d='M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'/>",
    "check":"<polyline points='20 6 9 17 4 12'/>",
    "x":"<line x1='18' y1='6' x2='6' y2='18'/><line x1='6' y1='6' x2='18' y2='18'/>",
    "rocket":"<path d='M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z'/><path d='m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z'/><path d='M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0'/><path d='M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5'/>",
    "beaker":"<path d='M4.5 3h15'/><path d='M6 3v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V3'/><path d='M6 14h12'/>",
}

def svg_icon(name, size=18, color="#38bdf8"):
    body = SVG_ICONS.get(name, SVG_ICONS["target"])
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' viewBox='0 0 24 24' "
            f"fill='none' stroke='{color}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' "
            f"style='vertical-align:middle;display:inline-block;flex-shrink:0;'>{body}</svg>")

def _auto_icon_name(title):
    """Pick an icon name from a section title's keywords."""
    t = (title or "").lower()
    rules = [
        (["mutation","variant","genomic","dna","sequenc","clinvar","alphamissense"], "dna"),
        (["drug","pharma","compound","inhibitor","medic","pkpd","admet"], "pill"),
        (["experiment","assay","cascad","follow up","follow-up","wet-lab","wet lab"], "flask"),
        (["explorer","structure","3d","alphafold","fold","protein expl"], "microscope"),
        (["scorecard","metric","analytics","data","stats","score","trend"], "chart"),
        (["target","goal","priority","precision","hit","druggab"], "target"),
        (["brain","neuro","synap","axon","epilep"], "brain"),
        (["paper","publication","literature","abstract","pubmed","semantic"], "book"),
        (["report","intelligen","verdict","summary","ai report"], "book"),
        (["chemistry","molecule","molecular","atomic"], "atom"),
        (["warning","caution","alert","risk","conflict"], "warning"),
        (["interaction","network","string","pathway","partner","interac"], "network"),
        (["population","frequenc","global","world","gnomad","epidemio"], "globe"),
        (["regulator","fda","ema","approval","designation"], "building"),
        (["kinase","phospho","enzyme","cascad"], "zap"),
        (["disease","link","associat","causal","clinical"], "activity"),
        (["search","find","lookup","query","disambig"], "search"),
        (["workspace","history","saved","domain expan","case stud"], "layers"),
        (["patient","cohort","person","trial"], "user"),
        (["regulatory","quality"], "shield"),
        (["roadmap","strategy","launch","pursue"], "rocket"),
    ]
    for kws, name in rules:
        if any(k in t for k in kws): return name
    return "target"