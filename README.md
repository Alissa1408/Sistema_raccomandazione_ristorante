# Sistema di raccomandazione per il menu di un ristorante

**Market Basket Analysis per l'upselling nella ristorazione** · Tesi di laurea magistrale in Intelligenza Artificiale, Impresa e Società (IULM) · Alissa Di Lorenzo

Un sistema che, mentre il cliente compone l'ordine sul menu digitale, propone **la categoria di prodotti che quel tavolo ha più probabilità di ordinare**, al momento giusto del pasto e con una spiegazione chiara. È costruito sullo storico reale degli scontrini della Pizzeria Marina.

> «Nel 66% dei tavoli con *Margherita* c'era anche una birra.» Così il sistema motiva ogni suggerimento.

🍕 **[Prova la demo del menu](demo-web/index.html)**: funziona nel browser, senza installare nulla.

---

## I dati

| | |
|---|---|
| Tavoli (turni) | **5.413** |
| Serate di cena | **245**, dal 29/08/2025 al 18/09/2026 |
| Righe prodotto | **35.774** |
| Prodotti | **230**, in **18 categorie** |

## Il metodo

| Passo | Cosa fa | File |
|---|---|---|
| 1 | Caricamento e pulizia degli scontrini (esclusi coperto, acqua, personalizzazioni) | `baseline.py` |
| 2 | Baseline: prodotti più venduti, categorie più frequenti, categorie complementari | `baseline.py` |
| 3 | Divisione **temporale** 70/30: si impara dalle serate passate, si valuta su quelle future | `baseline.py` |
| 4 | Simulazione: per ogni tavolo del test si nasconde un prodotto e si chiede al sistema di ritrovarlo | `simulazione.py` |
| 5 | Regole associative (confidenza) e metriche Top-K: Precision, Recall, Hit Rate, con intervalli bootstrap | `regole.py`, `valutazione.py`, `punto5_esecuzione.py` |
| 6 | Esempi su sei tipi di tavolo reali | `esempi.py` |
| 7 | Variabili di contesto: regressione logistica per categoria con giorno, fascia oraria e commensali, verificata su quattro finestre temporali | `contesto.py`, `verifiche.py`, `punto7_esecuzione.py` |

I report completi di ogni passo sono in [`notebook/`](notebook/).

### Le regole del momento del pasto (`momento.py`)

- antipasto → piatto principale → bevanda → dolce → caffè → amaro;
- dolci, caffè e amari solo se nel carrello c'è già un piatto principale;
- mai una categoria già presente nel carrello;
- la categoria dipende dall'**ultimo piatto aggiunto**: si propone quella che i tavoli con quel piatto ordinano più spesso (per esempio bibite con patatine e wurstel, vino bianco con il pesce), corretta dal contesto;
- nessun suggerimento se il piatto compare in meno di 10 tavoli, se la categoria non è mai stata ordinata con quel piatto, nel menu del pranzo;
- sotto il 10% di probabilità stimata il sistema **sta in silenzio**.

## Risultati

Hit Rate a livello di categoria (un prodotto nascosto, 4.363 casi di test):

| Sistema | K = 1 | K = 3 | K = 5 |
|---|---:|---:|---:|
| Baseline C: categorie più frequenti | 44,2% | 73,5% | 87,4% |
| Regole associative | 43,8% | 74,4% | 88,5% |
| Modello: solo carrello | 44,1% | 77,8% | 89,7% |
| Modello: carrello + contesto (giorno, fascia, commensali) | 44,7% | 78,0% | 89,9% |

Unendo quattro finestre temporali (6.398 casi), con K = 3:
- modello con contesto contro baseline C: **+4,8 punti** (IC 95%: +3,8 / +5,7);
- contesto contro solo carrello: **+0,4 punti** (IC 95%: 0,0 / +0,8). L'effetto del contesto è piccolo; il numero di commensali è la variabile che aiuta di più.

A livello di singolo prodotto il compito è molto più difficile (Hit Rate con K = 3 intorno al 14–16%). Per questo il sistema sceglie la **categoria** con il modello e poi ordina i prodotti per quante volte sono stati ordinati insieme al piatto appena aggiunto.

### Valutazione passo per passo, come funziona l'app (`punto9_valutazione.py`)

Le metriche sopra nascondono un prodotto e usano una regola sul momento del pasto più semplice di quella dell'app. Per misurare il sistema com'è davvero, i piatti dei 1.862 tavoli di test si aggiungono nell'ordine dell'orario di inserimento; dopo ogni piatto il sistema propone una categoria con le regole dell'app, e il successo è che la categoria venga ordinata più avanti nello stesso tavolo (8.031 passi).

| Sistema | Successo |
|---|---:|
| Baseline vincolata (categoria più frequente tra quelle consentite) | 53,3% |
| Sistema per piatto, senza contesto | 52,7% |
| Sistema per piatto con contesto (app) | 52,8% |

Dove il sistema propone (99% dei passi) la differenza con la baseline è +0,1 punti (IC 95%: −0,1 / +0,3): è alla pari, non migliore. Il vantaggio della scelta per piatto è qualitativo, non misurabile con questo indicatore.

## Il prototipo

- `app.py`: menu digitale del ristorante in **Streamlit**, con barra laterale per simulare il tavolo (giorno, orario, commensali) e una "modalità dimostrazione" che mostra probabilità, motivazioni e regole applicate;
- `motore.py`: il motore usato dal prototipo (modello con contesto + regole operative + motivazioni);
- `modello_aggregato.json`: i parametri dei modelli e i conteggi aggregati (tavoli per prodotto, per coppia di prodotti e per categoria), creati con `crea_modello_aggregato.py`. Se `dettaglio_ordini_cena.csv` non c'è, l'app parte da questo file: è così che gira la versione online, senza pubblicare gli scontrini. Su 1.500 carrelli casuali dà esattamente gli stessi suggerimenti del modello addestrato sui dati;
- `demo-web/`: **versione precedente** della demo in una sola pagina HTML, non ancora aggiornata alle ultime regole (scelta della categoria per piatto, pagina «Prima di iniziare»). Il modello addestrato è esportato in JSON (`esporta_modello.py`: solo pesi e conteggi aggregati, nessuno scontrino) e il motore è riscritto in JavaScript (`motore.js`). Sui 400 carrelli di verifica dà gli stessi suggerimenti del motore Python.

## Come eseguirlo

```bash
pip install -r requirements.txt
# metti dettaglio_ordini_cena.csv nella cartella principale (vedi dati/README.md)
python punto5_esecuzione.py          # regole e metriche
python punto7_esecuzione.py          # variabili di contesto (qualche minuto)
streamlit run app.py                 # prototipo del menu (funziona anche senza il CSV, con modello_aggregato.json)
python crea_modello_aggregato.py     # rigenera modello_aggregato.json dai dati
python demo-web/costruisci_demo.py   # rigenera la demo web
```

## Dati

Lo storico degli scontrini non è incluso perché contiene dati di vendita riservati del ristorante. Il formato del file è descritto in [`dati/README.md`](dati/README.md).

---

Alissa Di Lorenzo · [GitHub](https://github.com/Alissa1408) · [LinkedIn](https://www.linkedin.com/in/alissa-di-lorenzo-7b0717428)
