"""Binding kinetics from numbers YOU measured (SPR, BLI, radioligand association/dissociation).

This is arithmetic on your inputs, not a prediction. Protellect cannot compute kon or koff for an orphan receptor: that needs
the ligand-bound structure and long molecular dynamics, which are not available here. Use this to turn a measured pair of
rates into the quantities people compare (Kd, residence time, occupancy, time to equilibrium), and to plan the time points
of the next experiment.
"""
from __future__ import annotations

import math
from typing import Dict, Optional


def kinetics(kon: float, koff: float, conc: Optional[float] = None) -> Dict:
    """kon in 1/(M*s), koff in 1/s, conc in M. Returns derived quantities, or raises ValueError on non-positive input."""
    kon, koff = float(kon), float(koff)
    if not (kon > 0 and koff > 0):
        raise ValueError("kon and koff must both be greater than zero")
    kd = koff / kon
    out = {"Kd_M": kd, "residence_time_s": 1.0 / koff, "half_life_s": math.log(2) / koff}
    if conc is not None and float(conc) > 0:
        c = float(conc)
        kobs = kon * c + koff
        out.update({"occupancy": c / (c + kd), "kobs_per_s": kobs, "t_half_assoc_s": math.log(2) / kobs, "t_95pct_equilibrium_s": math.log(20) / kobs})
    return out


def fmt_time(s: float) -> str:
    if s < 1: return f"{s * 1000:.0f} ms"
    if s < 120: return f"{s:.1f} s"
    if s < 7200: return f"{s / 60:.1f} min"
    return f"{s / 3600:.1f} h"


def fmt_molar(m: float) -> str:
    for scale, unit in ((1.0, "M"), (1e-3, "mM"), (1e-6, "µM"), (1e-9, "nM"), (1e-12, "pM")):
        if m >= scale:
            return f"{m / scale:.3g} {unit}"
    return f"{m / 1e-15:.3g} fM"


def reading(res: Dict) -> str:
    """Plain statement of what the numbers mean for the experiment, with the standard caveat on equilibrium."""
    rt = res["residence_time_s"]
    lines = [f"Kd = {fmt_molar(res['Kd_M'])}; a bound ligand stays on for about {fmt_time(rt)} (half-life {fmt_time(res['half_life_s'])})."]
    if "t_95pct_equilibrium_s" in res:
        lines.append(f"At your concentration, binding reaches 95% of equilibrium after about {fmt_time(res['t_95pct_equilibrium_s'])}, so incubate at least that long before reading an endpoint; a shorter incubation underestimates affinity, most for slow-off ligands.")
    if rt > 600:
        lines.append("A residence time of this length means washout experiments and pre-incubation matter: a short wash will not remove it.")
    return " ".join(lines)
