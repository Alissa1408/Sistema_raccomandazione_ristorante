// Porting in JavaScript di motore.Motore.suggerisci (Python): stessi pesi, stesse regole operative.
// Il modello (modello.json) contiene solo parametri e conteggi aggregati.
(function (root) {
  const TARDIVE = new Set(["Dessert", "Caffetteria", "Amari e digestivi"]);
  const VARIABILI = ["giorno", "fascia", "commensali", "valore"];
  const ePrincipale = f => /^(Pizze|Primi|Secondi)/.test(f);
  function fase(f) {
    if (f.startsWith("Antipasti")) return 1;
    if (/^(Pizze|Primi|Secondi)/.test(f)) return 2;
    if (f === "Contorni") return 3;
    if (f === "Bibite analcoliche" || f === "Birra" || f.startsWith("Vino")) return 4;
    return { "Dessert": 5, "Caffetteria": 6, "Amari e digestivi": 7 }[f] || 2;
  }
  const PROPONIBILI = { 1: [2], 2: [4], 3: [], 4: [5], 5: [6], 6: [7], 7: [] };
  function nonConsentiteFasi(catCart, tutte, ultimoCat) {
    if (!catCart.length && !ultimoCat) return new Set();
    const f = ultimoCat ? fase(ultimoCat) : Math.max(...catCart.map(fase));
    let consentite = PROPONIBILI[f];
    if (f === 2 && catCart.some(c => fase(c) === 4)) consentite = [5];
    const ok = new Set(tutte.filter(c => consentite.includes(fase(c))));
    if (!catCart.some(ePrincipale)) TARDIVE.forEach(t => ok.delete(t));
    return new Set(tutte.filter(c => !ok.has(c)));
  }
  const etichettaCommensali = n => n <= 2 ? "1_2" : (n <= 4 ? "3_4" : "5+");
  const pct = x => Math.round(x * 100) + "%";

  function creaMotore(M, disponibili) {
    const cats = M.cats, ci = Object.fromEntries(cats.map((c, i) => [c, i]));
    const pi = Object.fromEntries(M.prodotti.map((p, i) => [p, i]));
    const prodPerCat = cats.map(c => M.prodotti.map((p, i) => [p, i]).filter(([p]) => M.fam[p] === c).map(([, i]) => i));
    const disp = disponibili ? new Set(disponibili) : null;

    function contesto(mod, giorno, fascia, comm, vpp) {
      const x = [];
      if (mod.vars.includes("giorno")) ["ven", "sab", "dom"].forEach(v => x.push(giorno === v ? 1 : 0));
      if (mod.vars.includes("fascia")) ["prima_20", "dopo_21"].forEach(v => x.push(fascia === v ? 1 : 0));
      if (mod.vars.includes("commensali")) ["3_4", "5+"].forEach(v => x.push(comm === v ? 1 : 0));
      if (mod.vars.includes("valore")) { x.push(vpp <= mod.q[0] ? 1 : 0); x.push(vpp > mod.q[1] ? 1 : 0); }
      return x;
    }
    function probabilita(mod, catCart, giorno, fascia, comm, vpp) {
      const F = cats.map(c => catCart.includes(c) ? 1 : 0).concat(contesto(mod, giorno, fascia, comm, vpp));
      return mod.W.map((w, j) => { let z = mod.b[j]; for (let k = 0; k < F.length; k++) z += w[k] * F[k]; return 1 / (1 + Math.exp(-z)); });
    }
    const quotaCategoria = (ultimo, c) => (ultimo in pi) ? [M.quota[pi[ultimo]][ci[c]], M.nP[pi[ultimo]]] : [0, 0];

    function motivoCategoria(c, j, catCart, p, pSolo) {
      const righe = []; let migliore = null;
      for (const a of catCart) {
        const ia = ci[a]; if (ia === undefined || M.nC[ia] < M.min_coppie) continue;
        const conf = M.conf_cat[ia][j], lift = conf / M.base[j];
        if (!migliore || lift > migliore[2]) migliore = [a, conf, lift];
      }
      if (migliore && migliore[2] >= 1.1) righe.push(`Nel ${pct(migliore[1])} dei tavoli passati con «${migliore[0]}» c'era anche «${c}» (in media: ${pct(M.base[j])}).`);
      else righe.push(`«${c}» è molto ordinata in generale (${pct(M.base[j])} dei tavoli)` + (catCart.length ? " e il carrello non la rende più o meno probabile." : "."));
      const delta = (p - pSolo) * 100;
      righe.push(Math.abs(delta) >= 1 ? `Il contesto ${delta > 0 ? "aumenta" : "riduce"} la probabilità di ${Math.round(Math.abs(delta))} punti (${pct(pSolo)} → ${pct(p)}).` : "Il contesto cambia poco la probabilità.");
      return righe;
    }

    function suggerisci(carrello, giorno, fascia, n, { k = 12, valore = 0, ultimo = null } = {}) {
      const catCart = [...new Set(carrello.map(p => M.fam[p]).filter(Boolean))].sort();
      if (ultimo && (!(ultimo in pi) || M.nP[pi[ultimo]] < M.min_coppie))
        return { out: [], regole: [`Nessun suggerimento: il piatto non ha abbastanza storico (almeno ${M.min_coppie} tavoli) per basare una raccomandazione sui dati.`] };
      const bloccate = nonConsentiteFasi(catCart, cats, ultimo ? M.fam[ultimo] : null);
      const comm = etichettaCommensali(n), vpp = valore / Math.max(n, 1);
      const pCtx = probabilita(M.modelli.tutte, catCart, giorno, fascia, comm, vpp);
      const pSolo = probabilita(M.modelli.solo, catCart, giorno, fascia, comm, vpp);
      const pVar = Object.fromEntries(VARIABILI.map(v => [v, probabilita(M.modelli["solo_" + v], catCart, giorno, fascia, comm, vpp)]));
      const regole = ["Momento del pasto: dopo l'antipasto si propone un piatto principale, dopo il principale una bevanda, dopo la bevanda il dolce, dopo il dolce il caffè, dopo il caffè l'amaro. Se la bevanda è già nel carrello prima del piatto, dopo il piatto si propone direttamente il dolce."];
      if (!catCart.some(ePrincipale)) regole.push("Dolci, caffè e amari/digestivi non vengono proposti finché nel carrello non c'è un piatto principale (pizza, primo o secondo).");
      if (catCart.length) regole.push("Non si propone una categoria già presente nel carrello: " + catCart.join(", ") + ".");
      regole.push("Si propone una categoria solo se, con questo carrello, è più frequente della media nei tavoli che hanno ordinato l'ultimo piatto aggiunto.");
      regole.push(`Si propone una categoria solo se la probabilità stimata è almeno del ${Math.round(M.soglia * 100)}%: altrimenti il sistema sta in silenzio.`);
      const punt = pCtx.slice();
      cats.forEach((c, i) => {
        if (catCart.includes(c) || bloccate.has(c)) punt[i] = -1;
        else if (disp && !prodPerCat[i].some(j => disp.has(M.prodotti[j]))) punt[i] = -1;
      });
      const ordine = punt.map((v, i) => [v, i]).sort((a, b) => b[0] - a[0] || a[1] - b[1]).slice(0, k).map(x => x[1]);
      const out = [];
      for (const i of ordine) {
        if (punt[i] < M.soglia) continue;
        const c = cats[i];
        if (ultimo && quotaCategoria(ultimo, c)[0] <= 0) continue;
        if (ultimo && M.fam[ultimo] && !TARDIVE.has(c)) {
          const ia = ci[M.fam[ultimo]];
          if (ia !== undefined && M.nC[ia] >= M.min_coppie && M.conf_cat[ia][i] < M.base[i]) continue;
        }
        out.push({ categoria: c, prob: pCtx[i], prob_solo: pSolo[i], base: M.base[i],
          motivo: motivoCategoria(c, i, catCart, pCtx[i], pSolo[i]),
          effetti: Object.fromEntries(VARIABILI.map(v => [v, pVar[v][i] - pSolo[i]])) });
      }
      return { out, regole, top: ordine.filter(i => punt[i] >= 0).slice(0, 3).map(i => [cats[i], pCtx[i]]) };
    }

    function ordinaCategoria(c, ultimo) {
      const a = pi[ultimo];
      const righe = prodPerCat[ci[c]].filter(j => !disp || disp.has(M.prodotti[j])).map(j => {
        const n = a !== undefined ? M.coppie[a][j] : 0;
        return [M.prodotti[j], n, a !== undefined && M.nP[a] ? n / M.nP[a] : 0];
      });
      const con = righe.filter(x => x[1] > 0).sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0]));
      const senza = righe.filter(x => x[1] === 0).sort((x, y) => x[0].localeCompare(y[0]));
      return con.concat(senza);
    }
    return { suggerisci, ordinaCategoria, quotaCategoria, cats };
  }
  root.creaMotore = creaMotore;
  if (typeof module !== "undefined") module.exports = { creaMotore };
})(typeof window !== "undefined" ? window : globalThis);
