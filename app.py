"""Prototipo dimostrativo del sistema di raccomandazione, con il menu digitale Marina (Streamlit).

Avvio:  streamlit run app.py
Serve nella stessa cartella: dettaglio_ordini_cena.csv, menu_marina.json, menu_marina.py,
baseline.py, regole.py, momento.py, contesto.py, motore.py
Barra laterale (freccia in alto a sinistra): contesto del tavolo, esempi rapidi e "Modalità dimostrazione".
"""
import base64
import html
import re

import streamlit as st

from menu_marina import carica_menu
from momento import TARDIVE, non_consentite_fasi
from motore import Motore, GIORNI, FASCE, SOGLIA

LOGO_URL = "https://znxdanvdfkagvxqslnzt.supabase.co/storage/v1/object/public/dish-images/789780f3-5717-42d9-b26a-56bd1fd149fa/logo/logo_1772890857340.webp"

st.set_page_config(page_title="Menù - Marina", page_icon="🍕", layout="centered", initial_sidebar_state="collapsed")

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500&family=Jost:wght@300;400;500;600;700&display=swap');

.stApp, .stApp p, .stApp label, .stApp li, .stApp small, .stApp input, .stApp td, .stApp th { font-family: 'Inter', sans-serif; }
.stApp h1, .stApp h2, .stApp h3, .stApp button, .jost { font-family: 'Jost', sans-serif; }
.stApp { background: #fef7df; }
.stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp small, .stApp td, .stApp th,
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stCaptionContainer"] { color: #57210d; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"], footer { display: none !important; }
.block-container { max-width: 42rem; padding-top: 1rem; padding-bottom: 3rem; }

/* barra laterale */
[data-testid="stSidebar"] { background: #f4e8c2; }
[data-testid="stSidebar"] * { color: #57210d; }
[data-baseweb="select"] > div, [data-testid="stNumberInputContainer"], [data-testid="stNumberInputContainer"] input {
  background: #fff !important; color: #57210d !important; border-radius: 12px; }
[data-baseweb="select"] *, [data-testid="stNumberInputContainer"] * { color: #57210d !important; }
[data-baseweb="popover"] ul, [data-baseweb="popover"] li { background: #fff !important; color: #57210d !important; }
[data-testid="stSidebar"] [data-testid="stExpander"] { background: transparent; border-color: #57210d; }

/* intestazione e titoli */
.logo { text-align: center; }
.logo img { height: 11rem; width: auto; max-width: 85%; object-fit: contain; }
.titolo { text-align: center; font-family: 'Jost', sans-serif; font-size: 1.9rem; letter-spacing: .05em; text-transform: uppercase; font-weight: 400; margin: .6rem 0 1.4rem; color: #57210d; }
.h1 { text-align: center; font-family: 'Jost', sans-serif; font-size: 1.7rem; letter-spacing: 3px; text-transform: uppercase; font-weight: 600; margin: .6rem 0 .5rem; color: #57210d; }
.barra { width: 40px; height: 2px; border-radius: 999px; background: #57210d; opacity: .5; margin: 0 auto 1.2rem; }
.pillola { font-family: 'Jost', sans-serif; background: #57210d; border-radius: 999px; padding: .75rem 1.5rem; text-align: center;
  font-weight: 600; letter-spacing: .1em; text-transform: uppercase; margin: 1.4rem 0 .6rem; font-size: 1rem; }
.pillola, .pillola * { color: #fff !important; }
.banner { width: 100%; aspect-ratio: 5/4; object-fit: cover; border-radius: 16px; margin: .4rem 0 .8rem; }
.nota-t { font-family: 'Jost', sans-serif; font-weight: 600; font-size: .9rem; margin-bottom: .2rem; }
.nota-d { font-size: .75rem; line-height: 1.6; color: #1a1a1a !important; opacity: .8; white-space: pre-wrap; }
.sezione { text-align: center; font-family: 'Jost', sans-serif; font-size: 1.1rem; letter-spacing: .1em; text-transform: uppercase; margin: 1.6rem 0 .8rem; font-weight: 500; }

/* bottoni a pillola (come il menu) */
.stButton > button { font-family: 'Jost', sans-serif; background: #57210d; color: #fff; border: none; border-radius: 999px; padding: .55rem 1.2rem;
  letter-spacing: .1em; text-transform: uppercase; font-weight: 500; box-shadow: 0 3px 8px rgba(87,33,13,.25); transition: all .15s; }
.stButton > button:hover { background: #73301a; color: #fff; border: none; }
.stButton > button p, .stButton > button [data-testid="stMarkdownContainer"], .stButton > button div { color: inherit !important; }
.stButton > button:focus:not(:active) { color: #fff; border: none; }
[class*="st-key-cat_"] button, [class*="st-key-alt_"] button { min-height: 3.1rem; font-size: 1.02rem; width: 100%; }
[class*="st-key-torna"] button { background: transparent; color: #57210d; box-shadow: none; border: 1px solid #57210d; font-size: .8rem; padding: .3rem 1rem; min-height: 0; }
[class*="st-key-torna"] button:hover { background: #57210d; color: #fff; }
[class*="st-key-svuota"] button, [class*="st-key-apri"] button { background: transparent; color: #57210d; box-shadow: none; border: 1px solid #57210d; font-size: .75rem; padding: .2rem .9rem; min-height: 0; }
[class*="st-key-svuota"] button:hover, [class*="st-key-apri"] button:hover { background: #57210d; color: #fff; }
[class*="st-key-add_"] button { padding: .15rem .7rem; font-size: .72rem; letter-spacing: .05em; min-height: 0; box-shadow: none; white-space: nowrap; }
[class*="st-key-plus_"] button, [class*="st-key-minus_"] button, [class*="st-key-cplus_"] button, [class*="st-key-cminus_"] button {
  width: 1.9rem; height: 1.9rem; min-height: 0; padding: 0; font-size: 1.05rem; letter-spacing: 0; }
[class*="st-key-plus_"] button, [class*="st-key-minus_"] button, [class*="st-key-cplus_"] button, [class*="st-key-cminus_"] button { position: relative; top: .5rem; }
[class*="st-key-minus_"] button, [class*="st-key-cminus_"] button { background: #fff; color: #57210d; border: 1.5px solid #57210d; box-shadow: none; }
[class*="st-key-minus_"] button:hover, [class*="st-key-cminus_"] button:hover { background: #ead9ad; color: #57210d; }
.qta { text-align: center; font-family: 'Jost', sans-serif; font-weight: 700; font-size: .95rem; height: 1.9rem; line-height: 1.9rem; margin: 0; padding: 0; color: #57210d !important; }
[class*="st-key-row_"] .stButton, [class*="st-key-crow_"] .stButton { margin: 0; line-height: 0; }
[class*="st-key-row_"] [data-testid="stMarkdownContainer"] p, [class*="st-key-crow_"] [data-testid="stMarkdownContainer"] p { margin: 0; }
[class*="st-key-row_"] [data-testid="stColumn"], [class*="st-key-crow_"] [data-testid="stColumn"] { display: flex; flex-direction: column; justify-content: center; }

/* scheda del menu */
.st-key-pagina { background: #fff; border: 2px solid #57210d; border-radius: 16px; padding: 1rem 1.2rem 1.4rem; box-shadow: 0 8px 10px -1px rgba(0,0,0,.1), 0 1px 3px rgba(0,0,0,.1); }
[class*="st-key-row_"] { border-bottom: 1px dashed rgba(26,26,26,.19); padding: .45rem 0 .6rem; }
[class*="st-key-row_"] [data-testid="stHorizontalBlock"], [class*="st-key-crow_"] [data-testid="stHorizontalBlock"], .st-key-ordine [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .4rem; }
[class*="st-key-row_"] [data-testid="stColumn"], [class*="st-key-crow_"] [data-testid="stColumn"], .st-key-ordine [data-testid="stColumn"] { min-width: 0 !important; }
.nome { font-family: 'Jost', sans-serif; font-weight: 600; letter-spacing: .03em; text-transform: uppercase; font-size: .92rem; color: #1a1a1a !important; line-height: 1.25; }
.prezzo { display: flex; align-items: center; justify-content: flex-end; min-height: 1.9rem; padding-right: .5rem; font-family: 'Jost', sans-serif; font-weight: 700; white-space: nowrap; font-size: .92rem; color: #1a1a1a !important; }
.desc { font-size: .75rem; line-height: 1.5; color: #1a1a1a !important; opacity: .8; white-space: pre-wrap; margin-top: .25rem; }

/* carrello fisso in alto */
.st-key-ordine { background: #fff; border: 2px solid #57210d; border-radius: 16px; padding: .6rem 1rem;
  margin-bottom: 1rem; box-shadow: 0 8px 14px -2px rgba(0,0,0,.18); max-height: 68vh; overflow-y: auto; }
.riepilogo { font-family: 'Jost', sans-serif; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; font-size: .95rem; line-height: 1.3; }
.riepilogo span { font-weight: 400; opacity: .8; text-transform: none; }
[class*="st-key-crow_"] { border-top: 1px dashed rgba(26,26,26,.19); padding: .35rem 0; }

/* suggerimento accanto al piatto: piccolo e discreto */
[class*="st-key-sugg_"] { background: #fef7df; border: 1px dashed rgba(87,33,13,.5); border-radius: 12px; padding: .45rem .8rem 1rem; margin: .35rem 0 .7rem; }
[class*="st-key-sugg_"] [class*="st-key-row_"] { border-bottom: none; padding: 0; }
[class*="st-key-sugg_"] .nome { font-size: .8rem; }
[class*="st-key-sugg_"] .prezzo { font-size: .8rem; }
[class*="st-key-sugg_"] [class*="st-key-add_"] button { padding: .1rem .7rem; font-size: .68rem; }
[class*="st-key-no_"] button { background: transparent; color: #57210d; border: none; box-shadow: none; text-transform: none; letter-spacing: 0; text-decoration: underline;
  font-size: .72rem; padding: .1rem .2rem; min-height: 0; font-weight: 400; }
[class*="st-key-no_"] button:hover { background: transparent; color: #57210d; opacity: .7; }
[class*="st-key-sugg_"] [class*="st-key-si_"] button { padding: .3rem 1.1rem; font-size: .74rem; letter-spacing: .04em; min-height: 0; box-shadow: none; white-space: nowrap; }
[class*="st-key-sugg_"] [class*="st-key-no_"] button { background: transparent !important; color: #57210d !important; padding: .3rem .4rem; font-size: .74rem; min-height: 0; box-shadow: none;
    text-decoration: underline; text-underline-offset: 3px; opacity: .75; white-space: nowrap; }
.sugg-titolo { font-family: 'Jost', sans-serif; font-size: .68rem; letter-spacing: .12em; text-transform: uppercase; font-weight: 500; opacity: .75; margin-bottom: .2rem; }
.sugg-motivo { font-size: .72rem; opacity: .85; margin-top: .1rem; }
.tecnico { font-size: .74rem; line-height: 1.5; border-top: 1px dashed rgba(87,33,13,.35); margin-top: .4rem; padding-top: .4rem; color: #57210d !important; }

/* piè di pagina (come il menu) */
.sep { width: 80px; height: 2px; background: #57210d; margin: 2.2rem auto 2rem; border-radius: 99px; }
.recensione { background: #57210d; border-radius: 24px; padding: 2rem; text-align: center; box-shadow: 0 10px 15px -3px rgba(0,0,0,.15); }
.recensione h2 { font-family: 'Jost', sans-serif; color: #fff !important; font-weight: 300; letter-spacing: 1px; text-transform: uppercase; font-size: 1.25rem; margin: 0 0 1rem; }
.recensione a { display: block; background: rgba(255,255,255,.125); color: #fff !important; font-family: 'Jost', sans-serif; font-weight: 300; letter-spacing: 1px;
  text-transform: uppercase; text-decoration: none; padding: .8rem; border-radius: 999px; box-shadow: 0 4px 6px rgba(0,0,0,.15); }
.social { display: flex; justify-content: center; gap: 1rem; margin: 1.8rem 0; }
.social a { width: 56px; height: 56px; border-radius: 50%; background: #57210d; color: #fff !important; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 6px rgba(0,0,0,.2); }
.piede { text-align: center; font-size: .85rem; color: #444 !important; line-height: 2; margin-top: 2.4rem; }
.piede a { color: #1a1a1a !important; text-decoration: none; }
.piede u { text-decoration: underline dotted; }

/* apertura della barra laterale: ben visibile */
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] button, [data-testid="collapsedControl"] button {
  background: #57210d !important; color: #fff !important; border-radius: 999px !important; padding: .35rem .9rem !important;
  box-shadow: 0 4px 6px rgba(0,0,0,.2); opacity: 1 !important; width: auto !important; height: auto !important; }
[data-testid="stExpandSidebarButton"] *, [data-testid="stSidebarCollapsedControl"] button *, [data-testid="collapsedControl"] button * {
  color: #fff !important; fill: #fff !important; opacity: 1 !important; }
[data-testid="stExpandSidebarButton"]::after, [data-testid="stSidebarCollapsedControl"] button::after, [data-testid="collapsedControl"] button::after {
  content: " Opzioni"; color: #fff; font-family: 'Jost', sans-serif; letter-spacing: .06em; text-transform: uppercase; font-size: .85rem; }

/* pulsanti + e - del numero di commensali: segni ben visibili */
[data-testid="stNumberInputStepUp"], [data-testid="stNumberInputStepDown"] { background: #57210d !important; border-radius: 8px !important; }
[data-testid="stNumberInputStepUp"] *, [data-testid="stNumberInputStepDown"] *,
[data-testid="stNumberInputContainer"] [data-testid="stNumberInputStepUp"] *, [data-testid="stNumberInputContainer"] [data-testid="stNumberInputStepDown"] * {
  color: #fff !important; fill: #fff !important; stroke: #fff !important; }
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Sto preparando il modello (qualche secondo)...")
def carica():
    m_ = Motore("dettaglio_ordini_cena.csv")
    pagine_, voci_ = carica_menu("menu_marina.json", list(m_.fam))
    for v in voci_.values():
        if v["id"].startswith("menu-pranzo-mer-gio-ven:"):
            v["csv"], v["pranzo"] = None, True        # le raccomandazioni valgono solo per il menu della sera
    # nel menu la birra alla spina è una voce sola ("bionda - rossa"); nei dati la rossa è un prodotto a parte
    for rossa, base in (("MEDIA ROSSA", "BIRRA MEDIA"), ("PICCOLA ROSSA", "BIRRA PICCOLA")):
        b = next((v for v in voci_.values() if v["csv"] == base), None)
        if b and rossa in m_.fam:
            voci_[b["id"] + ":rossa"] = dict(b, id=b["id"] + ":rossa", nome=b["nome"].replace("ALLA SPINA", "ALLA SPINA · ROSSA"),
                                              desc="", csv=rossa)
    coll = [v for v in voci_.values() if v["csv"]]
    prezzi = {}
    for v in coll:
        if v["prezzo"]:
            prezzi.setdefault(v["csv"], v["prezzo"])
    m_.imposta_menu({v["csv"] for v in coll}, prezzi)          # il modello propone solo piatti del menu attuale
    per_csv = {}
    for v in coll:
        per_csv.setdefault(v["csv"], v)                         # prodotto del modello -> voce del menu
    return m_, pagine_, voci_, per_csv


m, PAGINE, VOCI, PER_CSV = carica()
st.session_state.setdefault("qty", {})           # id voce -> quantità
st.session_state.setdefault("ultimo", None)      # ultimo piatto aggiunto: è quello a cui riferire il suggerimento
st.session_state.setdefault("rifiutate", [])
st.session_state.setdefault("impasto", None)      # supplemento impasto in attesa di sapere a quale pizza va
st.session_state.setdefault("sfoglia", None)     # (categoria, piatto di riferimento) quando il cliente accetta e apre il menu della categoria
st.session_state.setdefault("pagina", None)
st.session_state.setdefault("aperto", False)
# giorno e ora: quelli di adesso (orologio del locale); nella barra laterale si possono cambiare per simulare altre serate
from datetime import datetime
from zoneinfo import ZoneInfo
_ora = datetime.now(ZoneInfo("Europe/Rome"))
GIORNI_APERTURA = ["Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]     # lunedì e martedì il locale è chiuso
st.session_state.setdefault("giorno", list(GIORNI)[_ora.weekday()] if list(GIORNI)[_ora.weekday()] in GIORNI_APERTURA else "Mercoledì")
st.session_state.setdefault("fascia", "Prima delle 20" if _ora.hour < 20 else ("20:00 - 20:59" if _ora.hour == 20 else "Dopo le 21"))
st.session_state.setdefault("commensali", 2)
st.session_state.setdefault("avviata", False)

NOMI_VAR = {"giorno": "giorno", "fascia": "fascia oraria", "commensali": "commensali"}


def eur(x):
    return f"{x:.2f}".replace(".", ",") + " €"


def e(s):
    return html.escape(s or "")


def piu(i):
    st.session_state.qty[i] = st.session_state.qty.get(i, 0) + 1
    st.session_state.ultimo = i


def meno(i):
    q = st.session_state.qty.get(i, 0) - 1
    if q <= 0:
        st.session_state.qty.pop(i, None)
    else:
        st.session_state.qty[i] = q
    st.session_state.ultimo = None


def svuota():
    st.session_state.qty = {}
    st.session_state.ultimo = None
    st.session_state.rifiutate = []
    st.session_state.sfoglia = None
    st.session_state.impasto = None


def rifiuta(categoria):
    if categoria not in st.session_state.rifiutate:
        st.session_state.rifiutate.append(categoria)
    st.session_state.ultimo = None


def vai(slug):
    st.session_state.pagina = slug
    st.session_state.sfoglia = None
    st.session_state.ultimo = None          # cambiando menu il suggerimento non si ripropone
    st.session_state.impasto = None


def e_impasto(v):
    return v["nome"].lower().startswith("impasto")


def scegli_impasto(imp_id):
    st.session_state.impasto = imp_id
    st.session_state.ultimo = None


def annulla_impasto():
    st.session_state.impasto = None


def variante(pizza_id, imp_id):
    """Riga di carrello «pizza + impasto»: così si capisce a quale pizza si riferisce il supplemento."""
    vid = f"{pizza_id}|{imp_id}"
    if vid not in VOCI:
        p, imp = VOCI[pizza_id], VOCI[imp_id]
        VOCI[vid] = dict(p, id=vid, nome=f"{p['nome']} · {imp['nome'].lower().replace(' supplemento', '')}", nome_base=p["nome"],
                         prezzo=(p["prezzo"] or 0) + (imp["prezzo"] or 0), prezzo_txt=eur((p["prezzo"] or 0) + (imp["prezzo"] or 0)), desc="")
    return vid


def applica_impasto(pizza_id, imp_id, tutte=False):
    q = st.session_state.qty
    n = q[pizza_id] if tutte else 1
    q[pizza_id] -= n
    if q[pizza_id] <= 0:
        q.pop(pizza_id)
    vid = variante(pizza_id, imp_id)
    q[vid] = q.get(vid, 0) + n
    st.session_state.impasto = None
    st.session_state.ultimo = None


def apri_cat(categoria, base):
    st.session_state.sfoglia = (categoria, base)
    st.session_state.ultimo = None


def chiudi_cat():
    st.session_state.sfoglia = None


def alterna():
    st.session_state.aperto = not st.session_state.aperto


def esempio(prodotti, giorno, fascia, n):
    st.session_state.qty = {PER_CSV[p]["id"]: 1 for p in prodotti if p in PER_CSV}
    st.session_state.ultimo = None
    st.session_state.rifiutate = []
    st.session_state.giorno, st.session_state.fascia, st.session_state.commensali = giorno, fascia, n


def avvia():
    st.session_state.avviata = True


# ---------------------------------------------------------------- domande iniziali (solo per la demo)
if not st.session_state.avviata:
    st.markdown(f'<div class="logo"><img src="{LOGO_URL}"></div>', unsafe_allow_html=True)
    st.markdown('<div class="titolo">Prima di iniziare</div>', unsafe_allow_html=True)
    st.info("Questa è una demo. Il sistema usa il contesto dell'ordine per scegliere i suggerimenti: giorno, fascia oraria e numero di commensali. Nel sito vero queste informazioni non verranno chieste ma calcolate in automatico dal sistema. "
            "Qui servono per simulare serate diverse e vedere come cambiano i suggerimenti.")
    st.selectbox("Giorno", GIORNI_APERTURA, key="giorno")
    st.selectbox("Fascia oraria", list(FASCE), key="fascia")
    st.number_input("Commensali", min_value=1, max_value=20, key="commensali")
    st.button("Apri il menu", key="avvia", on_click=avvia, use_container_width=True)
    st.stop()


qty = st.session_state.qty
for _i in list(qty):
    if "|" in _i:
        variante(*_i.split("|"))
carrello = [(VOCI[i], q) for i, q in qty.items()]
n_art = sum(q for _, q in carrello)
valore = round(sum((v["prezzo"] or 0) * q for v, q in carrello), 2)
n_comm = int(st.session_state.commensali)

# ---------------------------------------------------------------- barra laterale (simulazione e dimostrazione)
with st.sidebar:
    st.header("Simulazione del tavolo")
    st.caption("Nel sito vero questi dati li calcola il sistema (orologio, coperti, carrello). Qui puoi cambiarli per simulare un'altra serata.")
    st.selectbox("Giorno", GIORNI_APERTURA, key="giorno")
    st.selectbox("Fascia oraria", list(FASCE), key="fascia")
    st.number_input("Commensali", min_value=1, max_value=20, key="commensali")
    st.metric("Totale dell'ordine", eur(valore))
    st.divider()
    st.radio("Sistema di suggerimento", ["Il mio sistema", "Baseline"], key="sistema",
             help="Il mio sistema sceglie la categoria in base al piatto e al contesto. La baseline propone sempre la categoria più ordinata in generale tra quelle consentite, uguale per tutti i piatti: serve per il confronto.")
    demo = st.toggle("Modalità dimostrazione", value=False,
                     help="Mostra i dettagli tecnici (probabilità, motivazioni, regole, variabili di contesto). Spenta = ciò che vedrebbe il cliente.")
    fisso = st.toggle("Carrello sempre visibile in alto", value=False,
                      help="Spento: il carrello sta fermo in cima alla pagina. Acceso: resta visibile mentre scorri il menu.")
    soglia = SOGLIA
    if demo:
        soglia = st.slider("Soglia di rilevanza", 5, 50, int(SOGLIA * 100), 5, format="%d%%",
                           help="Il suggerimento compare solo se la probabilità stimata supera questa soglia.") / 100
    st.subheader("Esempi rapidi")
    st.button("Tavolo di pesce", key="ex1", on_click=esempio, args=(["SPAGHETTI ALLO SCOGLIO"], "Sabato", "20:00 - 20:59", 5), use_container_width=True)
    st.button("Pizza e birra", key="ex2", on_click=esempio, args=(["MARGHERITA", "BIRRA MEDIA"], "Mercoledì", "Prima delle 20", 2), use_container_width=True)
    st.button("Cena quasi completa", key="ex3", on_click=esempio, args=(["MARGHERITA", "BUFALA", "BIRRA MEDIA", "COCA COLA"], "Venerdì", "Dopo le 21", 4), use_container_width=True)
    with st.expander("Come funziona"):
        st.markdown(
            "Il modello è stato addestrato sugli ordini storici dei tavoli. Ogni volta che si aggiunge un piatto, stima per ogni categoria "
            "la probabilità che il tavolo la ordini (in base al carrello e al contesto) e propone la più probabile tra quelle non ancora "
            "presenti. Dentro la categoria sceglie il prodotto più spesso ordinato insieme al piatto appena aggiunto, tra quelli del menu attuale.\n\n"
            "Prototipo dimostrativo: non è collegato a un ordine reale."
        )

if fisso:
    st.markdown("<style>div:has(> .st-key-ordine) { position: sticky; top: 3.3rem; z-index: 60; }</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------- suggerimento (si aggiorna a ogni piatto aggiunto)
def senza_suggerimenti(v):
    """Supplementi (impasto kamut/multicereali) e coperto non sono piatti: non generano raccomandazioni."""
    n = v["nome"].lower()
    return "supplemento" in n or n.startswith("coperto")


ultimo_id = st.session_state.ultimo
sugg, tutti, regole, candidati = None, [], [], []
if (ultimo_id in qty and not senza_suggerimenti(VOCI[ultimo_id]) and VOCI[ultimo_id]['csv'] and not VOCI[ultimo_id].get('pranzo')
        and st.session_state.sfoglia is None):
    csv_cart = [v["csv"] for v, _ in carrello if v["csv"]]
    if csv_cart:
        tutti, regole, _ = m.suggerisci(csv_cart, GIORNI[st.session_state.giorno], FASCE[st.session_state.fascia], n_comm,
                                        k=12, valore=valore, ultimo=VOCI[ultimo_id]["csv"], n_prodotti=1)
        if st.session_state.get("sistema") == "Baseline":
            # baseline: la categoria piu' ordinata in generale tra quelle consentite, senza guardare il piatto ne' il contesto
            _cc = sorted({m.fam[p] for p in csv_cart})
            _no = non_consentite_fasi(_cc, m.cats, m.fam.get(VOCI[ultimo_id]["csv"])) | set(_cc)
            _ok = [c for c in sorted(m.cats, key=lambda c: -m.base[c]) if c not in _no
                   and any(m.regole.prodotti[j] in m.disponibili for j in m.regole.prod_per_cat[c])]
            tutti = [{"categoria": c, "prob": m.base[c], "prob_modello": m.base[c], "prob_solo": m.base[c], "quota_piatto": None,
                      "base": m.base[c], "motivo": ["Baseline: categoria più ordinata in generale."], "effetti": {}, "prodotti": []} for c in _ok]
            regole = ["Baseline: stessa lista per tutti i piatti, nessun uso del piatto né del contesto. Valgono le stesse regole sul momento del pasto."]
            candidati = tutti
        else:
            candidati = [s for s in tutti if s["prob"] >= soglia]
        sugg = candidati[0] if candidati else None      # solo la più rilevante; se il cliente dice no, per quel piatto si sta in silenzio


ARTICOLO = {"Birra": "una birra", "Bibite analcoliche": "una bibita", "Contorni": "un contorno", "Dessert": "un dolce",
            "Caffetteria": "un caffè", "Amari e digestivi": "un amaro o un digestivo", "Vino bianco e spumante": "un vino bianco o uno spumante",
            "Vino rosso": "un vino rosso", "Pizze": "una pizza", "Primi di pesce": "un primo di pesce", "Primi di carne": "un primo di carne",
            "Primi vegetariani/altri": "un primo vegetariano", "Secondi di pesce": "un secondo di pesce", "Secondi di carne": "un secondo di carne",
            "Secondi vegetariani/altri": "un secondo vegetariano", "Antipasti di pesce": "un antipasto di pesce",
            "Antipasti di carne/salumi": "un antipasto di salumi", "Antipasti vegetariani/altri": "un antipasto"}
ETI_GIORNO = {"feriale": "dei giorni feriali", "ven": "del venerdì", "sab": "del sabato", "dom": "della domenica"}
ETI_FASCIA = {"prima_20": "prima delle 20", "20_21": "tra le 20 e le 21", "dopo_21": "dopo le 21"}
ETI_COMM = {"1_2": "da 1–2 persone", "3_4": "da 3–4 persone", "5+": "da 5 o più persone"}
ETI = {"giorno": ETI_GIORNO, "fascia": ETI_FASCIA, "commensali": ETI_COMM}
NOMI_V = {"giorno": "Giorno", "fascia": "Fascia oraria", "commensali": "Commensali"}
TITOLO = {"Birra": "Birre", "Bibite analcoliche": "Bibite", "Contorni": "Contorni", "Dessert": "Dessert", "Caffetteria": "Caffetteria",
          "Amari e digestivi": "Amari e digestivi", "Vino bianco e spumante": "Vini bianchi e spumanti", "Vino rosso": "Vini rossi"}


TITOLO_BREVE = {"Birra": "le birre", "Bibite analcoliche": "le bibite", "Contorni": "i contorni", "Dessert": "i dolci", "Caffetteria": "i caffè",
                "Amari e digestivi": "gli amari", "Vino bianco e spumante": "i vini bianchi", "Vino rosso": "i vini rossi"}


def motivo_cliente(p, categoria):
    mm = re.search(r"«(.+?)»", p["motivo"])
    pc = re.search(r"\((\d+)% dei tavoli", p["motivo"])
    if p["motivo"].startswith("Ordinato insieme") and mm and pc:
        base = PER_CSV.get(mm.group(1), {}).get("nome", mm.group(1).title())
        testo = f"Nel {pc.group(1)}% dei tavoli con «{base}» c'era anche questo."
    else:
        testo = "Tra i più scelti in questa categoria."
    if categoria in TARDIVE:
        testo += " Lo proponiamo ora perché nell'ordine c'è già un piatto principale."
    return testo


def blocco_suggerimento():
    if sugg is None:
        if demo and ultimo_id in qty:
            nome_u = VOCI[ultimo_id]["nome"]
            if VOCI[ultimo_id].get("pranzo"):
                st.caption("Nessun suggerimento: le raccomandazioni valgono solo per il menu della sera, non per il menù pranzo.")
            elif not VOCI[ultimo_id]["csv"]:
                st.caption(f"Nessun suggerimento: «{nome_u}» non è tra i prodotti dei dati storici (supplementi, coperto e voci senza storico non generano raccomandazioni).")
            elif not candidati:
                st.caption(f"Nessun suggerimento: nessuna categoria raggiunge il {int(soglia * 100)}% di probabilità. Il silenzio è un risultato valido.")
        return
    cat = sugg["categoria"]
    base_csv = VOCI[ultimo_id]["csv"]
    base_nome = VOCI[ultimo_id].get("nome_base", VOCI[ultimo_id]["nome"])
    quota, n_tav = m.quota_categoria(base_csv, cat)
    art = ARTICOLO.get(cat, "un prodotto della categoria «" + cat + "»")
    base_lab = f"«{base_nome}»" if m.storico_piatto(base_csv) else ARTICOLO.get(m.fam.get(base_csv), "un piatto di questa categoria")
    if cat in TARDIVE:
        motivo = f"Nel {quota:.0%} dei tavoli con {base_lab} ({n_tav} tavoli) c'era anche {art}. Lo proponiamo ora perché nell'ordine c'è già un piatto principale."
    else:
        motivo = f"Nel {quota:.0%} dei tavoli con {base_lab} ({n_tav} tavoli) c'era anche {art}."
    baseline = st.session_state.get("sistema") == "Baseline"
    if baseline:
        motivo = f"BASELINE: {art} è la categoria più ordinata in generale ({m.base[cat]:.0%} dei tavoli), la stessa per qualsiasi piatto. Non guarda il piatto né il contesto."
    with st.container(key="sugg_1"):
        st.markdown('<div class="sugg-titolo">Ti potrebbe interessare</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="nome">{e(art[0].upper() + art[1:])}?</div><div class="sugg-motivo">{e(motivo)}</div>', unsafe_allow_html=True)
        with st.container(key=f"row_s_{ultimo_id}"):
            c, d, _ = st.columns([3.2, 1.8, 3], vertical_alignment="center")
            c.button(f"Scopri {TITOLO_BREVE.get(cat, 'le proposte').lower()} →", key="si_s", on_click=apri_cat, args=(cat, base_csv))
            d.button("No, grazie", key="no_s", on_click=rifiuta, args=(cat,))
        if baseline:
            return
        gk, fk = GIORNI[st.session_state.giorno], FASCE[st.session_state.fascia]
        q_ctx, n_ctx, q_med, usate, dett = m.profilo_contesto(base_csv, cat, gk, fk, n_comm)
        if usate and n_ctx:
            quando = ", ".join(ETI[v][val] for v, val in usate)
            frase_ctx = f"Nei tavoli {quando}: il {q_ctx:.0%} ha ordinato anche {art} (in media il {q_med:.0%})."
        else:
            frase_ctx = ""
        ETI_S = {"giorno": {"feriale": "Giorni feriali", "ven": "Venerdì", "sab": "Sabato", "dom": "Domenica"},
                 "fascia": {"prima_20": "Prima delle 20", "20_21": "20:00 - 20:59", "dopo_21": "Dopo le 21"},
                 "commensali": {"1_2": "1–2 commensali", "3_4": "3–4 commensali", "5+": "5 o più commensali"}}
        righe_v = [f"{ETI_S[v][val]}: {q:.0%} ({n} tavoli)" for v, val, q, n in dett if q is not None and n >= 5]
        if righe_v:
            st.markdown(f'<div class="sugg-motivo">Tenendo conto anche del contesto, quota di tavoli con questo piatto che hanno ordinato {e(art)}:<br>'
                        + "<br>".join(e(r) for r in righe_v) + "</div>", unsafe_allow_html=True)
        if demo:
            st.markdown(f'<div class="sugg-motivo">Stima per questo piatto, corretta dal contesto: <b>{sugg["prob"]:.0%}</b> '
                        f'(dati del solo piatto: {sugg["quota_piatto"]:.0%}; media: {q_med:.0%}).</div>', unsafe_allow_html=True)
        if demo:
            eff = ", ".join(f"{NOMI_VAR[k]} {dd * 100:+.0f}" for k, dd in sugg["effetti"].items())
            righe = [f"<b>Categoria proposta:</b> {e(sugg['categoria'])} · probabilità stimata <b>{sugg['prob']:.0%}</b> (soglia {int(soglia * 100)}%)",
                     "<b>Perché la categoria:</b> " + " ".join(e(r) for r in sugg["motivo"]),
                     f"<b>Se il cliente accetta:</b> si apre il menu «{e(cat)}» con i prodotti ordinati per quante volte sono stati ordinati insieme a «{e(base_nome)}» ({n_tav} tavoli nei dati storici); quelli mai ordinati insieme restano in fondo.",
                     f"<b>Effetto di ogni variabile da sola</b> (punti di probabilità): {e(eff)}",
                     "<b>Regole operative applicate:</b> " + " ".join(e(r) for r in regole),
                     "<b>Classifica categorie:</b> " + " · ".join(e(f"{x['categoria']} {x['prob']:.0%}") for x in tutti[:3])]
            st.markdown('<div class="tecnico">' + "<br>".join(righe) + "</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- intestazione
st.markdown(f'<div class="logo"><img src="{LOGO_URL}"></div>', unsafe_allow_html=True)

slug = st.session_state.pagina
pag = next((p for p in PAGINE if p["slug"] == slug), None)
if pag is None:
    st.markdown('<div class="titolo">I nostri menù</div>', unsafe_allow_html=True)
else:
    st.button("← Tutti i menù", key="torna_su", on_click=vai, args=(None,))

# ---------------------------------------------------------------- carrello (sempre visibile in alto)
if carrello:
    with st.container(key="ordine"):
        a, b = st.columns([4, 1.4], vertical_alignment="center")
        a.markdown(f'<div class="riepilogo">🛒 Il tuo ordine <span>· {n_art} {"articolo" if n_art == 1 else "articoli"} ·</span> {eur(valore)}</div>', unsafe_allow_html=True)
        b.button("Chiudi" if st.session_state.aperto else "Vedi", key="apri_ordine", on_click=alterna)
        if st.session_state.aperto:
            for v, q in carrello:
                with st.container(key=f"crow_{v['id']}"):
                    c1, c2, c3, c4, c5 = st.columns([5, 2, 1, 0.8, 1], vertical_alignment="center")
                    c1.markdown(f'<div class="nome">{e(v["nome"])}</div>', unsafe_allow_html=True)
                    c2.markdown(f'<div class="prezzo">{eur((v["prezzo"] or 0) * q)}</div>', unsafe_allow_html=True)
                    c3.button("−", key=f"cminus_{v['id']}", on_click=meno, args=(v["id"],))
                    c4.markdown(f'<div class="qta">{q}</div>', unsafe_allow_html=True)
                    c5.button("+", key=f"cplus_{v['id']}", on_click=piu, args=(v["id"],))
            st.button("Svuota l'ordine", key="svuota_ordine", on_click=svuota)

# il suggerimento sta accanto al piatto appena scelto; se quel piatto non è in questa pagina, compare qui in alto
ultimo_in_pagina = pag is not None and any(v["id"] == ultimo_id for s in pag["sez"] for v in s["voci"])
if ultimo_id in qty and not ultimo_in_pagina:
    blocco_suggerimento()


def scelta_pizza(imp):
    """Subito sotto la riga dell'impasto: a quale pizza (e a quante) si riferisce."""
    pizze = [(v, q) for v, q in carrello if v["id"].startswith(("le-nostre-pizze:", "pizze-speciali:")) and "|" not in v["id"]
             and not e_impasto(v) and not v["nome"].lower().startswith("coperto")]
    nome_imp = imp["nome"].lower().replace(" supplemento", "")
    with st.container(key="sugg_impasto"):
        if not pizze:
            st.markdown(f'<div class="nome">A quale pizza vuoi aggiungere {e(nome_imp)}?</div>'
                        '<div class="sugg-motivo">Nel carrello non c\'è ancora nessuna pizza: aggiungila, poi scegli l\'impasto.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="nome">A quale pizza vuoi aggiungere {e(nome_imp)}?</div>'
                        '<div class="sugg-motivo">Scegli la pizza: le altre restano con l\'impasto normale.</div>', unsafe_allow_html=True)
        for v, q in pizze:
            if q == 1:
                st.button(v["nome"], key=f"imp_{v['id']}", on_click=applica_impasto, args=(v["id"], imp["id"]))
            else:
                st.button(f'Una {v["nome"]} (su {q})', key=f"imp_{v['id']}", on_click=applica_impasto, args=(v["id"], imp["id"]))
                st.button(f'Tutte e {q} le {v["nome"]}', key=f"imptutte_{v['id']}", on_click=applica_impasto, args=(v["id"], imp["id"], True))
        st.button("Annulla", key="imp_annulla", on_click=annulla_impasto)


def riga_menu(v, nota=None):
    with st.container(key=f"row_m_{v['id']}"):
        q = qty.get(v["id"], 0)
        a, b, c, d, f = st.columns([6, 2.2, 0.95, 0.6, 0.95], vertical_alignment="center")
        desc = f'<div class="desc">{e(v["desc"])}</div>' if v["desc"] else ""
        if nota:
            desc += f'<div class="desc">{e(nota)}</div>'
        a.markdown(f'<div class="nome">{e(v["nome"])}</div>{desc}', unsafe_allow_html=True)
        b.markdown(f'<div class="prezzo">{e(v["prezzo_txt"])}</div>', unsafe_allow_html=True)
        if q and not e_impasto(v):
            c.button("−", key=f"minus_{v['id']}", on_click=meno, args=(v["id"],))
            d.markdown(f'<div class="qta">{q}</div>', unsafe_allow_html=True)
        if e_impasto(v):
            f.button("+", key=f"plus_{v['id']}", on_click=scegli_impasto, args=(v["id"],))
        else:
            f.button("+", key=f"plus_{v['id']}", on_click=piu, args=(v["id"],))


# ---------------------------------------------------------------- menu della categoria consigliata
def vista_categoria():
    cat, base_csv = st.session_state.sfoglia
    base_nome = PER_CSV[base_csv]["nome"] if base_csv in PER_CSV else base_csv.title()
    ordinati = [(PER_CSV[p], n, q) for p, n, q in m.ordina_categoria(cat, base_csv) if p in PER_CSV]
    etich = f"«{base_nome}»" if m.storico_piatto(base_csv) else ARTICOLO.get(m.fam.get(base_csv), "un piatto di questa categoria")
    with st.container(key="pagina"):
        st.markdown(f'<div class="h1">{e(TITOLO.get(cat, cat))}</div><div class="barra"></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="nota-d">Ordinati in base a quanto si scelgono insieme a {e(etich)}.</div>', unsafe_allow_html=True)
        for v, n, q in ordinati:
            nota = (f"Nel {q:.0%} dei tavoli con {etich}" if q >= 0.01 else f"In meno dell'1% dei tavoli con {etich}") if n > 0 else None
            riga_menu(v, nota)
    st.button("← Torna al menu", key="chiudi_cat", on_click=chiudi_cat, use_container_width=True)


# ---------------------------------------------------------------- menu
if st.session_state.sfoglia is not None:
    vista_categoria()
elif pag is None:
    for i, p in enumerate(PAGINE):
        st.button(p["titolo"], key=f"cat_{i}", on_click=vai, args=(p["slug"],), use_container_width=True)
else:
    with st.container(key="pagina"):
        st.markdown(f'<div class="h1">{e(pag["titolo"])}</div><div class="barra"></div>', unsafe_allow_html=True)
        if pag["img"]:
            st.markdown(f'<img class="banner" src="{pag["img"]}">', unsafe_allow_html=True)
        if pag["nota"]:
            t, _, d_ = pag["nota"].partition("\n")
            st.markdown(f'<div class="nota-t">{e(t)}</div><div class="nota-d">{e(d_)}</div>', unsafe_allow_html=True)
        for sez in pag["sez"]:
            if sez["nome"]:
                st.markdown(f'<div class="pillola">{e(sez["nome"])}</div>', unsafe_allow_html=True)
            for v in sez["voci"]:
                riga_menu(v)
                if e_impasto(v) and st.session_state.impasto == v["id"]:
                    scelta_pizza(v)
                if ultimo_in_pagina and v["id"] == ultimo_id:
                    blocco_suggerimento()
    st.markdown('<div class="sezione">Scopri gli altri menù</div>', unsafe_allow_html=True)
    for i, p in enumerate(PAGINE):
        if p["slug"] != slug:
            st.button(p["titolo"], key=f"alt_{i}", on_click=vai, args=(p["slug"],), use_container_width=True)

# ---------------------------------------------------------------- piè di pagina
ICONE = {
    "instagram": '<rect width="20" height="20" x="2" y="2" rx="5" ry="5"></rect><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path><line x1="17.5" x2="17.51" y1="6.5" y2="6.5"></line>',
    "facebook": '<path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"></path>',
    "pin": '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"></path><circle cx="12" cy="10" r="3"></circle>',
    "star": '<path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"></path>',
}
LINK = [("instagram", "https://www.instagram.com/ristorante_marina/", "Instagram"),
        ("facebook", "https://www.facebook.com/marinapizzeriaconcucina/", "Facebook"),
        ("pin", "https://maps.app.goo.gl/Ckifgdvxebabtzhj6", "Google Maps"),
        ("star", "https://www.tripadvisor.it/Restaurant_Review-g2550546-d4409834-Reviews-Pizzeria_Marina-Gessate_Province_of_Milan_Lombardy.html?m=19905", "TripAdvisor")]
social = "".join(
    f'<a href="{u}" target="_blank" aria-label="{n}"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
    f'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{ICONE[k]}</svg></a>' for k, u, n in LINK)
st.markdown(
    '<div class="sep"></div>'
    '<div class="recensione"><h2>Come ti sei trovato?</h2><a href="https://recensioni.share-me.it/marina" target="_blank">Lascia una recensione</a></div>'
    f'<div class="social">{social}</div>'
    '<div class="piede">Hai trovato utile il nostro servizio? <a href="https://share-me.it/referral-program" target="_blank"><u>Aiutaci a supportare altri professionisti</u></a><br>'
    '<a href="https://docs.cookie-script.com/69d9efdd133459c4c38625d3ebb807b3/it/cookie-policy.html" target="_blank">Cookie Policy</a> &nbsp;•&nbsp; '
    '<a href="https://share-me.it/soluzioni-digitali-ristorazione/privacy-policy/" target="_blank">Privacy Policy</a> &nbsp;•&nbsp; '
    '<a href="https://share-me.it/soluzioni-digitali-ristorazione/termini-e-condizioni/" target="_blank">Termini e Condizioni</a><br>'
    'Powered by <b class="jost">Share Me</b></div>',
    unsafe_allow_html=True)
