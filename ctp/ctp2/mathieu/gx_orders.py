"""CTP 2 - Exercice 3 : suite d'expectations pour les commandes ShopFast (GX Core 1.x), 12 expectations.
Lancement :  python gx_orders.py
Data Docs :  gx/uncommitted/data_docs/local_site/index.html
"""
import os
from pathlib import Path

import great_expectations as gx
import pandas as pd

HERE = Path(__file__).resolve().parent


def kit_file(name):
    candidates = [os.environ.get("SHOPFAST_KIT", ""), HERE / "../shopfast-kit/data",
                  HERE / "../../shopfast-kit/data", HERE / "../../../shopfast-kit/data"]
    for d in candidates:
        if d and (Path(d) / name).exists():
            return Path(d) / name
    raise FileNotFoundError(f"{name} introuvable, definir SHOPFAST_KIT=chemin/vers/shopfast-kit/data")


orders = pd.read_csv(kit_file("orders.csv"), dtype=str)
customers = pd.read_csv(kit_file("customers.csv"), dtype=str)
orders["total_amount_eur"] = pd.to_numeric(orders["total_amount_eur"], errors="coerce")
orders["order_date_dt"] = pd.to_datetime(orders["order_date"], format="%Y-%m-%d", errors="coerce")  # copie typee pour les plages

# valeurs observees avant de choisir les listes autorisees
for col in ["status", "channel", "shipping_country"]:
    print(orders[col].map(repr).value_counts(dropna=False).to_string(), "\n")

# date de reference fixe (jour de l'extraction) plutot que date.today() : sinon le resultat de la regle
# "pas dans le futur" change selon le jour ou on relance le script, et le scorecard ne serait plus reproductible
REF_DATE = pd.Timestamp("2026-11-25")

context = gx.get_context(mode="file", project_root_dir=HERE)   # cree ./gx/ (config + Data Docs) a cote du script
source = context.data_sources.add_or_update_pandas("shopfast")
asset = source.add_dataframe_asset(name="orders")
batch_def = asset.add_batch_definition_whole_dataframe("all_orders")

suite = context.suites.add_or_update(gx.ExpectationSuite(name="orders_suite"))
E = gx.expectations
for e in [
    # volume attendu d'un export complet : moins de 1000 lignes = export tronque
    E.ExpectTableRowCountToBeBetween(min_value=1000, max_value=100000),
    E.ExpectColumnValuesToNotBeNull(column="order_id"),
    # une commande en double = chiffre d'affaires compte deux fois
    E.ExpectColumnValuesToBeUnique(column="order_id"),

    # TODO 1 : une commande sans client ne peut etre ni facturee ni livree
    E.ExpectColumnValuesToNotBeNull(column="customer_id"),
    # TODO 2 : cle etrangere, le client doit exister dans customers (sinon commande orpheline)
    E.ExpectColumnValuesToBeInSet(column="customer_id", value_set=sorted(set(customers["customer_id"].dropna()))),
    # TODO 3 : la date sert a rattacher le CA au bon mois, elle est obligatoire...
    E.ExpectColumnValuesToNotBeNull(column="order_date"),
    # ... et au format ISO YYYY-MM-DD pour que tous les outils la lisent pareil
    E.ExpectColumnValuesToMatchRegex(column="order_date", regex=r"^\d{4}-\d{2}-\d{2}$"),
    # TODO 4 : une commande ne peut pas avoir lieu dans le futur (bug d'horloge ou saisie)
    # borne basse 2020 : ShopFast n'a pas de commandes plus anciennes, une date avant = erreur de saisie
    E.ExpectColumnValuesToBeBetween(column="order_date_dt", min_value=pd.Timestamp("2020-01-01"), max_value=REF_DATE),
    # TODO 5 : cycle de vie d'une commande, en minuscules ; "SHIPPED" ou "canceled" casseraient les filtres des rapports
    E.ExpectColumnValuesToBeInSet(column="status", value_set=["pending", "shipped", "delivered", "cancelled", "returned"]),
    # TODO 6 : les 3 canaux de vente existants (value_counts : web, mobile_app, marketplace)
    E.ExpectColumnValuesToBeInSet(column="channel", value_set=["web", "mobile_app", "marketplace"]),
    # ShopFast ne livre que FR, BE, DE, ES (codes ISO-2) : autre pays = pas de transporteur ni de TVA prevue
    E.ExpectColumnValuesToBeInSet(column="shipping_country", value_set=["FR", "BE", "DE", "ES"]),
    # TODO 7 : montant strictement positif (un remboursement n'est pas une commande) et plafond a 5000 EUR :
    # le max observe est ~1400 EUR, 5000 laisse de la marge mais attrape un montant x100 (centimes)
    E.ExpectColumnValuesToBeBetween(column="total_amount_eur", min_value=0, max_value=5000, strict_min=True),
]:
    suite.add_expectation(e)
suite.save()

vd = context.validation_definitions.add_or_update(gx.ValidationDefinition(name="orders_validation", data=batch_def, suite=suite))
checkpoint = context.checkpoints.add_or_update(gx.Checkpoint(name="orders_checkpoint", validation_definitions=[vd],
                                                             actions=[gx.checkpoint.UpdateDataDocsAction(name="docs")]))
result = checkpoint.run(batch_parameters={"dataframe": orders})

print("\nExpectations in suite:", len(suite.expectations))
print("Suite passed:", result.success)
for vr in result.run_results.values():
    for r in vr.results:
        cfg = r.expectation_config
        print(f"{'PASS' if r.success else 'FAIL'}  {cfg.type:<45} {cfg.kwargs.get('column', ''):<18} unexpected={r.result.get('unexpected_count', '-')}")
print("\nOpen the report: gx/uncommitted/data_docs/local_site/index.html")
