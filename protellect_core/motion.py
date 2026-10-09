"""Collective motions of the AlphaFold structure from an anisotropic network model (ANM).

What this IS: the lowest-frequency mechanical motions of the folded model, computed from the C-alpha geometry alone
(Atilgan et al. 2001, Biophys J 80:505; springs between C-alpha atoms closer than the cutoff). It shows which segments of the
fold are mechanically free to move and in which collective direction, and it often tracks experimentally observed
open/close motions of a domain.

What this is NOT: a prediction of the active state, of ligand-induced change, of a lipid effect or of any kinetics. The
network has no ligand, no membrane and no G protein in it. The viewer says so next to the animation.
"""
from __future__ import annotations

from typing import Dict, List, Optional

MAX_RESIDUES = 700   # 3N x 3N eigen-decomposition; keeps it well under a few seconds
CUTOFF = 15.0        # Angstrom, the standard ANM choice


def ca_trace(pdb_text: str):
    """[(resi, x, y, z)] for chain A C-alpha atoms, in file order; first altloc only."""
    out, seen = [], set()
    for ln in (pdb_text or "").splitlines():
        if not ln.startswith("ATOM") or ln[12:16].strip() != "CA":
            continue
        try:
            resi = int(ln[22:26]); x, y, z = float(ln[30:38]), float(ln[38:46]), float(ln[46:54])
        except ValueError:
            continue
        if resi in seen:
            continue
        seen.add(resi)
        out.append((resi, x, y, z))
    return out


def normal_modes(pdb_text: str, n_modes: int = 3, cutoff: float = CUTOFF) -> Optional[Dict]:
    """Lowest non-trivial ANM modes. Returns None when the structure is missing, too small or too large."""
    try:
        import numpy as np
    except Exception:
        return None
    ca = ca_trace(pdb_text)
    n = len(ca)
    if n < 30 or n > MAX_RESIDUES:
        return None
    res = [c[0] for c in ca]
    xyz = np.array([[c[1], c[2], c[3]] for c in ca], dtype=float)
    d = xyz[:, None, :] - xyz[None, :, :]
    r2 = (d ** 2).sum(-1)
    contact = (r2 < cutoff ** 2) & (r2 > 0)
    H = np.zeros((3 * n, 3 * n))
    for i, j in zip(*np.nonzero(np.triu(contact, 1))):
        v = d[i, j]
        blk = -np.outer(v, v) / r2[i, j]
        H[3 * i:3 * i + 3, 3 * j:3 * j + 3] = blk
        H[3 * j:3 * j + 3, 3 * i:3 * i + 3] = blk
        H[3 * i:3 * i + 3, 3 * i:3 * i + 3] -= blk
        H[3 * j:3 * j + 3, 3 * j:3 * j + 3] -= blk
    w, U = np.linalg.eigh(H)
    keep = [k for k in range(len(w)) if w[k] > 1e-6][:max(1, n_modes)]   # drops the six rigid-body zero modes
    if not keep:
        return None
    modes: List[Dict] = []
    msf = np.zeros(n)
    for rank, k in enumerate(keep):
        vec = U[:, k].reshape(n, 3)
        mag = np.linalg.norm(vec, axis=1)
        vec = vec / (mag.max() or 1.0)                      # largest C-alpha move = 1
        msf += (np.linalg.norm(U[:, k].reshape(n, 3), axis=1) ** 2) / w[k]
        modes.append({"mode": rank + 1, "eigenvalue": float(w[k]), "vec": [[round(float(a), 3) for a in row] for row in vec]})
    msf = msf / (msf.max() or 1.0)
    return {"resi": res, "modes": modes, "mobility": [round(float(m), 3) for m in msf], "n": n, "cutoff": cutoff,
            "method": "Anisotropic network model on C-alpha atoms (Atilgan et al. 2001)"}
