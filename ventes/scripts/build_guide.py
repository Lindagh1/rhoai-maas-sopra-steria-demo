"""Create the presenter handout; run with the bundled PDF runtime."""
from pathlib import Path
import json
from html import escape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf/guide-demo-ventes.pdf'
OUT.parent.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/liberation-sans-fonts'
pdfmetrics.registerFont(TTFont('Demo',f'{FONT}/LiberationSans-Regular.ttf'))
pdfmetrics.registerFont(TTFont('DemoBold',f'{FONT}/LiberationSans-Bold.ttf'))
pdfmetrics.registerFontFamily('Demo',normal='Demo',bold='DemoBold',italic='Demo',boldItalic='DemoBold')
INK=colors.HexColor('#202b33'); RED=colors.HexColor('#b12c2d'); GREY=colors.HexColor('#5d6870'); PALE=colors.HexColor('#f2f4f5')
W,H=595.28,841.89; M=44; WIDTH=W-2*M
c=canvas.Canvas(str(OUT),pagesize=(W,H))
c.setTitle('Prévoir les ventes avec OpenShift AI 3.5')
c.setAuthor('Guide de démonstration')
styles={
 'body':ParagraphStyle('body',fontName='Demo',fontSize=10.4,leading=15.6,textColor=INK,spaceAfter=7),
 'small':ParagraphStyle('small',fontName='Demo',fontSize=8.5,leading=12,textColor=GREY),
 'h2':ParagraphStyle('h2',fontName='DemoBold',fontSize=14,leading=19,textColor=INK),
 'quote':ParagraphStyle('quote',fontName='Demo',fontSize=11.5,leading=18,textColor=INK),
 'title':ParagraphStyle('title',fontName='DemoBold',fontSize=26,leading=32,textColor=INK)}
page=0; y=0
def para(text,kind='body',x=M,width=WIDTH,gap=8):
 global y
 p=Paragraph(text,styles[kind]);_,h=p.wrap(width,H)
 if y-h<52: raise RuntimeError(f'Content overflow on page {page}: {text[:60]}')
 p.drawOn(c,x,y-h);y-=h+gap
def title(kicker,heading,subtitle=None):
 global page,y
 if page:c.showPage()
 page+=1
 c.setFillColor(RED);c.rect(M,H-41,30,4,fill=1,stroke=0)
 c.setFillColor(GREY);c.setFont('Demo',8);c.drawString(M+40,H-39,'OPENSHIFT AI 3.5  /  DÉMONSTRATION PRÉDICTIVE')
 c.setFont('Demo',8);c.drawString(M,30,'Données synthétiques · Apprentissage réel · CPU uniquement')
 c.drawRightString(W-M,30,f'{page} / 8')
 y=H-75
 para(kicker,'small',gap=9)
 para(heading,'title',gap=12)
 if subtitle:para(subtitle,'body',gap=17)
def section(label):para(label,'h2',gap=8)
def step(n,text):para(f'<b>{n}.</b> {text}',gap=7)
def say(text):
 global y
 p=Paragraph('« '+text+' »',styles['quote']);_,h=p.wrap(WIDTH-30,H)
 c.setFillColor(PALE);c.roundRect(M,y-h-22,WIDTH,h+22,5,fill=1,stroke=0)
 p.drawOn(c,M+15,y-h-11);y-=h+36
def link(label,url):para(f'<link href="{escape(url,quote=True)}" color="#8c2526">{escape(label)}</link>','small',gap=7)
def flow(labels):
 global y
 n=len(labels);gap=12;box=(WIDTH-gap*(n-1))/n;h=50
 for i,(top,bottom) in enumerate(labels):
  x=M+i*(box+gap);c.setFillColor(PALE);c.roundRect(x,y-h,box,h,4,fill=1,stroke=0)
  p=Paragraph(f'<b>{top}</b><br/>{bottom}',styles['small']);_,ph=p.wrap(box-14,h)
  p.drawOn(c,x+7,y-8-ph)
  if i<n-1:
   c.setStrokeColor(GREY);c.line(x+box+2,y-h/2,x+box+gap-2,y-h/2)
 y-=h+20

title('LE FIL ROUGE · 1 MINUTE','Combien de glaces<br/>vendre demain ?',
      'Un responsable de magasin veut préparer une quantité adaptée. Nous allons transformer un historique de ventes en une prévision, puis automatiser ce travail.')
say('J’ai les ventes passées, la météo prévue et les promotions. Est-ce que je peux mieux préparer la journée de demain ?')
flow([('Projet','Le dossier'),('Workbench','L’atelier'),('Connexion','Partager'),('Notebook','Apprendre'),('Pipeline','Automatiser'),('Modèle','Répondre')])
section('Une histoire en six moments')
step('1','Créer le projet et choisir l’environnement de travail. <b>3 min</b>')
step('2','Relier l’atelier aux données du magasin. <b>2 min</b>')
step('3','Lire les données, apprendre et vérifier une prévision. <b>7 min</b>')
step('4','Lancer les mêmes étapes dans un pipeline. <b>4 min</b>')
step('5','Déployer le modèle et demander une réponse. <b>3 min</b>')
step('6','Changer une hypothèse et voir l’activité du service. <b>2 min</b>')
para('Compter <b>20 à 25 minutes</b>, hors attente de démarrage à froid. Une répétition complète est déjà préparée dans la sandbox.','small')
section('Ce que le public doit retenir')
para('Le notebook aide à comprendre et à expérimenter. Le pipeline conserve une recette que l’on peut relancer avec d’autres paramètres.')
para('La connexion partage les données et le modèle. Le déploiement permet à une application de demander une prévision. Le compteur de requêtes montre l’activité technique du service.','small')
para('<b>À annoncer dès le début :</b> les données sont synthétiques et volontairement simples. Le modèle est réellement entraîné et les étapes sont réellement exécutées. Les scores ne constituent pas une preuve de performance commerciale.')

title('ÉTAPE 1 · 3 MINUTES','Créer le dossier<br/>et l’atelier','Utiliser un compte autorisé à créer des projets et des workbenches, par exemple l’administrateur de la sandbox.')
section('Créer le projet')
step('1','Dans <b>Projects</b>, choisir <b>Create project</b>.')
step('2','Nom : <b>Ventes du magasin - direct</b>. Nom de ressource : <b>ventes-demo-live</b>.')
step('3','Description : « Prévoir les ventes de glaces du lendemain ». Créer le projet.')
say('Le projet rassemble les fichiers, l’environnement de travail et les exécutions de notre équipe.')
section('Créer le workbench')
step('4','Dans le projet : <b>Workbenches → Create workbench</b>. Nom : <b>Atelier de prévision</b>.')
step('5','Image : <b>Jupyter Data Science CPU Python 3.12</b>, version <b>3.5</b>. Profil : <b>default-profile</b>.')
step('6','Garder 2 CPU et 4 GiB si proposés. Créer un stockage persistant de <b>5 GiB</b>. Aucun GPU ni variable supplémentaire ne sont nécessaires.')
step('7','Créer, attendre <b>Ready</b>, puis ouvrir JupyterLab.')
say('Le workbench est mon atelier dans le cluster. Les calculs s’exécutent ici ; mon navigateur affiche le résultat.')
section('Si le démarrage prend trop longtemps')
para('Basculer explicitement vers le projet <b>Ventes du magasin</b>, puis ouvrir <b>Atelier de prévision</b>. Cette répétition contient déjà les fichiers. Ne pas supprimer le nouveau projet pour gagner du temps.')
para('Le profil matériel est le choix de CPU et de mémoire. Le stockage persistant garde les fichiers lorsque le workbench est arrêté.','small')

title('ÉTAPE 2 · 2 MINUTES','Relier les données','Dans le projet Ventes du magasin, ouvrir Connections. La connexion Données du magasin est déjà créée et liée à l’atelier ainsi qu’au modèle.')
section('Expliquer le rôle de la connexion')
say('Cette connexion indique où ranger et retrouver les données. Elle conserve les identifiants à part du notebook : je n’écris aucun mot de passe dans mon code.')
flow([('Disque de l’atelier','Mes fichiers de travail'),('Stockage partagé','Données et modèles'),('Connexion','Les informations d’accès')])
section('Pour montrer sa création dans un nouveau projet')
step('1','Ouvrir <b>Connections → Create connection</b>. Choisir <b>S3 compatible object storage</b>.')
step('2','Nom : <b>Données du magasin</b>. Description : « Lire les ventes et partager le modèle ».')
step('3','Renseigner endpoint, région, bucket, clé d’accès et clé secrète avec les valeurs privées préparées pour <b>ce projet</b>. Ne pas afficher la clé au public.')
step('4','Créer, puis modifier le workbench : <b>Connections → Attach existing connections</b>, choisir <b>Données du magasin</b> et enregistrer.')
step('5','Si l’atelier était ouvert, enregistrer le travail avant son redémarrage, puis rouvrir JupyterLab.')
section('La preuve à montrer')
para('Le notebook <b>03_utiliser_le_modele.ipynb</b> relit <b>210 journées</b> depuis le stockage partagé. Il y écrit aussi une comparaison de prévisions. Le serveur charge le modèle depuis la même connexion.')
para('L’option de vérification intégrée au formulaire dépend de la configuration de la plateforme et est en Technology Preview en 3.5. Notre vérification est une vraie lecture et une vraie écriture depuis l’atelier.','small')

title('ÉTAPE 3 · 7 MINUTES','Apprendre puis vérifier','Charger 01_prevoir_les_ventes.ipynb, ventes.csv et exporter_modele.py dans le même dossier Jupyter. Exécuter les cellules dans l’ordre avec Maj + Entrée.')
section('Montrer seulement quatre idées')
step('1','<b>Une ligne = une journée.</b> Montrer la date, la température prévue, le week-end, la promotion et les ventes.')
step('2','<b>168 jours pour apprendre, 42 pour vérifier.</b> Garder les journées les plus récentes pour le test.')
step('3','<b>Le modèle apprend une formule.</b> Montrer la ligne <b>modele.fit(...)</b>, sans expliquer les mathématiques.')
step('4','<b>Une prévision doit être évaluée.</b> Comparer l’erreur du modèle à celle de la moyenne historique.')
say('Je garde des journées de côté. Le modèle ne voit pas leurs réponses pendant l’apprentissage : elles servent à vérifier son travail.')
section('Résultats mesurés dans la répétition')
flow([('26,2 glaces/jour','Erreur de la moyenne'),('7,0 glaces/jour','Erreur du modèle'),('217 glaces','Prévision du scénario')])
para('L’erreur affichée est la <b>MAE</b> : l’écart absolu moyen entre ventes prévues et observées. Une valeur plus basse est meilleure. <b>7 glaces d’erreur moyenne ne signifie ni 93 % de fiabilité, ni une garantie de ±7.</b>')
section('La décision métier')
para('Dans l’étape 7 du notebook : température <b>24</b>, week-end <b>1</b>, promotion <b>1</b>. La prévision vaut <b>217 glaces</b>. Le « demain » de cette histoire est le samedi 1 août 2026 ; c’est une date fixe de scénario.')
say('Je dispose maintenant d’une estimation pour préparer la journée, avec une mesure de l’erreur observée sur notre test.')
para('Exécuter aussi l’étape 8 : elle crée <b>resultats/prevision.csv</b> et <b>resultats/qualite.json</b>. Les scores portent sur 42 journées synthétiques, du 18 juin au 29 juillet 2026.','small')
para('L’étape 9 exporte le modèle appris au format <b>ONNX</b> et le range dans <b>modeles/ventes/1/model.onnx</b> grâce à la connexion. L’export vérifie les 42 prévisions avant le partage.','small')

title('ÉTAPE 4 · 4 MINUTES','Automatiser la recette','Dans le projet de répétition, le serveur de pipelines et son stockage sont déjà prêts. Pour un nouveau projet, voir la préparation page 8 avant l’import.')
flow([('1 Préparer','210 journées'),('2 Entraîner','Un modèle'),('3 Évaluer','Une erreur'),('4 Prévoir','Un fichier')])
section('Importer et lancer')
step('1','Ouvrir <b>Develop & train → Pipelines → Pipeline definitions</b> et sélectionner le projet.')
step('2','Choisir <b>Import pipeline</b>. Nom : <b>Prévoir les ventes</b>. Charger le fichier local <b>pipeline_ventes.yaml</b>. Dans la répétition, il est déjà importé.')
step('3','Créer une exécution dans l’expérience <b>Ventes du magasin</b>. Nom : <b>Samedi avec promotion</b>.')
step('4','Paramètres : <b>temperature = 24</b>, <b>weekend = 1</b>, <b>promotion = 1</b>. Lancer avec <b>Create run</b>.')
step('5','Ouvrir le graphe. Attendre <b>Succeeded</b>. Cliquer sur <b>Évaluer</b> puis sur <b>Prévoir</b> pour consulter métriques, sorties et journaux.')
say('Nous avons transformé notre expérimentation en quatre étapes reproductibles. Le système conserve les résultats de chaque exécution.')
section('La preuve à montrer')
para('La dernière étape affiche <b>PRÉVISION : 217 glaces</b>. L’évaluation retrouve une MAE proche de <b>7,0</b>. Le pipeline conserve les données, le modèle et le fichier de prévision dans son stockage.')
para('Le cache est désactivé : les quatre étapes recalculent réellement. Évaluer mesure la qualité sans seuil automatique. Le pipeline ne déploie pas automatiquement le modèle : le déploiement est une étape distincte.','small')

title('ÉTAPE 5 · 3 MINUTES','Mettre le modèle<br/>à disposition','Dans la répétition, Prévision des ventes est déjà déployé sur CPU. Montrer Deployments et son état prêt. Les clics ci-dessous servent à refaire le parcours dans un nouveau projet.')
section('Déployer depuis le stockage partagé')
step('1','Après l’export du notebook : <b>Deployments → Deploy model</b>.')
step('2','<b>Existing connection : Données du magasin</b>. Chemin : <b>modeles/ventes</b>. Type : <b>Predictive model</b>.')
step('3','Nom : <b>Prévision des ventes</b>. Nom de ressource : <b>prevision-des-ventes</b>. Profil CPU : <b>default-profile</b>. Une seule réplique suffit.')
step('4','Format : <b>onnx-1</b>. Serveur : <b>OpenVINO Model Server</b>. La répétition utilise 250 mCPU demandés, 1 CPU maximum, 512 MiB demandés et 1 GiB maximum.')
step('5','Garder un accès interne pour cette démo. Vérifier le récapitulatif, déployer et attendre l’état prêt (<b>Ready / Started</b> selon la vue).')
say('Le modèle est maintenant un service. Une application peut lui envoyer une journée à prévoir et recevoir une réponse, sans refaire l’apprentissage.')
section('Utiliser le modèle')
para('Ouvrir <b>03_utiliser_le_modele.ipynb</b>. Exécuter les cellules : la connexion relit les ventes, puis une requête est envoyée au modèle. Le formulaire permet de changer la météo et la promotion.')
para('Sur cette installation, l’appel interne utilise le port <b>8888</b>, comme le prévoit la note du tutoriel officiel. Le notebook le configure déjà. Aucun endpoint public supplémentaire n’est créé.','small')

title('ÉTAPE 6 · 2 MINUTES','Changer une hypothèse','Dans le formulaire du notebook 03, le magasin hésite à lancer une promotion. Garder la météo et le jour identiques, puis modifier un seul paramètre.')
step('1','Régler la météo à <b>24 °C</b>, garder <b>Week-end</b> et <b>Promotion</b> cochés, puis cliquer <b>Calculer la prévision</b> : <b>217 glaces</b>.')
step('2','Décocher <b>Promotion</b>, recalculer : <b>172 glaces</b>. Le serveur répond sans réentraîner le modèle.')
step('3','Réexécuter la cellule du compteur de requêtes : il augmente. La dernière cellule écrit les deux scénarios dans <b>resultats/comparaison.json</b>, dans le stockage partagé.')
say('La même recette est disponible à la demande. Le magasin change son hypothèse et obtient une nouvelle estimation.')
section('Questions simples et réponses courtes')
para('<b>Pourquoi un modèle ?</b><br/>Pour combiner plusieurs informations au lieu de prévoir la même quantité tous les jours.')
para('<b>Pourquoi garder des données de test ?</b><br/>Pour mesurer l’erreur sur des journées qui n’ont pas servi à apprendre.')
para('<b>Pipeline ou service ?</b><br/>Le pipeline rejoue les étapes de calcul. Le service utilise un modèle déjà appris pour répondre aux demandes.')
para('<b>Est-ce prêt pour un vrai magasin ?</b><br/>Il faudrait de vraies données, contrôler les ruptures de stock et les jours de fermeture, évaluer plusieurs périodes et suivre l’erreur dans le temps.')
section('La dernière phrase')
say('Nous sommes partis d’une question métier, nous avons appris un modèle, puis nous l’avons rendu utilisable par une application.')
para('Le compteur mesure l’activité depuis le dernier démarrage, pas la qualité ni la dérive du modèle. La différence entre scénarios synthétiques ne démontre pas l’effet causal d’une promotion réelle.','small')

title('AVANT DE PRÉSENTER','Préparation et sources','Faire une répétition complète, ouvrir les onglets utiles et garder une exécution réussie à portée de main.')
section('Les éléments préparés')
para('<b>Projet :</b> Ventes du magasin<br/><b>Workbench :</b> Atelier de prévision<br/><b>Connexion :</b> Données du magasin<br/><b>Modèle :</b> Prévision des ventes<br/><b>Notebooks :</b> 01_prevoir_les_ventes.ipynb puis 03_utiliser_le_modele.ipynb')
link('Ouvrir le workbench de répétition','https://ADRESSE-OPENSHIFT-AI/notebook/ventes-du-magasin/atelier-ventes/lab/tree/demo-ventes')
section('Pour un nouveau projet')
para('Préparer hors scène le stockage et le serveur de pipelines du nouveau projet avec le script du kit. Ses valeurs S3 sont écrites dans un fichier privé <b>secrets/&lt;projet&gt;-stockage.txt</b>, hors du ZIP. Utiliser des identifiants propres à chaque projet.')
para('Le fichier <b>LIRE-MOI.md</b> décrit aussi la préparation automatique. Le stockage S4 fourni par le tutoriel Red Hat sert ici de stockage local de démonstration. Le kit reste indépendant de la démo MaaS et du GPU de Llama.','small')
section('Documentation officielle Red Hat 3.5')
base='https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/'
for label,url in [
 ('1. Créer un projet',base+'getting_started_with_red_hat_openshift_ai_self-managed/creating-a-project_get-started'),
 ('2. Créer un workbench et choisir une image',base+'getting_started_with_red_hat_openshift_ai_self-managed/creating-a-workbench-select-ide_get-started'),
 ('3. Utiliser JupyterLab',base+'working_in_your_data_science_ide/working_in_jupyterlab'),
 ('4. Configurer le serveur et importer un pipeline',base+'working_with_ai_pipelines/managing-ai-pipelines_ai-pipelines'),
 ('5. Lancer et gérer les exécutions',base+'working_with_ai_pipelines/managing-pipeline-runs_ai-pipelines'),
 ('6. Consulter les journaux des étapes',base+'working_with_ai_pipelines/working-with-pipeline-logs_ai-pipelines'),
 ('7. Tutoriel officiel et stockage de démonstration',base+'openshift_ai_tutorial_-_fraud_detection_example/t-fdt-setting-up-a-project-and-storage')]:link(label,url)
link('8. Créer et utiliser une connexion',base+'working_on_projects/using-connections_projects')
link('9. Déployer le modèle et tester son API',base+'openshift_ai_tutorial_-_fraud_detection_example/t-fdt-deploying-and-testing-a-model')
para('Consultées le 17 novembre 2026. Parcours préparé sur OpenShift AI 3.5.3 / OpenShift 4.20.46. Le cas « ventes de glaces » et les données sont une adaptation pédagogique originale ; les libellés peuvent varier selon la langue du dashboard.','small')
c.save()
print(OUT)
