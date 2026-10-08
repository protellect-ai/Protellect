"""Generate the SYNTHETIC cancer-immune GPCRome test case. Run: python make_example.py

Every expression value is invented. What is real is only (a) the receptor and marker-gene names, (b) the curated primary G-protein couplings of the
characterised receptors (unverified annotations), and (c) the kind of question being asked. The structure planted in the numbers is for testing the
software and says nothing about biology.
"""
import json
import numpy as np
import pandas as pd

rng = np.random.default_rng(20240607)
CTX = ["Tumor epithelial (HPV+)", "Tumor epithelial (HPV-)", "CAF fibroblast", "Endothelial", "Pericyte", "CD8 T effector", "CD8 T exhausted", "CD4 T cell", "Treg", "NK cell",
       "B cell", "Plasma cell", "Macrophage", "Dendritic cell", "Neutrophil", "Monocyte"]
P = {  # context profiles (arbitrary units)
    "Q": [90, 95, 70, 60, 55, 6, 5, 4, 3, 4, 3, 3, 8, 6, 5, 6],
    "I": [5, 6, 10, 12, 8, 85, 70, 90, 75, 85, 70, 35, 30, 40, 25, 30],
    "S": [20, 18, 15, 10, 12, 25, 100, 30, 35, 30, 15, 8, 70, 60, 55, 65],
    "M": [2, 3, 4, 5, 3, 6, 5, 5, 6, 4, 3, 3, 96, 10, 12, 20],
    "T": [95, 90, 12, 8, 5, 3, 3, 3, 3, 3, 3, 3, 5, 3, 3, 4],
    "EXH": [3, 3, 3, 3, 3, 15, 95, 10, 40, 20, 3, 3, 5, 3, 3, 4],
    "YAP": [85, 90, 80, 40, 50, 3, 3, 3, 3, 3, 3, 3, 10, 5, 4, 6],
    "TREG": [2, 2, 2, 2, 2, 10, 15, 25, 95, 8, 2, 2, 3, 3, 3, 3],
    "CYT": [2, 2, 2, 2, 2, 90, 60, 10, 10, 95, 2, 5, 4, 4, 10, 6],
    "HYP": [80, 85, 40, 30, 20, 10, 15, 10, 10, 10, 10, 10, 35, 15, 25, 20],
    "PGE": [60, 95, 40, 10, 10, 5, 5, 5, 5, 5, 5, 5, 70, 30, 30, 40],        # PTGS2 / PTGES: tumour and macrophage
    "CD73": [60, 70, 85, 80, 60, 5, 5, 5, 5, 5, 5, 5, 10, 5, 5, 5],
    "CD39": [20, 25, 20, 20, 15, 10, 90, 10, 80, 10, 5, 5, 20, 10, 10, 10],
    "CXCL12": [10, 12, 100, 35, 40, 3, 3, 3, 3, 3, 4, 5, 6, 3, 3, 4],
    "S_EXH": [15, 15, 12, 8, 10, 20, 100, 25, 30, 25, 10, 6, 40, 30, 28, 32],
}
GQ = "CHRM3 HTR2A AGTR1 EDNRA HRH1 GRM5 P2RY2 F2R CASR FFAR1".split()
GI = "CXCR4 CCR5 CCR4 CXCR3 CCR7 CXCR2 S1PR1 P2RY12 ADORA3 CNR2 DRD2 OPRM1 GRM2 HTR1A".split()
GS = "ADRB2 ADORA2A PTGER4 PTGER2 DRD1 GLP1R MC1R VIPR1 GPBAR1 TSHR".split()
rows = {}


def gene(name, mod, other=None, mix=0.12, sigma=0.25):
    base = np.array(P[mod], float) * rng.uniform(0.6, 1.4)
    if other:
        base = (1 - mix) * base + mix * np.array(P[other], float)
    rows[name] = np.maximum(0.0, base * np.exp(rng.normal(0, sigma, len(CTX))) + rng.uniform(0, 2, len(CTX)))


for g in GQ: gene(g, "Q", rng.choice(["I", "S"]))
for g in GI: gene(g, "I", rng.choice(["Q", "S"]))
for g in GS: gene(g, "S_EXH" if g in ("ADRB2", "ADORA2A", "PTGER4", "PTGER2") else "S", rng.choice(["Q", "I"]))
gene("GPR87", "YAP", "Q", 0.2); gene("GPRC5A", "T", "Q", 0.35); gene("GPR160", "T")
gene("GPR174", "I"); gene("GPR65", "S"); gene("GPR132", "M")
gene("GPR171", "EXH", sigma=0.2); gene("GPR20", "TREG", sigma=0.2)
for g in ("GPR35", "GPR37", "GPR19", "GPR82"):                       # noise controls: no structure at all
    rows[g] = rng.uniform(1, 60, len(CTX))
# marker programs
for g in "PDCD1 HAVCR2 LAG3 TIGIT TOX CTLA4".split(): gene(g, "EXH", sigma=0.2)
gene("ENTPD1", "CD39", sigma=0.2)
for g in "CCN1 CCN2 ANKRD1 AXL AMOTL2".split(): gene(g, "YAP", sigma=0.2)
for g in "FOXP3 IL2RA IKZF2".split(): gene(g, "TREG", sigma=0.2)
for g in "GZMB PRF1 IFNG NKG7 GZMA GNLY".split(): gene(g, "CYT", sigma=0.2)
for g in "CA9 VEGFA SLC2A1 LDHA BNIP3 PGK1".split(): gene(g, "HYP", sigma=0.25)
# oncocrine producers
gene("PTGS2", "PGE", sigma=0.2); gene("PTGES", "PGE", sigma=0.2); gene("NT5E", "CD73", sigma=0.2); gene("CXCL12", "CXCL12", sigma=0.2)
gene("TP53", "Q", "T", 0.5); gene("PTPRC", "I", "S"); gene("EPCAM", "T"); gene("CD8A", "I")
mat = pd.DataFrame(rows, index=CTX).T.round(2)
mat.index.name = "gene"
mat.reset_index().to_csv("gpcrome_matrix.csv", index=False)

# differential table, in the three-column format: exhausted vs effector CD8 T cells (derived from the matrix; the p-values are invented)
ex, ef = mat["CD8 T exhausted"], mat["CD8 T effector"]
lfc = np.log2((ex + 1) / (ef + 1))
diff = pd.DataFrame({"gene": mat.index, "log2FoldChange": lfc.round(3).to_numpy(), "padj": np.clip(10 ** (-3.5 * np.abs(lfc.to_numpy())) * rng.uniform(0.3, 3, len(lfc)), 1e-12, 1).round(8)})
diff.to_csv("gpcrome_differential.csv", index=False)

orphans = ["GPR87", "GPRC5A", "GPR160", "GPR174", "GPR65", "GPR132", "GPR171", "GPR20", "GPR35", "GPR37", "GPR19", "GPR82"]
skip = set(GQ + GI + GS) | set(orphans)
reg = [{"gene": g, "status": "orphan" if g in orphans else "characterized", "source": "DEMO status for the synthetic example only", "note": "load the Guide to Pharmacology file for real statuses"} for g in list(GQ + GI + GS) + orphans]
pd.DataFrame(reg).to_csv("gpcrome_registry.csv", index=False)

alt = [("GPR87", "HNSC", 0.0, 0.18, 0.0), ("GPR87", "LUSC", 0.0, 0.31, 0.0), ("GPR87", "BRCA", 0.0, 0.02, 0.0), ("GPR160", "HNSC", 0.0, 0.07, 0.0), ("PTGER4", "SKCM", 0.03, 0.01, 0.0),
       ("GPRC5A", "HNSC", 0.02, 0.0, 0.12), ("CXCR4", "SKCM", 0.01, 0.0, 0.0)]
pd.DataFrame(alt, columns=["gene", "cancer_type", "mutation_freq", "amp_freq", "del_freq"]).to_csv("gpcrome_alterations.csv", index=False)

truth = {
    "coupling": {"GPR87": "Gq", "GPR174": "Gi", "GPR65": "Gs"},
    "no_call": ["GPR35", "GPR37", "GPR19", "GPR82"],
    "top_context": {"GPR87": ["Tumor epithelial (HPV+)", "Tumor epithelial (HPV-)", "CAF fibroblast"], "GPR160": ["Tumor epithelial (HPV+)", "Tumor epithelial (HPV-)"], "GPR132": ["Macrophage"],
                    "GPR174": ["CD8 T effector", "CD4 T cell", "Treg", "NK cell", "B cell"]},
    "enrichment": {"Gs": "up", "Gi": "down"},
    "programs": {"GPR87": "YAP/TAZ targets", "GPR171": "T-cell exhaustion", "GPR20": "Regulatory T cell"},
    "oncocrine": [{"ligand": "Prostaglandin E2", "receptor": "PTGER4", "target": "CD8 T exhausted"}, {"ligand": "CXCL12", "receptor": "CXCR4", "source": "CAF fibroblast"},
                  {"ligand": "Adenosine", "receptor": "ADORA2A", "target": "CD8 T exhausted"}],
    "alteration": {"GPR87": "HNSC"},
}
json.dump(truth, open("truth.json", "w"), indent=1)
print("wrote", mat.shape, "matrix;", len(diff), "differential rows;", len(reg), "registry rows;", len(alt), "alteration rows")
