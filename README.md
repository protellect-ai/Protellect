# 🔬 Protellect v25 — Fixed
Run: pip install -r requirements.txt && streamlit run app.py

Login: protellect@gmail.com / dev@protellect  (enterprise, unlimited)
Demo:  demo@protellect.com / protellect2024   (free, 5 searches)

To fix GitHub repo: python3 fix_github.py YOUR_GITHUB_TOKEN
Get token: github.com/settings/tokens → New token (classic) → check repo → Generate

Fixes applied vs v25 FINAL:
1. AlphaFold: ATOM check now uses full PDB text (was checking only first 100 chars)
2. ClinVar: genesymbol→gene→gene_name multi-strategy (was single strategy, fails on Streamlit Cloud)
3. UniProt: diseaseCrossReferences handles both singular and plural API response variants
v25 already had: germline_classification.description (correct ClinVar field), diseaseId (correct disease name field)
