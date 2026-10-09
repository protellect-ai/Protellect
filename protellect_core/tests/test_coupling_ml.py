import random
import numpy as np
from protellect_core.coupling_ml import features, evaluate, predict_orphans, parse_tms, group_of

AA = "ACDEFGHIKLMNPQRSTVWY"


def rnd(n, rng, bias=""):
    return "".join(rng.choice(list(bias) * 4 + list(AA)) for _ in range(n))


def receptor(rng, cls, signal=True):
    """Synthetic seven-TM sequence; with signal=True, Gi has a long ICL3, Gs a long C-tail, Gq a short ICL3 and short tail."""
    icl3 = {"Gi": 110, "Gs": 28, "Gq": 55}[cls] if signal else rng.choice([28, 55, 110])
    tail = {"Gi": 30, "Gs": 90, "Gq": 45}[cls] if signal else rng.choice([30, 45, 90])
    parts, tms, pos = [], [], 1
    seg = [("n", 25), ("tm", 24), ("l", 12), ("tm", 24), ("l", 14), ("tm", 24), ("l", 15), ("tm", 24), ("l", 20), ("tm", 24), ("l", icl3), ("tm", 24), ("l", 10), ("tm", 24), ("c", tail)]
    for kind, n in seg:
        s = rnd(n, rng, "AVILMFW" if kind == "tm" else "SKEDPT")
        if kind == "tm":
            tms.append((pos, pos + n - 1))
        parts.append(s); pos += n
    return "".join(parts), tms


def dataset(n_per=18, signal=True, seed=1):
    rng = random.Random(seed)
    data, labels = {}, {}
    for cls in ("Gi", "Gs", "Gq"):
        for k in range(n_per):
            gene = f"{cls.upper()}FAM{k}X{k}"        # each receptor its own subfamily after digit stripping
            gene = "".join(chr(65 + (k * 7 + j * 3 + ord(cls[1])) % 26) for j in range(5)) + str(k)
            seq, tms = receptor(rng, cls, signal)
            data[gene], labels[gene] = {"seq": seq, "tms": tms}, cls
    return data, labels


def test_features_need_seven_tms():
    rng = random.Random(0); seq, tms = receptor(rng, "Gi")
    f = features(seq, tms)
    assert f and f["len_icl3"] == 110 and f["len_ctail"] == 30
    assert features(seq, tms[:6]) is None and features("", tms) is None
    assert parse_tms("TRANSMEM 41..65; /note=H1; TRANSMEM 70..90") == [(41, 65), (70, 90)]
    assert group_of("ADRB2") == "ADRB" and group_of("HTR1A") == "HTR"


def test_real_signal_passes_the_self_test_and_predicts():
    data, labels = dataset(signal=True)
    rep = evaluate(data, labels)
    assert rep["trusted"] and rep["accuracy"] > 0.9 and rep["p_permutation"] < 0.05 and rep["ci95"][0] > rep["baseline"]
    rng = random.Random(9); seq, tms = receptor(rng, "Gi"); data["NEWGENE1"] = {"seq": seq, "tms": tms}
    pr = predict_orphans(data, labels, ["NEWGENE1", "MISSING"], rep)
    assert len(pr) == 1 and pr[0]["top"] == "Gi" and abs(sum(pr[0]["probabilities"].values()) - 1) < 0.01


def test_no_signal_is_refused_and_gives_no_predictions():
    data, labels = dataset(signal=False)
    rep = evaluate(data, labels)
    assert not rep["trusted"] and "No prediction is shown" in rep["reason"]
    assert predict_orphans(data, labels, list(data)[:3], rep) == []


def test_too_few_labelled_receptors_refused():
    data, labels = dataset(n_per=5)
    rep = evaluate(data, labels)
    assert not rep["trusted"] and "noise" in rep["reason"]
    assert evaluate({}, {})["trusted"] is False


def test_null_false_positive_rate_over_many_random_datasets():
    trusted = 0
    for seed in range(8):
        data, labels = dataset(n_per=16, signal=False, seed=100 + seed)
        trusted += evaluate(data, labels, n_boot=150, n_perm=25)["trusted"]
    assert trusted <= 2        # about 5% expected; a leaky gate would give most of 12
