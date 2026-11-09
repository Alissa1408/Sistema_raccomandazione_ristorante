"""Punto 9 - valutazione del sistema come funziona nell'app: ordine ricostruito passo per passo.
Per ogni turno del test (serate piu' recenti, 30%) i piatti si aggiungono nell'ordine dell'orario di inserimento (colonna Ora).
Dopo ogni piatto il sistema propone UNA categoria, con le stesse regole dell'app (momento del pasto, categoria non gia' nel carrello,
silenzio sotto soglia o senza storico). Successo = la categoria proposta viene ordinata piu' avanti nello stesso turno.
Sistemi: baseline vincolata (categorie piu' frequenti nel training, stessi vincoli), piatto senza contesto, piatto + contesto (app).
Servono nella stessa cartella baseline.py, regole.py, contesto.py, momento.py, motore.py, valutazione.py e dettaglio_ordini_cena.csv."""
import numpy as np, pandas as pd
from baseline import carica_turni, dividi_temporale, BaselineCategorieComplementari as BC
from contesto import tabella_turni
from motore import Motore, etichetta_commensali
from momento import non_consentite_fasi
from valutazione import differenza_bootstrap

d = carica_turni('dettaglio_ordini_cena.csv')
train, test, taglio = dividi_temporale(d)
fam = dict(zip(d['nome_articolo'], d['macro_categoria'].map(BC._famiglia)))
turni = tabella_turni(d)
M = Motore(dati=train); M.fam = fam                       # modello addestrato solo sul training
cats = M.cats
freq = train.assign(f=train['nome_articolo'].map(fam)).groupby('f')['identificativo_turno'].nunique()
ordine_freq = list(freq.sort_values(ascending=False).index)

righe = []
for tur, g in test.groupby('identificativo_turno'):
    g = g.sort_values('Ora', kind='stable')
    prod = list(g['nome_articolo'])
    t = turni.loc[tur]
    for k in range(1, len(prod)):
        cart, ult = prod[:k], prod[k - 1]
        cat_cart = sorted({fam[p] for p in cart})
        futuro = {fam[p] for p in prod[k:]} - set(cat_cart)
        bl = non_consentite_fasi(cat_cart, cats, fam[ult]) | set(cat_cart)
        base = next((c for c in ordine_freq if c not in bl), None)
        r = {'turno': tur, 'base': base in futuro if base else False, 'ha_base': base is not None}
        for nome, uc in [('piatto', False), ('app', True)]:
            s, _, _ = M.suggerisci(cart, t['giorno'], t['fascia'], t['n'], k=1, ultimo=ult, n_prodotti=1, usa_contesto=uc)
            r[nome + '_prop'] = bool(s); r[nome] = bool(s) and s[0]['categoria'] in futuro
        r['ammesso'] = base is not None
        righe.append(r)
R = pd.DataFrame(righe)
R = R[R['ammesso']]
print(f"{R['turno'].nunique()} tavoli del test, {len(R)} passi in cui il sistema potrebbe proporre qualcosa")
print(f"Il sistema propone (non resta in silenzio) nel {R['app_prop'].mean():.0%} dei passi")

def conf(a, b, nome):
    x, (lo, hi) = differenza_bootstrap(R[a].values.astype(float), R[b].values.astype(float), R['turno'].values)
    print(f"{nome}: {x*100:+.1f} punti (IC 95% {lo*100:+.1f} / {hi*100:+.1f})")

print('\nTutti i passi (il silenzio conta come errore):')
for n, c in [('Baseline vincolata', 'base'), ('Piatto senza contesto', 'piatto'), ('Piatto + contesto (app)', 'app')]:
    print(f"  {n}: {R[c].mean():.1%}")
S = R[R['app_prop']]
print(f'\nSoli passi in cui l\'app propone ({len(S)}):')
for n, c in [('Baseline vincolata', 'base'), ('Piatto senza contesto', 'piatto'), ('Piatto + contesto (app)', 'app')]:
    print(f"  {n}: {S[c].mean():.1%}")
R_all = R
print('\nDifferenze (tutti i passi):')
conf('app', 'base', 'App contro baseline vincolata')
conf('piatto', 'base', 'Piatto senza contesto contro baseline vincolata')
conf('app', 'piatto', 'Contesto: app contro piatto senza contesto')
R = S
print('\nDifferenze (solo passi con proposta):')
conf('app', 'base', 'App contro baseline vincolata')
conf('app', 'piatto', 'Contesto: app contro piatto senza contesto')
