"""Verifiche tecniche: baseline con gli stessi vincoli, intervalli di confidenza e conferma su piu' finestre temporali."""
import numpy as np, pandas as pd
from baseline import *
from simulazione import *
from momento import *
from regole import *
from contesto import *
from valutazione import differenza_bootstrap


def prepara(percorso='dettaglio_ordini_cena.csv'):
    d = carica_turni(percorso)
    fam = dict(zip(d['nome_articolo'], d['macro_categoria'].map(BaselineCategorieComplementari._famiglia)))
    turni = tabella_turni(d)
    prezzi = {(a, b): c for a, b, c in zip(d['identificativo_turno'], d['nome_articolo'], d['prezzo'])}
    return d, fam, turni, prezzi


def finestre(d, inizio=0.5, passo=0.125):
    """Finestre in avanti: si impara sulle serate piu' vecchie e si valuta sul blocco successivo."""
    date = sorted(d['data'].unique()); n = len(date)
    tagli = [inizio + i * passo for i in range(int(round((1 - inizio) / passo)) + 1)]
    for a, b in zip(tagli[:-1], tagli[1:]):
        t0, t1 = date[int(n * a)], (date[int(n * b)] if b < 1 else None)
        train = d[d['data'] < t0]
        test = d[(d['data'] >= t0) & ((d['data'] < t1) if t1 is not None else True)]
        yield a, b, train, test


def sistemi_categorie(train, fam, turni, prezzi, casi):
    """Hit per caso (K=1,3) per ogni sistema a livello di categoria. Tutti con gli stessi vincoli."""
    C = BaselineCategorieSole().fit(train); R = RaccomandatoreRegole().fit(train)
    solo = ModelloCategorie([]).fit(train, turni); tutte = ModelloCategorie(VARIABILI).fit(train, turni)
    s = {'Baseline C (categorie più frequenti)': [[x for x in C.raccomanda(c['cat_carrello'], 60) if x not in non_consentite(c['cat_carrello'])][:5] for c in casi],
         'Regole (punto 5)': [R.categorie(c['cat_carrello'], 5, non_consentite(c['cat_carrello'])) for c in casi],
         'Modello solo carrello': solo.suggerimenti(casi, turni, prezzi, 5),
         'Modello carrello + contesto': tutte.suggerimenti(casi, turni, prezzi, 5)}
    return {nome: {K: np.array([any(x in c['cat_nascoste'] for x in v[i][:K]) for i, c in enumerate(casi)], float) for K in (1, 3)} for nome, v in s.items()}


def sistemi_prodotti(train, fam, casi):
    """Hit per caso (K=1,3) a livello di prodotto. Baseline A vincolata: i piu' venduti, ma solo di categorie consentite e non nel carrello."""
    A = BaselineProdotti().fit(train); B2 = BaselineCategorieComplementari().fit(train); R = RaccomandatoreRegole().fit(train)
    def a_vinc(c, K=5):
        nc = non_consentite(c['cat_carrello']) | set(c['cat_carrello'])
        return [p for p in A.raccomanda(c['carrello'], 80) if fam[p] not in nc][:K]
    def b2(c, K=5):
        nc = non_consentite(c['cat_carrello']); return [p for p in B2.raccomanda(c['carrello'], 60) if fam[p] not in nc][:K]
    s = {'Baseline A vincolata (più venduti, stessi vincoli)': [a_vinc(c) for c in casi],
         'Baseline B2 (categorie + prodotto top)': [b2(c) for c in casi],
         'Regole (punto 5)': [R.prodotti_(c['carrello'], 5, non_consentite(c['cat_carrello'])) for c in casi]}
    return {nome: {K: np.array([any(x in c['nascosti'] for x in v[i][:K]) for i, c in enumerate(casi)], float) for K in (1, 3)} for nome, v in s.items()}
