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
