"""Momento del pasto: dolci, caffetteria e digestivi si propongono solo se nel carrello c'e' gia' un piatto principale
(pizza, primo o secondo). Prima di allora il sistema non li suggerisce."""
from baseline import BaselineCategorieComplementari as BC

TARDIVE = {"Dessert", "Caffetteria", "Amari e digestivi"}


def e_principale(famiglia):
    return famiglia.startswith(("Pizze", "Primi", "Secondi"))


def non_consentite(cat_carrello):
    """Categorie che non si possono ancora suggerire con questo carrello."""
    return set() if any(e_principale(c) for c in cat_carrello) else set(TARDIVE)


def filtra_casi(casi, famiglia_di):
    """Tiene solo i prodotti/categorie nascosti che il sistema avrebbe potuto suggerire in quel momento;
    scarta i casi che restano senza nulla da ritrovare."""
    out = []
    for c in casi:
        nc = non_consentite(c["cat_carrello"])
        c = dict(c)
        c["cat_nascoste"] = [x for x in c["cat_nascoste"] if x not in nc]
        c["nascosti"] = [p for p in c["nascosti"] if famiglia_di[p] not in nc]
        out.append(c)
    return [c for c in out if c["nascosti"]]



# ---------------------------------------------------------------------------------------------
# Regola sul momento del pasto: cosa si puo' proporre dopo l'ultimo piatto aggiunto
def fase(famiglia):
    if famiglia.startswith("Antipasti"):
        return 1
    if famiglia.startswith(("Pizze", "Primi", "Secondi")):
        return 2
    if famiglia == "Contorni":
        return 3
    if famiglia in ("Bibite analcoliche", "Birra") or famiglia.startswith("Vino"):
        return 4
    return {"Dessert": 5, "Caffetteria": 6, "Amari e digestivi": 7}.get(famiglia, 2)


PROPONIBILI = {1: {2}, 2: {4}, 3: set(), 4: {5}, 5: {6}, 6: {7}, 7: set()}   # antipasto→principale, principale→bevanda, bevanda→dolce, dolce→caffè, caffè→amaro


def non_consentite_fasi(cat_carrello, tutte, ultimo_cat=None):
    """Categorie non proponibili in questo momento: dipende dall'ultimo piatto aggiunto
    (senza, dalla fase piu' avanzata del carrello); dolci/caffe'/amari solo se c'e' un principale."""
    if not cat_carrello and not ultimo_cat:
        return set()
    f = fase(ultimo_cat) if ultimo_cat else max(fase(c) for c in cat_carrello)
    consentite = PROPONIBILI[f]
    if f == 2 and any(fase(c) == 4 for c in cat_carrello):
        consentite = {5}        # la bevanda e' gia' stata scelta (prima del piatto): dopo il piatto si propone direttamente il dolce
    ok = {c for c in tutte if fase(c) in consentite}
    if f == 1:
        ok = {c for c in ok if c.startswith("Primi")}      # dopo un antipasto si propone un primo (non pizza ne' secondo)
    if not any(e_principale(c) for c in cat_carrello):
        ok -= TARDIVE
    return set(tutte) - ok
