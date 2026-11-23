# Possiamo fidarci dei sensori? Qualità dell'aria in provincia di Cuneo, 2026

Caso studio indipendente su dati pubblici di ARPA Piemonte.
Prima di usare i dati di una rete di sensori per prendere decisioni, controllo quanto sono affidabili.

**Pagina:** https://felipervm.github.io/qualita-aria-cuneo/
**Control room (prototipo):** https://felipervm.github.io/qualita-aria-cuneo/control-room/

## Cosa controlla

- copertura di ogni serie (ore o giorni con dato valido) e mese per mese
- il buco più lungo senza dati validi
- buchi nello stesso momento in più stazioni (possibile causa comune)
- valori uguali per molte ore di fila e valori negativi segnati come validi
- confronto delle medie PM10 sugli stessi giorni

## Control room: il report delle 8:00

Un prototipo di report giornaliero sulla salute dei sensori, come lo userebbe una control room.
Per ogni sensore e ogni giorno:

- **non trasmette:** nessun dato valido
- **dati parziali:** meno di 18 ore valide su 24
- **valori ripetuti:** 6 o più ore di fila con lo stesso valore, sopra 5 µg/m³
- **spento:** non trasmette da più di 14 giorni
- **in attesa:** PM10 dopo l'ultimo giorno pubblicato da ARPA (ritardo del laboratorio, non un guasto)
- **guasto comune:** lo stesso inquinante manca in 2 o più stazioni nello stesso giorno, quindi va controllata prima la trasmissione

Il prototipo gira su dati già validati da ARPA. In una control room vera gli stessi controlli girerebbero sui dati grezzi appena arrivano.

## Dati

7 stazioni attive della provincia di Cuneo (Alba, Bra, Cavallermaggiore, Cuneo, Mondovì, Revello, Saliceto),
NO2 e O3 orari e PM10 giornaliero, dal 1 gennaio al 20 novembre 2026.
Fonte: ARPA Piemonte, Sistema Regionale di Rilevamento della Qualità dell'Aria
([aria.ambiente.piemonte.it](https://aria.ambiente.piemonte.it/qualita-aria/dati)).
Lo script usato per scaricarli è in `fetch/`. I dati in stato P (non ancora verificati) vengono esclusi.

## Come si usa

```bash
pip install -r requirements.txt
python src/qualita.py data/arpa_cuneo_2026.csv.gz output/
python src/control_room.py data/arpa_cuneo_2026.csv.gz output/control_room.json
python build_site.py          # genera docs/index.html e docs/control-room/index.html
pytest -q
```

## Struttura

```
data/        export ARPA (csv.gz)
fetch/       script per scaricare i dati
src/         controlli di qualità (qualita.py) e report giornaliero (control_room.py)
tests/       test automatici
output/      salute_serie.csv, report.json e control_room.json
site/        template della pagina
docs/        pagina pubblicata (GitHub Pages)
```

Progetto di Felipe Mattos. Nessuna affiliazione con ARPA Piemonte. I dati sono di ARPA Piemonte, le interpretazioni sono mie.
