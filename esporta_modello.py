"""Esporta il modello addestrato (motore.Motore) in un file JSON per la demo web.
Contiene solo parametri e conteggi aggregati: nessuno scontrino, nessuna data, nessun tavolo."""
import json, sys, numpy as np
sys.path.insert(0, '.')
from motore import Motore, SOGLIA
from menu_marina import carica_menu
from regole import MIN_COPPIE

m = Motore(sys.argv[2] if len(sys.argv) > 2 else "dettaglio_ordini_cena.csv")
pagine, voci = carica_menu("menu_marina.json", list(m.fam))
linked = sorted({v["csv"] for v in voci.values() if v["csv"]} | {"MEDIA ROSSA", "PICCOLA ROSSA"} & set(m.fam))
r = m.regole
idx = [r.pi[p] for p in linked if p in r.pi]
names = [r.prodotti[i] for i in idx]
d = m.d
fam_series = d["nome_articolo"].map(m.fam)
turni_cat = {c: set(d.loc[fam_series == c, "identificativo_turno"]) for c in m.cats}
quota = {}
for p in names:
    t_u = set(d.loc[d["nome_articolo"] == p, "identificativo_turno"])
    quota[p] = [round(len(t_u & turni_cat[c]) / len(t_u), 4) if t_u else 0 for c in m.cats]

def mod(M):
    return {"vars": M.variabili, "q": [float(x) for x in M.q],
            "W": [[round(float(w), 5) for w in mm.coef_[0]] for mm in M.modelli],
            "b": [round(float(mm.intercept_[0]), 5) for mm in M.modelli]}

out = {
    "cats": m.cats, "soglia": SOGLIA, "min_coppie": MIN_COPPIE,
    "fam": {p: m.fam[p] for p in names},
    "prodotti": names,
    "nP": [int(r.nP[i]) for i in idx],
    "coppie": [[int(r.coppie[a, b]) for b in idx] for a in idx],
    "quota": [quota[p] for p in names],
    "conf_cat": [[round(float(x), 4) for x in row] for row in r.conf_cat],
    "nC": [int(x) for x in r.nC], "base": [round(float(m.base[c]), 4) for c in m.cats],
    "n_turni": int(r.n_turni),
    "modelli": {"tutte": mod(m.tutte), "solo": mod(m.solo), **{"solo_" + v: mod(mm) for v, mm in m.singole.items()}},
}
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "modello.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("prodotti", len(names), "cats", len(m.cats))
