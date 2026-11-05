"""Punto 2: modelli baseline.

Baseline A - prodotti più frequenti: propone i K prodotti ordinati in più turni.
Baseline B - categorie più frequenti: prende le categorie ordinate in più turni e,
             per ciascuna, propone il prodotto più frequente di quella categoria.
In entrambi i casi non si propone mai un prodotto già nel carrello, né acqua,
né voci aggiuntive (macchiato, affogato caffè). Le frequenze si calcolano solo sul training set.
"""
import pandas as pd

ESCLUSI_PRODOTTI = {"macchiato", "affogato caffe"}
ESCLUSE_CATEGORIE = {"ESCLUDERE", "Acqua"}


def carica_turni(percorso_csv):
    d = pd.read_csv(percorso_csv, sep=";", decimal=",")
    d = d[~d["macro_categoria"].isin(ESCLUSE_CATEGORIE)]
    d = d[~d["nome_articolo"].isin(ESCLUSI_PRODOTTI)].copy()
    d["data"] = pd.to_datetime(d["Data"], format="%d/%m/%Y")
    d = d.drop_duplicates(["identificativo_turno", "nome_articolo"])
    return d


def dividi_temporale(d, quota_train=0.7):
    """Training = le serate più vecchie, test = le più recenti; un turno resta intero in un solo insieme."""
    date = sorted(d["data"].unique())
    taglio = date[int(len(date) * quota_train)]
    return d[d["data"] < taglio], d[d["data"] >= taglio], taglio


class BaselineProdotti:
    def fit(self, train):
        self.ranking = train.groupby("nome_articolo")["identificativo_turno"].nunique().sort_values(ascending=False)
        return self

    def raccomanda(self, carrello, k=3):
        return [p for p in self.ranking.index if p not in set(carrello)][:k]


class BaselineCategorie:
    def fit(self, train):
        self.cat = train.groupby("macro_categoria")["identificativo_turno"].nunique().sort_values(ascending=False)
        prod = train.groupby(["macro_categoria", "nome_articolo"])["identificativo_turno"].nunique()
        self.top_per_cat = {c: prod[c].sort_values(ascending=False).index.tolist() for c in self.cat.index}
        return self

    def raccomanda(self, carrello, k=3):
        gia, out = set(carrello), []
        for c in self.cat.index:
            for p in self.top_per_cat[c]:
                if p not in gia:
                    out.append(p)
                    break
            if len(out) == k:
                break
        return out


class BaselineCategorieComplementari(BaselineCategorie):
    """Come B, ma salta le categorie che il carrello contiene già (con la pizza nel carrello non propone un'altra pizza)."""
    def fit(self, train):
        super().fit(train)
        self.categoria = dict(zip(train["nome_articolo"], train["macro_categoria"].map(self._famiglia)))
        return self

    @staticmethod
    def _famiglia(c):
        return "Pizze" if str(c).startswith("Pizze") else c

    def raccomanda(self, carrello, k=3):
        gia, cat_gia, out = set(carrello), {self.categoria.get(p) for p in carrello}, []
        for c in self.cat.index:
            if self._famiglia(c) in cat_gia:
                continue
            for p in self.top_per_cat[c]:
                if p not in gia:
                    out.append(p)
                    break
            if len(out) == k:
                break
        return out


class BaselineCategorieSole:
    """Livello categorie: propone le K categorie più frequenti non ancora nel carrello (pizze = una sola famiglia)."""
    def fit(self, train):
        f = train["macro_categoria"].map(BaselineCategorieComplementari._famiglia)
        self.cat = train.assign(fam=f).groupby("fam")["identificativo_turno"].nunique().sort_values(ascending=False)
        return self

    def raccomanda(self, categorie_carrello, k=3):
        gia = {BaselineCategorieComplementari._famiglia(c) for c in categorie_carrello}
        return [c for c in self.cat.index if c not in gia][:k]


if __name__ == "__main__":
    d = carica_turni("../dettaglio_ordini_cena.csv")
    train, test, taglio = dividi_temporale(d)
    print(f"Training: {train.identificativo_turno.nunique()} turni (fino al {pd.Timestamp(taglio).date()}) | "
          f"test: {test.identificativo_turno.nunique()} turni")
    A, B, B2 = BaselineProdotti().fit(train), BaselineCategorie().fit(train), BaselineCategorieComplementari().fit(train)
    nt = train.identificativo_turno.nunique()
    print("\nPRODOTTI PIU' FREQUENTI (quota di turni di training)")
    print((A.ranking.head(12) / nt).round(3).to_string())
    print("\nCATEGORIE PIU' FREQUENTI (quota di turni di training)")
    print((B.cat.head(12) / nt).round(3).to_string())
    for nome, carrello in [("carrello vuoto", []), ("pizza margherita", ["MARGHERITA"]),
                           ("pizza + birra media", ["MARGHERITA", "BIRRA MEDIA"]), ("primo di pesce", ["SPAGHETTI VONGOLE"])]:
        print(f"\n{nome}: A -> {A.raccomanda(carrello)} | B -> {B.raccomanda(carrello)} | B2 -> {B2.raccomanda(carrello)}")
    C = BaselineCategorieSole().fit(train)
    print("\nBASELINE C (livello categorie), carrello con una pizza ->", C.raccomanda(["Pizze vegetariane"]))
