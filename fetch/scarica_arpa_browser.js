// Script usato per scaricare i dati (eseguito nella console del browser su https://aria.ambiente.piemonte.it/qualita-aria/dati).
// Usa lo stesso servizio pubblico che alimenta la pagina "Accesso ai dati misurati" di ARPA Piemonte.
// Stazioni attive della provincia di Cuneo con NO2, O3 e PM10 (gravimetrico basso volume).
const piano = {
  '004003.800': ['04', '05', 'PM10_GBV'], // Alba - Tanaro
  '004029.801': ['04', 'PM10_GBV'],       // Bra - Madonna Fiori
  '004059.800': ['04', 'PM10_GBV'],       // Cavallermaggiore - Galilei
  '004078.800': ['04', '05', 'PM10_GBV'], // Cuneo - Alpini
  '004130.801': ['04', 'PM10_GBV'],       // Mondovì - Aragno
  '004180.800': ['04', '05'],             // Revello - Staffarda
  '004201.800': ['04', '05', 'PM10_GBV'], // Saliceto - Moizo
};
const righe = [];
for (const [stazione, parametri] of Object.entries(piano)) {
  for (const p of parametri) {
    let offset = 0, totale = 0;
    do {
      const body = { periodo_da: '01012026', periodo_a: '20112026', stazioni: [{ id_stazione: stazione, parametri: [p] }], flag_validato: false, formato: 'json' };
      const r = await fetch(`/ariaweb/ariaws/rest/getRilevamenti?offset=${offset}&limit=5000`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const j = await r.json();
      totale = j.resultTotalCount;
      for (const x of j.risultati) righe.push([stazione, x.desc_stazione, p, x.desc_parametro, x.data, x.ora, x.valore, x.stato, x.desc_unita_misura]);
      offset += 5000;
      if (!j.risultati.length) break;
    } while (offset < totale);
  }
}
const csv = 'id_stazione;stazione;id_parametro;parametro;data;ora;valore;stato;unita\n' +
  righe.map(r => r.map(v => v === null ? '' : String(v).replace(/;/g, ',')).join(';')).join('\n');
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
a.download = 'arpa_cuneo_2026.csv';
a.click();
