"""Build the teaching notebook and deterministic synthetic sales data."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(42)
dates = pd.date_range("2026-01-01", periods=210)
temperature = np.round(19 + 8 * np.sin(np.arange(210) / 210 * np.pi) + rng.normal(0, 3, 210), 1)
weekend = (dates.dayofweek >= 5).astype(int)
promotion = rng.binomial(1, 0.25, 210)
sales = np.maximum(0, np.rint(40 + 4 * temperature + 35 * weekend + 45 * promotion + rng.normal(0, 8, 210))).astype(int)
data = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "temperature_prevue": temperature,
                     "weekend": weekend, "promotion": promotion, "ventes": sales})
data.to_csv(ROOT / "ventes.csv", index=False)
cells = []
def md(text): cells.append(nbf.v4.new_markdown_cell(text))
def code(text): cells.append(nbf.v4.new_code_cell(text))

md("""# Combien de glaces vendre demain ?

**Notre décision :** préparer une quantité adaptée pour le magasin.

Nous allons lire 210 jours de ventes, apprendre une relation simple, vérifier l'erreur sur des jours non utilisés pour apprendre, puis prévoir un nouveau jour.

**Données entièrement synthétiques.** L'apprentissage et les calculs sont réels. Ce jeu est volontairement facile ; les résultats ne prouvent pas la performance dans un vrai magasin. Aucun GPU n'est nécessaire.

Exécuter les cellules dans l'ordre avec **Maj + Entrée**. Les fichiers `ventes.csv` et ce notebook doivent être dans le même dossier.""")
md("""## 1. Regarder les données
Une ligne = une journée. La colonne **ventes** est la réponse que le modèle doit apprendre à prévoir.
Les entrées sont la température prévue, le week-end (1 = oui) et la promotion (1 = oui). Elles doivent être connues au moment de faire la prévision.""")
code("""from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

donnees = pd.read_csv('ventes.csv').sort_values('date').reset_index(drop=True)
print(f'{len(donnees)} journées de démonstration')
display(donnees.head(6))""")
md("""## 2. Voir ce que l'on cherche à expliquer
Chaque point représente une journée. Les ventes dépendent de plusieurs facteurs : une journée chaude ne suffit pas à expliquer toute la variation.""")
code("""fig, ax = plt.subplots(figsize=(9, 3.6))
for promo, couleur, nom in [(0, '#546e7a', 'Sans promotion'), (1, '#c43c32', 'Avec promotion')]:
    lignes = donnees[donnees.promotion == promo]
    ax.scatter(lignes.temperature_prevue, lignes.ventes, c=couleur, alpha=0.65, label=nom)
ax.set(title='Ventes de glaces selon la température prévue', xlabel='Température prévue (°C)', ylabel='Glaces vendues par jour')
ax.legend(); ax.grid(alpha=0.15)
fig.tight_layout()
plt.show()
print('Source : données synthétiques, du 1 janvier au 29 juillet 2026.')""")
md("""## 3. Séparer apprendre et vérifier
Le modèle apprend sur les **168 premiers jours**. Nous gardons les **42 derniers jours** pour l'examen.
Le découpage suit le temps : on ne montre pas les réponses de l'examen au modèle pendant l'apprentissage.""")
code("""colonnes = ['temperature_prevue', 'weekend', 'promotion']
apprentissage = donnees.iloc[:168]
test = donnees.iloc[168:]
X_train, y_train = apprentissage[colonnes], apprentissage.ventes
X_test, y_test = test[colonnes], test.ventes
print(f'Apprentissage : {len(apprentissage)} jours | Test : {len(test)} jours')
print(f'Test du {test.date.iloc[0]} au {test.date.iloc[-1]}')""")
md("""## 4. Apprendre un modèle simple
Une **régression linéaire** apprend une formule à partir des exemples. La ligne `fit` réalise l'apprentissage ; nous n'écrivons pas nous-mêmes les coefficients de prévision.""")
code("""modele = LinearRegression()
modele.fit(X_train, y_train)
print('Le modèle a appris à partir des 168 jours.')""")
md("""## 5. Vérifier si le modèle apporte quelque chose
La référence simple prévoit toujours la moyenne des ventes d'apprentissage.
La **MAE**, ou erreur absolue moyenne, mesure l'écart moyen en nombre de glaces. **Plus elle est petite, mieux c'est.** Ce n'est pas un pourcentage de fiabilité.""")
code("""predictions = modele.predict(X_test)
reference = np.full(len(test), y_train.mean())
erreur_reference = mean_absolute_error(y_test, reference)
erreur_modele = mean_absolute_error(y_test, predictions)
print(f'Moyenne historique : erreur moyenne de {erreur_reference:.1f} glaces / jour')
print(f'Modèle appris      : erreur moyenne de {erreur_modele:.1f} glaces / jour')
fig, ax = plt.subplots(figsize=(8, 3.4))
ax.barh(['Moyenne historique', 'Modèle appris'], [erreur_reference, erreur_modele], color=['#89959b', '#c43c32'])
ax.set(xlabel='Erreur absolue moyenne (glaces par jour)', title='Erreur sur les 42 jours mis de côté')
ax.invert_yaxis(); fig.tight_layout(); plt.show()""")
md("""## 6. Comparer les ventes prévues aux ventes observées
Sur le graphique, les deux courbes doivent être proches. Elles ne sont pas identiques : une prévision garde une part d'erreur.""")
code("""fig, ax = plt.subplots(figsize=(10, 3.6))
ax.plot(pd.to_datetime(test.date), y_test, label='Ventes observées', color='#546e7a')
ax.plot(pd.to_datetime(test.date), predictions, label='Ventes prévues', color='#c43c32', linestyle='--')
ax.set(title='Prévisions sur les journées de test', xlabel='Date en 2026', ylabel='Glaces par jour')
ax.legend(); ax.grid(alpha=0.15); fig.autofmt_xdate(); fig.tight_layout(); plt.show()""")
md("""## 7. Prévoir une nouvelle journée
Notre « demain » est le **samedi 1 août 2026 du scénario**. Ce n'est pas la date réelle du jour.
Prévision météo : **24 °C**. Promotion : **oui**.

Essayer ensuite `promotion = 0` et réexécuter cette cellule. Observer la différence, sans la présenter comme une preuve de causalité sur des données réelles.""")
code("""temperature_prevue = 24.0
weekend = 1
promotion = 1

demain = pd.DataFrame([{'temperature_prevue': temperature_prevue, 'weekend': weekend, 'promotion': promotion}])
prevision = max(0, round(float(modele.predict(demain)[0])))
print(f'Prévision pour demain dans le scénario : {prevision} glaces')
print(f'À mettre en perspective avec une erreur moyenne de {erreur_modele:.1f} glaces sur le test.')
print('Cette erreur moyenne n’est pas un intervalle de confiance ni une garantie.')""")
md("""## 8. Conserver le résultat et passer au pipeline
Nous enregistrons la prévision. Le responsable du magasin peut utiliser ce fichier pour préparer sa journée.
Dans OpenShift AI, le pipeline automatisera **préparer → entraîner → évaluer → prévoir**. Chaque exécution conservera ses résultats.

Pour la démo : ouvrir **Develop & train → Pipelines → Pipeline definitions**, importer `pipeline_ventes.yaml`, puis créer une exécution. Les prérequis du serveur de pipelines sont expliqués dans le guide.""")
code("""Path('resultats').mkdir(exist_ok=True)
pd.DataFrame([{'date_scenario': '2026-08-01', 'temperature_prevue': temperature_prevue,
               'weekend': weekend, 'promotion': promotion, 'ventes_prevues': prevision}]).to_csv('resultats/prevision.csv', index=False)
Path('resultats/qualite.json').write_text(json.dumps({'mae_reference': erreur_reference, 'mae_modele': erreur_modele,
    'jours_apprentissage': 168, 'jours_test': 42}, indent=2), encoding='utf-8')
print('Fichiers créés : resultats/prevision.csv et resultats/qualite.json')""")
md("""## 9. Partager le modèle avec le magasin
La connexion **Données du magasin** permet de partager les données et le modèle sans écrire de mot de passe dans le notebook.
Le fichier ONNX est une version du modèle que le serveur de prédiction sait lire. L'export vérifie que les prévisions restent identiques à une petite tolérance numérique près.

Cette étape nécessite la connexion attachée au workbench et le fichier `exporter_modele.py`, fournis dans la répétition préparée. Dans un nouveau projet, les préparer avant d'exécuter cette cellule.
Le déploiement reste une action distincte dans l'onglet **Deployments** : connexion **Données du magasin**, chemin **modeles/ventes**, format **ONNX**, serveur **OpenVINO**, CPU uniquement.
Après le déploiement, ouvrir `03_utiliser_le_modele.ipynb` pour demander une prévision au service.""")
code("""from exporter_modele import publier
publication = publier(modele, donnees)
print('Notre modèle est maintenant disponible dans le stockage partagé.')""")
md("""## Ce que nous avons montré
- Le **projet** regroupe le travail.
- Le **workbench** fournit l'environnement de travail.
- Le **notebook** permet d'explorer, apprendre, vérifier et expliquer.
- Le **pipeline** rejoue un enchaînement et conserve les résultats.

Le cas métier et les données de ce kit sont une création pédagogique. Le parcours de plateforme suit la documentation officielle **Red Hat OpenShift AI Self-Managed 3.5** :
[Projet et workbench](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/getting_started_with_red_hat_openshift_ai_self-managed/creating-a-workbench-select-ide_get-started) ·
[Pipelines](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/working_with_ai_pipelines/managing-ai-pipelines_ai-pipelines).""")
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}})
nbf.write(nb, ROOT / '01_prevoir_les_ventes.ipynb')
(ROOT / 'exporter_modele.py').write_bytes((ROOT / 'scripts/exporter_modele.py').read_bytes())
print('Notebook et 210 journées synthétiques créés.')
