"""Genera site/index.html a partire da output/report.json."""
import json
from pathlib import Path

REPO = "qualita-aria-cuneo"
r = json.loads(Path("output/report.json").read_text())
sal = next(x for x in r["livello_segnale"] if x["stazione"].startswith("Saliceto") and x["inquinante"] == "NO2")
html = Path("site/template.html").read_text()
html = (html.replace("__DATA__", json.dumps(r, ensure_ascii=False))
            .replace("__REPO__", REPO)
            .replace("__SAL_MED__", f"{sal['mediana']:g}".replace(".", ","))
            .replace("__SAL_PCT__", f"{sal['pct_sotto_soglia']:g}".replace(".", ",")))
Path("docs").mkdir(exist_ok=True)
Path("docs/index.html").write_text(html)
print("docs/index.html", len(html))

# Pagina della control room (report giornaliero sulla salute dei sensori)
cr = json.loads(Path("output/control_room.json").read_text())
g = cr["ultimo_pm10"].split("-")
mesi = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
t = (Path("site/control-room.html").read_text()
     .replace("__DATA__", json.dumps(cr, ensure_ascii=False, separators=(",", ":")))
     .replace("__ULTIMO__", cr["giorni"][-1])
     .replace("__ULTIMO_PM10__", f"{int(g[2])} {mesi[int(g[1]) - 1]}")
     .replace("__ORE_MIN__", str(cr["regole"]["ore_min"]))
     .replace("__PIATTO__", str(cr["regole"]["piatto_ore"]))
     .replace("__BASSO__", str(cr["regole"]["segnale_basso"]))
     .replace("__SPENTO__", str(cr["regole"]["spento_dopo"])))
Path("docs/control-room").mkdir(parents=True, exist_ok=True)
Path("docs/control-room/index.html").write_text(t)
print("docs/control-room/index.html", len(t))
