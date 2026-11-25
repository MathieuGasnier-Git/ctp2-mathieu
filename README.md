# CTP 2 - Data Quality : Measure, Clean, Test

Data Governance - EFREI - Mathieu Gasnier

Tous les livrables sont dans `ctp/ctp2/mathieu/`.

| Exercice | Fichier | Contenu |
|---|---|---|
| 1. Profiling | `profile_customers.py` | TODO 1 à 7 sur `customers.csv` (pandas) |
| 1. Scorecard | `quality_scorecard.csv` | 21 règles, 6 dimensions, sévérité et responsable |
| 2. Nettoyage | `openrefine_customers_recipe.json` | recette OpenRefine (Undo/Redo > Apply) |
| 2. Nettoyage | `clean_customers.py` | mêmes étapes en pandas |
| 2. Nettoyage | `customers_clean.csv` | résultat : 1233 lignes, colonne `is_duplicate_email` |
| 3. Great Expectations | `gx_orders.py` | suite de 12 expectations sur `orders.csv` + Data Docs |
| 4. Incident des centimes | `gx_payments.py` | suite naïve vs suite smart (historique OK, batch 2 KO) |
| 5. Gouvernance | `reponse.md` | la garde qui manquait chez ShopFast |

## Lancer les scripts

Environnement du kit ShopFast (Python 3.12, pandas 2.3.3, great-expectations 1.25.0).
Les scripts cherchent `shopfast-kit/data/` à côté du dépôt ; sinon définir `SHOPFAST_KIT=chemin/vers/shopfast-kit/data`.
`gx_payments.py` a aussi besoin de `payments_batch_2.csv` (fourni avec l'énoncé).

```
cd ctp/ctp2/mathieu
python profile_customers.py
python clean_customers.py
python gx_orders.py      # Data Docs : gx/uncommitted/data_docs/local_site/index.html
python gx_payments.py
```
