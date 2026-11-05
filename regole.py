"""Punto 5: sistema di raccomandazione basato sulle regole (calcolate solo sul training).

Livello categoria: per ogni categoria non ancora nel carrello si prende la confidenza piu' alta
tra le regole "categoria del carrello -> categoria candidata" e si propongono le K categorie col punteggio maggiore.
Livello prodotto: per ciascuna delle K categorie si propone il prodotto migliore: quello con la confidenza piu' alta
rispetto ai prodotti del carrello (solo coppie viste in almeno MIN_COPPIE turni); se non ci sono dati, il piu' venduto della categoria.
"""
import numpy as np
import pandas as pd
from baseline import BaselineCategorieComplementari as BC

MIN_COPPIE = 30  # turni minimi in cui due prodotti compaiono insieme


class RaccomandatoreRegole:
    def fit(self, train):
        t = train.assign(fam=train["macro_categoria"].map(BC._famiglia))
        turni = sorted(t["identificativo_turno"].unique())
        riga = {x: i for i, x in enumerate(turni)}
        self.prodotti = sorted(t["nome_articolo"].unique())
        self.cats = sorted(t["fam"].unique())
        pi = {p: i for i, p in enumerate(self.prodotti)}
        ci = {c: i for i, c in enumerate(self.cats)}
        P = np.zeros((len(turni), len(self.prodotti)))
        Cm = np.zeros((len(turni), len(self.cats)))
        for r, p, c in zip(t["identificativo_turno"], t["nome_articolo"], t["fam"]):
            P[riga[r], pi[p]] = 1
            Cm[riga[r], ci[c]] = 1
        self.pi, self.ci = pi, ci
        nP, nC = P.sum(0), Cm.sum(0)
        # confidenza a->b = turni con entrambi / turni con a
        self.conf_cat = (Cm.T @ Cm) / np.maximum(nC[:, None], 1)
        coppie = P.T @ P
        self.conf_prod = np.where(coppie >= MIN_COPPIE, coppie / np.maximum(nP[:, None], 1), -1.0)
        self.vendite = nP
        self.coppie, self.nP, self.nC, self.n_turni = coppie, nP, nC, len(turni)
        self.cat_di = {p: ci[c] for p, c in zip(t["nome_articolo"], t["fam"])}
        self.prod_per_cat = {c: [pi[p] for p in self.prodotti if self.cat_di[p] == ci[c]] for c in self.cats}
        return self

    def categorie(self, cat_carrello, k=3, escludi=()):
        idx = [self.ci[c] for c in cat_carrello if c in self.ci]
        punt = self.conf_cat[idx].max(0) if idx else np.zeros(len(self.cats))
        for i in idx:
            punt[i] = -1                       # mai una categoria gia' nel carrello
        for c in escludi:                      # categorie non ancora consentite (momento del pasto)
            if c in self.ci:
                punt[self.ci[c]] = -2
        ordine = np.argsort(-punt, kind="stable")[:k]
        return [self.cats[i] for i in ordine]

    def prodotti_(self, carrello, k=3, escludi=()):
        cart = [self.pi[p] for p in carrello if p in self.pi]
        cat_cart = {self.cat_di[p] for p in carrello if p in self.cat_di}
        out = []
        for c in self.categorie([self.cats[i] for i in cat_cart], k, escludi):
            cand = self.prod_per_cat[c]
            punt = self.conf_prod[np.ix_(cart, cand)].max(0) if cart else np.full(len(cand), -1.0)
            ordine = sorted(range(len(cand)), key=lambda j: (-punt[j], -self.vendite[cand[j]]))
            out.append(self.prodotti[cand[ordine[0]]])
        return out
