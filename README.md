# CTP 2 - Data Quality

Rendu du CTP 2 de Data Governance (Mathieu Gasnier), tout est dans `ctp/ctp2/mathieu/`.

- `profile_customers.py` : profiling de customers.csv (exercice 1)
- `quality_scorecard.csv` : scorecard qualité
- `openrefine_customers_recipe.json` : recette OpenRefine (exercice 2)
- `clean_customers.py` et `customers_clean.csv` : le même nettoyage en Python et le résultat
- `gx_orders.py` : 12 expectations sur orders.csv (exercice 3)
- `data_docs.png`, `data_docs_failed.png` : captures des Data Docs
- `gx_payments.py` et `payments_batch_2.csv` : incident des centimes (exercice 4)
- `reponse.md` : la garde de gouvernance qui manquait

## Lancer

Depuis `ctp/ctp2/mathieu`, avec le venv du kit ShopFast (le kit doit être dans `shopfast-kit/data/` à la racine, sinon définir `SHOPFAST_KIT`) :

```
python profile_customers.py
python clean_customers.py
python gx_orders.py
python gx_payments.py
```
