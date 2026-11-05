"""Punto 5 - esecuzione: tabella dei risultati e confronto con intervallo di confidenza.
Servono nella stessa cartella baseline.py, simulazione.py, regole.py, momento.py, valutazione.py e dettaglio_ordini_cena.csv."""
import pandas as pd
from baseline import *
from simulazione import *
from regole import *
from momento import *
from valutazione import *

d = carica_turni('dettaglio_ordini_cena.csv')
train, test, taglio = dividi_temporale(d)
fam = dict(zip(d['nome_articolo'], d['macro_categoria'].map(BaselineCategorieComplementari._famiglia)))

R = RaccomandatoreRegole().fit(train)        # regole calcolate SOLO sul training
A = BaselineProdotti().fit(train)
B2 = BaselineCategorieComplementari().fit(train)
C = BaselineCategorieSole().fit(train)

# i sistemi, tutti con i vincoli e la regola del momento del pasto
def sugg_C(c, K):
    nc = non_consentite(c['cat_carrello']); return [x for x in C.raccomanda(c['cat_carrello'], 60) if x not in nc][:K]
def sugg_A(c, K):                                    # senza vincoli sulle categorie nel carrello (solo riferimento)
    nc = non_consentite(c['cat_carrello']); return [p for p in A.raccomanda(c['carrello'], 60) if fam[p] not in nc][:K]
def sugg_Av(c, K):                                   # A vincolata: stessi vincoli del sistema
    nc = non_consentite(c['cat_carrello']) | set(c['cat_carrello']); return [p for p in A.raccomanda(c['carrello'], 80) if fam[p] not in nc][:K]
def sugg_B2(c, K):
    nc = non_consentite(c['cat_carrello']); return [p for p in B2.raccomanda(c['carrello'], 60) if fam[p] not in nc][:K]
def sugg_Rc(c, K): return R.categorie(c['cat_carrello'], K, non_consentite(c['cat_carrello']))
def sugg_Rp(c, K): return R.prodotti_(c['carrello'], K, non_consentite(c['cat_carrello']))

righe = []
for n in (1, 2):
    tutti = costruisci_casi(test, n)
    casi = filtra_casi(tutti, fam)
    print(f'{n} nascosti: {len(tutti)} casi, {len(casi)} dopo la regola del momento del pasto')
    for K in (1, 3, 5):
        sistemi = [('Categorie - baseline C', lambda c: sugg_C(c, K), 'cat_nascoste'),
                   ('Categorie - regole', lambda c: sugg_Rc(c, K), 'cat_nascoste'),
                   ('Prodotti - baseline A vincolata', lambda c: sugg_Av(c, K), 'nascosti'),
                   ('Prodotti - baseline B2', lambda c: sugg_B2(c, K), 'nascosti'),
                   ('Prodotti - regole', lambda c: sugg_Rp(c, K), 'nascosti'),
                   ('Prodotti - baseline A senza vincoli (riferimento)', lambda c: sugg_A(c, K), 'nascosti')]
        for nome, f, chiave in sistemi:
            (p, r, h), _, _ = metriche(casi, f, chiave, K)
            righe.append({'Prodotti nascosti': n, 'K': K, 'Sistema': nome, 'Precision %': round(p*100, 1),
                          'Recall %': round(r*100, 1), 'Hit Rate %': round(h*100, 1)})
risultati = pd.DataFrame(righe)
print(risultati)



casi = filtra_casi(costruisci_casi(test, 1), fam)
K = 3
def hr(f, chiave): return metriche(casi, f, chiave, K)[1:]
hc, tc = hr(lambda c: sugg_C(c, K), 'cat_nascoste')
hr_, tr_ = hr(lambda c: sugg_Rc(c, K), 'cat_nascoste')
hav, tav = hr(lambda c: sugg_Av(c, K), 'nascosti')
ha, ta = hr(lambda c: sugg_A(c, K), 'nascosti')
hb, tb = hr(lambda c: sugg_B2(c, K), 'nascosti')
hp, tp = hr(lambda c: sugg_Rp(c, K), 'nascosti')
for nome, x, y, t in [('Categorie: regole (74,4%) - baseline C (73,5%)', hr_, hc, tr_),
                      ('Prodotti: regole - baseline A vincolata', hp, hav, tp),
                      ('Prodotti: regole - baseline B2', hp, hb, tp),
                      ('Prodotti: regole - baseline A senza vincoli (riferimento)', hp, ha, tp)]:
    diff, (lo, hi) = differenza_bootstrap(x, y, t)
    print(f'{nome}: {diff*100:+.1f} punti  (intervallo 95%: da {lo*100:+.1f} a {hi*100:+.1f})')
