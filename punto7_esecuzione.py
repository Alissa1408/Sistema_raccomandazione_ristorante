"""Punto 7 - variabili di contesto: confronto dei modelli, intervalli di confidenza, coefficienti e conferma su piu' finestre temporali.
Servono nella stessa cartella baseline.py, simulazione.py, regole.py, momento.py, valutazione.py, contesto.py, verifiche.py e dettaglio_ordini_cena.csv. Richiede qualche minuto."""
import numpy as np, pandas as pd
from baseline import *
from simulazione import *
from momento import *
from regole import *
from contesto import *
from valutazione import differenza_bootstrap

d = carica_turni('dettaglio_ordini_cena.csv')
train, test, taglio = dividi_temporale(d)
fam = dict(zip(d['nome_articolo'], d['macro_categoria'].map(BaselineCategorieComplementari._famiglia)))
turni = tabella_turni(d)
prezzi = {(a, b): c for a, b, c in zip(d['identificativo_turno'], d['nome_articolo'], d['prezzo'])}

# casi: un prodotto nascosto, solo quelli con una categoria nuova da ritrovare
casi = [c for c in filtra_casi(costruisci_casi(test, 1), fam) if c['cat_nascoste']]
print(len(casi), 'casi')

config = {'Solo carrello': [], '+ giorno': ['giorno'], '+ fascia oraria': ['fascia'], '+ commensali': ['commensali'], '+ tutte e tre': VARIABILI}

sugg = {nome: ModelloCategorie(v).fit(train, turni).suggerimenti(casi, turni, prezzi, 5) for nome, v in config.items()}

def hit(s, K):
    return np.array([any(x in c['cat_nascoste'] for x in s[i][:K]) for i, c in enumerate(casi)], float)

righe = []
for nome, s in sugg.items():
    righe.append({'Modello': nome, **{f'Hit Rate K={K} %': round(hit(s, K).mean() * 100, 1) for K in (1, 3, 5)}})

# riferimenti dei punti precedenti (senza contesto)
R = RaccomandatoreRegole().fit(train); C = BaselineCategorieSole().fit(train)
for nome, f in [('Riferimento: baseline C (categorie più frequenti)', lambda c, K: [x for x in C.raccomanda(c['cat_carrello'], 60) if x not in non_consentite(c['cat_carrello'])][:K]),
                ('Riferimento: regole del punto 5', lambda c, K: R.categorie(c['cat_carrello'], K, non_consentite(c['cat_carrello'])))]:
    righe.append({'Modello': nome, **{f'Hit Rate K={K} %': round(np.mean([any(x in c['cat_nascoste'] for x in f(c, K)) for c in casi]) * 100, 1) for K in (1, 3, 5)}})
print(pd.DataFrame(righe).to_string())

turni_caso = np.array([c['turno'] for c in casi])
base = {K: hit(sugg['Solo carrello'], K) for K in (1, 3)}
righe = []
for nome in list(config)[1:]:
    r = {'Modello': nome}
    for K in (1, 3):
        diff, (lo, hi) = differenza_bootstrap(hit(sugg[nome], K), base[K], turni_caso)
        r[f'K={K}: differenza'] = f'{diff*100:+.1f} punti ({lo*100:+.1f} / {hi*100:+.1f})'
    righe.append(r)
print(pd.DataFrame(righe).to_string())

M_tutte = ModelloCategorie(VARIABILI).fit(train, turni)
nomi = M_tutte.cats + ['ven', 'sab', 'dom', 'prima_20', 'dopo_21', 'comm_3_4', 'comm_5+']
for cat in ['Dessert', 'Caffetteria', 'Vino bianco e spumante']:
    coef = pd.Series(M_tutte.modelli[M_tutte.cats.index(cat)].coef_[0], index=nomi).iloc[len(M_tutte.cats):].round(2)
    print(cat); print(coef.to_string()); print()

from verifiche import *

d2, fam2, turni2, prezzi2 = prepara('dettaglio_ordini_cena.csv')
blocchi = []
for a, b, tr, te in finestre(d2):
    cat_b = [c for c in filtra_casi(costruisci_casi(te, 1), fam2) if c['cat_nascoste']]
    blocchi.append((a, b, cat_b, sistemi_categorie(tr, fam2, turni2, prezzi2, cat_b)))

print(pd.DataFrame([{'Test (quota delle serate)': f'{a:.1%}-{b:.1%}', 'Casi': len(cb), **{k: round(v[3].mean() * 100, 1) for k, v in sc.items()}}
              for a, b, cb, sc in blocchi]).to_string())

t_cat = np.concatenate([[c['turno'] for c in cb] for a, b, cb, sc in blocchi])
nomi = list(blocchi[0][3])
coppie = [('Modello carrello + contesto', 'Modello solo carrello'), ('Modello solo carrello', 'Regole (punto 5)'),
          ('Regole (punto 5)', 'Baseline C (categorie più frequenti)'), ('Modello carrello + contesto', 'Baseline C (categorie più frequenti)')]
tab = None
for K in (1, 3):
    r = {n: np.concatenate([sc[n][K] for a, b, cb, sc in blocchi]) for n in nomi}
    righe = []
    for x, y in coppie:
        dd, (lo, hi) = differenza_bootstrap(r[x], r[y], t_cat)
        righe.append({'Confronto': f'{x}  contro  {y}', f'K={K}': f'{dd*100:+.1f} ({lo*100:+.1f} / {hi*100:+.1f})'})
    t = pd.DataFrame(righe)
    tab = t if tab is None else tab.merge(t, on='Confronto')
print(tab.to_string())

righe = []
for a, b, cb, sc in blocchi:
    t = np.array([c['turno'] for c in cb])
    dd, (lo, hi) = differenza_bootstrap(sc['Modello carrello + contesto'][3], sc['Modello solo carrello'][3], t)
    righe.append({'Test': f'{a:.1%}-{b:.1%}', 'Contesto - solo carrello, K=3': f'{dd*100:+.1f} ({lo*100:+.1f} / {hi*100:+.1f})'})
print(pd.DataFrame(righe).to_string())
