# Consommation, erreurs et questions de version

## Trois preuves différentes

1. **Réponse d'inférence** : `usage` prouve le comptage retourné pour cet appel. Elle ne prouve ni un quota restant agrégé ni une facturation.
2. **Gateway / Limitador** : relever appels acceptés/refusés, limites réellement générées et compteur lié à la route du modèle. Comparer les heures et la fenêtre de quota.
3. **Dashboard administrateur** : observer la consommation et les filtres effectivement disponibles. Consigner séparément ce qu'un utilisateur non-admin peut consulter.

Commandes de diagnostic en lecture seule, à adapter aux namespaces réellement découverts :

```bash
oc get maastenantconfig default-tenant -n models-as-a-service -o yaml
oc get maasmodelref sopra-qwen -n sopra-maas-models -o yaml
oc get authpolicy,tokenratelimitpolicy -A
oc get limitador -A
oc get pods -n kuadrant-system
oc logs -n redhat-ai-gateway-infra deployment/maas-api --since=10m
oc logs -n redhat-ods-applications deployment/maas-controller --since=10m
oc get servicemonitors,podmonitors -A
```

Pour un diagnostic ponctuel, ouvrir un port-forward authentifié vers le service Limitador découvert, lire `/metrics`, puis refermer le tunnel. Ne pas exposer ce port publiquement. Le script `scripts/usage.py` filtre les séries sur la route de ce modèle ; des séries absentes ne valent pas zéro consommation. Les logs bruts restent locaux et sont à relire avant partage.

Le libellé exact des compteurs dépend du composant. Examiner les lignes HELP et labels réels ; ne pas mélanger requêtes, tokens et montants. Les métriques Prometheus sont échantillonnées ; prévoir une réconciliation spécifique pour tout chargeback.

## Cas « aucune subscription »

Relever l'étape précise : catalogue, liste des souscriptions, création de clé ou inférence. Une absence de quota actif peut empêcher la création de la clé avant même l'appel. Le script de recette enregistre ces étapes au lieu de présumer systématiquement 403 ou 429.

Procédure interne proposée : « Votre compte n'a pas de souscription MaaS utilisable pour ce modèle. Contactez l'équipe plateforme avec votre groupe et le modèle souhaité. L'administrateur doit vérifier ensemble l'autorisation et la souscription. » Cette phrase est une aide à documenter ; elle n'est pas injectée dans l'UI RHOAI.

## Mémoire, hostname et versions

Les cases **04541689** et **04541847** sont mentionnées par le client ; leur contenu privé n'a pas été consulté ici. Ne pas annoncer leur clôture ni attribuer un fix sans confirmation du support.

Pour le sizing mémoire, relever le composant précis, ses requests/limits, les événements `OOMKilled`, la charge et les versions d'images. Un ajustement ponctuel d'un Deployment géré par opérateur peut être annulé par la réconciliation ; demander le champ de configuration supporté. Aucune valeur mémoire universelle n'est promise.

Pour une gateway sans LB externe, distinguer `status.addresses`, hostname des listeners, route d'exposition, résolution DNS, certificat et URL découverte par MaaS/UI. Le nom du cluster ne suffit pas à reconstruire l'URL. La recette présente utilise une gateway disposant d'une adresse LB ; elle **ne reproduit pas** le cas client sans LB.

Les notes 3.5 consultées décrivent **3.5.1 comme une mise à jour déjà publiée en septembre 2026**. La demande de « roadmap 3.5.1 » doit donc être reformulée en vérification de correctifs et de trajectoire vers une version supportée. Le correctif de découverte de hostname `RHOAIENG-65143` est mentionné dans les problèmes résolus 3.5 GA ; cela ne prouve pas qu'il correspond au problème rencontré dans les deux cases. [Notes officielles des problèmes résolus](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/release_notes/resolved-issues_relnotes).

Le [guide AI Services BU de dépannage après upgrade](https://rh-aiservices-bu.github.io/rhoai-maas-guide/modules/main/12-platform-upgrade.html) apporte des pistes complémentaires, mais ne remplace ni la documentation produit ni une validation du support. Les prescriptions de hostname peuvent varier avec le pattern de gateway : conserver la configuration réellement validée pour le build cible.

## À faire confirmer par Red Hat

- Versions fixes exactes des deux cases et éventuels backports en 3.5.z.
- Périmètre GA/TP et support du chemin externe, du multitenant et de l'observabilité retenus.
- YAML de référence adaptés aux CRDs installées sur `dps-demo`, y compris namespaces et gateway.
- UX sans souscription et possibilité réelle de consommation/quota restant pour le non-admin.
- Compatibilité des versions OCP, RHOAI, RHCL et stockage/DB ; inclusions de l'abonnement.

Ces éléments sont des questions à résoudre, pas une roadmap engagée.
