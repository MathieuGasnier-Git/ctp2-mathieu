# CTP 2 - Exercice 2 : les memes etapes que openrefine_customers_recipe.json, en pandas
# lancer depuis ctp/ctp2/mathieu :  python clean_customers.py
import os
import re

import pandas as pd

KIT = os.environ.get("SHOPFAST_KIT", "../../../shopfast-kit/data/")
df = pd.read_csv(KIT + "/customers.csv", dtype=str)
print("Rows in:", len(df))


def title_case(v):
    # comme toTitlecase() d'OpenRefine : majuscule seulement apres un espace
    return " ".join(w[:1].upper() + w[1:].lower() for w in v.split(" "))


def to_iso(v):
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", v):  # dd/mm/yyyy
        p = v.split("/")
        return p[2] + "-" + p[1] + "-" + p[0]
    if re.fullmatch(r"\d{2}-\d{2}-\d{4}", v):  # mm-dd-yyyy
        p = v.split("-")
        return p[2] + "-" + p[0] + "-" + p[1]
    if re.fullmatch(r"\d{4}/\d{2}/\d{2}", v):  # yyyy/mm/dd
        return v.replace("/", "-")
    return v


def clean_phone(v):
    v = re.sub(r"[^0-9+]", "", v)
    if v.startswith("0033"):
        return "+33" + v[4:]
    if v.startswith("0") and len(v) == 10:
        return "+33" + v[1:]
    return v


countries = {"fr": "FR", "fra": "FR", "france": "FR",
             "de": "DE", "deu": "DE", "germany": "DE", "allemagne": "DE",
             "es": "ES", "esp": "ES", "spain": "ES", "espagne": "ES",
             "be": "BE", "bel": "BE", "belgium": "BE", "belgique": "BE"}

# 1. doublons exacts : tri sur customer_id puis on garde la premiere ligne (= blank down + suppression)
df = df.sort_values("customer_id", kind="stable")
df = df[~df["customer_id"].duplicated()].reset_index(drop=True)

# 2. noms et adresse
for col in ["first_name", "last_name"]:
    df[col] = df[col].map(lambda v: title_case(re.sub(r"\s+", " ", v.strip())), na_action="ignore")
df["address"] = df["address"].str.strip()

# 3. email
df["email"] = df["email"].str.strip().str.lower()

# 4. pays (les cases vides restent vides)
df["country"] = df["country"].str.strip().str.lower().map(countries).fillna(df["country"])

# 5. dates
df["signup_date"] = df["signup_date"].map(to_iso, na_action="ignore")
df["birth_date"] = df["birth_date"].map(to_iso, na_action="ignore")

# 6. loyalty tier
df["loyalty_tier"] = df["loyalty_tier"].str.strip().str.lower().replace("platinium", "platinum")

# 7. CP francais a 4 chiffres (apres le pays, sinon "France" n'est pas encore FR)
fix = (df["country"] == "FR") & (df["postal_code"].str.len() == 4)
df.loc[fix, "postal_code"] = "0" + df.loc[fix, "postal_code"]

# 8. telephones
df["phone"] = df["phone"].map(clean_phone, na_action="ignore")

# 9. on signale les emails en double, on ne les supprime pas
dup = df["email"].notna() & df["email"].duplicated(keep=False)
df.insert(4, "is_duplicate_email", dup.map({True: "true", False: "false"}))

df.to_csv("customers_clean.csv", index=False, lineterminator="\n")
print("Rows out:", len(df))
print("is_duplicate_email:", df["is_duplicate_email"].value_counts().to_dict())
