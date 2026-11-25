"""CTP 2 - Exercice 2 : meme nettoyage que openrefine_customers_recipe.json, en pandas.
Chaque etape reprend l'expression GREL de la recette, dans le meme ordre.
Lancement :  python clean_customers.py   ->  customers_clean.csv
"""
import os
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def kit_file(name):
    candidates = [os.environ.get("SHOPFAST_KIT", ""), HERE / "../shopfast-kit/data",
                  HERE / "../../shopfast-kit/data", HERE / "../../../shopfast-kit/data"]
    for d in candidates:
        if d and (Path(d) / name).exists():
            return Path(d) / name
    raise FileNotFoundError(f"{name} introuvable, definir SHOPFAST_KIT=chemin/vers/shopfast-kit/data")


def on_text(s, fn):
    # comme OpenRefine : une cellule vide reste vide (erreur -> keep-original)
    return s.map(lambda v: fn(v) if isinstance(v, str) else v)


def title_case(v):
    # toTitlecase() d'OpenRefine : 1re lettre de chaque mot (separe par un espace) en majuscule, le reste en minuscules
    return " ".join(w[:1].upper() + w[1:].lower() for w in v.split(" "))


COUNTRY = {"fr": "FR", "fra": "FR", "france": "FR",
           "de": "DE", "deu": "DE", "germany": "DE", "allemagne": "DE",
           "es": "ES", "esp": "ES", "spain": "ES", "espagne": "ES",
           "be": "BE", "bel": "BE", "belgium": "BE", "belgique": "BE"}


def to_iso(v):
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", v):          # dd/mm/yyyy
        p = v.split("/")
        return p[2] + "-" + p[1] + "-" + p[0]
    if re.fullmatch(r"\d{2}-\d{2}-\d{4}", v):          # mm-dd-yyyy
        p = v.split("-")
        return p[2] + "-" + p[0] + "-" + p[1]
    if re.fullmatch(r"\d{4}/\d{2}/\d{2}", v):          # yyyy/mm/dd
        return v.replace("/", "-")
    return v


def tier(v):
    v = v.strip().lower()
    return "platinum" if v == "platinium" else v


def phone(v):
    v = re.sub(r"[^0-9+]", "", v)
    if v.startswith("0033"):
        return "+33" + v[4:]
    if v.startswith("0") and len(v) == 10:
        return "+33" + v[1:]
    return v


df = pd.read_csv(kit_file("customers.csv"), dtype=str)
print("Rows in:", len(df))

# 1. doublons exacts : tri customer_id, blank down, suppression des lignes vides
df = df.sort_values("customer_id", kind="stable").reset_index(drop=True)
df = df[~df["customer_id"].duplicated()].reset_index(drop=True)
print("Rows after removing exact duplicates:", len(df))

# 2. noms : trim + espaces multiples reduits + titlecase
for col in ["first_name", "last_name"]:
    df[col] = on_text(df[col], lambda v: title_case(re.sub(r"\s+", " ", v.strip())))
df["address"] = on_text(df["address"], lambda v: v.strip())   # espaces en fin d'adresse

# 3. email : value.trim().toLowercase()
df["email"] = on_text(df["email"], lambda v: v.strip().lower())

# 4. pays : les 18 orthographes -> FR / DE / ES / BE
df["country"] = on_text(df["country"], lambda v: COUNTRY.get(v.strip().lower(), v))

# 5. dates en YYYY-MM-DD
for col in ["signup_date", "birth_date"]:
    df[col] = on_text(df[col], to_iso)

# 6. loyalty tier
df["loyalty_tier"] = on_text(df["loyalty_tier"], tier)

# 7. codes postaux FR a 4 chiffres (le pays est deja normalise a l'etape 4)
fix_cp = (df["country"] == "FR") & (df["postal_code"].str.len() == 4)
df.loc[fix_cp, "postal_code"] = "0" + df.loc[fix_cp, "postal_code"]

# 8. telephones au format +33612345678
df["phone"] = on_text(df["phone"], phone)

# 9. is_duplicate_email juste apres email : on signale, on ne supprime pas
counts = df["email"].value_counts()
flag = df["email"].map(lambda v: isinstance(v, str) and v != "" and counts[v] > 1)
df.insert(4, "is_duplicate_email", flag.map({True: "true", False: "false"}))

out = HERE / "customers_clean.csv"
df.to_csv(out, index=False, lineterminator="\n")
print("Rows out:", len(df), "->", out.name)

# petit controle apres nettoyage
print("countries:", df["country"].value_counts(dropna=False).to_dict())
print("tiers:", df["loyalty_tier"].value_counts().to_dict())
print("dates not ISO:", (~df["signup_date"].str.match(r"^\d{4}-\d{2}-\d{2}$")).sum(),
      (~df["birth_date"].str.match(r"^\d{4}-\d{2}-\d{2}$")).sum())
print("FR postal codes not 5 digits:", ((df["country"] == "FR") & (df["postal_code"].str.len() != 5)).sum())
print("phone formats:", df["phone"].str.replace(r"\d", "9", regex=True).value_counts(dropna=False).to_dict())
print("is_duplicate_email:", df["is_duplicate_email"].value_counts().to_dict())
