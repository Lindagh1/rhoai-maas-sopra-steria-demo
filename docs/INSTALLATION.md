# Installer, rejouer et restaurer

## Contrat du kit

La plateforme MaaS est un prérequis. Le kit automatise **le scénario applicatif** sur RHOAI 3.5.x ; il ne se présente pas comme un installateur complet d'OpenShift AI. Sur une plateforme neuve, suivre les prérequis opérateurs, gateway/TLS, base MaaS et observabilité du [guide officiel 3.5](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/govern_llm_access_with_models-as-a-service/index), puis exécuter `./setup.sh check`.

Le compte préparateur crée un namespace, un groupe, quatre comptes de service de test et les ressources MaaS de démonstration. Le compte consommateur n'effectue aucune de ces opérations.

## Configuration portable

Adapter `config/demo.json` : namespaces modèle/tenant, AITenant existant, nom et namespace de gateway, identité humaine, groupe, modèle et quotas. Le setup vérifie la correspondance entre tenant, namespace et gateway avant d'appliquer. Les noms préfixés `sopra-` évitent les objets `demo-*` hérités. Sur une sandbox dont l’IdP est le Keycloak local, `python scripts/create_sandbox_user.py` crée le compte dédié sans rôle administrateur et conserve un compte déjà existant. Sur Entra ID ou un IdP partagé, créer le compte via le processus habituel ; ce script refuse d’y intervenir.

Le groupe créé par ce kit est dédié à la démonstration. Pour une vraie synchronisation Entra ID, intégrer les memberships au processus de gestion d'identités et adapter les manifestes ; ne pas laisser deux outils administrer le même groupe.

```bash
./setup.sh check                  # lecture seule
./setup.sh render                 # YAML local, sans accès cluster
./setup.sh apply                  # validation serveur puis application ordonnée
./setup.sh plan                   # dry-run serveur, après création des namespaces
./setup.sh status
./setup.sh verify-idempotence     # réapplique puis compare les états
```

`plan` nécessite que le namespace modèle existe : Kubernetes ne simule pas une transaction où un namespace créé en dry-run devient disponible pour les objets suivants. `apply` valide puis crée le namespace avant ses ressources. Une erreur arrête le traitement ; la correction puis la relance convergent sur les mêmes noms.

Les ressources sont gérées en server-side apply avec un field manager dédié, sans `--force-conflicts`. Une collision avec un objet non marqué comme appartenant au kit provoque un arrêt. Le kit ne résout pas silencieusement les conflits d'ownership. Exécuter depuis un seul poste/terminal à la fois.

## Ce que signifie idempotent

Une seconde préparation inchangée doit conserver UID, génération et contenu des ressources, ainsi que les pods du projet modèle. Le test enregistre ses deux instantanés dans `.state/idempotence.json`. Les valeurs de statut, horodatages et resourceVersion peuvent évoluer sous l'action des contrôleurs et ne sont pas des preuves de redéploiement.

L'installation ne crée ni ne renouvelle les clés personnelles. La recette API crée volontairement des clés de test puis les révoque. Une réponse générée, un compteur de tokens et une opération de rotation ne sont pas reproductibles bit à bit et ne font pas partie de la promesse d'idempotence.

Si le modèle ou un quota est modifié dans la configuration, la prochaine application remet les champs déclarés en conformité. Ne pas renommer les ressources dans la configuration pour simuler une mise à jour : l'ancien objet ne serait pas supprimé automatiquement.

## GPU : pause de Llama autorisée pour la recette

Sur la sandbox utilisée le 26 novembre, le seul GPU était pris par `my-first-model/llama-32-3b-instruct`. À la demande du propriétaire, son annotation `serving.kserve.io/stop` a été mise à `true`. Son état antérieur est conservé localement dans `.state/llama-before.json`, hors Git. Cette action est propre à cette sandbox ; le setup portable ne l'exécute jamais.

Pour rendre le GPU à Llama après la présentation, arrêter d'abord le nouveau modèle, puis réactiver Llama :

```bash
oc patch llminferenceservice sopra-qwen -n sopra-maas-models --type=merge -p '{"spec":{"replicas":0}}'
# Attendre la disparition du pod GPU sopra-qwen avant de poursuivre.
oc annotate inferenceservice llama-32-3b-instruct -n my-first-model serving.kserve.io/stop=false --overwrite
```

Pour rejouer le parcours MaaS ensuite, remettre Llama en pause de manière explicite et relancer `./setup.sh apply`. La configuration du nouveau modèle demande une réplique et un GPU. Vérifier les noms et l'état sauvegardé avant toute restauration sur un autre cluster.

## Certificats et secrets

Le kubeconfig de la session est privé dans `.state/`; clés et mots de passe sont dans `secrets/`. Les deux répertoires sont ignorés par Git. Les clients vérifient TLS ; utiliser `MAAS_CA_FILE=/chemin/ca.pem` pour une autorité privée. Ne pas publier un dump de Secret, un kubeconfig ou des sorties de notebooks contenant des accès.

## Complément prédictif

Utiliser Python 3.10–3.13 pour les dépendances du module ventes, puis :

```bash
pip install -r requirements-predictif.txt
python scripts/preflight.py ventes
python ventes/scripts/preparer.py --project sopra-ventes --deploy-model --example-runs
```

Ce module peut activer les composants workbenches/pipelines/kserve dans le DSC et crée stockage S3 de démo, workbench, pipeline et modèle ONNX. Le réserver à une sandbox. La démo MaaS n'en dépend pas. Les noms stables et empreintes des versions évitent les doublons de pipelines et d'exécutions d'exemple.
