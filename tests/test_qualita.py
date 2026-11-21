import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import qualita as q  # noqa: E402

INTEST = "id_stazione;stazione;id_parametro;parametro;data;ora;valore;stato;unita\n"


def csv(righe):
    return io.StringIO(INTEST + "\n".join(righe))


def test_ora_2359_diventa_mezzanotte():
    d = q.carica(csv([
        "1;A;04;NO2;01/01/2026;23:00;10;V;u",
        "1;A;04;NO2;01/01/2026;23:59;11;V;u",
    ]))
    assert d["ts"].tolist() == [pd.Timestamp("2026-01-01 23:00"), pd.Timestamp("2026-01-02 00:00")]
    assert d["ts"].duplicated().sum() == 0


def test_valore_undefined_diventa_nan():
    d = q.carica(csv(["1;A;04;NO2;01/01/2026;01:00;undefined;M;u"]))
    assert d["valore"].isna().all()


def test_sequenze():
    assert q.sequenze([False, True, True, False, True]) == [(1, 2), (4, 1)]
    assert q.sequenze([]) == []


def test_valori_piatti_ignora_i_buchi():
    v = [5, 5, 5, 5, 5, 5, 7, None, None, 3, 3]
    assert q.valori_piatti(v, minimo=6) == [(0, 6, 5)]
    assert q.valori_piatti([None] * 10, minimo=3) == []


def _orari(stazione, stati):
    righe = []
    for i, s in enumerate(stati):
        ts = pd.Timestamp("2026-02-01 01:00") + pd.Timedelta(hours=i)
        ora = "23:59" if ts.hour == 0 else f"{ts.hour:02d}:00"
        giorno = (ts - pd.Timedelta(hours=1)).strftime("%d/%m/%Y") if ts.hour == 0 else ts.strftime("%d/%m/%Y")
        val = "10" if s == "V" else "undefined"
        righe.append(f"x;{stazione};05;O3;{giorno};{ora};{val};{s};u")
    return righe


def test_buco_comune_trovato_solo_se_simultaneo():
    a = _orari("A", ["V"] * 10 + ["M"] * 30 + ["V"] * 10)
    b = _orari("B", ["V"] * 12 + ["E"] * 28 + ["V"] * 10)
    c = _orari("C", ["V"] * 50)
    d = q.carica(csv(a + b + c))
    buchi = q.buchi_comuni(d, pd.Timestamp("2026-03-01"), minimo=24)
    assert len(buchi) == 1
    assert buchi[0]["ore"] == 28
    assert buchi[0]["stazioni"] == ["A", "B"]
    assert buchi[0]["stazioni_attive_con_dati"] == ["C"]


def test_buco_non_simultaneo_ignorato():
    a = _orari("A", ["M"] * 30 + ["V"] * 40)
    b = _orari("B", ["V"] * 40 + ["M"] * 30)
    d = q.carica(csv(a + b))
    assert q.buchi_comuni(d, pd.Timestamp("2026-03-01"), minimo=24) == []


def test_copertura_e_soglia():
    d = q.carica(csv(_orari("A", ["V"] * 85 + ["M"] * 15)))
    s = q.salute_serie(d, pd.Timestamp("2026-03-01")).iloc[0]
    assert s["copertura_pct"] == 85.0
    assert bool(s["sotto_soglia"]) is True
    assert s["buco_max"] == 15
