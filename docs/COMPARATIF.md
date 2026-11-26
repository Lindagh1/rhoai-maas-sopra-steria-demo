# Comparatif fonctionnel — MaaS RHOAI, LiteLLM Proxy, LiteMaaS

État documentaire consulté le **26 novembre 2026**. RHOAI : documentation 3.5 évolutive, à confronter au build 3.5.0 du client. LiteLLM et LiteMaaS : documentation courante, sans benchmark ni installation comparative dans cette recette. Toute fonction marquée Enterprise doit être vérifiée avec l'édition effectivement retenue.

LiteMaaS est un portail qui s'appuie sur LiteLLM ; ce n'est pas un troisième moteur de routage indépendant. Le projet se présente comme un proof of concept. [Présentation du projet](https://github.com/rh-aiservices-bu/litemaas).

| Critère | MaaS dans RHOAI 3.5 | LiteLLM Proxy | LiteMaaS | Vérification pour Sopra Steria |
|---|---|---|---|---|
| Multi-modèles / providers | Service natif dans ce kit ; endpoint externe par provider/modèle. Fonctions externes TP. | Adaptateurs providers, routage et fallbacks ; support précis à vérifier par API. | Repose sur les providers du LiteLLM associé. | Rejouer OpenAI, Anthropic et Bedrock avec les mêmes outils, formats et erreurs. |
| Clés API | Création/révocation et expiration ; clé rattachée à une subscription. | Virtual keys, durée, modèles autorisés, rattachement utilisateur/équipe. | Gestion self-service de clés et abonnements. | Observer portée visible, expiration effective et délai de révocation ; tester une clé perdue. |
| Quotas / rate limiting | `tokenRateLimits` par modèle et fenêtre ; bénéficiaires users/groups. Ne pas assimiler automatiquement quota de groupe à budget financier collectif. | RPM/TPM et budgets aux niveaux clé, utilisateur, équipe ; options selon édition/version. | Budgets utilisateur/équipe/clé via LiteLLM. | Deux utilisateurs et deux clés par utilisateur ; vérifier mutualisation et fenêtre réelle. |
| Multi-tenancy | `AITenant` + gateway dédiée ; TP. Cette recette reste dans le tenant par défaut. | Séparation logique teams/keys ; séparation réseau dépend du déploiement. | RBAC du portail ; isolation du proxy à vérifier. | Deux tenants réels, tentative croisée et accès direct au backend ; aucune isolation réseau déduite d'un simple groupe. |
| Authentification | Dashboard via OpenShift OAuth ; API key pour l'inférence. OIDC direct MaaS distinct. | SSO Microsoft documenté ; JWT, SAML et fonctions avancées à vérifier par édition. | OAuth2/JWT et groupes OpenShift documentés. | Entra ID, claims, retrait d'un groupe, expiration, logout ; ne pas confondre session UI et credential d'inférence. |
| Observabilité / metering | `usage` des réponses, Limitador ; dashboard showback admin, TP. Consommation personnelle UI à qualifier. | Spend par clé/user/team ; export Prometheus, dont certaines séries Enterprise. | Vues utilisateur et admin, coûts et exports. | Vérifier visibilité non-admin, délais et réconciliation avec la facture fournisseur. |
| Installation / exploitation | CRDs, contrôleurs, gateway, Kuadrant/Authorino/Limitador, base et télémétrie ; opérateurs déjà présents ici. | Proxy, base PostgreSQL pour les clés ; dépendances HA/cache à configurer selon architecture. | Ajoute frontend/backend au proxy ; suivre sa matrice de versions. | Mesurer temps de reprise, sauvegarde, upgrade et diagnostic d'une panne auth/DB/gateway. |
| Extensibilité | CRDs/GitOps, raccordement endpoint ; contrat d'API à respecter. | Callbacks et authentification custom ; leur activation ne garantit pas tous les contrôles de budget et modèle. | Évolution du portail et de son intégration LiteLLM. | Qui maintient une adaptation custom lors d'une mise à jour ? |
| Support / cycle de vie | Distinguer GA et TP ; périmètre support et compatibilité à confirmer avec Red Hat. | OSS ou offre Enterprise ; engagement contractuel distinct. | Projet communautaire/PoC ; aucun SLA Red Hat déduit de son organisation GitHub. | Obtenir versions supportées OCP/RHOAI/RHCL, dates de maintenance et contrat applicable. |
| Coût total | Évaluer coût marginal si OCP/RHOAI sont déjà opérés ; CPU, GPU, logs, stockage, RHCL et support restent à chiffrer. | Exploitation DB/proxy/Redis éventuel + licence Enterprise éventuelle. | Exploitation du portail + proxy + intégration et maintenance. | Chiffrer à périmètre, HA, support et conservation des logs identiques. |

## Références des colonnes

- MaaS : [architecture et résultats locaux](ARCHITECTURE.md), [gouvernance Red Hat](https://www.redhat.com/ko/blog/models-service-maas-governance-managing-ai-access-and-token-quotas), [guide produit 3.5](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/govern_llm_access_with_models-as-a-service/index), [configuration OIDC amont](https://github.com/opendatahub-io/models-as-a-service/blob/main/docs/content/advanced-administration/external-oidc.md).
- LiteLLM : [virtual keys](https://docs.litellm.ai/docs/proxy/virtual_keys), [budgets équipes](https://docs.litellm.ai/docs/proxy/team_budgets), [routage](https://docs.litellm.ai/docs/proxy/load_balancing), [Microsoft SSO](https://docs.litellm.ai/docs/tutorials/msft_sso), [Prometheus](https://docs.litellm.ai/docs/proxy/prometheus), [auth custom et limites](https://docs.litellm.ai/docs/proxy/custom_auth).
- LiteMaaS : [fonctionnalités, architecture et déploiement](https://github.com/rh-aiservices-bu/litemaas), [releases et migrations](https://github.com/rh-aiservices-bu/litemaas/releases). La présentation consultée signale notamment un fork LiteLLM à partir de sa version 0.4.0 : vérifier le couple de versions, pas seulement le tag du portail.

## Trajectoires à examiner — appréciation, pas résultat de benchmark

**MaaS natif** paraît cohérent si la priorité est la gouvernance déclarative de modèles hébergés sur une plateforme RHOAI déjà opérée. Les fonctions TP et l'expérience du consommateur sont des critères de décision, pas des détails à reporter.

**LiteLLM** mérite un essai si la priorité est la diversité des providers et des politiques du proxy. Mesurer le coût d'exploitation et confirmer les fonctions de l'édition choisie avant de comparer les budgets.

**LiteMaaS** mérite un prototype si le portail utilisateur et le suivi individuel sont déterminants. L'équipe doit accepter de maintenir ce portail et son couple de versions avec LiteLLM.

Une combinaison reste possible, mais implique deux systèmes de clés, de quotas et de comptage. Définir alors quel système fait autorité ; ne pas additionner des compteurs qui mesurent les mêmes appels.

Aucun prix, SLA ou engagement de roadmap n'est inventé dans cette grille. Les coûts de licences et périmètres inclus doivent être confirmés dans les contrats applicables.
