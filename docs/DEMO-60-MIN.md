# Déroulé de démonstration — 60 minutes

## Avant la réunion

Préparer la plateforme, télécharger le modèle et exécuter `apply`, `verify-idempotence` et la recette API. Réserver un compte humain sans rôle administrateur, membre du groupe configuré, plus un compte témoin sans souscription. Deux profils de navigateur évitent de confondre les sessions. Ne pas utiliser l'ancien `demo-user` sans audit de ses droits : l'ancien kit lui accordait un rôle admin dans son projet.

Le compte `sopra-user` déclaré dans le kit doit exister dans l'IdP. Pour Azure AD / Entra ID, valider le raccordement à OpenShift OAuth et le mapping du nom d'utilisateur et des groupes. L'OIDC direct de MaaS est un autre parcours API, distinct de la connexion au dashboard. [Référence amont OIDC et limites du dashboard](https://github.com/opendatahub-io/models-as-a-service/blob/main/docs/content/advanced-administration/external-oidc.md).

## 0–5 min — périmètre et preuve de version

Afficher les versions OCP/RHOAI réelles. Annoncer la distinction entre `dps-demo` 3.5.0 et la sandbox de recette. Ouvrir [VALIDATION.md](VALIDATION.md). Expliquer qu'une réussite en 3.5.4 ne prouve pas le même comportement UI en 3.5.0.

## 5–17 min — administrateur : publier et gouverner

1. Montrer `config/demo.json` et les YAML rendus dans `.state/rendered.yaml`.
2. Montrer `LLMInferenceService/sopra-qwen` et `MaaSModelRef/sopra-qwen`, leur état et l'endpoint résolu.
3. Ouvrir `MaaSAuthPolicy/sopra-access` : qui peut appeler quel modèle.
4. Ouvrir `MaaSSubscription/sopra-standard` : bénéficiaires, modèle, fenêtre `1m`, limite `2000`.
5. Montrer la deuxième souscription `sopra-low`, dédiée au refus 429.
6. Pour un nouveau groupe : le créer/synchroniser dans l'IdP/OpenShift, l'ajouter aux sujets de la policy **et** aux propriétaires de la subscription. Vérifier les références exactes et leurs états. Une modification d'un objet n'implique pas automatiquement la modification de l'autre.
7. Rejouer `./setup.sh verify-idempotence` : mêmes objets, mêmes générations et mêmes pods.

Ces opérations ne se font pas avec le compte consommateur.

## 17–35 min — utilisateur final : de la connexion à la rotation

1. Ouvrir un profil de navigateur séparé ; se connecter au dashboard avec le compte de démonstration via OpenShift OAuth. Afficher son nom de compte.
2. Ouvrir **Gen AI studio → AI asset endpoints** et repérer le modèle publié. Comparer les modèles visibles à ceux du compte témoin. Vérifier également le catalogue API avec la clé ; l'UI seule ne prouve pas l'autorisation.
3. Dans **API keys**, créer une clé nommée `sopra-live` avec une durée courte et la souscription `sopra-standard`. Montrer la portée réellement affichée : une souscription peut contenir plusieurs modèles. Ne pas promettre un filtre arbitraire par modèle à l'intérieur d'une même souscription.
4. Copier la clé une fois, hors écran partagé, via `python scripts/save_key.py`.
5. Lancer le catalogue puis l'appel avec `scripts/client.py` comme dans le README. Utiliser l'ID exact retourné, y compris son préfixe et ses `/`.
6. Montrer le texte généré et `usage.prompt_tokens`, `completion_tokens`, `total_tokens`. Ce sont les tokens de cet appel, pas un quota restant global.
7. Ouvrir les souscriptions/limites disponibles dans cette version de l'UI. Consigner ce que le compte non-admin voit réellement. Si aucune consommation personnelle ou aucun quota restant n'est affiché, l'indiquer comme **écart fonctionnel**, sans ouvrir un dashboard admin sous cette identité.
8. Révoquer `sopra-live`, rejouer l'appel jusqu'au refus effectif ; consigner le délai éventuel de cache. Créer `sopra-live-v2`, remplacer le fichier local et vérifier un nouvel appel réussi.

Les intitulés et étapes du parcours sont à rapprocher de la [documentation utilisateur 3.5](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/govern_llm_access_with_models-as-a-service/use-models-as-a-service_maas-deploy). Le scope, les onglets et les erreurs doivent être vérifiés sur le build client.

### Exemple curl compatible OpenAI

Pour un terminal personnel uniquement : la commande lit le secret depuis stdin et le transmet à curl sans le placer dans ses arguments. Choisir l'ID exact après l'appel du catalogue.

```bash
export MAAS_URL='https://GATEWAY-MAAS'
python - <<'PY' | curl --silent --show-error --config - "$MAAS_URL/v1/models"
from pathlib import Path
k=Path('secrets/user.apikey').read_text().strip()
assert k and not any(x in k for x in '\r\n"\\')
print('header = "Authorization: Bearer '+k+'"')
PY
```

Enregistrer une requête sans secret dans `.state/request.json`, puis :

```json
{"model":"ID-EXACT-DU-CATALOGUE","messages":[{"role":"user","content":"Explique en une phrase ce que fait une API."}],"max_tokens":64,"temperature":0}
```

```bash
python - <<'PY' | curl --silent --show-error --config - \
  -H 'Content-Type: application/json' --data-binary @.state/request.json \
  "$MAAS_URL/v1/chat/completions"
from pathlib import Path
k=Path('secrets/user.apikey').read_text().strip()
assert k and not any(x in k for x in '\r\n"\\')
print('header = "Authorization: Bearer '+k+'"')
PY
```

## 35–45 min — refus et observabilité

- **Aucune subscription** : connexion possible au dashboard ne signifie pas droit à une clé MaaS. Tenter la création avec le compte témoin et relever message, endpoint, code et heure. Sur le build client, documenter le message « subscription required » et l'absence éventuelle d'indication du responsable à contacter. Le kit propose une procédure interne : demander au responsable MaaS d'ajouter groupe, modèle, autorisation et quota ; puis recréer une clé.
- **Policy seule / subscription seule** : utiliser les identités dédiées de `validate_live.py`. Distinguer le refus de création de clé d'un refus d'inférence : il ne faut pas attribuer un code HTTP universel à « aucune subscription ».
- **Quota dépassé** : créer une clé explicitement liée à `sopra-low`. Montrer le 429 ; vérifier le retour à un état utilisable après la fenêtre, sans augmenter le quota principal pour masquer le test.
- Côté administrateur, ouvrir Observe/Monitor MaaS si disponible et rapprocher compteur, fenêtre et heure de l'appel. Voir [observabilité](OBSERVABILITE-ET-LIMITES.md).

## 45–55 min — comparaison et décision

Ouvrir [COMPARATIF.md](COMPARATIF.md). Rechercher les critères éliminatoires : provider requis, self-service individuel, support des fonctions retenues, isolation et charge d'exploitation. Les colonnes ne sont pas des scores marketing.

## 55–60 min — points support et suite

Reprendre les cases 04541689 et 04541847, sans leur attribuer un diagnostic non lu. Demander le statut exact du problème mémoire, du hostname sans LB et la version contenant le correctif. Faire valider par Red Hat les YAML rendus pour `dps-demo`. Consigner le résultat dans la fiche de recette.

Le prédictif est un complément de 15–20 minutes, à prévoir dans une session distincte ou à substituer à une partie du comparatif.
