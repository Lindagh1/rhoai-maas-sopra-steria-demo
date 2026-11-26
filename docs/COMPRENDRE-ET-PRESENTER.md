# La démo expliquée simplement

[Accueil](../README.md) · [Installation](INSTALLATION.md) · [Conducteur détaillé](DEMO-60-MIN.md)

## Le pitch — à dire en introduction

« Vous avez déjà un modèle qui fonctionne. La question suivante est : comment le mettre à disposition de plusieurs équipes, sans distribuer les accès administrateur et sans laisser son utilisation sans contrôle ? Nous allons suivre deux personnes : l'administrateur qui publie le modèle et accorde un accès, puis le développeur qui crée sa clé et utilise le service. Nous vérifierons aussi les refus, les limites et la révocation. À la fin, nous disposerons d'un parcours rejouable et de faits pour comparer MaaS à LiteLLM et LiteMaaS. »

## Une histoire, deux rôles

**L'administrateur plateforme** exploite OpenShift AI. Il prépare un modèle, le publie et décide quelle équipe peut l'utiliser, avec quelle limite.

**Le développeur d'une équipe applicative** se connecte avec son compte habituel, trouve un modèle autorisé, crée sa clé et l'intègre à une application via une API. Dans la démo, un appel simple remplace l'application : « Explique en une phrase ce que fait une API. » Il obtient une vraie réponse générée par Qwen.

La question n'est pas d'évaluer la qualité métier de Qwen. Ce petit modèle permet de montrer le service complet : identité → autorisation → quota → clé → appel → suivi → révocation.

## Ce que le spectateur voit

1. **Un service existe.** Dans les déploiements, le modèle est prêt. Il est servi nativement par `LLMInferenceService` : nous couvrons le parcours demandé par Sopra Steria.
2. **L'administrateur ouvre l'accès.** Il associe l'équipe au modèle et à une limite de 2 000 tokens par minute. On distingue « a le droit » et « peut consommer combien ».
3. **Le développeur utilise le service.** Il se connecte, consulte les modèles, crée une clé liée à sa souscription et lance l'appel. On lit la réponse et le nombre de tokens.
4. **Les contrôles sont visibles.** Sans autorisation, l'appel est refusé. Sans souscription, la création de clé peut être refusée. Avec le petit quota de test, un appel finit en 429.
5. **Le développeur retire son accès technique.** Il révoque la clé ; l'ancienne ne fonctionne plus. Une nouvelle clé permet de reprendre.
6. **L'administrateur suit l'utilisation.** On rapproche les appels et les compteurs. On vérifie séparément ce que l'utilisateur peut voir dans l'UI.
7. **On compare et on décide.** On examine les fonctions, les manques et la charge d'exploitation face à LiteLLM/LiteMaaS.

Le parcours navigateur décrit ici est le parcours de présentation à répéter. Les contrôles API ont déjà été exécutés ; toute la navigation avec le compte humain n'a pas encore été validée. La consommation personnelle et le quota restant dans l'UI sont des points à qualifier, pas une fonctionnalité que le kit aurait ajoutée à RHOAI.

## Les mots à traduire pendant la présentation

- **LLMInferenceService** : le serveur de notre modèle.
- **MaaSModelRef** : sa publication dans MaaS.
- **MaaSAuthPolicy** : la règle qui autorise une personne ou un groupe à appeler un modèle.
- **MaaSSubscription** : le droit de consommation et ses limites ; ce n'est pas l'abonnement commercial Red Hat.
- **Gateway** : la porte d'entrée commune aux appels.
- **Token** : une unité de texte comptée dans les entrées et sorties ; ce n'est pas une requête.
- **Idempotent** : relancer la même préparation retrouve les mêmes objets, sans multiplier les installations.

## Répartir l'heure

- 0–5 min : besoin et environnement.
- 5–17 min : publication et accès administrateur.
- 17–35 min : parcours utilisateur et rotation de clé.
- 35–45 min : refus et observation des compteurs.
- 45–55 min : comparaison fonctionnelle.
- 55–60 min : questions support et prochaines validations.

Installer et télécharger les images avant la réunion. La session sert à montrer le parcours ; son heure ne comprend pas le temps de préparation du cluster. [Actions écran par écran et commandes](DEMO-60-MIN.md).

## Ce qui a été construit et ce qui reste

Le dépôt contient un déploiement GPU réel, des objets d'accès et de quota, des scripts de préparation et de recette, les guides et le comparatif. Sur la sandbox, le modèle est prêt et les appels, refus, quotas, rotation et relance ont été vérifiés. Le compte humain `sopra-user` a été créé.

Les vérifications restantes portent notamment sur le parcours navigateur, Entra ID chez Sopra Steria et le build client 3.5.0. Notre recette a utilisé RHOAI 3.5.4. Le scénario multitenant et la variante endpoint externe restent des compléments documentés, pas des démonstrations exécutées ici. [Détail des preuves](VALIDATION.md).

Le module prédictif « prévoir les ventes de glaces » a été repris de l'ancien projet. Il montre un autre sujet : données → apprentissage → pipeline → prédiction. Il n'est pas raccordé au LLM de cette démo et n'a pas été redéployé pendant cette préparation. Il peut faire l'objet d'une séquence séparée de 15–20 minutes.

## Ce que Sopra Steria récupère

Un dépôt contenant les sources et des commandes rejouables, un parcours administrateur/utilisateur, des exemples YAML, une recette et une grille de comparaison. Il ne contient pas les identifiants de notre sandbox. L'équipe client fournit sa plateforme, son identité et ses endpoints. Le guide d'installation indique qui prépare chaque couche et comment vérifier le résultat.
