"""Motore del prototipo: modello con categorie + contesto, regole operative e motivazioni."""
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


def etichetta_commensali(n):
    return "1_2" if n <= 2 else ("3_4" if n <= 4 else "5+")


class Motore:
    def __init__(self, percorso_csv="dettaglio_ordini_cena.csv"):
        d = carica_turni(percorso_csv)
        self.d = d
        self.fam = dict(zip(d["nome_articolo"], d["macro_categoria"].map(BC._famiglia)))
        turni = tabella_turni(d)
        self.tutte = ModelloCategorie(VARIABILI).fit(d, turni)       # categorie + contesto
        self.solo = ModelloCategorie([]).fit(d, turni)               # solo categorie nel carrello
        self.singole = {v: ModelloCategorie([v]).fit(d, turni) for v in VARIABILI}   # una variabile alla volta (per le motivazioni)
        self.regole = RaccomandatoreRegole().fit(d)                  # associazioni tra prodotti e categorie
        self.cats = self.tutte.cats
        self.base = {c: self.regole.nC[self.regole.ci[c]] / self.regole.n_turni for c in self.cats}
        unit = (d["prezzo"] / d["quantita"].where(d["quantita"] > 0, 1))
        self.prezzo = unit.groupby(d["nome_articolo"]).median().round(2).to_dict()
        self.disponibili = None     # prodotti realmente presenti nel menu di oggi (impostati dall'app)
        self.menu = (d.assign(fam=d["nome_articolo"].map(self.fam))
                     .groupby(["macro_categoria"])["nome_articolo"].apply(lambda s: sorted(set(s))).to_dict())

    def imposta_menu(self, disponibili, prezzi):
        """Limita i suggerimenti ai prodotti presenti nel menu attuale e usa i prezzi attuali."""
        self.disponibili = set(disponibili)
        self.prezzo.update(prezzi)

    # ------------------------------------------------------------------
    def valore_carrello(self, carrello):
        return round(sum(self.prezzo.get(p, 0) for p in carrello), 2)

    def suggerisci(self, carrello, giorno, fascia, n_commensali, k=3, valore=None, ultimo=None, n_prodotti=3):
        """Restituisce (suggerimenti, regole operative applicate, contesto)."""
        cat_cart = sorted({self.fam[p] for p in carrello})
        if ultimo and (ultimo not in self.regole.pi or self.regole.nP[self.regole.pi[ultimo]] < MIN_COPPIE):
            return [], ["Nessun suggerimento: il piatto non ha abbastanza storico (almeno %d tavoli) per basare una raccomandazione sui dati." % MIN_COPPIE], \
                {"Giorno": giorno, "Fascia": fascia, "Commensali": n_commensali, "Valore del carrello": valore}
        bloccate = non_consentite_fasi(cat_cart, self.cats, self.fam.get(ultimo) if ultimo else None)
        comm = etichetta_commensali(n_commensali)
        valore = self.valore_carrello(carrello) if valore is None else valore
        vpp = valore / max(n_commensali, 1)
        p_ctx = self.tutte.probabilita(cat_cart, giorno, fascia, comm, vpp)
        p_solo = self.solo.probabilita(cat_cart, giorno, fascia, comm, vpp)
        p_var = {v: m.probabilita(cat_cart, giorno, fascia, comm, vpp) for v, m in self.singole.items()}

        regole_applicate = []
        regole_applicate.append("Momento del pasto: dopo l'antipasto si propone un piatto principale, dopo il principale una bevanda, dopo la bevanda il dolce, dopo il dolce il caffè, dopo il caffè l'amaro. Se la bevanda è già nel carrello prima del piatto, dopo il piatto si propone direttamente il dolce.")
        if not any(e_principale(c) for c in cat_cart):
            regole_applicate.append("Dolci, caffè e amari/digestivi non vengono proposti finché nel carrello non c'è un piatto principale (pizza, primo o secondo).")
        if cat_cart:
            regole_applicate.append("Non si propone una categoria già presente nel carrello: " + ", ".join(cat_cart) + ".")
        regole_applicate.append("Si propone una categoria solo se, con questo carrello, è più frequente della media nei tavoli che hanno ordinato l'ultimo piatto aggiunto.")
        regole_applicate.append("Si propone una categoria solo se la probabilità stimata è almeno del %d%%: altrimenti il sistema sta in silenzio." % int(SOGLIA * 100))

        punt = p_ctx.copy()
        for i, c in enumerate(self.cats):
            if c in cat_cart or c in bloccate:
                punt[i] = -1
            elif self.disponibili is not None and not any(self.regole.prodotti[j] in self.disponibili for j in self.regole.prod_per_cat[c]):
                punt[i] = -1        # nessun prodotto di questa categoria e' nel menu attuale
        out = []
        for i in np.argsort(-punt)[:k]:
            if punt[i] < SOGLIA:
                continue
            c = self.cats[i]
            if ultimo and self.quota_categoria(ultimo, c)[0] <= 0:
                continue        # mai ordinata insieme a questo piatto nello storico: non si propone
            if ultimo and ultimo in self.fam and c not in TARDIVE:
                a = self.fam[ultimo]
                if a in self.regole.ci and self.regole.nC[self.regole.ci[a]] >= MIN_COPPIE \
                        and self.regole.conf_cat[self.regole.ci[a], i] < self.base[c]:
                    continue    # chi ordina l'ultimo piatto prende questa categoria MENO della media: non e' un'associazione, silenzio
            out.append({"categoria": c, "prob": float(p_ctx[i]), "prob_solo": float(p_solo[i]), "base": self.base[c],
                        "motivo": self._motivo_categoria(c, i, cat_cart, p_ctx[i], p_solo[i]),
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

    def quota_categoria(self, ultimo, c):
        """Quota di tavoli con `ultimo` in cui c'era almeno un prodotto della categoria `c` (e numero di tavoli)."""
        d = self.d
        t_u = set(d.loc[d["nome_articolo"] == ultimo, "identificativo_turno"])
        if not t_u:
            return 0.0, 0
        in_c = set(d.loc[d["nome_articolo"].map(self.fam) == c, "identificativo_turno"])
        return len(t_u & in_c) / len(t_u), len(t_u)

    def ordina_categoria(self, c, ultimo):
        """Prodotti della categoria `c` (presenti nel menu) ordinati per quante volte sono stati ordinati insieme a `ultimo`.
        Restituisce [(prodotto, tavoli insieme, quota sui tavoli con `ultimo`)]; quelli mai ordinati insieme vengono dopo, in ordine alfabetico."""
        r = self.regole
        a = r.pi.get(ultimo)
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
