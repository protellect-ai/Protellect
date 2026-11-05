import math
import numpy as np
import pytest
from protellect_core.states import compare_states, per_segment, add_state_mode, kabsch
from protellect_core.tests.test_motion import helix_pdb


def rot(pdb, angle, shift=(5, -3, 8), move=None, name="ALA"):
    c, s = math.cos(angle), math.sin(angle)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    out = []
    for ln in pdb.splitlines():
        x = np.array([float(ln[30:38]), float(ln[38:46]), float(ln[46:54])])
        i = int(ln[22:26])
        y = R @ x + np.array(shift)
        if move and move[0] <= i <= move[1]:
            y = y + np.array(move[2])
        out.append(ln[:30] + "%8.3f%8.3f%8.3f" % tuple(y) + ln[54:])
    return "\n".join(out)


def test_rigid_motion_gives_zero_difference():
    a = helix_pdb(120); b = rot(a, 0.7)
    r = compare_states(a, b)
    assert r["rmsd_all"] < 0.05 and any("almost identical" in w for w in r["warnings"])


def test_a_moved_segment_is_found_after_superposition():
    a = helix_pdb(120); b = rot(a, 1.1, move=(95, 120, (8, 0, 0)))
    r = compare_states(a, b)
    mag = dict(zip(r["resi"], r["magnitude"]))
    assert min(mag[i] for i in range(100, 119)) > 6 and max(mag[i] for i in range(5, 70)) < 1.5
    class S:
        def __init__(s, n, a_, b_): s.name, s.kind, s.start, s.end = n, "TM", a_, b_
    rows = per_segment(r, [S("TM1", 1, 40), S("TM6", 95, 120)])
    assert rows[1]["mean_A"] > 6 and rows[0]["mean_A"] < 1.5


def test_numbering_offset_and_too_little_overlap():
    a = helix_pdb(120); b = rot(a, 0.3)
    shifted = "\n".join(ln[:22] + "%4d" % (int(ln[22:26]) + 10) + ln[26:] for ln in b.splitlines())
    with pytest.raises(ValueError):
        compare_states(a, helix_pdb(30))
    assert compare_states(a, shifted, offset_b=-10)["rmsd_all"] < 0.05
    assert compare_states(a, shifted, offset_b=0)["n_shared"] == 110


def test_state_mode_is_appended_and_missing_residues_stay_still():
    a = helix_pdb(120); b = rot(a, 0.5, move=(100, 120, (6, 0, 0)))
    c = compare_states(a, b)
    m = add_state_mode(None, c, "inactive to active")
    assert m["modes"][0]["kind"] == "state" and len(m["modes"][0]["vec"]) == 120
    from protellect_core.motion import normal_modes
    nm = normal_modes(a)
    m2 = add_state_mode(nm, c, "x")
    assert len(m2["modes"]) == len(nm["modes"]) + 1 and m2["modes"][-1]["kind"] == "state"


def test_vectors_are_rotated_into_the_viewer_frame():
    from protellect_core.states import rotation_into, rotate_comparison
    view = helix_pdb(120)
    a = rot(view, 0.9, shift=(3, 4, 5))                        # A sits in a different frame than the displayed model
    b = rot(view, 0.9, shift=(3, 4, 5), move=None)
    # B = A with segment 95-120 moved by +8 A along the VIEW x axis, expressed in A's frame
    c, s_ = math.cos(0.9), math.sin(0.9)
    R_a = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]])
    b = rot(view, 0.9, shift=(3, 4, 5), move=(95, 120, tuple(R_a @ np.array([8.0, 0, 0]))))
    cmp = compare_states(a, b)
    R = rotation_into(view, a)
    out = rotate_comparison(cmp, R)
    mean_vec = np.mean([out["disp"][cmp["resi"].index(i)] for i in range(105, 118)], axis=0)
    assert np.allclose(mean_vec, [8, 0, 0], atol=1.5)
    assert rotation_into(view, helix_pdb(20)) is None
