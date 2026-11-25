"""CTP 2 - Exercice 1 : profiling de customers.csv avec pandas.
Lancement :  python profile_customers.py
Les chiffres affiches a la fin sont recopies dans quality_scorecard.csv
"""
import os
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def kit_file(name):
    # le kit peut etre a cote du dossier 02_CTP2 ou a la racine du repo
    candidates = [os.environ.get("SHOPFAST_KIT", ""), HERE / "../shopfast-kit/data",
                  HERE / "../../shopfast-kit/data", HERE / "../../../shopfast-kit/data"]
    for d in candidates:
        if d and (Path(d) / name).exists():
            return Path(d) / name
    raise FileNotFoundError(f"{name} introuvable, definir SHOPFAST_KIT=chemin/vers/shopfast-kit/data")


df = pd.read_csv(kit_file("customers.csv"), dtype=str)   # dtype=str : on garde le texte brut (ex 01300)
n = len(df)
TODAY = pd.Timestamp(date.today())
print("Rows:", n)
print(df.head())

rules = []  # (dimension, regle, colonne, failing)


def add(dim, rule, col, failing):
    failing = int(failing)
    rules.append((dim, rule, col, failing, n, round(100 * (1 - failing / n), 2)))


# --- Completeness ---
print("\nEmpty values per column:\n", df.isna().sum())
add("Completeness", "email is filled", "email", df["email"].isna().sum())
add("Completeness", "country is filled", "country", df["country"].isna().sum())
add("Completeness", "phone is filled", "phone", df["phone"].isna().sum())

# --- Uniqueness : customer_id ---
dup_id = df["customer_id"].duplicated(keep=False).sum()
print("\nDuplicated customer_id rows:", dup_id, "| exact duplicate rows (copies):", df.duplicated().sum())
add("Uniqueness", "customer_id is unique", "customer_id", dup_id)

# TODO 1 (Uniqueness) : email normalise (strip + minuscules), personnes inscrites deux fois
# on retire d'abord les doublons exacts de lignes pour ne pas compter deux fois le meme probleme
email_norm = df.drop_duplicates()["email"].str.strip().str.lower()
dup_email = email_norm[email_norm.notna() & email_norm.duplicated(keep=False)]
print("\nTODO 1 - rows sharing a normalised email:", len(dup_email), "| distinct emails concerned:", dup_email.nunique())
print(dup_email.value_counts().head(10))
add("Uniqueness", "one account per person (lower-cased email unique)", "email", len(dup_email))

# TODO 2 (Validity) : regex email
EMAIL_RX = r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$"
bad_email = df["email"].notna() & ~df["email"].str.match(EMAIL_RX, na=False)
print("\nTODO 2 - emails not matching the regex:", bad_email.sum())
print(df.loc[bad_email, "email"].tolist())
add("Validity", "email looks like an email (regex)", "email", bad_email.sum())

# TODO 3 (Consistency) : orthographes des pays
print("\nTODO 3 - country spellings (dropna=False):")
vc = df["country"].value_counts(dropna=False)
print(vc)
print("distinct spellings (incl. empty):", len(vc), "for 4 real countries")
bad_country = df["country"].notna() & ~df["country"].isin(["FR", "DE", "ES", "BE"])
add("Consistency", "country is an ISO-2 code in {FR, DE, ES, BE}", "country", bad_country.sum())

# TODO 4 (Consistency) : signup_date pas au format YYYY-MM-DD
ISO_RX = r"^\d{4}-\d{2}-\d{2}$"
bad_signup = ~df["signup_date"].str.match(ISO_RX, na=False)
print("\nTODO 4 - signup_date not YYYY-MM-DD:", bad_signup.sum())
print(df.loc[bad_signup, "signup_date"].str.replace(r"\d", "9", regex=True).value_counts())
add("Consistency", "signup_date is YYYY-MM-DD", "signup_date", bad_signup.sum())
bad_birth_fmt = ~df["birth_date"].str.match(ISO_RX, na=False)
add("Consistency", "birth_date is YYYY-MM-DD", "birth_date", bad_birth_fmt.sum())

# TODO 5 (Validity) : loyalty_tier hors bronze / silver / gold / platinum
TIERS = ["bronze", "silver", "gold", "platinum"]
bad_tier = ~df["loyalty_tier"].isin(TIERS)
print("\nTODO 5 - loyalty_tier outside the list:", bad_tier.sum())
print(df.loc[bad_tier, "loyalty_tier"].map(repr).value_counts())
add("Validity", "loyalty_tier in {bronze, silver, gold, platinum}", "loyalty_tier", bad_tier.sum())

# TODO 6 (Accuracy) : date de naissance dans le futur, avant 1906, ou client mineur
# on convertit les 4 formats (sinon les dates non ISO echappent au controle)
def parse_any(s):
    out = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    for fmt in ["%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d"]:
        out = out.fillna(pd.to_datetime(s, format=fmt, errors="coerce"))
    return out

birth = parse_any(df["birth_date"])
birth_iso_only = pd.to_datetime(df["birth_date"], format="%Y-%m-%d", errors="coerce")
limit_18 = TODAY - pd.DateOffset(years=18)
future = birth > TODAY
too_old = birth < pd.Timestamp("1906-01-01")
minor = (birth > limit_18) & ~future
print("\nTODO 6 - birth_date in the future:", future.sum(), "| before 1906:", too_old.sum(), "| under 18:", minor.sum())
print("   (ISO rows only: future", (birth_iso_only > TODAY).sum(), "before 1906", (birth_iso_only < pd.Timestamp("1906-01-01")).sum(), ")")
print("   unparseable:", birth.isna().sum())
print(df.loc[future | too_old | minor, ["customer_id", "birth_date"]].to_string())
add("Accuracy", "birth_date between 1906-01-01 and today - 18 years", "birth_date", (future | too_old | minor).sum())

signup = parse_any(df["signup_date"])
add("Accuracy", "signup_date not in the future", "signup_date", (signup > TODAY).sum())

# TODO 7 (Validity) : codes postaux FR qui n'ont pas 5 chiffres
# le pays est d'abord normalise, sinon on rate les lignes "France", "fra", "france "...
COUNTRY_MAP = {"fr": "FR", "fra": "FR", "france": "FR", "de": "DE", "deu": "DE", "germany": "DE", "allemagne": "DE",
               "es": "ES", "esp": "ES", "spain": "ES", "espagne": "ES", "be": "BE", "bel": "BE", "belgium": "BE", "belgique": "BE"}
country_norm = df["country"].str.strip().str.lower().map(COUNTRY_MAP)
is_fr = country_norm == "FR"
bad_cp = is_fr & ~df["postal_code"].str.match(r"^\d{5}$", na=False)
print("\nTODO 7 - French postal codes without 5 digits:", bad_cp.sum(), "out of", is_fr.sum(), "French customers")
print(df.loc[bad_cp, "postal_code"].str.len().value_counts())
add("Validity", "French postal_code has 5 digits", "postal_code", bad_cp.sum())

# --- Timeliness : fraicheur de l'extraction (regle au niveau du fichier) ---
last_signup = signup[signup <= TODAY].max()
age_days = (TODAY - last_signup).days
print(f"\nTimeliness - most recent signup: {last_signup.date()} ({age_days} days ago)")
rules.append(("Timeliness", "customers extract refreshed (last signup < 30 days old)", "signup_date",
              int(age_days >= 30), 1, 0.0 if age_days >= 30 else 100.0))

# Bonus : score de chaque regle
print("\n=== Scorecard (score_pct = 100 * (1 - failing / total)) ===")
out = pd.DataFrame(rules, columns=["dimension", "rule", "column", "failing_rows", "total_rows", "score_pct"])
print(out.to_string(index=False))
print("\nDimensions covered:", out["dimension"].nunique(), "| rules:", len(out))
