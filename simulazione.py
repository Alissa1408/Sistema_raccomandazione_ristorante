"""Punto 4: simulazione della raccomandazione sul test.

Per ogni turno del test con almeno 2 prodotti si nasconde uno (o due) prodotti:
quelli rimasti sono il "carrello visibile", quelli nascosti sono la "risposta" da ritrovare.
Un suggerimento e' un successo se il prodotto nascosto (o la sua categoria) e' tra i primi K suggeriti.
"""
import itertools
from baseline import BaselineCategorieComplementari as BC


def costruisci_casi(test, nascosti=1):
    """Restituisce una lista di casi: turno, carrello visibile, prodotti nascosti, categorie nascoste."""
    fam = test.drop_duplicates("nome_articolo").set_index("nome_articolo")["macro_categoria"].map(BC._famiglia).to_dict()
    casi = []
    for turno, g in test.groupby("identificativo_turno"):
        prodotti = sorted(g["nome_articolo"])
        if len(prodotti) <= nascosti:
            continue
        for nasc in itertools.combinations(prodotti, nascosti):
            visibili = [p for p in prodotti if p not in nasc]
            casi.append({"turno": turno, "carrello": visibili, "nascosti": list(nasc),
                         "cat_carrello": sorted({fam[p] for p in visibili}),
                         "cat_nascoste": sorted({fam[p] for p in nasc} - {fam[p] for p in visibili})})
    return casi


def successo_prodotto(caso, suggeriti):
    return any(p in caso["nascosti"] for p in suggeriti)


def successo_categoria(caso, suggerite):
    return any(c in caso["cat_nascoste"] for c in suggerite)
