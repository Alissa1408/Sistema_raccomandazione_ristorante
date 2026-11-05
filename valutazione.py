"""Punto 5: metriche Top-K (Precision, Recall, Hit Rate) sui casi di simulazione."""
import numpy as np


def metriche(casi, suggerisci, chiave, k):
    """chiave = 'nascosti' (prodotti) o 'cat_nascoste' (categorie). Restituisce (precision, recall, hit rate) e il vettore degli hit per caso."""
    casi = [c for c in casi if c[chiave]]
    hit_n, rec, hr, turni = [], [], [], []
    for c in casi:
        s = suggerisci(c)[:k]
        h = len(set(s) & set(c[chiave]))
        hit_n.append(h); rec.append(h / len(c[chiave])); hr.append(h > 0); turni.append(c["turno"])
    prec = np.array(hit_n) / k
    return (prec.mean(), np.mean(rec), np.mean(hr)), np.array(hr, float), np.array(turni)


def differenza_bootstrap(hr_a, hr_b, turni, n=1000, seed=0):
    """Differenza di Hit Rate (a - b) con intervallo al 95%, ricampionando i turni (i casi dello stesso turno sono legati)."""
    rng = np.random.default_rng(seed)
    nomi, inv = np.unique(turni, return_inverse=True)
    sa = np.bincount(inv, hr_a); sb = np.bincount(inv, hr_b); nn = np.bincount(inv)
    diff = []
    for _ in range(n):
        s = rng.integers(0, len(nomi), len(nomi))
        diff.append(sa[s].sum() / nn[s].sum() - sb[s].sum() / nn[s].sum())
    return np.mean(hr_a) - np.mean(hr_b), np.percentile(diff, [2.5, 97.5])
