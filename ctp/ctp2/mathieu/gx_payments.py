# CTP 2 - Exercice 4 : l'incident des centimes
# la suite naive passe sur payments_batch_2.csv alors que les montants sont en centimes
# lancer depuis ctp/ctp2/mathieu :  python gx_payments.py
import os

import great_expectations as gx
import pandas as pd

KIT = os.environ.get("SHOPFAST_KIT", "../../../shopfast-kit/data/")
files = {"payments (history)": KIT + "/payments.csv", "payments_batch_2 (new)": "payments_batch_2.csv"}

context = gx.get_context(mode="file")
source = context.data_sources.add_or_update_pandas("shopfast_payments")
asset = source.add_dataframe_asset(name="payments")
batch_def = asset.add_batch_definition_whole_dataframe("whole")
E = gx.expectations

naive = [E.ExpectColumnValuesToNotBeNull(column="payment_id"), E.ExpectColumnValuesToBeUnique(column="payment_id"),
         E.ExpectColumnValuesToNotBeNull(column="amount"), E.ExpectColumnValuesToBeInSet(column="currency", value_set=["EUR"]),
         E.ExpectColumnValuesToBeInSet(column="method", value_set=["card", "paypal", "apple_pay", "bank_transfer"])]
smart = naive + [
    # historique entre 13,70 et 1400 EUR, un paiement ne depasse pas le plafond des commandes (5000)
    E.ExpectColumnValuesToBeBetween(column="amount", min_value=0, max_value=5000, strict_min=True),
    # mediane ~184 EUR dans l'historique, 50-500 laisse de la marge mais pas pour un x100
    E.ExpectColumnMedianToBeBetween(column="amount", min_value=50, max_value=500),
    # moyenne ~236 EUR, meme idee
    E.ExpectColumnMeanToBeBetween(column="amount", min_value=50, max_value=500),
    # un montant en euros a des decimales (217.38), on tolere quelques montants ronds
    E.ExpectColumnValuesToMatchRegex(column="amount_txt", regex=r"^\d+\.\d{1,2}$", mostly=0.9),
]


def run(name, expectations, df):
    suite = context.suites.add_or_update(gx.ExpectationSuite(name=name))
    for e in expectations: suite.add_expectation(e.copy() if hasattr(e, "copy") else e)
    suite.save()
    return batch_def.get_batch(batch_parameters={"dataframe": df}).validate(suite)


for label, path in files.items():
    df = pd.read_csv(path, dtype=str); df["amount_txt"] = df["amount"]; df["amount"] = pd.to_numeric(df["amount"])
    for suite_name, exps in [("naive_payments", naive), ("smart_payments", smart)]:
        res = run(suite_name, exps, df)
        failed = [r.expectation_config.type for r in res.results if not r.success]
        print(f"{label:<24} {suite_name:<15} success={res.success}  failed={failed}")
