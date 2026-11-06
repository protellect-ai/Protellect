"""Compare two conformations of the same receptor (for example an inactive and an active structure or model) and morph between them.

Inputs are two PDB texts that YOU supply (RCSB structures, GPCRdb models, your own predictions). The structures are superposed
on their shared C-alpha atoms (Kabsch 1976), per-residue displacement is measured, and the viewer interpolates linearly
between the two end states.

What this is NOT: a simulation of the transition. The frames between the end states are straight-line interpolation, not a
pathway, and the end states are only as good as the structures you give it. Protellect does not predict the active state.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np

AA3 = {"ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
       "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V"}


def ca_atoms(pdb_text: str, chain: Optional[str] = None):
    """{resi: (xyz, one-letter)} for C-alpha atoms; first chain found unless one is named; first altloc only."""
    out, first = {}, None
    for ln in (pdb_text or "").splitlines():
        if not (ln.startswith("ATOM") and ln[12:16].strip() == "CA"):
            continue
        if ln[16] not in (" ", "A"):
            continue
        ch = ln[21]
        first = first or ch
        if (chain or first) != ch:
            continue
        try:
            r = int(ln[22:26]); xyz = np.array([float(ln[30:38]), float(ln[38:46]), float(ln[46:54])])
        except ValueError:
            continue
        out.setdefault(r, (xyz, AA3.get(ln[17:20].strip().upper(), "X")))
    return out


def kabsch(P: np.ndarray, Q: np.ndarray):
    """Rotation R and translation so that (Q - cQ) @ R + cP superposes Q onto P. Returns (R, cP, cQ)."""
    cP, cQ = P.mean(0), Q.mean(0)
    H = (Q - cQ).T @ (P - cP)
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(U @ Vt))
    D = np.diag([1, 1, d])
    return U @ D @ Vt, cP, cQ


def compare_states(pdb_a: str, pdb_b: str, offset_b: int = 0, core_percentile: float = 70.0) -> Dict:
    """Superpose B onto A (iteratively, on the best-matching core so a moving helix does not drag the fit) and report displacement.
    offset_b is added to B's residue numbers to match A's numbering."""
    A, B0 = ca_atoms(pdb_a), ca_atoms(pdb_b)
    B = {r + offset_b: v for r, v in B0.items()}
    shared = sorted(set(A) & set(B))
    if len(shared) < 50:
        raise ValueError(f"Only {len(shared)} residues are shared between the two structures. Check that they are the same protein and, if the numbering differs, set the residue offset.")
    ident = float(np.mean([A[r][1] == B[r][1] for r in shared if A[r][1] != "X" and B[r][1] != "X"] or [0]))
    P = np.array([A[r][0] for r in shared]); Q = np.array([B[r][0] for r in shared])
    use = np.ones(len(shared), bool)
    for _ in range(5):                                           # iterative core fit
        R, cP, cQ = kabsch(P[use], Q[use])
        Qa = (Q - cQ) @ R + cP
        d = np.linalg.norm(Qa - P, axis=1)
        thr = np.percentile(d, core_percentile)
        new = d <= thr
        if (new == use).all():
            break
        use = new
    disp = Qa - P
    mag = np.linalg.norm(disp, axis=1)
    rmsd_all = float(np.sqrt((mag ** 2).mean())); rmsd_core = float(np.sqrt((mag[use] ** 2).mean()))
    warn = []
    if ident < 0.8:
        warn.append(f"Only {ident * 100:.0f}% of shared residue positions have the same amino acid: the structures may be different proteins or numbered differently; use the residue offset.")
    if len(shared) < 0.6 * min(len(A), len(B)):
        warn.append("The structures overlap on fewer than 60% of their residues, so the comparison covers only part of the receptor.")
    if rmsd_all < 0.5:
        warn.append("The two structures are almost identical (RMSD under 0.5 A); there is no conformational difference to show.")
    return {"resi": shared, "disp": [[round(float(x), 3) for x in v] for v in disp], "magnitude": [round(float(m), 2) for m in mag],
            "rmsd_all": rmsd_all, "rmsd_core": rmsd_core, "identity": ident, "n_shared": len(shared), "warnings": warn}


def per_segment(cmp: Dict, segments: Sequence) -> List[Dict]:
    """Mean and maximum C-alpha displacement in each topology segment (TM helices first)."""
    res = np.array(cmp["resi"]); mag = np.array(cmp["magnitude"])
    rows = []
    for s in segments or []:
        m = (res >= s.start) & (res <= s.end)
        if m.sum() >= 3:
            rows.append({"segment": s.name, "kind": s.kind, "mean_A": round(float(mag[m].mean()), 1), "max_A": round(float(mag[m].max()), 1), "residues": int(m.sum())})
    return rows


def morph_mode(cmp: Dict, label: str) -> Dict:
    """A viewer 'mode' that carries absolute displacements in Angstrom (amp 1 = reach the second structure)."""
    return {"mode": label, "kind": "state", "amp": 1.0, "eigenvalue": None, "vec": cmp["disp"]}


def add_state_mode(motion: Optional[Dict], cmp: Dict, label: str) -> Dict:
    """Append the state morph to the viewer's motion payload (creating one if there are no normal modes). Residues not in the comparison stay still."""
    resi_all = list(motion["resi"]) if motion else list(cmp["resi"])
    pos = {r: i for i, r in enumerate(cmp["resi"])}
    vec = [cmp["disp"][pos[r]] if r in pos else [0.0, 0.0, 0.0] for r in resi_all]
    mode = {"mode": label, "kind": "state", "amp": 1.0, "eigenvalue": None, "vec": vec}
    if motion:
        out = dict(motion); out["modes"] = list(motion["modes"]) + [mode]
        return out
    mg = np.array([np.linalg.norm(v) for v in vec]); mg = mg / (mg.max() or 1.0)
    return {"resi": resi_all, "modes": [mode], "mobility": [round(float(x), 3) for x in mg], "n": len(resi_all), "cutoff": None, "method": "Two supplied structures"}


def rotation_into(pdb_view: str, pdb_a: str, offset_a: int = 0) -> Optional[np.ndarray]:
    """Rotation that takes vectors from structure A's frame into the frame of the structure being displayed (the viewer's model).
    None if they share fewer than 50 residues."""
    V = ca_atoms(pdb_view)
    A = {r + offset_a: v for r, v in ca_atoms(pdb_a).items()}
    shared = sorted(set(V) & set(A))
    if len(shared) < 50:
        return None
    P = np.array([V[r][0] for r in shared]); Q = np.array([A[r][0] for r in shared])
    use = np.ones(len(shared), bool)
    for _ in range(5):
        R, cP, cQ = kabsch(P[use], Q[use])
        d = np.linalg.norm((Q - cQ) @ R + cP - P, axis=1)
        new = d <= np.percentile(d, 70)
        if (new == use).all():
            break
        use = new
    return R


def rotate_comparison(cmp: Dict, R: np.ndarray) -> Dict:
    out = dict(cmp)
    out["disp"] = [[round(float(x), 3) for x in (np.array(v) @ R)] for v in cmp["disp"]]
    return out
