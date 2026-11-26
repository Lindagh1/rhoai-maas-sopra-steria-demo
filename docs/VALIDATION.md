# État de la recette — 26 novembre 2026

## Environnement réellement testé

- OpenShift **4.20.46**, RHOAI **3.5.4**, MaaS **0.2.0**, RHCL **1.4.4**.
- Un GPU NVIDIA ; Llama existant mis en pause avec accord explicite du propriétaire.
- Nouveau namespace `sopra-maas-models`, service natif `sopra-qwen`, tenant par défaut.
- Qwen2.5-0.5B-Instruct, véritables poids Hugging Face, runtime vLLM fourni par RHOAI.
- Gateway déjà active avec DNS/TLS et LoadBalancer. Aucun opérateur ni tenant partagé recréé.

## Résultats API observés

La recette s'est exécutée le 26 novembre à partir de 10 h 56, heure de Paris. Les appels MaaS ont utilisé des **ServiceAccounts sans administration**. Le compte administrateur n'a servi qu'à préparer les ressources et obtenir leurs jetons d'authentification.

| Test | Résultat observé |
|---|---|
| Création de clé avec souscription et expiration | HTTP 201 |
| Catalogue avec la clé | HTTP 200 ; uniquement le modèle autorisé |
| Inférence réelle | HTTP 200 ; réponse textuelle ; 44 tokens d'entrée + 43 de sortie = 87 |
| Inférence sans clé | HTTP 401 |
| Petit quota `sopra-low` | Premier appel 200, suivant 429 |
| Autorisation sans subscription | Création de clé refusée : HTTP 400, `invalid_subscription` |
| Subscription sans autorisation | Création 201, inférence 403 |
| Ni autorisation ni subscription | Création de clé refusée : HTTP 400 |
| Révocation de sa propre clé | HTTP 200 ; ancien credential refusé en 403 sur cette gateway |
| Nouvelle clé après révocation | HTTP 201 puis inférence 200 |
| Relance du setup | UID, générations, contenu des ressources et UID des pods inchangés |
| Tests hors cluster | 12 tests réussis, dont réconciliation prédictive et réutilisation des pipelines |

Les quatorze contrôles de recette API sont passés. Les clés de recette ont été révoquées à la fin. Les rapports bruts sont locaux dans `.state/`; une copie relue, sans secrets, est conservée dans [validation-api.json](validation-api.json).

**Interprétation du petit quota :** la limite configurée à 1 token n'a pas empêché le premier appel de consommer 87 tokens. Le refus apparaît à l'appel suivant. Il s'agit d'un contrôle de débit observé, pas d'une garantie de budget strict sans dépassement sur la requête en cours.

**Interprétation de la révocation :** le refus observé est 403 dans cette configuration, même si certaines sections documentaires décrivent 401. La recette accepte un refus d'authentification ou d'autorisation et conserve le code exact.

## Compteurs Limitador

Lecture à 10 h 58, heure de Paris : `sopra-standard` = 2 appels autorisés et 174 tokens ; `sopra-low` = 1 appel autorisé, 87 tokens et 1 refus. La série est filtrée sur `sopra-maas-models/sopra-qwen-kserve-route`. Ces compteurs confirment le trafic mesuré ; ils ne constituent pas une facture ni une vue du quota restant dans le dashboard utilisateur.

## Identité humaine préparée

Le compte `sopra-user` a été créé dans le Keycloak local de la sandbox, sans rôle administrateur. Une seconde exécution a conservé le compte et son mot de passe. Le mot de passe est enregistré uniquement dans `secrets/sopra-user.password`. Le groupe `sopra-maas-users` est déclaré dans OpenShift et dispose de la lecture du seul projet modèle. Le parcours navigateur reste à effectuer.

## Ce qui n'a pas été validé

- Parcours complet **dans un navigateur avec un humain non-administrateur** : connexion OAuth, filtres UI, création/révocation dans l'UI et consommation personnelle.
- Fédération Entra ID / Azure AD du client ; la sandbox utilise un IdP OpenID local.
- Cluster `dps-demo` en 3.5.0 ; le schéma et l'UX peuvent différer de 3.5.4.
- Deux tenants avec gateways dédiées, isolation réseau et rejet croisé des clés.
- Variante `ExternalProvider` / `ExternalModel`, provider cloud payant et KServe HTTP classique.
- Installation complète sur une nouvelle plateforme vide ; MaaS existait déjà sur la sandbox.
- Cas mémoire et hostname sans LoadBalancer des tickets support.
- Nouveau déploiement du module prédictif dans ce dépôt : sources reprises et tests locaux passés, déploiement hérité non rejoué.
- Approbation des YAML par le support Red Hat. Le dry-run serveur prouve l'acceptation du schéma installé, pas une certification éditeur.

## Recette à compléter sur le cluster client

- [ ] Noter les versions et images exactes avant toute action.
- [ ] Valider le YAML rendu avec le serveur 3.5.0 et relire les changements.
- [ ] Connecter le compte non-admin via Entra/OpenShift OAuth.
- [ ] Vérifier catalogue UI, accès API et absence de droits administrateur.
- [ ] Vérifier le scope et l'expiration visibles, puis la rotation.
- [ ] Relever l'UX sans souscription, avec le texte exact et l'étape concernée.
- [ ] Confirmer consommation personnelle et quota restant réellement accessibles.
- [ ] Rattacher les deux cases support à des correctifs/version confirmés.
