# Complément prédictif — prévoir les ventes

[Accueil](../README.md) · [Provenance](../docs/REUTILISATION.md)

Ce module CPU reprend le parcours du magasin de glaces : 210 journées synthétiques, apprentissage, pipeline à quatre étapes, export ONNX et inférence OpenVINO. Les modèles prédictifs V2 sont distincts du LLM publié dans MaaS.

## Préparation optionnelle

Dans un environnement Python 3.10 à 3.13, depuis la racine du dépôt, connecté à une sandbox :

```bash
pip install -r requirements-predictif.txt
python scripts/preflight.py ventes
python ventes/scripts/preparer.py --project sopra-ventes --deploy-model --example-runs
```

Cette préparation crée stockage S3 de démonstration, workbench, serveur de pipelines, pipeline et modèle. Elle peut activer les composants correspondants du DSC. Elle ne fait pas partie du setup MaaS et n’a pas été rejouée sur le cluster dans cette recette.

## Présenter — 15 à 20 minutes supplémentaires

1. Ouvrir le projet, la connexion S3 et le workbench préparés.
2. Exécuter `01_prevoir_les_ventes.ipynb` : entraînement, évaluation sur la fin chronologique de l’historique, comparaison à la moyenne.
3. Dans Pipelines, montrer les étapes et les deux exemples avec/sans promotion.
4. Ouvrir `03_utiliser_le_modele.ipynb` : appel réel au modèle ONNX et formulaire.

Les fichiers de l’atelier sont copiés dans `demo-ventes`. Les liens propres à l’installation sont écrits dans `.state/sopra-ventes/liens.json`. Une source inchangée ne remplace pas le travail utilisateur ; les versions modifiées sont sauvegardées avant mise à jour. Les versions de pipeline et les exemples utilisent une empreinte pour éviter les doublons.

Les nombres et conclusions de la démo décrivent un jeu synthétique ; ils ne prouvent pas une performance métier réelle. Les résultats de l’ancienne répétition et le détail pédagogique sont dans le [projet d’origine](https://github.com/Lindagh1/rhoai-3.5-demos/tree/b54c809/ventes).

Les tests locaux repris vérifient la conservation des secrets, des champs injectés et des exécutions existantes. Ils ne remplacent pas une recette de déploiement sur une nouvelle sandbox.
