# Possiamo fidarci dei sensori? Qualità dell'aria in provincia di Cuneo, 2026

Caso studio indipendente su dati pubblici di ARPA Piemonte.
Prima di usare i dati di una rete di sensori per prendere decisioni, controllo quanto sono affidabili.

**Pagina:** https://felipervm.github.io/qualita-aria-cuneo/

## Cosa controlla

- copertura di ogni serie (ore o giorni con dato valido) e mese per mese
- il buco più lungo senza dati validi
- buchi nello stesso momento in più stazioni (possibile causa comune)
- valori uguali per molte ore di fila e valori negativi segnati come validi
- confronto delle medie PM10 sugli stessi giorni

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
python build_site.py          # genera docs/index.html
pytest -q
```

## Struttura

```
data/        export ARPA (csv.gz)
fetch/       script per scaricare i dati
src/         controlli di qualità (qualita.py)
tests/       test automatici
output/      salute_serie.csv e report.json
site/        template della pagina
docs/        pagina pubblicata (GitHub Pages)
```

Progetto di Felipe Mattos. Nessuna affiliazione con ARPA Piemonte. I dati sono di ARPA Piemonte, le interpretazioni sono mie.
