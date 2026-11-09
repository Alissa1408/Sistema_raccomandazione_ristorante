"""Punto 7: variabili di contesto (giorno, fascia oraria, commensali).

Modello a livello di categoria: per ogni categoria una regressione logistica che stima la probabilita' che il tavolo
la ordini, dati (a) le categorie gia' nel carrello e, nelle versioni con contesto, (b) le variabili di contesto.
Il confronto "solo carrello" contro "carrello + contesto" usa lo stesso modello, cambiano solo le informazioni in ingresso.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from baseline import BaselineCategorieComplementari as BC
from momento import non_consentite

VARIABILI = ["giorno", "fascia", "commensali"]   # il valore del carrello non si usa: durante l'ordine non si sa quanto spendera' il cliente


def tabella_turni(d):
    """Una riga per turno: giorno, fascia oraria (prima ora del turno), commensali."""
    g = d.groupby("identificativo_turno")
    t = pd.DataFrame({"data": g["data"].first(), "ora": g["Ora"].min(), "n": g["n_commensali"].first(),
                      "totale": g["prezzo"].sum()})
    gs = t["data"].dt.dayofweek                       # 0 = lunedi
    t["giorno"] = np.select([gs == 4, gs == 5, gs == 6], ["ven", "sab", "dom"], "feriale")
    ora = t["ora"].str[:2].astype(int)
    t["fascia"] = np.select([ora < 20, ora == 20], ["prima_20", "20_21"], "dopo_21")
    n = t["n"].fillna(t["n"].median())
    t["commensali"] = np.select([n <= 2, n <= 4], ["1_2", "3_4"], "5+")
    t["n"] = n
    return t


class ModelloCategorie:
    """variabili: lista di variabili di contesto da usare (vuota = solo categorie nel carrello)."""
    def __init__(self, variabili=(), C=1.0):
        self.variabili, self.C = list(variabili), C

    def _contesto(self, giorno, fascia, commensali, valore_pp):
        cols = []
        if "giorno" in self.variabili:
            cols += [(giorno == v).astype(float) for v in ("ven", "sab", "dom")]
        if "fascia" in self.variabili:
            cols += [(fascia == v).astype(float) for v in ("prima_20", "dopo_21")]
        if "commensali" in self.variabili:
            cols += [(commensali == v).astype(float) for v in ("3_4", "5+")]
        if "valore" in self.variabili:       # valore del carrello per persona
            cols += [(valore_pp <= self.q[0]).astype(float), (valore_pp > self.q[1]).astype(float)]
        return np.column_stack(cols) if cols else np.zeros((len(giorno), 0))

    def fit(self, train, turni):
        t = train.assign(fam=train["macro_categoria"].map(BC._famiglia))
        self.cats = sorted(t["fam"].unique()); ci = {c: i for i, c in enumerate(self.cats)}
        ids = sorted(t["identificativo_turno"].unique()); riga = {x: i for i, x in enumerate(ids)}
        X = np.zeros((len(ids), len(self.cats)))
        for r, c in zip(t["identificativo_turno"], t["fam"]):
            X[riga[r], ci[c]] = 1
        prezzo_cat = np.zeros((len(ids), len(self.cats)))          # euro di ogni categoria nel turno
        for r, c, p in zip(t["identificativo_turno"], t["fam"], t["prezzo"]):
            prezzo_cat[riga[r], ci[c]] += p
        tt = turni.loc[ids]
        n = tt["n"].values
        totale = tt["totale"].values
        self.q = np.percentile(totale / n, [33.3, 66.7])
        self.modelli = []
        for j in range(len(self.cats)):
            cart = X.copy(); cart[:, j] = 0                       # il carrello non contiene la categoria da stimare
            valore_pp = (totale - prezzo_cat[:, j]) / n           # valore del carrello senza quella categoria
            F = np.hstack([cart, self._contesto(tt["giorno"].values, tt["fascia"].values, tt["commensali"].values, valore_pp)])
            self.modelli.append(LogisticRegression(C=self.C, max_iter=500).fit(F, X[:, j]))
        self.ci = ci
        return self

    def probabilita(self, cat_carrello, giorno, fascia, commensali, valore_pp):
        """Probabilita' stimata per ogni categoria, per un solo carrello (usata dal prototipo)."""
        cart = np.zeros((1, len(self.cats)))
        for cat in cat_carrello:
            if cat in self.ci:
                cart[0, self.ci[cat]] = 1
        ctx = self._contesto(np.array([giorno]), np.array([fascia]), np.array([commensali]), np.array([valore_pp]))
        F = np.hstack([cart, ctx])
        return np.array([m.predict_proba(F)[0, 1] for m in self.modelli])

    def punteggi(self, casi, turni, prezzi):
        """Matrice casi x categorie con la probabilita' stimata. prezzi: dict (turno, prodotto) -> prezzo."""
        ci = self.ci
        cart = np.zeros((len(casi), len(self.cats)))
        for i, c in enumerate(casi):
            for cat in c["cat_carrello"]:
                if cat in ci:
                    cart[i, ci[cat]] = 1
        tt = turni.loc[[c["turno"] for c in casi]]
        valore = np.array([tt["totale"].iloc[i] - sum(prezzi[(c["turno"], p)] for p in c["nascosti"]) for i, c in enumerate(casi)])
        ctx = self._contesto(tt["giorno"].values, tt["fascia"].values, tt["commensali"].values, valore / tt["n"].values)
        F = np.hstack([cart, ctx])
        return np.column_stack([m.predict_proba(F)[:, 1] for m in self.modelli]), cart

    def suggerimenti(self, casi, turni, prezzi, k=3):
        P, cart = self.punteggi(casi, turni, prezzi)
        out = []
        for i, c in enumerate(casi):
            p = P[i].copy()
            p[cart[i] == 1] = -1
            for x in non_consentite(c["cat_carrello"]):
                if x in self.ci:
                    p[self.ci[x]] = -2
            out.append([self.cats[j] for j in np.argsort(-p, kind="stable")[:k]])
        return out
