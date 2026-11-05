import math
from protellect_core.motion import normal_modes, ca_trace


def helix_pdb(n=80, extra=""):
    lines = []
    for i in range(n):
        a = i * 100 * math.pi / 180
        x, y, z = 2.3 * math.cos(a), 2.3 * math.sin(a), 1.5 * i
        lines.append("ATOM  %5d  CA  ALA A%4d    %8.3f%8.3f%8.3f  1.00 90.00           C" % (i + 1, i + 1, x, y, z))
    return "\n".join(lines) + extra


def test_modes_are_nontrivial_and_ends_move_most():
    r = normal_modes(helix_pdb(), n_modes=3)
    assert r and len(r["modes"]) == 3 and r["n"] == 80
    assert all(m["eigenvalue"] > 1e-6 for m in r["modes"])           # the six rigid-body modes are dropped
    mob = r["mobility"]
    assert max(mob) == 1.0 and min(mob[35:45]) < min(mob[0], mob[-1])  # a free rod flexes at its ends, not its middle
    assert len(r["modes"][0]["vec"]) == 80 and max(abs(c) for row in r["modes"][0]["vec"] for c in row) <= 1.0001


def test_missing_small_or_huge_structure_returns_none_not_a_crash():
    assert normal_modes("") is None and normal_modes(None) is None
    assert normal_modes(helix_pdb(10)) is None
    assert normal_modes(helix_pdb(701)) is None


def test_garbled_lines_are_skipped():
    assert len(ca_trace(helix_pdb(40, "\nATOM  junk  CA  ALA A  xx\n"))) == 40
