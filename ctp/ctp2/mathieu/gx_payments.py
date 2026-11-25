"""CTP 2 - Exercice 4 : rejouer l'incident des centimes.
La suite naive (not null / unique / valeurs autorisees) PASSE sur payments_batch_2.csv alors que chaque montant
est 100x trop grand (centimes au lieu d'euros). Seules des regles sur les valeurs et la distribution l'attrapent.
Lancement :  python gx_payments.py
"""
import os
from pathlib import Path

import great_expectations as gx
import pandas as pd

HERE = Path(__file__).resolve().parent


def find_file(name, folders):
    for d in [os.environ.get("SHOPFAST_KIT", "")] + folders:
        if d and (Path(d) / name).exists():
            return Path(d) / name
    raise FileNotFoundError(f"{name} introuvable")


KIT_DIRS = [HERE / "../shopfast-kit/data", HERE / "../../shopfast-kit/data", HERE / "../../../shopfast-kit/data"]
BATCH_DIRS = [HERE, HERE / "../02_CTP2", HERE / "../../../02_CTP2", HERE / "../../.."]
files = {"payments (history)": find_file("payments.csv", KIT_DIRS),
         "payments_batch_2 (new)": find_file("payments_batch_2.csv", BATCH_DIRS)}

context = gx.get_context(mode="file", project_root_dir=HERE)
source = context.data_sources.add_or_update_pandas("shopfast_payments")
asset = source.add_dataframe_asset(name="payments")
batch_def = asset.add_batch_definition_whole_dataframe("whole")
E = gx.expectations

naive = [E.ExpectColumnValuesToNotBeNull(column="payment_id"), E.ExpectColumnValuesToBeUnique(column="payment_id"),
         E.ExpectColumnValuesToNotBeNull(column="amount"), E.ExpectColumnValuesToBeInSet(column="currency", value_set=["EUR"]),
         E.ExpectColumnValuesToBeInSet(column="method", value_set=["card", "paypal", "apple_pay", "bank_transfer"])]
smart = naive + [
    # 1. plage par paiement : historique entre 13,70 et 1400,79 EUR, aucun panier ShopFast ne depasse 5000 EUR
    #    (meme plafond que total_amount_eur dans gx_orders.py, un paiement ne peut pas depasser la commande)
    E.ExpectColumnValuesToBeBetween(column="amount", min_value=0, max_value=5000, strict_min=True),
    # 2. mediane : ~184 EUR sur l'historique ; entre 50 et 500 on tolere une saison forte ou un nouveau produit,
    #    mais un x100 (18 488) sort tout de suite. La mediane resiste mieux qu'une moyenne a quelques gros paniers
    E.ExpectColumnMedianToBeBetween(column="amount", min_value=50, max_value=500),
    # 3. moyenne : ~236 EUR sur l'historique, meme logique que la mediane, alerte si le panier moyen bouge trop
    E.ExpectColumnMeanToBeBetween(column="amount", min_value=50, max_value=500),
    # 4. format texte : un montant en euros s'ecrit avec des centimes apres le point (217.38, 54.5).
    #    mostly=0.9 : on accepte quelques montants ronds ("50"), pas un fichier entier d'entiers
    E.ExpectColumnValuesToMatchRegex(column="amount_txt", regex=r"^\d+\.\d{1,2}$", mostly=0.9),
]


def run(name, expectations, df):
    suite = context.suites.add_or_update(gx.ExpectationSuite(name=name))
    for e in expectations:
        suite.add_expectation(e.copy() if hasattr(e, "copy") else e)
    suite.save()
    return batch_def.get_batch(batch_parameters={"dataframe": df}).validate(suite)


results = {}
for label, path in files.items():
    print(f"{label}: {path.resolve()}")
    df = pd.read_csv(path, dtype=str)
    df["amount_txt"] = df["amount"]
    df["amount"] = pd.to_numeric(df["amount"])
    print(f"\n{label}: {len(df)} rows, amount min={df['amount'].min()} median={df['amount'].median()} max={df['amount'].max()}")
    for suite_name, exps in [("naive_payments", naive), ("smart_payments", smart)]:
        res = run(suite_name, exps, df)
        failed = [r.expectation_config.type for r in res.results if not r.success]
        results[(label, suite_name)] = res.success
        print(f"{label:<24} {suite_name:<15} success={res.success}  failed={failed}")

# attendu : la naive passe partout, la smart passe sur l'historique et echoue sur le batch 2
ok = (results[("payments (history)", "smart_payments")] and not results[("payments_batch_2 (new)", "smart_payments")]
      and results[("payments_batch_2 (new)", "naive_payments")])
print("\nIncident caught by the smart suite (history passes, batch 2 fails):", ok)
