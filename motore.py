"""Motore del prototipo: modello con categorie + contesto, regole operative e motivazioni.

Il motore si puo' costruire in due modi:
- dai dati storici (dettaglio_ordini_cena.csv), addestrando i modelli: e' il modo usato nella tesi;
- dal file modello_aggregato.json, che contiene solo parametri e conteggi aggregati gia' calcolati
  (coefficienti delle regressioni, tavoli per prodotto, per coppia di prodotti, per prodotto e categoria,
  per prodotto e contesto). Serve per pubblicare l'app online senza pubblicare gli scontrini: i suggerimenti sono identici.
"""
import json
import os

import numpy as np
import pandas as pd
from baseline import carica_turni, BaselineCategorieComplementari as BC
from regole import RaccomandatoreRegole, MIN_COPPIE
from contesto import ModelloCategorie, tabella_turni, VARIABILI
from momento import non_consentite_fasi, TARDIVE, e_principale

GIORNI = {"Lunedì": "feriale", "Martedì": "feriale", "Mercoledì": "feriale", "Giovedì": "feriale",
          "Venerdì": "ven", "Sabato": "sab", "Domenica": "dom"}
FASCE = {"Prima delle 20": "prima_20", "20:00 - 20:59": "20_21", "Dopo le 21": "dopo_21"}
SOGLIA = 0.10   # sotto questa probabilita' il sistema sta in silenzio
MIN_STORICO = 10   # sotto questo numero di tavoli il piatto non ha storico: nessun suggerimento (e mai dati di altri piatti al suo posto)


def etichetta_commensali(n):
    return "1_2" if n <= 2 else ("3_4" if n <= 4 else "5+")


class _Logit:
    """Regressione logistica gia' addestrata (solo coefficienti), con la stessa interfaccia di sklearn usata dal motore."""
    def __init__(self, w, b):
        self.w, self.b = np.asarray(w, dtype=float), float(b)

    def predict_proba(self, F):
        p = 1 / (1 + np.exp(-(np.asarray(F, dtype=float) @ self.w + self.b)))
        return np.column_stack([1 - p, p])


class Motore:
    def __init__(self, percorso_csv="dettaglio_ordini_cena.csv", dati=None, percorso_aggregato="modello_aggregato.json"):
        if dati is None and not os.path.exists(percorso_csv) and os.path.exists(percorso_aggregato):
            self._da_aggregato(percorso_aggregato)      # versione online: nessuno scontrino, solo dati aggregati
            return
        d = carica_turni(percorso_csv) if dati is None else dati   # dati: per la valutazione, solo il training
        self.d = d
        self.fam = dict(zip(d["nome_articolo"], d["macro_categoria"].map(BC._famiglia)))
        turni = tabella_turni(d)
        self.turni = turni
        self.tutte = ModelloCategorie(VARIABILI).fit(d, turni)       # categorie + contesto
        self.solo = ModelloCategorie([]).fit(d, turni)               # solo categorie nel carrello
        self.singole = {v: ModelloCategorie([v]).fit(d, turni) for v in VARIABILI}   # una variabile alla volta (per le motivazioni)
        self.regole = RaccomandatoreRegole().fit(d)                  # associazioni tra prodotti e categorie
        self.cats = self.tutte.cats
        self.base = {c: self.regole.nC[self.regole.ci[c]] / self.regole.n_turni for c in self.cats}
        unit = (d["prezzo"] / d["quantita"].where(d["quantita"] > 0, 1))
        self.prezzo = unit.groupby(d["nome_articolo"]).median().round(2).to_dict()
        r = self.regole
        riga = {x: i for i, x in enumerate(sorted(d["identificativo_turno"].unique()))}
        P = np.zeros((len(riga), len(r.prodotti))); Cm = np.zeros((len(riga), len(r.cats)))
        for tur, nome, fm in zip(d["identificativo_turno"], d["nome_articolo"], d["nome_articolo"].map(self.fam)):
            P[riga[tur], r.pi[nome]] = 1
            Cm[riga[tur], r.ci[fm]] = 1
        self.con_cat = P.T @ Cm                                     # piatto x categoria: tavoli con il piatto che hanno ordinato anche la categoria
        self.Q = self.con_cat / np.maximum(P.sum(0)[:, None], 1)    # la stessa cosa, come quota
        # tavoli per piatto e per contesto (giorno|fascia|commensali): servono a mostrare i dati di contesto della motivazione
        chiavi = (turni["giorno"] + "|" + turni["fascia"] + "|" + turni["commensali"]).reindex(sorted(riga)).values
        self.ctx = {}
        for k in sorted(set(chiavi)):
            idx = np.where(chiavi == k)[0]
            self.ctx[k] = (P[idx].sum(0), P[idx].T @ Cm[idx])
        self.disponibili = None     # prodotti realmente presenti nel menu di oggi (impostati dall'app)
        self.menu = (d.assign(fam=d["nome_articolo"].map(self.fam))
                     .groupby(["macro_categoria"])["nome_articolo"].apply(lambda s: sorted(set(s))).to_dict())

    # ------------------------------------------------------------------ dati aggregati (per la versione online)
    def esporta_aggregato(self, percorso="modello_aggregato.json"):
        """Salva solo cio' che serve all'app: parametri dei modelli e conteggi aggregati, nessun tavolo singolo.
        I conteggi per contesto si salvano solo per i piatti con almeno MIN_STORICO tavoli (gli unici su cui il sistema propone)."""
        r = self.regole
        ok = (r.nP >= MIN_STORICO)[:, None]

        def modello(mc):
            return {"variabili": mc.variabili, "q": list(map(float, mc.q)), "cats": mc.cats,
                    "W": [list(map(float, m.coef_[0])) for m in mc.modelli],
                    "b": [float(m.intercept_[0]) for m in mc.modelli]}

        out = {"fam": self.fam, "prezzo": self.prezzo, "menu": self.menu, "cats": self.cats,
               "regole": {"prodotti": r.prodotti, "cats": r.cats, "conf_cat": r.conf_cat.round(10).tolist(),
                          "coppie": r.coppie.astype(int).tolist(), "nP": r.nP.astype(int).tolist(),
                          "nC": r.nC.astype(int).tolist(), "n_turni": int(r.n_turni),
                          "cat_di": {p: int(i) for p, i in r.cat_di.items()}},
               "con_cat": (self.con_cat * ok).astype(int).tolist(),
               "ctx": {k: {"n": (n * ok[:, 0]).astype(int).tolist(), "c": (c * ok).astype(int).tolist()} for k, (n, c) in self.ctx.items()},
               "modelli": {"tutte": modello(self.tutte), "solo": modello(self.solo),
                           **{"solo_" + v: modello(m) for v, m in self.singole.items()}}}
        with open(percorso, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        return percorso

    def _da_aggregato(self, percorso):
        A = json.load(open(percorso, encoding="utf-8"))
        self.d = None
        self.fam, self.prezzo, self.menu = A["fam"], A["prezzo"], A["menu"]

        def modello(x):
            mc = ModelloCategorie(x["variabili"])
            mc.cats, mc.q = x["cats"], np.array(x["q"])
            mc.ci = {c: i for i, c in enumerate(mc.cats)}
            mc.modelli = [_Logit(w, b) for w, b in zip(x["W"], x["b"])]
            return mc

        M = A["modelli"]
        self.tutte, self.solo = modello(M["tutte"]), modello(M["solo"])
        self.singole = {v: modello(M["solo_" + v]) for v in VARIABILI}
        R, r = A["regole"], RaccomandatoreRegole()
        r.prodotti, r.cats = R["prodotti"], R["cats"]
        r.pi = {p: i for i, p in enumerate(r.prodotti)}
        r.ci = {c: i for i, c in enumerate(r.cats)}
        r.conf_cat = np.array(R["conf_cat"])
        r.coppie = np.array(R["coppie"], dtype=float)
        r.nP, r.nC, r.n_turni = np.array(R["nP"], dtype=float), np.array(R["nC"], dtype=float), R["n_turni"]
        r.vendite = r.nP
        r.cat_di = R["cat_di"]
        r.conf_prod = np.where(r.coppie >= MIN_COPPIE, r.coppie / np.maximum(r.nP[:, None], 1), -1.0)
        r.prod_per_cat = {c: [r.pi[p] for p in r.prodotti if r.cat_di[p] == r.ci[c]] for c in r.cats}
        self.regole = r
        self.cats = self.tutte.cats
        self.base = {c: r.nC[r.ci[c]] / r.n_turni for c in self.cats}
        self.con_cat = np.array(A["con_cat"], dtype=float)
        self.Q = self.con_cat / np.maximum(r.nP[:, None], 1)
        self.ctx = {k: (np.array(v["n"], dtype=float), np.array(v["c"], dtype=float)) for k, v in A["ctx"].items()}
        self.disponibili = None

    def imposta_menu(self, disponibili, prezzi):
        """Limita i suggerimenti ai prodotti presenti nel menu attuale e usa i prezzi attuali."""
        self.disponibili = set(disponibili)
        self.prezzo.update(prezzi)

    # ------------------------------------------------------------------
    def valore_carrello(self, carrello):
        return round(sum(self.prezzo.get(p, 0) for p in carrello), 2)

    def suggerisci(self, carrello, giorno, fascia, n_commensali, k=3, valore=None, ultimo=None, n_prodotti=3, usa_contesto=True):
        """Restituisce (suggerimenti, regole operative applicate, contesto)."""
        cat_cart = sorted({self.fam[p] for p in carrello})
        if ultimo and (ultimo not in self.regole.pi or self.regole.nP[self.regole.pi[ultimo]] < MIN_STORICO):
            return [], ["Nessun suggerimento: il piatto non ha storico sufficiente (almeno %d tavoli) per basare una raccomandazione sui dati." % MIN_STORICO], \
                {"Giorno": giorno, "Fascia": fascia, "Commensali": n_commensali, "Valore del carrello": valore}
        bloccate = non_consentite_fasi(cat_cart, self.cats, self.fam.get(ultimo) if ultimo else None)
        valore = self.valore_carrello(carrello) if valore is None else valore
        comm = etichetta_commensali(n_commensali)
        vpp = valore / max(n_commensali, 1)
        p_ctx = self.tutte.probabilita(cat_cart, giorno, fascia, comm, vpp)
        p_solo = self.solo.probabilita(cat_cart, giorno, fascia, comm, vpp)
        if not usa_contesto:        # solo per la valutazione: stesso sistema senza variabili di contesto
            p_ctx = p_solo
        p_var = {v: m.probabilita(cat_cart, giorno, fascia, comm, vpp) for v, m in self.singole.items()}

        regole_applicate = []
        regole_applicate.append("Momento del pasto: dopo l'antipasto si propone un piatto principale, dopo il principale una bevanda, dopo la bevanda il dolce, dopo il dolce il caffè, dopo il caffè l'amaro. Se la bevanda è già nel carrello prima del piatto, dopo il piatto si propone direttamente il dolce.")
        if not any(e_principale(c) for c in cat_cart):
            regole_applicate.append("Dolci, caffè e amari/digestivi non vengono proposti finché nel carrello non c'è un piatto principale (pizza, primo o secondo).")
        if cat_cart:
            regole_applicate.append("Non si propone una categoria già presente nel carrello: " + ", ".join(cat_cart) + ".")
        regole_applicate.append("La categoria si sceglie in base ai dati dell'ultimo piatto aggiunto (quota di tavoli con quel piatto che hanno ordinato la categoria), corretti dal contesto.")
        regole_applicate.append("Si propone una categoria solo se la probabilità stimata è almeno del %d%%: altrimenti il sistema sta in silenzio." % int(SOGLIA * 100))

        # punteggio di ogni categoria: dati del piatto appena scelto (quota di tavoli con quel piatto che hanno ordinato la categoria),
        # corretti dal contesto con il rapporto tra la probabilita' del modello con e senza contesto
        qd = self.Q[self.regole.pi[ultimo]] if ultimo else None

        def aggiusta(q, ps, pc):
            q, ps, pc = [min(max(x, 1e-6), 1 - 1e-6) for x in (q, ps, pc)]
            odds = q / (1 - q) * (pc / (1 - pc)) / (ps / (1 - ps))
            return odds / (1 + odds)

        punt = np.array([aggiusta(qd[i], p_solo[i], p_ctx[i]) if ultimo else p_ctx[i] for i in range(len(self.cats))])
        for i, c in enumerate(self.cats):
            if c in cat_cart or c in bloccate:
                punt[i] = -1
            elif self.disponibili is not None and not any(self.regole.prodotti[j] in self.disponibili for j in self.regole.prod_per_cat[c]):
                punt[i] = -1        # nessun prodotto di questa categoria e' nel menu attuale
            elif ultimo and qd[i] <= 0:
                punt[i] = -1        # mai ordinata insieme a questo piatto nello storico
        out = []
        for i in np.argsort(-punt)[:k]:
            if punt[i] < SOGLIA:
                continue
            c = self.cats[i]
            if ultimo:
                n_t = int(self.regole.nP[self.regole.pi[ultimo]])
                delta = (punt[i] - qd[i]) * 100
                motivo = [f"Nel {qd[i]:.0%} dei tavoli con «{ultimo}» ({n_t} tavoli) c'era anche «{c}» (in media: {self.base[c]:.0%}).",
                          (f"Il contesto {'aumenta' if delta > 0 else 'riduce'} la probabilità di {abs(delta):.0f} punti ({qd[i]:.0%} → {punt[i]:.0%})." if abs(delta) >= 1
                           else "Il contesto cambia poco la probabilità.")]
            else:
                motivo = self._motivo_categoria(c, i, cat_cart, p_ctx[i], p_solo[i])
            out.append({"categoria": c, "prob": float(punt[i]), "prob_modello": float(p_ctx[i]), "prob_solo": float(p_solo[i]),
                        "quota_piatto": float(qd[i]) if ultimo else None, "base": self.base[c],
                        "motivo": motivo,
                        "effetti": {v: float(p_var[v][i] - p_solo[i]) for v in VARIABILI},
                        "prodotti": self._prodotti_per(c, carrello, ultimo, n_prodotti)})
        contesto = {"Giorno": giorno, "Fascia": fascia, "Commensali": n_commensali, "Valore del carrello": valore}
        return out, regole_applicate, contesto

    # ------------------------------------------------------------------
    def _motivo_categoria(self, c, j, cat_cart, p, p_solo):
        r = self.regole
        righe = []
        migliore = None
        for a in cat_cart:
            ia = r.ci[a]
            if r.nC[ia] < MIN_COPPIE:
                continue
            conf = r.conf_cat[ia, j]; lift = conf / self.base[c]
            if migliore is None or lift > migliore[2]:
                migliore = (a, conf, lift)
        if migliore and migliore[2] >= 1.1:
            a, conf, _ = migliore
            righe.append(f"Nel {conf:.0%} dei tavoli passati con «{a}» c'era anche «{c}» (in media: {self.base[c]:.0%}).")
        else:
            righe.append(f"«{c}» è molto ordinata in generale ({self.base[c]:.0%} dei tavoli)" + ("." if not cat_cart else " e il carrello non la rende più o meno probabile."))
        delta = (p - p_solo) * 100
        if abs(delta) >= 1:
            righe.append(f"Il contesto {'aumenta' if delta > 0 else 'riduce'} la probabilità di {abs(delta):.0f} punti ({p_solo:.0%} → {p:.0%}).")
        else:
            righe.append("Il contesto cambia poco la probabilità.")
        return righe

    def storico_piatto(self, ultimo):
        """True se il piatto ha abbastanza tavoli (MIN_STORICO) per usare i suoi dati. Non si usano mai dati di altri piatti al posto suoi."""
        return ultimo in self.regole.pi and self.regole.nP[self.regole.pi[ultimo]] >= MIN_STORICO

    def quota_categoria(self, ultimo, c):
        """Quota di tavoli con `ultimo` in cui c'era almeno un prodotto della categoria `c` (e numero di tavoli).
        Se il piatto non ha storico sufficiente non si usano dati di altri piatti: (0, 0)."""
        if not self.storico_piatto(ultimo):
            return 0.0, 0
        a = self.regole.pi[ultimo]
        return float(self.Q[a, self.cats.index(c)]), int(self.regole.nP[a])

    def profilo_contesto(self, ultimo, c, giorno, fascia, commensali, minimo=15):
        """Dai dati: quota di tavoli con `ultimo` e quel contesto che hanno ordinato anche la categoria `c`.
        Restituisce (quota nel contesto, tavoli, quota media, lista di variabili usate, dettaglio per variabile)."""
        a, ci = self.regole.pi[ultimo], self.cats.index(c)
        comm = etichetta_commensali(commensali)
        filtri = [("giorno", giorno), ("fascia", fascia), ("commensali", comm)]
        pos = {"giorno": 0, "fascia": 1, "commensali": 2}

        def conta(condizioni):
            n = k = 0.0
            for chiave, (np_, cc) in self.ctx.items():
                parti = chiave.split("|")
                if all(parti[pos[v]] == val for v, val in condizioni):
                    n += np_[a]; k += cc[a, ci]
            return int(n), k

        n_tot, k_tot = conta([])
        media = k_tot / n_tot if n_tot else 0.0
        dettaglio = []
        for v, val in filtri:
            n, k = conta([(v, val)])
            dettaglio.append((v, val, float(k / n) if n else None, n))
        usate = list(filtri)
        while True:
            n, k = conta(usate)
            if n >= minimo or not usate:
                break
            usate = usate[1:]                      # pochi tavoli: si toglie la variabile meno stabile (prima il giorno)
        return (float(k / n) if n else 0.0), n, float(media), usate, dettaglio

    def ordina_categoria(self, c, ultimo):
        """Prodotti della categoria `c` (presenti nel menu) ordinati per quante volte sono stati ordinati insieme a `ultimo`.
        Restituisce [(prodotto, tavoli insieme, quota sui tavoli con `ultimo`)]; quelli mai ordinati insieme vengono dopo, in ordine alfabetico."""
        r = self.regole
        a = r.pi.get(ultimo) if self.storico_piatto(ultimo) else None
        righe = []
        for j in r.prod_per_cat[c]:
            nome = r.prodotti[j]
            if self.disponibili is not None and nome not in self.disponibili:
                continue
            n = int(r.coppie[a, j]) if a is not None else 0
            righe.append((nome, n, n / r.nP[a] if a is not None and r.nP[a] else 0.0))
        con = sorted([x for x in righe if x[1] > 0], key=lambda x: (-x[1], x[0]))
        senza = sorted([x for x in righe if x[1] == 0], key=lambda x: x[0])
        return con + senza

    def _prodotti_per(self, c, carrello, ultimo, n):
        """Prodotti della categoria piu' spesso ordinati insieme all'ultimo piatto aggiunto (se ci sono abbastanza dati), altrimenti insieme al carrello."""
        if ultimo and ultimo in self.regole.pi:
            prod = self._prodotti(c, [ultimo], n)
            if prod and prod[0]["motivo"].startswith("Ordinato insieme"):
                return prod
        return self._prodotti(c, carrello, n)

    def _prodotti(self, c, carrello, n=3):
        r = self.regole
        cart = [r.pi[p] for p in carrello if p in r.pi]
        cand = [j for j in r.prod_per_cat[c] if self.disponibili is None or r.prodotti[j] in self.disponibili]
        righe = []
        for jj in cand:
            nome = r.prodotti[jj]
            migliore = None
            for a in cart:
                n_ins = r.coppie[a, jj]
                if n_ins >= MIN_COPPIE:
                    conf = n_ins / r.nP[a]
                    if migliore is None or conf > migliore[2]:
                        migliore = (r.prodotti[a], int(n_ins), conf)
            righe.append((nome, migliore, r.vendite[jj]))
        righe.sort(key=lambda x: (-(x[1][2] if x[1] else -1), -x[2]))
        out = []
        for nome, m, vend in righe[:n]:
            if m:
                motivo = f"Ordinato insieme a «{m[0]}» in {m[1]} tavoli ({m[2]:.0%} dei tavoli con quel prodotto)."
            else:
                motivo = f"Tra i più venduti della categoria ({int(vend)} tavoli)."
            out.append({"nome": nome, "prezzo": self.prezzo.get(nome), "motivo": motivo})
        return out
