# MaaS RHOAI — démonstration Sopra Steria

Une démonstration de **60 minutes** : publier un véritable LLM natif, autoriser une équipe, attribuer un quota, créer une clé et observer un appel réel puis un refus.

Ce dépôt reprend les projets [rhoai-maas-demo](https://github.com/Lindagh1/rhoai-maas-demo) et [rhoai-3.5-demos](https://github.com/Lindagh1/rhoai-3.5-demos). Le module prédictif de ventes est conservé en complément ; le cœur de cette session répond aux questions MaaS de Sopra Steria.

**Cible client : RHOAI 3.5.0. Sandbox disponible : 3.5.4.** Les résultats réellement obtenus, les écarts de version et les vérifications restantes sont dans [VALIDATION.md](docs/VALIDATION.md). Ces manifestes sont des exemples de démonstration, pas des modèles certifiés par le support Red Hat.

## Démarrer

Prérequis : RHOAI 3.5.x avec MaaS déjà actif, gateway/TLS et tenant prêts, un GPU NVIDIA disponible, `oc`, Python 3.10+, et un compte administrateur pour la préparation.

```bash
git clone https://github.com/Lindagh1/rhoai-maas-sopra-steria-demo.git
cd rhoai-maas-sopra-steria-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Se connecter au cluster avec oc login, puis adapter config/demo.json.
./setup.sh check
./setup.sh render
./setup.sh apply
./setup.sh verify-idempotence
```

Le setup déploie Qwen2.5-0.5B-Instruct sur GPU via `LLMInferenceService`, publie son `MaaSModelRef`, puis crée les autorisations et souscriptions de démonstration. Il ne remplace pas les opérateurs, l'IdP, la gateway ou le tenant existants. Une installation de plateforme neuve suit [INSTALLATION.md](docs/INSTALLATION.md).

`config/demo.json` désigne une identité de démonstration `sopra-user`, à créer dans l'IdP ou à remplacer par une identité existante. Les quatre ServiceAccounts servent uniquement aux tests API automatisés. Ils ne remplacent pas le parcours humain OAuth.

## Préparer la réunion

- [Déroulé de 60 minutes et parcours utilisateur/admin](docs/DEMO-60-MIN.md).
- [Chaîne de CRDs, namespaces et gouvernance](docs/ARCHITECTURE.md).
- [Comparatif MaaS / LiteLLM / LiteMaaS sur les dix critères](docs/COMPARATIF.md).
- [Installation, idempotence et restauration du GPU](docs/INSTALLATION.md).
- [Observabilité et diagnostic 3.5.0 / support](docs/OBSERVABILITE-ET-LIMITES.md).
- [Reprises des anciens projets](docs/REUTILISATION.md).
- [Complément prédictif](ventes/README.md).

## Rejouer un appel avec une clé utilisateur

Dans le dashboard, créer une clé liée à `sopra-standard`, puis :

```bash
python scripts/save_key.py
python scripts/client.py --url https://GATEWAY-MAAS --key-file secrets/user.apikey
# Copier exactement l'id renvoyé par le catalogue :
python scripts/client.py --url https://GATEWAY-MAAS --key-file secrets/user.apikey \
  --model 'ID-EXACT-DU-CATALOGUE'
```

La recette automatisée côté préparation utilise des identités limitées, crée des clés temporaires puis les révoque :

```bash
python scripts/validate_live.py --url https://GATEWAY-MAAS
python -m unittest discover -s tests -p test_maas.py -v
```

Une préparation rejouée conserve les ressources et ne crée pas de nouvelles clés personnelles. Les appels de recette consomment des tokens et la rotation crée volontairement de nouvelles clés : ces actions métier ne sont pas une opération idempotente.
