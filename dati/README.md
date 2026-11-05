# Dati

Lo storico degli scontrini del ristorante **non è pubblicato** perché contiene dati di vendita riservati.
Per eseguire il codice, metti qui (o nella cartella principale) il file `dettaglio_ordini_cena.csv`.

## Formato atteso

File CSV separato da `;`, con la virgola come separatore decimale. Una riga per prodotto ordinato:

| Colonna | Esempio | Significato |
|---|---|---|
| `Data` | `29/08/2025` | data della serata (gg/mm/aaaa) |
| `Ora` | `19:55:19` | ora dell'ordine |
| `tavolo` | `1` | numero del tavolo |
| `identificativo_turno` | `1_29/08/2025_s1` | tavolo + data + turno: è il "carrello" |
| `n_commensali` | `2` | persone al tavolo |
| `codice_articolo` | `611` | codice interno del prodotto |
| `nome_articolo` | `PROSCIUTTO E FUNGHI` | nome del prodotto |
| `quantita` | `1,0` | quantità |
| `prezzo` | `8,5` | importo della riga in euro |
| `macro_categoria` | `Pizze con carne/salumi` | una delle categorie (o `ESCLUDERE` / `Acqua`, che vengono scartate) |
| `sotto_categoria` | | facoltativa |
