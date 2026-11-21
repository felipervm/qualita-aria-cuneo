"""Controllo di affidabilità dei dati dei sensori di qualità dell'aria (ARPA Piemonte, provincia di Cuneo).

Uso:
    python src/qualita.py data/arpa_cuneo_2026.csv.gz output/

Legge l'export di ARPA Piemonte (separatore ';') e produce:
    output/salute_serie.csv     una riga per stazione e parametro
    output/report.json          tutti i risultati usati dalla pagina
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ORARI = {"04": "NO2", "05": "O3"}
GIORNALIERI = {"PM10_GBV": "PM10"}
SOGLIA_COPERTURA = 90.0   # % di dati validi richiesta di solito per le statistiche annuali
MIN_PIATTO = 6            # ore consecutive con lo stesso valore
MIN_BUCO_COMUNE = 24      # ore: un buco così lungo in più stazioni insieme è un segnale


def carica(percorso):
    """Legge l'export e crea un timestamp pulito.

    ARPA indica l'ultima ora del giorno come 23:59 (fine giornata): la trattiamo come ora 24,
    altrimenti si sovrappone alle 23:00. Per i dati giornalieri l'ora è sempre 23:59.
    """
    d = pd.read_csv(percorso, sep=";", dtype=str)
    d["valore"] = pd.to_numeric(d["valore"].replace("undefined", np.nan), errors="coerce")
    d["giorno"] = pd.to_datetime(d["data"], format="%d/%m/%Y")
    ora = d["ora"].replace("23:59", "24:00").str.slice(0, 2).astype(int)
    d["ts"] = d["giorno"] + pd.to_timedelta(ora, unit="h")
    d["inquinante"] = d["id_parametro"].map({**ORARI, **GIORNALIERI})
    d["stazione"] = d["stazione"].str.replace("Mondovi'", "Mondovì", regex=False)
    return d


def sequenze(mask):
    """Restituisce (inizio, lunghezza) di ogni sequenza di True."""
    out, start, n = [], None, 0
    for i, m in enumerate(mask):
        if m:
            if n == 0:
                start = i
            n += 1
        elif n:
            out.append((start, n))
            n = 0
    if n:
        out.append((start, n))
    return out


def valori_piatti(valori, minimo=MIN_PIATTO):
    """Sequenze di valori validi identici e consecutivi (sensore bloccato o segnale troppo basso)."""
    out, start, n, prev = [], 0, 0, None
    for i, v in enumerate(valori):
        if v is not None and not pd.isna(v) and v == prev:
            n += 1
        else:
            if n >= minimo:
                out.append((start, n, prev))
            start, n, prev = i, (1 if v is not None and not pd.isna(v) else 0), v
    if n >= minimo:
        out.append((start, n, prev))
    return out


def salute_serie(d, fine):
    righe = []
    for (staz, inq), g in d[d["giorno"] < fine].groupby(["stazione", "inquinante"]):
        g = g.sort_values("ts").reset_index(drop=True)
        orario = inq in ORARI.values()
        stati = g["stato"].value_counts()
        validi = g["valore"].where(g["stato"] == "V")
        buchi = sequenze((g["stato"] != "V").tolist())
        lungo = max(buchi, key=lambda b: b[1], default=None)
        piatti = valori_piatti(validi.tolist()) if orario else []
        righe.append({
            "stazione": staz,
            "inquinante": inq,
            "frequenza": "oraria" if orario else "giornaliera",
            "attesi": len(g),
            "validi": int(stati.get("V", 0)),
            "invalidati": int(stati.get("E", 0)),
            "mancanti": int(stati.get("M", 0)),
            "copertura_pct": round(100 * stati.get("V", 0) / len(g), 1),
            "sotto_soglia": bool(100 * stati.get("V", 0) / len(g) < SOGLIA_COPERTURA),
            "buco_max": lungo[1] if lungo else 0,
            "buco_max_da": str(g.loc[lungo[0], "ts"]) if lungo else "",
            "buco_max_a": str(g.loc[lungo[0] + lungo[1] - 1, "ts"]) if lungo else "",
            "sequenze_piatte": len(piatti),
            "piatto_max_ore": max((p[1] for p in piatti), default=0),
            "negativi_validi": int((validi < 0).sum()),
            "timestamp_duplicati": int(g["ts"].duplicated().sum()),
        })
    return pd.DataFrame(righe)


def copertura_mensile(d, fine):
    x = d[d["giorno"] < fine].copy()
    x["mese"] = x["giorno"].dt.month
    x["valido"] = x["stato"] == "V"
    t = x.groupby(["stazione", "inquinante", "mese"])["valido"].mean().mul(100).round(1)
    return t.reset_index().rename(columns={"valido": "copertura_pct"})


def buchi_comuni(d, fine, minimo=MIN_BUCO_COMUNE):
    """Periodi in cui lo stesso inquinante manca in almeno 2 stazioni nelle stesse ore, per >= minimo ore di fila.

    Un buco nello stesso momento in più stazioni fa pensare a una causa comune
    (manutenzione programmata, sistema centrale, trasmissione) più che a un singolo sensore.
    """
    x = d[(d["giorno"] < fine) & d["inquinante"].isin(ORARI.values())]
    out = []
    for inq, g in x.groupby("inquinante"):
        m = g.pivot_table(index="ts", columns="stazione", values="stato", aggfunc="first").sort_index()
        assenti = m.ne("V")
        quante = assenti.sum(axis=1)
        for start, n in sequenze((quante >= 2).tolist()):
            if n < minimo:
                continue
            blocco = assenti.iloc[start:start + n]
            # stazioni assenti per almeno metà del periodo comune
            coinvolte = [c for c in blocco.columns if blocco[c].mean() >= 0.5]
            out.append({
                "inquinante": inq,
                "da": str(blocco.index[0]),
                "a": str(blocco.index[-1]),
                "ore": int(n),
                "stazioni": coinvolte,
                "stazioni_attive_con_dati": [c for c in blocco.columns if c not in coinvolte],
                "stazioni_totali": int(m.shape[1]),
            })
    return out


def confronto_stessi_giorni(d, fine, riferimento="Mondovì - Aragno"):
    """Media PM10 di ogni stazione: su tutti i suoi giorni validi e solo sui giorni validi del riferimento."""
    x = d[(d["giorno"] < fine) & (d["inquinante"] == "PM10")]
    w = x.pivot_table(index="giorno", columns="stazione", values="valore", aggfunc="first")
    s = x.pivot_table(index="giorno", columns="stazione", values="stato", aggfunc="first")
    w = w.where(s == "V")
    giorni = w[riferimento].dropna().index
    righe = []
    for c in w.columns:
        righe.append({
            "stazione": c,
            "giorni_validi": int(w[c].notna().sum()),
            "media_tutti_i_giorni": round(float(w[c].mean()), 1),
            "giorni_in_comune": int(w.loc[giorni, c].notna().sum()),
            "media_giorni_riferimento": round(float(w.loc[giorni, c].mean()), 1),
        })
    mesi = sorted(set(giorni.month))
    return {"riferimento": riferimento, "giorni_riferimento": len(giorni), "mesi_riferimento": mesi, "stazioni": righe}


def livello_segnale(d, fine, soglia=5):
    """Mediana dei valori validi e quota di ore sotto la soglia: un segnale basso rende normali i valori 'piatti'."""
    x = d[(d["giorno"] < fine) & (d["stato"] == "V") & d["inquinante"].isin(ORARI.values())]
    g = x.groupby(["stazione", "inquinante"])["valore"]
    t = pd.DataFrame({"mediana": g.median(), "pct_sotto_soglia": g.apply(lambda v: round(100 * (v <= soglia).mean(), 1))})
    return t.reset_index().assign(soglia=soglia).to_dict(orient="records")


def main(src, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    d = carica(src)
    pendenti = d[d["stato"] == "P"]
    fine = pendenti["giorno"].min() if len(pendenti) else d["giorno"].max() + pd.Timedelta(days=1)
    salute = salute_serie(d, fine)
    salute.to_csv(outdir / "salute_serie.csv", index=False)
    report = {
        "fonte": "ARPA Piemonte, Sistema Regionale di Rilevamento della Qualità dell'Aria (aria.ambiente.piemonte.it)",
        "periodo": [str(d["giorno"].min().date()), str((fine - pd.Timedelta(days=1)).date())],
        "escluso_non_verificato": {"giorno": str(fine.date()), "righe": int(len(pendenti))},
        "righe_totali": int(len(d)),
        "stazioni": sorted(d["stazione"].unique().tolist()),
        "soglia_copertura": SOGLIA_COPERTURA,
        "salute": salute.to_dict(orient="records"),
        "copertura_mensile": copertura_mensile(d, fine).to_dict(orient="records"),
        "buchi_comuni": buchi_comuni(d, fine),
        "confronto_pm10": confronto_stessi_giorni(d, fine),
        "livello_segnale": livello_segnale(d, fine),
    }
    (outdir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str))
    return report


if __name__ == "__main__":
    r = main(sys.argv[1], sys.argv[2])
    print(f"{r['righe_totali']} righe, periodo {r['periodo'][0]} - {r['periodo'][1]}")
    print(pd.DataFrame(r["salute"])[["stazione", "inquinante", "copertura_pct", "buco_max", "sequenze_piatte", "negativi_validi"]].to_string(index=False))
    for b in r["buchi_comuni"]:
        print("BUCO COMUNE", b["inquinante"], b["ore"], b["stazioni"], b["da"], b["a"], "ok:", b["stazioni_attive_con_dati"])
