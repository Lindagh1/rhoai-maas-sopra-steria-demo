"""Build the notebook that consumes the deployed model through its real API."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
cells=[]
def md(value): cells.append(nbf.v4.new_markdown_cell(value))
def code(value): cells.append(nbf.v4.new_code_cell(value))

md("""# Demander une prévision au magasin

Le modèle **Prévision des ventes** fonctionne maintenant comme un service sur CPU.
Ce notebook joue le rôle d'une petite application : il envoie une demande et reçoit une réponse. **Il ne réentraîne pas le modèle.**

Avant de commencer : la connexion **Données du magasin** doit être attachée à ce workbench, et le déploiement doit afficher **Ready**.
Exécuter les cellules dans l'ordre avec **Maj + Entrée**. Données et cas métier synthétiques.""")

md("""## 1. Retrouver les données grâce à la connexion
Les identifiants sont fournis par la connexion. Nous ne les écrivons pas dans le code et nous ne les affichons pas.
Le disque du workbench garde nos fichiers de travail ; le stockage partagé garde les données et le modèle pour les autres étapes.""")
code("""import os, io, json, time
from pathlib import Path
import boto3
import pandas as pd
import requests
import ipywidgets as widgets
from IPython.display import display, HTML

s3 = boto3.client('s3', endpoint_url=os.environ['AWS_S3_ENDPOINT'],
                  region_name=os.environ['AWS_DEFAULT_REGION'])
bucket = os.environ['AWS_S3_BUCKET']
historique = pd.read_csv(io.BytesIO(s3.get_object(Bucket=bucket, Key='donnees/ventes.csv')['Body'].read()))
print(f'Connexion Données du magasin : {len(historique)} journées retrouvées.')
display(historique.head(3))""")

md("""## 2. Vérifier que le modèle est prêt
L'adresse ci-dessous est interne au cluster. Elle est accessible depuis ce workbench, qui dispose déjà de la connexion au projet.
Le service renvoie une quantité estimée ; nous l'arrondissons au nombre entier de glaces pour la décision du magasin.""")
code("""# Le nom du projet est fourni au workbench par Kubernetes.
namespace_file = Path('/var/run/secrets/kubernetes.io/serviceaccount/namespace')
projet = namespace_file.read_text().strip() if namespace_file.exists() else 'ventes-demo-repetition'
modele_nom = 'prevision-des-ventes'
service = f'http://{modele_nom}-predictor.{projet}.svc.cluster.local:8888'
session = requests.Session()
etat = session.get(f'{service}/v2/models/{modele_nom}/ready', timeout=15)
etat.raise_for_status()
print('Prévision des ventes : prêt à répondre.')

def demander_prevision(temperature, weekend, promotion):
    if weekend not in (0, 1) or promotion not in (0, 1):
        raise ValueError('Week-end et promotion doivent valoir 0 ou 1.')
    requete = {'inputs': [{'name': 'donnees', 'shape': [1, 3], 'datatype': 'FP32',
                           'data': [float(temperature), float(weekend), float(promotion)]}]}
    debut = time.perf_counter()
    reponse = session.post(f'{service}/v2/models/{modele_nom}/infer', json=requete, timeout=15)
    reponse.raise_for_status()
    resultat = reponse.json()
    brut = float(resultat['outputs'][0]['data'][0])
    return {'glaces': max(0, round(brut)), 'estimation': brut,
            'duree_ms': round((time.perf_counter()-debut)*1000, 1),
            'version': resultat.get('model_version', '?')}

avec = demander_prevision(24, 1, 1)
sans = demander_prevision(24, 1, 0)
print(f'Samedi à 24 °C : {avec["glaces"]} glaces avec promotion, {sans["glaces"]} sans promotion.')""")

md("""## 3. Le petit formulaire du magasin
Changer la température ou la promotion, puis cliquer sur **Calculer la prévision**.
Chaque clic envoie une vraie requête au modèle déployé. Aucun calcul d'apprentissage n'est relancé.

La première prévision est affichée automatiquement. Les réponses sont illustratives : une différence entre scénarios ne démontre pas une causalité dans un vrai magasin.""")
code("""temperature = widgets.FloatSlider(value=24, min=10, max=35, step=1,
                                  description='Météo (°C)', continuous_update=False)
weekend = widgets.Checkbox(value=True, description='Week-end')
promotion = widgets.Checkbox(value=True, description='Promotion')
bouton = widgets.Button(description='Calculer la prévision', button_style='primary',
                        layout=widgets.Layout(width='210px'))
sortie = widgets.Output()
dernier_resultat = None

def calculer(_=None):
    global dernier_resultat
    bouton.disabled = True
    try:
        resultat = demander_prevision(temperature.value, int(weekend.value), int(promotion.value))
        dernier_resultat = resultat
        with sortie:
            sortie.clear_output(wait=True)
            display(HTML(f'<div style="padding:18px;border-left:5px solid #b12c2d">'
                         f'<strong style="font-size:32px">{resultat["glaces"]} glaces</strong><br>'
                         f'Prévision reçue du modèle, version {resultat["version"]}.<br>'
                         'Erreur moyenne mesurée sur le test : environ 7 glaces par jour.<br>'
                         '<small>Données synthétiques. Cette erreur moyenne n’est pas une garantie.</small></div>'))
    except requests.RequestException:
        with sortie:
            sortie.clear_output(wait=True)
            print('Le service ne répond pas. Vérifier que Prévision des ventes est Ready dans Deployments.')
        dernier_resultat = None
    finally:
        bouton.disabled = False

bouton.on_click(calculer)
display(widgets.VBox([temperature, weekend, promotion, bouton, sortie]))
calculer()""")

md("""## 4. Voir l'activité du service
Après quelques clics, réexécuter cette cellule : le nombre de requêtes réussies augmente.
Ce compteur décrit l'activité technique depuis le dernier démarrage du serveur. Il ne mesure pas la qualité des prédictions ni la dérive des données.
Les mêmes métriques sont collectées par la supervision de la plateforme.""")
code("""mesures = session.get(service + '/metrics', timeout=15)
mesures.raise_for_status()
lignes = [ligne for ligne in mesures.text.splitlines()
          if ligne.startswith('ovms_requests_success{')
          and 'method="ModelInfer"' in ligne and 'interface="REST"' in ligne]
compteur = sum(float(ligne.rsplit(' ', 1)[1]) for ligne in lignes)
print(f'Requêtes de prévision réussies depuis le dernier démarrage : {int(compteur)}')""")

md("""## 5. Conserver un résultat partagé
Nous rangeons les deux scénarios dans le stockage partagé. Une autre application autorisée pourrait les relire.""")
code("""comparaison = {'avec_promotion': avec, 'sans_promotion': sans,
               'temperature': 24, 'weekend': 1, 'donnees': 'synthetiques'}
s3.put_object(Bucket=bucket, Key='resultats/comparaison.json',
              Body=json.dumps(comparaison, ensure_ascii=False, indent=2).encode(),
              ContentType='application/json')
print('Comparaison enregistrée : resultats/comparaison.json')
print('Notre parcours : données → apprentissage → stockage → déploiement → utilisation.')""")
md("""## Pour le présentateur
- **Connections** : Données du magasin, utilisée par l'atelier et le modèle.
- **Deployments** : Prévision des ventes, CPU, version 1, statut Ready.
- **Pipelines** : les étapes automatisent l'apprentissage et la prévision par lot ; le déploiement reste distinct dans ce kit.

[Connexions dans la documentation 3.5](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/working_on_projects/using-connections_projects) ·
[Déploiement et test du tutoriel officiel 3.5](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/openshift_ai_tutorial_-_fraud_detection_example/t-fdt-deploying-and-testing-a-model).""")
nb=nbf.v4.new_notebook(cells=cells, metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}})
nbf.write(nb,ROOT/'03_utiliser_le_modele.ipynb')
print('Notebook d’application créé.')
