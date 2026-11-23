import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import control_room as cr  # noqa: E402


def giorno(valori, stati=None):
    return stati or ["V"] * len(valori), valori


def test_nessun_dato_valido_e_fermo():
    assert cr.stato_orario(["M"] * 24, [None] * 24)["stato"] == "fermo"


def test_poche_ore_valide_e_parziale():
    stati = ["V"] * 17 + ["M"] * 7
    valori = list(range(17)) + [None] * 7
    r = cr.stato_orario(stati, valori)
    assert r["stato"] == "parziale" and r["validi"] == 17


def test_valori_ripetuti_sopra_soglia_e_bloccato():
    valori = [20, 21, 22] + [10] * 7 + list(range(30, 44))
    r = cr.stato_orario(*giorno(valori))
    assert r["stato"] == "bloccato"
    assert r["piatto_ore"] == 7 and r["piatto_valore"] == 10


def test_valori_ripetuti_con_segnale_basso_restano_ok():
    valori = [3] * 8 + list(range(10, 26))
    r = cr.stato_orario(*giorno(valori))
    assert r["stato"] == "ok" and r["segnale_basso"]


def test_cinque_ore_uguali_non_bastano():
    valori = [10] * 5 + list(range(20, 39))
    assert cr.stato_orario(*giorno(valori))["stato"] == "ok"


def test_pm10_giornaliero():
    assert cr.stato_giornaliero("V")["stato"] == "ok"
    assert cr.stato_giornaliero("M")["stato"] == "fermo"


def test_giorni_di_fila_e_spento():
    giorni = [{"stato": "ok"}] + [{"stato": "fermo"} for _ in range(16)] + [{"stato": "ok"}]
    cr.aggiungi_serie_di_giorni(giorni)
    assert giorni[1]["giorni_di_fila"] == 1
    assert giorni[14]["stato"] == "fermo" and giorni[14]["giorni_di_fila"] == 14
    assert giorni[15]["stato"] == "spento" and giorni[15]["fermo_da"] == 15
    assert giorni[17]["giorni_di_fila"] == 0


def test_in_attesa_non_conta_come_guasto():
    giorni = [{"stato": "fermo"}, {"stato": "in_attesa"}, {"stato": "in_attesa"}]
    cr.aggiungi_serie_di_giorni(giorni)
    assert [g["stato"] for g in giorni] == ["fermo", "in_attesa", "in_attesa"]
    assert giorni[1]["giorni_di_fila"] == 0


def test_guasto_comune_serve_almeno_due_stazioni():
    sensori = [
        {"stazione": "A", "inquinante": "O3", "stato": "fermo"},
        {"stazione": "B", "inquinante": "O3", "stato": "parziale"},
        {"stazione": "C", "inquinante": "O3", "stato": "ok"},
        {"stazione": "A", "inquinante": "NO2", "stato": "fermo"},
        {"stazione": "B", "inquinante": "NO2", "stato": "bloccato"},
        {"stazione": "A", "inquinante": "PM10", "stato": "in_attesa"},
        {"stazione": "B", "inquinante": "PM10", "stato": "in_attesa"},
    ]
    assert cr.guasti_comuni(sensori) == [{"inquinante": "O3", "stazioni": ["A", "B"], "su": 3}]
