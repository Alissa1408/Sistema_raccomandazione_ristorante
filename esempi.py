"""Punto 6: esempi concreti per diversi tipi di tavolo."""
import random
import pandas as pd
from baseline import *
from simulazione import *
from regole import *
from momento import *
from valutazione import metriche

def tipo_tavolo(g):
    cat = set(g["macro_categoria"]); n = g["n_commensali"].iloc[0]
    if any(c in cat for c in ("Antipasti di pesce", "Primi di pesce", "Secondi di pesce")): return "1. Con piatti di pesce"
    if any(c in cat for c in ("Primi di carne", "Secondi di carne")): return "2. Con primi o secondi di carne"
    if n >= 6: return "3. Tavolo grande (6+ commensali)"
    if n <= 2: return "4. Coppia (2 commensali)"
    if any(c.startswith("Antipasti") for c in cat): return "5. Pizza con antipasti"
    return "6. Solo pizza e bevande"


def scegli_esempio(test, tipi, tipo, seed=7):
    """Un turno a caso (seme fisso) del tipo dato, con 5-9 prodotti, per non scegliere i casi piu' belli."""
    turni = sorted(t for t in tipi[tipi == tipo].index if 5 <= test[test.identificativo_turno == t].shape[0] <= 9)
    return random.Random(seed).choice(turni)


def esempio(turno, test, fam, R, B2, K=3):
    """Per ogni prodotto del turno: lo nascondo e guardo cosa suggeriscono il sistema con le regole e la baseline B2."""
    g = test[test.identificativo_turno == turno]
    prodotti = sorted(g["nome_articolo"])
    righe = []
    for p in prodotti:
        carrello = [x for x in prodotti if x != p]
        cat_c = sorted({fam[x] for x in carrello})
        nc = non_consentite(cat_c)
        cat_r = R.categorie(cat_c, K, nc)
        prod_r = R.prodotti_(carrello, K, nc)
        prod_b = [x for x in B2.raccomanda(carrello, 60) if fam[x] not in nc][:K]
        righe.append({"Nascosto": p, "Categorie suggerite (regole)": ", ".join(cat_r),
                      "Categoria ritrovata?": ("sì" if fam[p] in cat_r else ("già nel carrello" if fam[p] in cat_c else "no")),
                      "Prodotti suggeriti (regole)": ", ".join(prod_r), "Prodotto ritrovato (regole)?": "sì" if p in prod_r else "no",
                      "Prodotti suggeriti (baseline B2)": ", ".join(prod_b), "Prodotto ritrovato (B2)?": "sì" if p in prod_b else "no"})
    return g["n_commensali"].iloc[0], prodotti, pd.DataFrame(righe)
