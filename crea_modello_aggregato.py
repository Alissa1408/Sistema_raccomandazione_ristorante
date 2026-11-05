"""Crea modello_aggregato.json a partire dai dati storici (da eseguire in locale, dove c'è il file degli scontrini).

    python crea_modello_aggregato.py

Il file contiene solo parametri dei modelli e conteggi aggregati: nessun tavolo singolo.
È quello che usa l'app pubblicata online, dove dettaglio_ordini_cena.csv non c'è.
"""
from motore import Motore

if __name__ == "__main__":
    print("Creato:", Motore("dettaglio_ordini_cena.csv").esporta_aggregato("modello_aggregato.json"))
