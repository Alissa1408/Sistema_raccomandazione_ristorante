"""Costruisce demo-web/index.html: il menu Marina con il sistema di raccomandazione, eseguibile nel browser.

Uso (dalla cartella principale del progetto, con dettaglio_ordini_cena.csv in dati/ o nella cartella principale):
    python demo-web/costruisci_demo.py

Esporta il modello addestrato (solo pesi e conteggi aggregati, nessuno scontrino) e lo inserisce nella pagina
insieme a motore.js, il porting JavaScript di motore.Motore.suggerisci.
"""
import json, os, subprocess, sys
QUI = os.path.dirname(os.path.abspath(__file__)); RADICE = os.path.dirname(QUI)
sys.path.insert(0, RADICE); os.chdir(RADICE)
csv = "dettaglio_ordini_cena.csv" if os.path.exists("dettaglio_ordini_cena.csv") else os.path.join("dati", "dettaglio_ordini_cena.csv")
from motore import Motore
from menu_marina import carica_menu, LOGO_B64

subprocess.run([sys.executable, "esporta_modello.py", os.path.join(QUI, "modello.json"), csv], check=True)
m = Motore(csv)
pagine, _ = carica_menu("menu_marina.json", list(m.fam))
for p in pagine:
    for s in p["sez"]:
        nuove = []
        for v in s["voci"]:
            v = dict(v); v.pop("pagina", None)
            if v["id"].startswith("menu-pranzo-mer-gio-ven:"):
                v["pranzo"], v["csv"] = True, None          # le raccomandazioni valgono solo per la sera
            nuove.append(v)
            rossa = {"BIRRA MEDIA": "MEDIA ROSSA", "BIRRA PICCOLA": "PICCOLA ROSSA"}.get(v["csv"])
            if rossa and rossa in m.fam:
                nuove.append(dict(v, id=v["id"] + ":rossa", nome=v["nome"].replace("ALLA SPINA", "ALLA SPINA · ROSSA"), desc="", csv=rossa))
        s["voci"] = nuove
t = open(os.path.join(QUI, "template.html"), encoding="utf-8").read()
t = (t.replace("__MODELLO__", open(os.path.join(QUI, "modello.json"), encoding="utf-8").read())
      .replace("__MENU__", json.dumps(pagine, ensure_ascii=False, separators=(",", ":")))
      .replace("__LOGO__", LOGO_B64).replace("__MOTORE__", open(os.path.join(QUI, "motore.js"), encoding="utf-8").read()))
open(os.path.join(QUI, "index.html"), "w", encoding="utf-8").write(t)
print("Creato demo-web/index.html")
