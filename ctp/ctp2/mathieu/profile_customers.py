# CTP 2 - Exercice 1 : profiling de customers.csv
# lancer depuis ctp/ctp2/mathieu :  python profile_customers.py
import os
from datetime import date

import pandas as pd

KIT = os.environ.get("SHOPFAST_KIT", "../../../shopfast-kit/data/")
df = pd.read_csv(KIT + "/customers.csv", dtype=str)  # dtype=str pour garder les 0 des codes postaux
n = len(df)
today = pd.Timestamp(date.today())
print("Rows:", n)
print(df.head())

rules = []  # (dimension, regle, colonne, lignes en erreur)

# Completeness
print("\nEmpty values per column:\n", df.isna().sum())
rules.append(("Completeness", "email is filled", "email", df["email"].isna().sum()))
rules.append(("Completeness", "country is filled", "country", df["country"].isna().sum()))
rules.append(("Completeness", "phone is filled", "phone", df["phone"].isna().sum()))

# Uniqueness : customer_id
dup_id = df["customer_id"].duplicated(keep=False).sum()
print("\nDuplicated customer_id rows:", dup_id, "| exact duplicate rows:", df.duplicated().sum())
rules.append(("Uniqueness", "customer_id is unique", "customer_id", dup_id))

# TODO 1 : meme email apres strip + lower (on enleve d'abord les lignes copiees en double)
emails = df.drop_duplicates()["email"].str.strip().str.lower()
dup_email = emails[emails.notna() & emails.duplicated(keep=False)]
print("\nTODO 1 - rows sharing an email:", len(dup_email), "| people concerned:", dup_email.nunique())
rules.append(("Uniqueness", "one account per person (lower-cased email unique)", "email", len(dup_email)))

# TODO 2 : regex email
bad_email = df["email"].notna() & ~df["email"].str.match(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$", na=False)
print("\nTODO 2 - invalid emails:", bad_email.sum())
print(df.loc[bad_email, "email"].tolist())
rules.append(("Validity", "email looks like an email (regex)", "email", bad_email.sum()))

# TODO 3 : orthographes des pays
counts = df["country"].value_counts(dropna=False)
print("\nTODO 3 - country spellings:\n", counts)
print("distinct spellings:", len(counts), "for 4 countries")
bad_country = df["country"].notna() & ~df["country"].isin(["FR", "DE", "ES", "BE"])
rules.append(("Consistency", "country is an ISO-2 code in {FR, DE, ES, BE}", "country", bad_country.sum()))

# TODO 4 : dates pas au format YYYY-MM-DD
bad_signup = ~df["signup_date"].str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)
bad_birth = ~df["birth_date"].str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)
print("\nTODO 4 - signup_date not YYYY-MM-DD:", bad_signup.sum())
print(df.loc[bad_signup, "signup_date"].str.replace(r"\d", "9", regex=True).value_counts())
rules.append(("Consistency", "signup_date is YYYY-MM-DD", "signup_date", bad_signup.sum()))
rules.append(("Consistency", "birth_date is YYYY-MM-DD", "birth_date", bad_birth.sum()))

# TODO 5 : loyalty_tier
bad_tier = ~df["loyalty_tier"].isin(["bronze", "silver", "gold", "platinum"])
print("\nTODO 5 - bad loyalty_tier:", bad_tier.sum())
print(df.loc[bad_tier, "loyalty_tier"].map(repr).value_counts())
rules.append(("Validity", "loyalty_tier in {bronze, silver, gold, platinum}", "loyalty_tier", bad_tier.sum()))


# TODO 6 : dates de naissance impossibles
# on lit les 4 formats, sinon les dates pas en ISO ne sont pas controlees
def parse_dates(s):
    d = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    for fmt in ["%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d"]:
        d = d.fillna(pd.to_datetime(s, format=fmt, errors="coerce"))
    return d


birth = parse_dates(df["birth_date"])
future = birth > today
too_old = birth < pd.Timestamp("1906-01-01")
minor = (birth > today - pd.DateOffset(years=18)) & ~future
print("\nTODO 6 - future:", future.sum(), "| before 1906:", too_old.sum(), "| under 18:", minor.sum())
print(df.loc[future | too_old | minor, ["customer_id", "birth_date"]].to_string())
rules.append(("Accuracy", "birth_date between 1906-01-01 and today - 18 years", "birth_date", (future | too_old | minor).sum()))

signup = parse_dates(df["signup_date"])
rules.append(("Accuracy", "signup_date not in the future", "signup_date", (signup > today).sum()))

# TODO 7 : codes postaux FR sans 5 chiffres (il faut normaliser le pays avant, sinon on rate "France", "fra"...)
countries = {"fr": "FR", "fra": "FR", "france": "FR", "de": "DE", "deu": "DE", "germany": "DE", "allemagne": "DE",
             "es": "ES", "esp": "ES", "spain": "ES", "espagne": "ES", "be": "BE", "bel": "BE", "belgium": "BE", "belgique": "BE"}
is_fr = df["country"].str.strip().str.lower().map(countries) == "FR"
bad_cp = is_fr & ~df["postal_code"].str.match(r"^\d{5}$", na=False)
print("\nTODO 7 - FR postal codes without 5 digits:", bad_cp.sum(), "out of", is_fr.sum())
rules.append(("Validity", "French postal_code has 5 digits", "postal_code", bad_cp.sum()))

# Timeliness : regle sur le fichier entier (1 ligne)
last_signup = signup[signup <= today].max()
age = (today - last_signup).days
print(f"\nTimeliness - last signup: {last_signup.date()} ({age} days ago)")

# Bonus : score de chaque regle
card = pd.DataFrame(rules, columns=["dimension", "rule", "column", "failing_rows"])
card["total_rows"] = n
card.loc[len(card)] = ["Timeliness", "customers extract refreshed (last signup < 30 days old)", "signup_date", int(age >= 30), 1]
card["score_pct"] = (100 * (1 - card["failing_rows"] / card["total_rows"])).round(2)
print("\nScorecard (score_pct = 100 * (1 - failing / total))")
print(card.to_string(index=False))
print("\nDimensions covered:", card["dimension"].nunique(), "| rules:", len(card))
