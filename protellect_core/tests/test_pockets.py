import math
import numpy as np
from protellect_core.pockets import find_pockets, annotate, variants_in_pockets, atoms


def pdb_from(points, bf=90.0):
    lines = []
    for i, (x, y, z) in enumerate(points):
        lines.append("ATOM  %5d  CA  ALA A%4d    %8.3f%8.3f%8.3f  1.00 %5.1f           C" % (i + 1, i + 1, x, y, z, bf))
    return "\n".join(lines)


def shell(radius, spacing=2.6, open_cone=None):
    pts = []
    n = int(4 * math.pi * radius ** 2 / spacing ** 2)
    ga = math.pi * (3 - 5 ** 0.5)
    for i in range(n):
        zc = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - zc * zc); th = ga * i
        x, y, z = radius * r * math.cos(th), radius * r * math.sin(th), radius * zc
        if open_cone is not None and zc > open_cone:
            continue
        pts.append((x, y, z))
    return pts


def test_cup_has_a_pocket_and_flat_plate_does_not():
    cup = pdb_from(shell(11, open_cone=0.8))
    pk = find_pockets(cup)
    assert pk and pk[0]["volume_A3"] > 300 and abs(pk[0]["center"][0]) < 3 and abs(pk[0]["center"][1]) < 3
    plate = pdb_from([(x * 2.8, y * 2.8, 0) for x in range(-12, 13) for y in range(-12, 13)])
    assert not find_pockets(plate) or find_pockets(plate)[0]["volume_A3"] < pk[0]["volume_A3"] / 4


def test_pocket_lining_residues_and_low_confidence_flag():
    pk = find_pockets(pdb_from(shell(11, open_cone=0.8), bf=55.0))
    assert pk and len(pk[0]["residues"]) > 10 and pk[0]["low_confidence_share"] == 1.0


def test_tiny_or_empty_structure_gives_nothing():
    assert find_pockets("") == [] and find_pockets(pdb_from([(0, 0, 0), (3, 0, 0)])) == []


def test_annotation_uses_helices():
    class S:  # minimal segment
        def __init__(self, n, k, a, b): self.name, self.kind, self.start, self.end = n, k, a, b
    cup = pdb_from(shell(11, open_cone=0.8))
    pk = find_pockets(cup)
    segs = [S("TM1", "TM", 1, 60), S("TM2", "TM", 61, 120)]
    pk = annotate(pk, segs, cup)
    assert "helices" in pk[0] and 0 <= pk[0]["lipid_exposed_share"] <= 1 and pk[0]["kind"]


def test_variant_enrichment_test_is_directional_and_guarded():
    pocket = list(range(100, 130))
    enriched = variants_in_pockets(pocket, list(range(100, 112)) + [10, 20, 30, 400], 400)
    assert enriched["enriched"] and enriched["odds_ratio"] > 5
    random_like = variants_in_pockets(pocket, [5, 50, 150, 220, 300, 350], 400)
    assert not random_like["enriched"]
    assert variants_in_pockets([], [1], 100)["testable"] is False
