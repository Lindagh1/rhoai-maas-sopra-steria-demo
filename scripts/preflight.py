"""Read-only checks before any cluster mutation."""
import json
import os
import shutil
import subprocess
import sys

def read(*args):
    return json.loads(subprocess.check_output(['oc', 'get', *args, '-o', 'json']))

def main():
    mode = sys.argv[1]
    server = subprocess.check_output(['oc', 'whoami', '--show-server'], text=True).strip()
    if 'sandbox' not in server and os.getenv('ALLOW_NON_SANDBOX') != '1':
        sys.exit('Cluster hors sandbox : définir ALLOW_NON_SANDBOX=1 seulement pour un environnement de démonstration.')
    if subprocess.check_output(['oc', 'auth', 'can-i', '*', '*', '--all-namespaces'], text=True).strip() != 'yes':
        sys.exit('Connexion administrateur du cluster requise pour cette préparation.')
    csvs = read('csv', '-n', 'redhat-ods-operator')['items']
    versions = [v['spec'].get('version', '') for v in csvs if 'rhods-operator' in v['metadata']['name']]
    if not any(v.startswith('3.5.') for v in versions):
        sys.exit(f'RHOAI 3.5.x installé requis ; versions détectées : {versions}. Le script ne met pas à niveau la plateforme.')
    if not read('dsc')['items']:
        sys.exit('DataScienceCluster absent : terminer l’installation OpenShift AI.')
    classes = read('storageclass')['items']
    if not any(c['metadata'].get('annotations', {}).get('storageclass.kubernetes.io/is-default-class') == 'true' for c in classes):
        sys.exit('Une StorageClass par défaut est nécessaire pour les volumes persistants.')
    if mode in ('maas', 'all'):
        for name in ('curl', 'envsubst', 'make'):
            if not shutil.which(name):
                sys.exit(f'Outil MaaS manquant : {name}')
        if not (shutil.which('openssl') or shutil.which('htpasswd')):
            sys.exit('Installer openssl ou htpasswd pour créer le compte de démonstration.')
        # MaaS scripts were validated against the standard sandbox DSC/DSCI names.
        read('dsc', 'default-dsc')
        read('dscinitialization', 'default-dsci')
    print('Prérequis OK : RHOAI 3.5, droits administrateur, stockage persistant.')

if __name__ == '__main__':
    main()
