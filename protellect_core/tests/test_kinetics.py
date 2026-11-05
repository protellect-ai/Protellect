import math, pytest
from protellect_core.kinetics import kinetics, reading, fmt_molar, fmt_time


def test_known_values():
    r = kinetics(1e6, 1e-2, 1e-8)           # Kd 10 nM, 10 nM ligand -> 50% occupancy
    assert math.isclose(r["Kd_M"], 1e-8) and math.isclose(r["occupancy"], 0.5)
    assert math.isclose(r["residence_time_s"], 100) and math.isclose(r["half_life_s"], math.log(2) / 1e-2)
    assert math.isclose(r["kobs_per_s"], 1e6 * 1e-8 + 1e-2) and r["t_95pct_equilibrium_s"] > r["t_half_assoc_s"]


@pytest.mark.parametrize("kon,koff", [(0, 1), (1, 0), (-1, 1), ("x", 1)])
def test_bad_inputs_raise_valueerror_not_nonsense(kon, koff):
    with pytest.raises(ValueError):
        kinetics(kon, koff)


def test_formatting_and_reading():
    assert fmt_molar(1e-8) == "10 nM" and fmt_time(0.2) == "200 ms" and fmt_time(300) == "5.0 min"
    assert "washout" in reading(kinetics(1e5, 1e-3, 1e-7))
