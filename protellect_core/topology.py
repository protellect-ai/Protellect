"""The receptor's real topology, conserved motifs and per-segment variant burden, built from UniProt's annotated helices and the sequence.

Nothing here is drawn from a template: segment boundaries are UniProt's transmembrane features, motifs are found by pattern search in the actual
sequence (and only reported if found), and variant counts come from the loaded ClinVar records.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .adapters import Bundle

LOOPS = ["ICL1", "ECL1", "ICL2", "ECL2", "ICL3", "ECL3"]      # standard 7TM topology: N-terminus outside; TM1 runs out to in


@dataclass
class Segment:
    name: str
    kind: str          # TM | ECL | ICL | N-term | C-term
    start: int
    end: int
    side: str          # extracellular | intracellular | membrane

    @property
    def length(self) -> int:
        return max(0, self.end - self.start + 1)

    def contains(self, pos: Optional[int]) -> bool:
        return pos is not None and self.start <= pos <= self.end


def topology(b: Bundle) -> Optional[List[Segment]]:
    """Seven annotated transmembrane helices -> the full segment list; anything else -> None (the caller falls back to a domain map)."""
    tms = sorted([d for d in b.domains if d["type"] == "Transmembrane"], key=lambda d: d["start"])
    if len(tms) != 7 or b.length <= 0:
        return None
    segs = [Segment("N-terminus", "N-term", 1, tms[0]["start"] - 1, "extracellular")]
    for i, t in enumerate(tms):
        segs.append(Segment(f"TM{i + 1}", "TM", t["start"], t["end"], "membrane"))
        if i < 6:
            nm = LOOPS[i]
            segs.append(Segment(nm, nm[:3], t["end"] + 1, tms[i + 1]["start"] - 1, "intracellular" if nm.startswith("ICL") else "extracellular"))
    segs.append(Segment("C-terminus", "C-term", tms[6]["end"] + 1, b.length, "intracellular"))
    return segs


def segment_of(segs: Optional[List[Segment]], pos: Optional[int]) -> str:
    for s in segs or []:
        if s.contains(pos):
            return s.name
    return ""


def motifs(b: Bundle, segs: Optional[List[Segment]]) -> List[dict]:
    """Class A conserved motifs found in the real sequence, each searched only where it belongs. Absent motifs are not reported."""
    if not segs or not b.sequence:
        return []
    seg = {s.name: s for s in segs}
    out = []
    spec = [("D/ERY (ionic lock, TM3 end)", r"[DE]R[YFWHC]", seg["TM3"].end - 6, seg["TM3"].end + 8, "TM3 / ICL2"),
            ("CWxP (toggle switch, TM6)", r"CW.P", seg["TM6"].start, seg["TM6"].end, "TM6"),
            ("NPxxY (TM7)", r"NP..Y", seg["TM7"].start, seg["TM7"].end, "TM7")]
    for name, pat, lo, hi, where in spec:
        window = b.sequence[max(lo - 1, 0):hi]
        m = re.search(pat, window)
        if m:
            s = max(lo - 1, 0) + m.start() + 1
            out.append({"motif": name, "start": s, "end": s + len(m.group(0)) - 1, "seq": m.group(0), "where": where})
    return out


def segment_stats(b: Bundle, segs: Optional[List[Segment]]) -> Dict[str, dict]:
    out = {}
    for s in segs or []:
        vs = [v for v in b.variants if s.contains(v.pos)]
        am = [max(d["score"] for d in b.am[p].values()) for p in range(s.start, s.end + 1) if p in b.am and b.am[p]]
        out[s.name] = {"plp": sum(v.is_plp for v in vs), "vus": sum(v.significance == "uncertain" for v in vs), "n": len(vs), "am_mean": (sum(am) / len(am)) if am else None}
    return out
