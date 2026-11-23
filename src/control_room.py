"""Report giornaliero sulla salute dei sensori, pensato per una control room.

Per ogni giorno e per ogni sensore (stazione + inquinante) assegna uno stato:
    ok         dati completi e normali
    bloccato   6+ ore di fila con lo stesso valore (sopra il livello di segnale basso)
    parziale   meno di 18 ore valide su 24
    fermo      nessun dato valido nel giorno
    spento     fermo da più di SPENTO_DOPO giorni: non è più un allarme, va verificato se è voluto
    in_attesa  PM10 dopo l'ultimo giorno pubblicato da qualunque stazione: il dato di laboratorio
               non è ancora arrivato, quindi non è un guasto

Uso:
    python src/control_room.py data/arpa_cuneo_2026.csv.gz output/control_room.json
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import qualita as q  # noqa: E402

ORE_MIN = 18          # ore valide minime per considerare completo un giorno (75%)
PIATTO_ORE = 6        # ore consecutive con lo stesso valore
SEGNALE_BASSO = 5     # µg/m³: sotto questo livello valori ripetuti sono normali
SPENTO_DOPO = 14      # giorni di fila senza dati dopo i quali il sensore si considera spento

ORDINE = {"fermo": 4, "parziale": 3, "bloccato": 2, "spento": 1, "in_attesa": 0, "ok": 0}


def stato_orario(stati, valori):
    """Stato di un giorno per un sensore orario. stati e valori sono liste di 24 elementi."""
    validi = sum(1 for s in stati if s == "V")
    if validi == 0:
        return {"stato": "fermo", "validi": 0}
    vv = [v if s == "V" else None for s, v in zip(stati, valori)]
    piatti = q.valori_piatti(vv, PIATTO_ORE)
    piatto = max(piatti, key=lambda p: p[1], default=None)
    info = {"validi": validi}
    if piatto:
        info["piatto_ore"] = int(piatto[1])
        info["piatto_valore"] = float(piatto[2])
    if validi < ORE_MIN:
        return {"stato": "parziale", **info}
    if piatto and piatto[2] > SEGNALE_BASSO:
        return {"stato": "bloccato", **info}
    if piatto:
        info["segnale_basso"] = True
    return {"stato": "ok", **info}


def stato_giornaliero(stato):
    """PM10: un solo valore al giorno."""
    return {"stato": "ok", "validi": 1} if stato == "V" else {"stato": "fermo", "validi": 0}


def aggiungi_serie_di_giorni(giorni):
    """Per ogni giorno conta da quanti giorni di fila il sensore non è ok, e marca come 'spento'
    i fermi che durano da più di SPENTO_DOPO giorni."""
    fila = 0
    fermo_fila = 0
    for g in giorni:
        if g["stato"] == "in_attesa":
            g["giorni_di_fila"] = 0
            continue
        fila = fila + 1 if g["stato"] != "ok" else 0
        fermo_fila = fermo_fila + 1 if g["stato"] == "fermo" else 0
        g["giorni_di_fila"] = fila
        if g["stato"] == "fermo" and fermo_fila > SPENTO_DOPO:
            g["stato"] = "spento"
            g["fermo_da"] = fermo_fila
    return giorni


def guasti_comuni(giorno_sensori):
    """Stesso inquinante fermo o parziale in almeno 2 stazioni nello stesso giorno."""
    per_inq = {}
    for s in giorno_sensori:
        if s["stato"] in ("fermo", "parziale"):
            per_inq.setdefault(s["inquinante"], []).append(s["stazione"])
    totali = {}
    for s in giorno_sensori:
        totali[s["inquinante"]] = totali.get(s["inquinante"], 0) + 1
    return [{"inquinante": k, "stazioni": v, "su": totali[k]} for k, v in per_inq.items() if len(v) >= 2]


def ultimo_giornaliero_pubblicato(d):
    """Ultimo giorno in cui almeno una stazione ha un PM10 valido."""
    x = d[(d["inquinante"].isin(q.GIORNALIERI.values())) & (d["stato"] == "V")]
    return x["giorno"].max().strftime("%Y-%m-%d") if len(x) else None


def costruisci(d, fine):
    d = d[d["giorno"] < fine]
    ultimo_pm10 = ultimo_giornaliero_pubblicato(d)
    giorni = sorted(d["giorno"].dt.strftime("%Y-%m-%d").unique())
    sensori = []
    for (staz, inq), g in d.groupby(["stazione", "inquinante"]):
        orario = inq in q.ORARI.values()
        g = g.sort_values("ts")
        per_giorno = []
        for giorno, gg in g.groupby(g["giorno"].dt.strftime("%Y-%m-%d")):
            if orario:
                r = stato_orario(gg["stato"].tolist(), gg["valore"].tolist())
            elif ultimo_pm10 and giorno > ultimo_pm10:
                r = {"stato": "in_attesa", "validi": 0}
            else:
                r = stato_giornaliero(gg["stato"].iloc[0])
            per_giorno.append({"giorno": giorno, **r})
        aggiungi_serie_di_giorni(per_giorno)
        sensori.append({"stazione": staz, "inquinante": inq, "frequenza": "oraria" if orario else "giornaliera",
                        "giorni": per_giorno})
    # vista per giorno, usata dalla pagina
    indice = {s["stazione"] + "|" + s["inquinante"]: {x["giorno"]: x for x in s["giorni"]} for s in sensori}
    per_giorno = {}
    for giorno in giorni:
        righe = []
        for s in sensori:
            x = indice[s["stazione"] + "|" + s["inquinante"]].get(giorno)
            if x:
                righe.append({"stazione": s["stazione"], "inquinante": s["inquinante"], **{k: v for k, v in x.items() if k != "giorno"}})
        per_giorno[giorno] = {"sensori": righe, "comuni": guasti_comuni(righe)}
    return {"giorni": giorni, "sensori": [{"stazione": s["stazione"], "inquinante": s["inquinante"], "frequenza": s["frequenza"]} for s in sensori],
            "per_giorno": per_giorno, "ultimo_pm10": ultimo_pm10,
            "regole": {"ore_min": ORE_MIN, "piatto_ore": PIATTO_ORE, "segnale_basso": SEGNALE_BASSO, "spento_dopo": SPENTO_DOPO}}


def main(src, out):
    d = q.carica(src)
    pendenti = d[d["stato"] == "P"]
    fine = pendenti["giorno"].min() if len(pendenti) else d["giorno"].max() + pd.Timedelta(days=1)
    r = costruisci(d, fine)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(r, ensure_ascii=False, separators=(",", ":")))
    return r


if __name__ == "__main__":
    r = main(sys.argv[1], sys.argv[2])
    from collections import Counter
    c = Counter(s["stato"] for g in r["per_giorno"].values() for s in g["sensori"])
    print(len(r["giorni"]), "giorni", len(r["sensori"]), "sensori", dict(c))
    peggiori = sorted(r["per_giorno"].items(), key=lambda kv: -sum(ORDINE[s["stato"]] >= 2 for s in kv[1]["sensori"]))[:8]
    for g, v in peggiori:
        print(g, [(s["stazione"][:8], s["inquinante"], s["stato"]) for s in v["sensori"] if ORDINE[s["stato"]] >= 2], v["comuni"])
