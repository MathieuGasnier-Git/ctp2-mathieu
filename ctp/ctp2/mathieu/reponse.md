# Quelle garde de gouvernance manquait chez ShopFast ?

Il manquait un **contrat de données** sur `payments` (unité de `amount` = euros avec deux décimales), vérifié par un **test** sur la plage et la distribution des montants : sans lui, l'équipe paiement a pu passer aux centimes sans prévenir personne, et la suite naïve (non nul, unique, valeurs autorisées) a laissé passer un fichier valide en apparence mais 100 fois trop cher.
