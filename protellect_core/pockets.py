"""Candidate pockets on the AlphaFold structure (geometry only) and whether disease variants concentrate in them.

Method: LIGSITE-style buriedness (Hendlich et al. 1997, J Mol Graph Model 15:359). Solvent grid points that have protein on
both sides along several scan lines are 'buried'; connected buried points form a candidate pocket. Pockets are ranked by
volume, and the helices lining them and the share of their lining that faces lipid are reported.

What this is NOT: a prediction that a ligand binds there, a druggability score or a binding energy. AlphaFold models have no
ligand, and low-confidence regions give unreliable pockets (the share of low-confidence lining is reported). Treat the
output as places to look at, then test.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
from scipy import ndimage, stats
from scipy.spatial import cKDTree

PROBE = 1.9          # Angstrom: solvent grid points closer than this to an atom are 'protein'
SPACING = 1.0
MAX_SCAN = 12        # Angstrom: how far to look for protein on each side
MIN_HITS = 5         # of 7 scan lines
MIN_POINTS = 25
DIRS = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1), (1, 1, -1), (1, -1, 1), (-1, 1, 1)]


def atoms(pdb_text: str):
    """(coords Nx3, resi N, name N, bfactor N) for heavy atoms; hydrogens skipped."""
    xyz, resi, name, bf = [], [], [], []
    for ln in (pdb_text or "").splitlines():
        if not ln.startswith("ATOM"):
            continue
        el = (ln[76:78].strip() or ln[12:16].strip()[:1]).upper()
        if el == "H":
            continue
        try:
            xyz.append((float(ln[30:38]), float(ln[38:46]), float(ln[46:54]))); resi.append(int(ln[22:26])); name.append(ln[12:16].strip())
            bf.append(float(ln[60:66]) if ln[60:66].strip() else 0.0)
        except ValueError:
            continue
    return np.array(xyz, float).reshape(-1, 3), np.array(resi, int), np.array(name), np.array(bf, float)


def _scan_hits(protein: np.ndarray, solvent: np.ndarray) -> np.ndarray:
    """For every grid point, in how many of the scan directions is there protein on both sides within MAX_SCAN."""
    L = int(MAX_SCAN / SPACING)
    pad = L + 1
    P = np.pad(protein, pad)
    sh = protein.shape
    hits = np.zeros(sh, dtype=np.int8)
    core = tuple(slice(pad, pad + s) for s in sh)
    for d in DIRS:
        sides = []
        for sgn in (1, -1):
            found = np.zeros(sh, dtype=bool)
            for k in range(1, L + 1):
                sl = tuple(slice(pad + sgn * k * d[i], pad + sgn * k * d[i] + sh[i]) for i in range(3))
                found |= P[sl]
            sides.append(found)
        hits += (sides[0] & sides[1]).astype(np.int8)
    return np.where(solvent, hits, 0)


def find_pockets(pdb_text: str, max_pockets: int = 8) -> List[Dict]:
    xyz, resi, name, bf = atoms(pdb_text)
    if len(xyz) < 200:
        return []
    lo = xyz.min(0) - MAX_SCAN * 0.6; hi = xyz.max(0) + MAX_SCAN * 0.6
    axes = [np.arange(lo[i], hi[i] + SPACING, SPACING) for i in range(3)]
    shape = tuple(len(a) for a in axes)
    if np.prod(shape) > 8e6:
        return []
    G = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    tree = cKDTree(xyz)
    dist, _ = tree.query(G, distance_upper_bound=PROBE)
    protein = (dist < PROBE).reshape(shape)
    solvent = ~protein
    hits = _scan_hits(protein, solvent)
    buried = hits >= MIN_HITS
    lab, n = ndimage.label(buried, structure=np.ones((3, 3, 3)))
    if n == 0:
        return []
    sizes = ndimage.sum(buried, lab, index=range(1, n + 1))
    order = [i for i in np.argsort(-sizes) if sizes[i] >= MIN_POINTS][:max_pockets]
    out = []
    # residue burial for the lipid-facing estimate: C-alpha neighbours within 12 A (low = exposed)
    ca_mask = name == "CA"
    ca_xyz, ca_res = xyz[ca_mask], resi[ca_mask]
    ca_tree = cKDTree(ca_xyz)
    nbrs = np.array([len(x) - 1 for x in ca_tree.query_ball_point(ca_xyz, 12.0)]) if len(ca_xyz) else np.array([])
    for rank, i in enumerate(order, 1):
        idx = np.argwhere(lab == i + 1)
        pts = np.stack([axes[0][idx[:, 0]], axes[1][idx[:, 1]], axes[2][idx[:, 2]]], 1)
        near = tree.query_ball_point(pts, 4.0)
        atom_ids = sorted({a for lst in near for a in lst})
        res = sorted({int(resi[a]) for a in atom_ids})
        lining_bf = float(np.mean([bf[a] for a in atom_ids])) if atom_ids else float("nan")
        out.append({"rank": rank, "volume_A3": int(len(pts) * SPACING ** 3), "center": [round(float(c), 1) for c in pts.mean(0)],
                    "residues": res, "mean_burial_hits": float(np.mean(hits[lab == i + 1])), "mean_plddt_lining": round(lining_bf, 1),
                    "low_confidence_share": round(float(np.mean([bf[a] < 70 for a in atom_ids])), 2) if atom_ids else 1.0})
    return out


def annotate(pockets: List[Dict], segments: Optional[Sequence] = None, pdb_text: str = "") -> List[Dict]:
    """Add the helices lining each pocket and the share of lining residues that look lipid-exposed (few C-alpha neighbours)."""
    xyz, resi, name, _ = atoms(pdb_text)
    ca = name == "CA"
    ca_xyz, ca_res = xyz[ca], resi[ca]
    expo = {}
    if len(ca_xyz):
        tree = cKDTree(ca_xyz)
        cnt = np.array([len(x) - 1 for x in tree.query_ball_point(ca_xyz, 12.0)])
        thr = float(np.percentile(cnt, 30))
        expo = {int(r): bool(c <= thr) for r, c in zip(ca_res, cnt)}
    tms = [s for s in (segments or []) if getattr(s, "kind", "") == "TM"]
    for p in pockets:
        helices = []
        for s in tms:
            n = sum(s.start <= r <= s.end for r in p["residues"])
            if n >= 2:
                helices.append(s.name)
        tm_res = [r for r in p["residues"] if any(s.start <= r <= s.end for s in tms)]
        frac = (sum(expo.get(r, False) for r in tm_res) / len(tm_res)) if tm_res else 0.0
        p["helices"] = helices
        p["lipid_exposed_share"] = round(frac, 2)
        p["kind"] = ("membrane-facing candidate (possible allosteric site)" if tms and len(tm_res) >= 4 and frac >= 0.4 else
                     "inside the helical bundle" if tms and len(tm_res) >= 4 else "outside the transmembrane region or topology unknown")
    return pockets


def variants_in_pockets(pocket_residues: Sequence[int], plp_positions: Sequence[int], n_residues: int) -> Dict:
    """Do residues with pathogenic/likely-pathogenic variants fall in the pockets more than chance? Fisher exact on residues."""
    pr = set(int(r) for r in pocket_residues)
    plp = set(int(r) for r in plp_positions if r)
    if not pr or not plp or n_residues <= 0:
        return {"testable": False, "note": "No pocket residues or no pathogenic variants with a position."}
    a = len(pr & plp); b = len(pr - plp); c = len(plp - pr); d = max(n_residues - a - b - c, 0)
    odds, p = stats.fisher_exact([[a, b], [c, d]], alternative="greater")
    return {"testable": True, "plp_in_pockets": a, "plp_total": len(plp), "pocket_residues": len(pr), "odds_ratio": float(odds) if np.isfinite(odds) else float("inf"),
            "p_value": float(p), "enriched": bool(p < 0.05 and a >= 2)}
