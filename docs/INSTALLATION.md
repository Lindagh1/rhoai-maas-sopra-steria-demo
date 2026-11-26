# Installer, rejouer et restaurer

[Accueil](../README.md) · [Comprendre la démo](COMPRENDRE-ET-PRESENTER.md)

## Choisir son point de départ

**Cas A — RHOAI et MaaS fonctionnent déjà.** C'est le cas de notre sandbox et, sous réserve d'audit, celui de `dps-demo`. Vérifier les prérequis ci-dessous, puis suivre les étapes « Installer le scénario ». Ne pas réinstaller les opérateurs ni remplacer la gateway existante.

**Cas B — OpenShift est disponible mais MaaS n'est pas prêt.** L'administrateur doit d'abord préparer la plateforme selon la section dédiée. Le script de ce dépôt ne réalise pas cette partie. Un cluster OpenShift vide n'est donc pas encore une cible « une commande et tout fonctionne ».

**Cas C — aucun cluster n'est disponible.** Faire provisionner une sandbox OpenShift AI et son GPU avant de commencer. Le kit ne crée pas les machines ou le cluster cloud.

## Prérequis à transmettre à l'équipe client

### Plateforme à fournir

- OpenShift dans une version supportée pour RHOAI 3.5 ; le guide MaaS indique 4.19.9 ou ultérieur. Notre référence testée est OCP 4.20.46 / RHOAI 3.5.4, pas une certification de toutes les combinaisons plus récentes.
- RHOAI 3.5.x avec KServe / inférence native `LLMInferenceService`, AI Gateway et MaaS actifs.
- Red Hat Connectivity Link 1.4.x et Kuadrant prêts, avec leurs services Authorino et Limitador opérationnels.
- Une gateway MaaS accessible en HTTPS, un DNS résolu depuis le poste de démonstration et des certificats reconnus.
- PostgreSQL 14 ou ultérieur, joignable depuis MaaS, et secret de connexion configuré. Cette base doit être fournie et exploitée ; RHOAI ne la provisionne pas pour le client.
- User Workload Monitoring actif ; ajouter/configurer les composants d'observabilité requis pour les vues de consommation choisies.

Référence produit : [prérequis, gateway, base et activation MaaS — sections 1.2 à 1.9](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/pdf/govern_llm_access_with_models-as-a-service/Red_Hat_OpenShift_AI_Self-Managed-3.5-Govern_LLM_access_with_Models-as-a-Service-en-US.pdf). Les versions et statuts de support se vérifient avant une installation client.

### Capacité propre à notre scénario

Le manifeste Qwen demande **1 GPU NVIDIA**, **1 CPU et 4 GiB de mémoire système réservés**, avec des limites de **4 CPU et 8 GiB**. La mémoire système n'est pas la mémoire du GPU. La recette a utilisé une **NVIDIA L4**, dont le nœud annonce 23 034 MiB de mémoire GPU. Cette carte est une référence testée, pas un minimum matériel démontré.

Le GPU doit être libre et ses pilotes / composants de gestion doivent permettre à Kubernetes d'allouer `nvidia.com/gpu`. Vérifier aussi la place disque pour les images et les poids. Ces ressources sont celles du modèle uniquement : elles ne dimensionnent pas l'ensemble OpenShift + RHOAI + MaaS + PostgreSQL + monitoring. Nous n'avons pas établi de sizing minimal global.

Si le GPU est déjà occupé, réserver une capacité ou planifier une pause avec le propriétaire du workload. Le setup ne libère jamais un GPU en arrêtant automatiquement un autre modèle.

### Accès, identité et réseau

- Un administrateur prépare la plateforme et lance le setup. Le kit actuel crée aussi un Namespace et un Group, qui ne sont pas de simples droits utilisateur de projet.
- Une identité **non-administrateur** pour la présentation, plus idéalement une identité témoin sans souscription. Avec Entra ID, utiliser l'intégration OpenShift OAuth déjà gérée par le client et vérifier les noms réellement transmis.
- Un groupe dédié au kit, distinct d'un groupe synchronisé par un autre outil. Le script refuse d'adopter un groupe existant qu'il ne gère pas.
- Accès depuis le poste à l'API OpenShift, au dashboard et à la gateway ; accès depuis le cluster aux registres d'images et aux poids Hugging Face. Les domaines de téléchargement/redirection doivent être compatibles avec la politique réseau. En environnement déconnecté, préparer des miroirs et adapter les URI/images : le kit ne le fait pas automatiquement.
- Stockage persistant pour PostgreSQL si hébergé dans le cluster ; backend externe géré possible. Le module prédictif ajoute ses propres besoins de volumes et n'est pas requis pour MaaS.
- Sur le poste : Git, `oc`, Python avec `venv` et `pip`. Python 3.12 permet d'utiliser aussi le module prédictif. Navigateur récent pour la session humaine ; `curl` pour les exemples curl.
- Accès au dépôt GitHub **privé**, ou copie fournie par son propriétaire. Le dépôt ne devient pas accessible au client simplement parce qu'on lui communique son URL.

### Informations à renseigner avant de commencer

Préparer : version OCP/RHOAI, adresse API du cluster, URL dashboard, nom/namespace de gateway, URL HTTPS publique de MaaS, nom de l'AITenant et son namespace de gouvernance, disponibilité GPU, nom exact du compte utilisateur et groupe dédié. Ne pas placer les mots de passe ou jetons dans `config/demo.json`.

## Préparer la plateforme si MaaS est absent

Cette phase est réalisée par l'administrateur plateforme avec la documentation de sa version. C'est un processus expliqué, **pas un automatisme fourni par ce dépôt**.

1. **Installer et vérifier OpenShift AI.** Confirmer les souscriptions opérateurs et l'état de la plateforme. Activer KServe et les dépendances d'inférence native, puis vérifier la disponibilité de la CRD `llminferenceservices.serving.kserve.io` et du GPU.
2. **Installer la couche d'accès.** Installer RHCL, préparer Kuadrant et attendre ses composants. La gateway doit pouvoir appeler les services d'authentification et de limitation.
3. **Préparer l'entrée réseau.** Choisir une implémentation Gateway API prise en charge, configurer gateway, exposition, DNS et TLS. Une adresse LoadBalancer n'est qu'un pattern possible ; le cas sans LB demande une configuration d'exposition et de découverte validée pour ce cluster.
4. **Préparer l'état persistant et les métriques.** Provisionner PostgreSQL, sa base et son accès MaaS ; configurer le secret dans le namespace d'infrastructure attendu. Activer User Workload Monitoring. Suivre l'ordre de bootstrap prévu pour le build installé quand les namespaces sont créés par les opérateurs.
5. **Activer MaaS dans le DSC.** Les champs 3.5 à vérifier sont `spec.components.aigateway.managementState: Managed` et `spec.components.aigateway.modelsAsAService.managementState: Managed`. Modifier la ressource existante selon la procédure produit, sans la remplacer par un DSC minimal qui effacerait d'autres composants.
6. **Rendre les écrans disponibles.** Vérifier `modelAsService` et les prérequis Gen AI studio/OGX du build. Déclarer une fonctionnalité côté contrôleur ne garantit pas que son écran est activé. [Instructions d'installation amont](https://github.com/opendatahub-io/models-as-a-service/blob/main/docs/content/install/maas-setup.md), à confronter à la documentation RHOAI 3.5.
7. **Vérifier le tenant et le routage.** Attendre le tenant par défaut actif, sa configuration prête, les services MaaS disponibles et la gateway programmée. Configurer la collecte et les dashboards nécessaires à la séquence d'observabilité.

Contrôles d'inventaire en lecture seule :

```bash
oc get clusterversion version
oc get csv -n redhat-ods-operator
oc get datasciencecluster
oc get crd llminferenceservices.serving.kserve.io
oc get kuadrant -n kuadrant-system
oc get aitenants -n ai-tenants
oc get maastenantconfigs -A
oc get gateways -A
oc get pods -n redhat-ai-gateway-infra
```

Les noms/namespace d'infrastructure peuvent varier : les découvrir avant de reprendre une commande. Un `Ready` ou `Active` dans cet inventaire est une étape ; l'appel réel de la recette vérifiera le chemin complet.

## Installer le scénario sur une autre sandbox

### 1. Récupérer une copie propre

```bash
git clone https://github.com/Lindagh1/rhoai-maas-sopra-steria-demo.git
cd rhoai-maas-sopra-steria-demo
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Utiliser un clone par sandbox. Ne pas recopier `.state/`, `secrets/` ou le kubeconfig de notre ancienne sandbox. Si `git clone` est refusé, vérifier l'accès au dépôt privé avant de chercher un problème OpenShift.

### 2. Se connecter au bon cluster

Effectuer `oc login` avec la méthode prévue par le client. Vérifier immédiatement :

```bash
oc whoami
oc whoami --show-server
```

Le premier indique le compte préparateur ; le second doit désigner la sandbox cible. Le script utilise cette session existante : il ne choisit pas un autre cluster ni une autre identité à votre place.

### 3. Adapter la configuration

Ouvrir `config/demo.json` et renseigner :

- `model_namespace` : nouveau projet dédié au modèle, par défaut `sopra-maas-models`.
- `model_name` : nom du déploiement et de sa publication, par défaut `sopra-qwen` ; le conserver pour suivre le conducteur sans adaptation.
- `tenant_namespace` et `aitenant` : gouvernance existante, par défaut `models-as-a-service`.
- `gateway_name` et `gateway_namespace` : gateway MaaS réellement associée à ce tenant.
- `user` : nom exact du compte humain transmis par OpenShift OAuth.
- `group` : nouveau groupe réservé à cette démo.
- `model_uri` et `served_model` : conserver Qwen pour reproduire notre recette ; choisir un autre modèle implique de revoir les ressources du manifeste.
- `token_limit`, `low_token_limit`, `window` : quota principal et petit quota de test.

Commencer avec le tenant par défaut : c'est le chemin validé. La présence de paramètres de tenant ne constitue pas une recette multitenant validée.

### 4. Vérifier et voir ce qui sera créé

```bash
./setup.sh check
./setup.sh render
```

`check` lit la version RHOAI, les CRDs essentielles et la cohérence tenant/gateway. Il **ne vérifie pas exhaustivement** la capacité GPU, le DNS/TLS, les téléchargements, l'IdP, PostgreSQL ni les écrans. Utiliser la liste de prérequis ci-dessus.

`render` écrit `.state/rendered.yaml`. Relire ce fichier : il montre les objets à créer. Le faire examiner par l'équipe plateforme de Sopra Steria avant leur déploiement sur son environnement.

### 5. Déployer et vérifier la relance

```bash
./setup.sh apply
./setup.sh status
./setup.sh verify-idempotence
```

`apply` crée le projet, le groupe, les comptes de test, le serveur Qwen, sa publication MaaS, les règles d'accès, les souscriptions et la lecture du projet pour le groupe. Chaque objet est validé par le serveur avant application. Le script attend jusqu'à 15 minutes pour le modèle ; la durée réelle dépend du téléchargement, du stockage et du GPU.

Résultat attendu : modèle `Ready`, publication `Ready`, gouvernance `Active`, pod prêt. `verify-idempotence` réapplique et vérifie que les ressources et pods n'ont pas été recréés. Les clés personnelles ne sont pas générées pendant l'installation.

### 6. Préparer l'utilisateur humain

Faire créer ou fournir le compte non-admin par l'équipe identité, avec le nom configuré. Le groupe dédié du kit référence ce nom dans OpenShift. Tester une vraie connexion OAuth et contrôler l'absence de droits d'administration. Sur notre sandbox seulement, le script optionnel Keycloak décrit plus bas peut créer le compte.

### 7. Vérifier un appel puis répéter l'écran

Renseigner l'URL HTTPS **réelle de la nouvelle gateway**, sans chemin `/v1` :

```bash
python scripts/validate_live.py --url https://VOTRE-GATEWAY-MAAS
```

Cette recette utilise les identités techniques limitées ; elle crée puis révoque ses clés de test. Si elle réussit, effectuer ensuite le [parcours navigateur](DEMO-60-MIN.md) : connexion du compte humain, catalogue, clé, appel, limites visibles et révocation. Une recette API réussie ne remplace pas cette répétition.

L'équipe peut considérer le scénario prêt quand le modèle répond réellement, les refus sont démontrés, la relance est stable et le parcours humain a été observé sur **son** build. Consigner les éventuels écarts dans la fiche de recette.

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
