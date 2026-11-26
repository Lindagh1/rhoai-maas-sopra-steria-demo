"""Install the sales demo without duplicate pipelines, credential rotation or idle restarts."""
import argparse
import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time

import boto3
import kfp
from botocore.config import Config
from botocore.exceptions import ClientError
from reconcile import get, oc, reconcile

ROOT = Path(__file__).resolve().parents[1]
STATE_NAME = 'demo-installation'


def digest(value):
    return hashlib.sha256(value).hexdigest()


def wait_for(check, message, seconds=600):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return
        time.sleep(5)
    raise RuntimeError(message)


def ready(kind, name, ns):
    obj = get(kind, name, ns)
    if not obj:
        return False
    status = obj.get('status', {})
    generation = obj['metadata'].get('generation', 0)
    if status.get('observedGeneration', generation) < generation:
        return False
    return any(c['type'] == 'Ready' and c['status'] == 'True' for c in status.get('conditions', []))


@contextmanager
def storage(ns, credentials):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    forward = subprocess.Popen(['oc', 'port-forward', '-n', ns, 'svc/s4', f'{port}:7480'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        client = boto3.client('s3', endpoint_url=f'http://127.0.0.1:{port}', region_name='us-east-1',
                              aws_access_key_id=credentials['AWS_ACCESS_KEY_ID'],
                              aws_secret_access_key=credentials['AWS_SECRET_ACCESS_KEY'],
                              config=Config(connect_timeout=3, read_timeout=10, retries={'max_attempts': 1}))
        def available():
            if forward.poll() is not None:
                raise RuntimeError('Le tunnel vers le stockage est arrêté.')
            try:
                client.list_buckets()
                return True
            except Exception:
                return False
        wait_for(available, 'Stockage S3 indisponible.', 90)
        yield client
    finally:
        forward.terminate()
        forward.wait(timeout=10)


def load_manifest(name, ns):
    return json.loads((ROOT / 'manifests' / name).read_text().replace('ventes-demo-repetition', ns))


def sync_files(ns, files):
    """Only update changed source files, backing up previous user work on upgrades."""
    payload = {name: base64.b64encode(content).decode() for name, content in files.items()}
    script = '''import base64,hashlib,json,pathlib,sys
root=pathlib.Path('/opt/app-root/src/demo-ventes'); root.mkdir(exist_ok=True)
statefile=root/'.installation.json'
old=json.loads(statefile.read_text()) if statefile.exists() else {}
new={}
for name,encoded in json.load(sys.stdin).items():
 content=base64.b64decode(encoded); sha=hashlib.sha256(content).hexdigest(); p=root/name
 if old.get(name)!=sha or not p.exists():
  if p.exists() and p.read_bytes()!=content:
   backup=p.with_name(p.name+'.sauvegarde-'+hashlib.sha256(p.read_bytes()).hexdigest()[:12])
   if not backup.exists(): backup.write_bytes(p.read_bytes())
  p.write_bytes(content)
  print('Fichier préparé : '+name)
 new[name]=sha
if new!=old: statefile.write_text(json.dumps(new))
'''
    print(oc('exec', '-i', '-n', ns, 'atelier-ventes-0', '-c', 'atelier-ventes', '--',
             'python', '-c', script, data=json.dumps(payload)).strip(), flush=True)


def all_pages(method, field, **kwargs):
    token = None
    while True:
        response = method(page_size=100, page_token=token, **kwargs)
        yield from getattr(response, field) or []
        token = response.next_page_token
        if not token:
            break


def ensure_pipeline(ns, package, example_runs):
    host = get('route', 'ds-pipeline-dspa', ns)['spec']['host']
    # Token stays in memory; never in a URL, command argument or state file.
    client = kfp.Client(host='https://' + host, namespace=ns, existing_token=oc('whoami', '-t').strip())
    name = 'Prévoir les ventes'
    pipeline = next((p for p in all_pages(client.list_pipelines, 'pipelines') if p.display_name == name), None)
    sha = digest(package.read_bytes())[:16]
    version_name = 'demo-' + sha
    if pipeline is None:
        pipeline = client.upload_pipeline(str(package), pipeline_name=name)
    versions = list(all_pages(client.list_pipeline_versions, 'pipeline_versions', pipeline_id=pipeline.pipeline_id))
    version = next((v for v in versions if v.display_name == version_name), None)
    if version is None:
        version = client.upload_pipeline_version(str(package), pipeline_version_name=version_name,
                                                 pipeline_id=pipeline.pipeline_id)
        print('Version du pipeline importée : ' + version_name, flush=True)
    experiment = next((e for e in all_pages(client.list_experiments, 'experiments') if e.display_name == 'Ventes du magasin'), None)
    if experiment is None:
        experiment = client.create_experiment('Ventes du magasin', namespace=ns)
    runs = []
    if example_runs:
        existing = list(all_pages(client.list_runs, 'runs', experiment_id=experiment.experiment_id))
        for promo, label in [(1, '01 - Samedi avec promotion'), (0, '02 - Samedi sans promotion')]:
            run_name = label + ' [' + sha[:8] + ']'
            run = next((r for r in existing if r.display_name == run_name), None)
            if run is None:
                run = client.run_pipeline(experiment.experiment_id, run_name, pipeline_id=pipeline.pipeline_id,
                                          version_id=version.pipeline_version_id,
                                          params={'temperature': 24.0, 'weekend': 1, 'promotion': promo})
            print('Vérification de l’exécution : ' + label, flush=True)
            result = client.wait_for_run_completion(run.run_id, timeout=600, sleep_duration=5)
            if result.state != 'SUCCEEDED':
                raise RuntimeError(f'Exécution {run.run_id} : {result.state}. Examiner les logs ; aucune nouvelle exécution créée automatiquement.')
            runs.append(run.run_id)
    return {'pipeline_id': pipeline.pipeline_id, 'version_id': version.pipeline_version_id,
            'experiment_id': experiment.experiment_id, 'example_run_ids': runs}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', default='ventes-du-magasin')
    p.add_argument('--pipelines-only', action='store_true')
    p.add_argument('--deploy-model', action='store_true')
    p.add_argument('--example-runs', action='store_true')
    args = p.parse_args()
    ns = args.project
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,28}[a-z0-9]', ns):
        p.error('Nom de projet : 2 à 30 lettres minuscules, chiffres ou tirets.')
    if args.pipelines_only and args.deploy_model:
        p.error('--deploy-model nécessite le workbench.')
    os.umask(0o077)
    subprocess.run(['python3', str(ROOT.parent/'scripts/preflight.py'), 'ventes'], check=True)
    dsc = json.loads(oc('get', 'dsc', '-o', 'json'))['items'][0]
    components = {k: {'managementState': 'Managed'} for k in ['workbenches', 'aipipelines', 'kserve']}
    reconcile({'apiVersion': dsc['apiVersion'], 'kind': dsc['kind'], 'metadata': {'name': dsc['metadata']['name']},
               'spec': {'components': components}})
    wait_for(lambda: get('imagestream', 's2i-generic-data-science-notebook', 'redhat-ods-applications') is not None,
             'Image du workbench indisponible.')
    image_stream = get('imagestream', 's2i-generic-data-science-notebook', 'redhat-ods-applications')
    tag = next(t for t in image_stream['spec']['tags'] if t['name'] == '3.5')
    image = tag['from']['name']
    if not get('hardwareprofile', 'default-profile', 'redhat-ods-applications'):
        raise RuntimeError('Profil matériel default-profile absent. Créer un profil CPU dans OpenShift AI avant de poursuivre.')
    current = get('namespace', ns)
    if current and current['metadata'].get('labels', {}).get('app.kubernetes.io/part-of') != 'ventes-demo':
        raise RuntimeError('Ce projet existe hors de cette démo ; choisir un autre nom avec --project.')
    reconcile(load_manifest('namespace.json', ns))
    state = (get('configmap', STATE_NAME, ns) or {}).get('data', {})
    def save_state():
        reconcile({'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': STATE_NAME, 'namespace': ns}, 'data': state})
    if get('secret', 's4-credentials', ns) is None:
        import secrets
        reconcile({'apiVersion': 'v1', 'kind': 'Secret', 'metadata': {'name': 's4-credentials', 'namespace': ns},
                   'stringData': {'UI_USERNAME': 'demo', 'UI_PASSWORD': secrets.token_urlsafe(24),
                                  'AWS_ACCESS_KEY_ID': 'ventes-demo', 'AWS_SECRET_ACCESS_KEY': secrets.token_urlsafe(32)}})
    credentials = {k: base64.b64decode(v).decode() for k, v in get('secret', 's4-credentials', ns)['data'].items()}
    # Preserve all other monitoring settings; only add this required switch.
    import yaml
    monitoring = get('configmap', 'cluster-monitoring-config', 'openshift-monitoring')
    config = yaml.safe_load((monitoring or {}).get('data', {}).get('config.yaml', '')) or {}
    if not config.get('enableUserWorkload'):
        config['enableUserWorkload'] = True
        reconcile({'apiVersion': 'v1', 'kind': 'ConfigMap',
                   'metadata': {'name': 'cluster-monitoring-config', 'namespace': 'openshift-monitoring'},
                   'data': {'config.yaml': yaml.safe_dump(config)}})
    reconcile(load_manifest('s3-storage.json', ns))
    print(oc('rollout', 'status', 'deployment/s4', '-n', ns, '--timeout=300s').strip(), flush=True)
    with storage(ns, credentials) as s3:
        if 'ventes-demo' not in [b['Name'] for b in s3.list_buckets()['Buckets']]:
            s3.create_bucket(Bucket='ventes-demo')
    connection = load_manifest('connection-template.json', ns)
    source = connection.pop('dataSource')
    connection['stringData'] = {**source['configuration'], **{k: credentials[k] for k in source['copiedKeys']}}
    reconcile(connection)
    reconcile(load_manifest('pipeline-server.json', ns))
    wait_for(lambda: ready('dspa', 'dspa', ns), 'Le serveur de pipelines ne devient pas prêt.')
    notebook = load_manifest('workbench.json', ns)
    pinned = notebook['spec']['template']['spec']['containers'][0]['image']
    package = (ROOT/'pipeline_ventes.yaml').read_text().replace(pinned, image).encode()
    output = ROOT.parent/'.state'/ns
    output.mkdir(parents=True, exist_ok=True)
    package_path = output/'pipeline_ventes.yaml'
    package_path.write_bytes(package)
    if not args.pipelines_only:
        notebook['spec']['template']['spec']['containers'][0]['image'] = image
        # OpenShift admission resolves the multi-architecture digest to the
        # platform digest from ImageStream status. Both identify this image.
        # Preserve the admitted digest on a rerun to avoid a needless rollout.
        current_notebook = get('notebook', 'atelier-ventes', ns)
        admitted_images = {image}
        for status_tag in image_stream.get('status', {}).get('tags', []):
            if status_tag['tag'] == '3.5' and status_tag.get('items'):
                admitted_images.add(status_tag['items'][0]['dockerImageReference'])
        if current_notebook:
            current_image = current_notebook['spec']['template']['spec']['containers'][0]['image']
            if current_image in admitted_images:
                notebook['spec']['template']['spec']['containers'][0]['image'] = current_image
        notebook['metadata']['annotations']['notebooks.opendatahub.io/last-image-version-git-commit-selection'] = tag['annotations']['opendatahub.io/notebook-build-commit']
        reconcile(load_manifest('workbench-storage.json', ns))
        reconcile(notebook)
        wait_for(lambda: ready('notebook', 'atelier-ventes', ns) and ready('pod', 'atelier-ventes-0', ns), 'Atelier indisponible.')
        # Ensure StatefulSet has observed the Notebook revision before using the pod.
        print(oc('rollout', 'status', 'statefulset/atelier-ventes', '-n', ns, '--timeout=600s').strip(), flush=True)
        files = {n: (ROOT/n).read_bytes() for n in ['01_prevoir_les_ventes.ipynb', '03_utiliser_le_modele.ipynb', 'ventes.csv']}
        files['exporter_modele.py'] = (ROOT/'scripts/exporter_modele.py').read_bytes()
        files['pipeline_ventes.yaml'] = package
        sync_files(ns, files)
        if args.deploy_model:
            source_hash = digest(files['ventes.csv'] + files['exporter_modele.py'] + image.encode())
            model_hash = state.get('model-hash', '')
            present = False
            if model_hash:
                with storage(ns, credentials) as s3:
                    try:
                        s3.head_object(Bucket='ventes-demo', Key=f'modeles/versions/{model_hash}/1/model.onnx')
                        s3.head_object(Bucket='ventes-demo', Key='donnees/ventes.csv')
                        present = True
                    except ClientError as exc:
                        if exc.response['Error']['Code'] not in ('404', 'NoSuchKey'):
                            raise
            if state.get('export-source') != source_hash or not present:
                print(oc('exec', '-n', ns, 'atelier-ventes-0', '-c', 'atelier-ventes', '--',
                         'bash', '-c', 'cd /opt/app-root/src/demo-ventes && python exporter_modele.py').strip(), flush=True)
                with storage(ns, credentials) as s3:
                    content = s3.get_object(Bucket='ventes-demo', Key='modeles/ventes/1/model.onnx')['Body'].read()
                    model_hash = digest(content)
                    target = f'modeles/versions/{model_hash}/1/model.onnx'
                    try:
                        s3.head_object(Bucket='ventes-demo', Key=target)
                    except ClientError as exc:
                        if exc.response['Error']['Code'] not in ('404', 'NoSuchKey'):
                            raise
                        s3.put_object(Bucket='ventes-demo', Key=target, Body=content)
                state.update({'model-hash': model_hash, 'export-source': source_hash})
                save_state()
            runtime = load_manifest('model-runtime.json', ns)
            template = get('template', 'kserve-ovms', 'redhat-ods-applications')
            official = next(o for o in template['objects'] if o['kind'] == 'ServingRuntime')
            runtime['spec']['containers'][0]['image'] = official['spec']['containers'][0]['image']
            reconcile(runtime)
            service = load_manifest('model-service.json', ns)
            service['spec']['predictor']['model']['storage']['path'] = f'modeles/versions/{model_hash}'
            reconcile(service)
            wait_for(lambda: ready('inferenceservice', 'prevision-des-ventes', ns), 'Le modèle ne devient pas prêt.')
            print(oc('rollout', 'status', 'deployment/prevision-des-ventes-predictor', '-n', ns, '--timeout=600s').strip(), flush=True)
            # End-to-end request from the workbench, with the OVMS port explicitly set.
            check = """import requests
u='http://prevision-des-ventes-predictor.NAMESPACE.svc.cluster.local:8888/v2/models/prevision-des-ventes/infer'
r=requests.post(u,json={'inputs':[{'name':'donnees','shape':[2,3],'datatype':'FP32','data':[24,1,1,24,1,0]}]},timeout=30)
r.raise_for_status(); y=r.json()['outputs'][0]['data']; assert [round(v) for v in y]==[217,172],y
print('API vérifiée : 217 glaces avec promotion, 172 sans promotion.')
""".replace('NAMESPACE', ns)
            print(oc('exec', '-n', ns, 'atelier-ventes-0', '-c', 'atelier-ventes', '--', 'python', '-c', check).strip(), flush=True)
    ids = ensure_pipeline(ns, package_path, args.example_runs)
    # Keep existing example IDs when rerunning without --example-runs.
    if not args.example_runs:
        ids['example_run_ids'] = json.loads(state.get('pipelines', '{}')).get('example_run_ids', [])
    state['pipelines'] = json.dumps(ids, sort_keys=True)
    save_state()
    dashboard = get('dashboard', 'default-dashboard')['status']['url'].rstrip('/')
    result = {'project': ns, 'dashboard': dashboard,
              'workbench': f'{dashboard}/notebook/{ns}/atelier-ventes/lab/tree/demo-ventes/01_prevoir_les_ventes.ipynb',
              'application': f'{dashboard}/notebook/{ns}/atelier-ventes/lab/tree/demo-ventes/03_utiliser_le_modele.ipynb', **ids}
    (output/'liens.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print('Démo prête : ' + result['workbench'], flush=True)
    print('Liens et références : ' + str(output/'liens.json'), flush=True)


if __name__ == '__main__':
    main()
