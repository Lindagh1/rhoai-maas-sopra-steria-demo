# Ce que nous avons récupéré

Inventaire du 26 novembre 2026. Aucun secret, historique d'authentification ou journal brut n'est repris dans Git.

## rhoai-3.5-demos — base principale

Source locale au commit `b54c809`, dépôt [rhoai-3.5-demos](https://github.com/Lindagh1/rhoai-3.5-demos).

- Reprise du module `ventes/` : données synthétiques, notebooks, pipeline, modèle ONNX, préparation et réconciliation.
- Reprise des tests de non-duplication des pipelines et de conservation des champs injectés par les webhooks.
- Adaptation du manifeste GPU `LLMInferenceService` et du principe de publication/policy/quota.
- Adaptation du lecteur des compteurs Limitador à la route du nouveau modèle.
- Conservation des leçons d'idempotence : noms stables, clés personnelles séparées, pas de nettoyage automatique.

Les guides anciens et captures de la simulation ne sont pas présentés comme preuves d'inférence réelle. Les sorties des notebooks sont nettoyées avant publication.

## rhoai-maas-demo — antécédent MaaS

Source locale au commit `2115124`, dépôt [rhoai-maas-demo](https://github.com/Lindagh1/rhoai-maas-demo). Le clone historique dans `Projects/` était plus ancien (`0348346`). Le kit contenait déjà publication native, parcours administrateur/consommateur, quotas et observabilité.

Éléments non repris tels quels : bootstrap global de la plateforme, hypothèses de namespaces/nom de sandbox, création automatique d'identités, droits admin de projet et lecture cluster-wide des services accordés au consommateur. Ils ne constituent pas un bon contrat portable pour le cas Sopra Steria.

## rhoai-maas-corporate-scenario — référence complémentaire

Le [dépôt privé Corporate Scenario](https://github.com/Lindagh1/rhoai-maas-corporate-scenario) a été identifié et son README inspecté. Il fige le guide AI Services BU au commit `ca26a4561673c05a19cd1be5e2eb7663cdb8b17d` et documente un scénario à plusieurs divisions. Le contenu complet et ses résultats n'ont pas été réaudités ici. Il reste une piste de réutilisation pour une session multi-équipes, pas une preuve du nouveau scénario.

## Nouveau travail

- Configuration explicite du modèle, du tenant, de la gateway, du groupe et des quotas.
- Ressources isolées des anciennes démos, détection de collisions, validation serveur et test de relance.
- Recette API avec comptes limités distincts pour cas positif, absence d'accès et absence de quota.
- Parcours humain, comparaison sourcée et registre des limites de version/support.

Les liens des sources amont restent datés : une réussite sur une ancienne sandbox ne vaut pas validation sur `dps-demo`.
