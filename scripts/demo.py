#!/usr/bin/env python3
"""Préparer et vérifier les seules ressources de la démonstration Sopra."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import yaml

ROOT = Path(__file__).resolve().parents[1]
MANAGER = 'sopra-maas-demo'


def oc(*args, body=None):
    p = subprocess.run(['oc', '--request-timeout=30s', *args], input=body,
                       capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f'oc {args[0]} : {p.stderr.strip()}')
    return p.stdout.strip()


def get(kind, name, namespace=None):
    scope = ['-n', namespace] if namespace else []
    raw = oc('get', kind, name, *scope, '--ignore-not-found', '-o', 'json')
    return json.loads(raw) if raw else None


def load_config(path):
    c = json.loads(Path(path).read_text())
    for field in ('model_namespace', 'tenant_namespace', 'aitenant', 'gateway_namespace', 'gateway_name', 'model_name', 'group'):
        if not re.fullmatch(r'[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?', c[field]):
            raise ValueError(f'Nom Kubernetes invalide : {field}')
    if c['model_namespace'] == c['tenant_namespace']:
        raise ValueError('Séparer le namespace du modèle du namespace de gouvernance.')
    for k in ('token_limit', 'low_token_limit'):
        if type(c[k]) is not int or c[k] < 1:
            raise ValueError(f'{k} doit être un entier positif')
    if not c['user'] or not re.fullmatch(r'[1-9][0-9]*[smhd]', c['window']):
        raise ValueError('Identité ou fenêtre de quota invalide')
    return c


def resource(kind, name, ns=None, spec=None, api='maas.opendatahub.io/v1alpha1'):
    m = {'name': name, 'labels': {'app.kubernetes.io/managed-by': MANAGER}}
    if ns:
        m['namespace'] = ns
    obj = {'apiVersion': api, 'kind': kind, 'metadata': m}
    if spec is not None:
        obj['spec'] = spec
    return obj


def manifests(c):
    ns, tenant, name = c['model_namespace'], c['tenant_namespace'], c['model_name']
    namespace = resource('Namespace', ns, api='v1')
    namespace['metadata']['labels'].update({'opendatahub.io/dashboard': 'true', 'maas.opendatahub.io/gateway-access': 'true'})
    group = resource('Group', c['group'], api='user.openshift.io/v1')
    group['users'] = [c['user']]
    llm = yaml.safe_load((ROOT/'manifests/native/llm.yaml').read_text())
    llm['metadata']['name'], llm['metadata']['namespace'] = name, ns
    llm['spec']['model'] = {'name': c['served_model'], 'uri': c['model_uri']}
    llm['spec']['router']['gateway']['refs'] = [{'name': c['gateway_name'], 'namespace': c['gateway_namespace']}]
    ref = {'name': name, 'namespace': ns}
    refs = [ref]
    principal = lambda sa: f'system:serviceaccount:{ns}:{sa}'
    subjects = {'groups': [{'name': c['group']}], 'users': [principal('consumer')]}
    docs = [namespace, group]
    docs += [resource('ServiceAccount', sa, ns, api='v1') for sa in ('consumer', 'auth-only', 'quota-only', 'no-access')]
    docs += [llm, resource('MaaSModelRef', name, ns, {'modelRef': {'kind': 'LLMInferenceService', 'name': name}})]
    docs += [resource('MaaSAuthPolicy', 'sopra-access', tenant, {'subjects': subjects, 'modelRefs': refs})]
    for sub, limit, priority in [('sopra-standard', c['token_limit'], 10), ('sopra-low', c['low_token_limit'], 1)]:
        docs += [resource('MaaSSubscription', sub, tenant, {'owner': subjects, 'priority': priority,
                 'modelRefs': [dict(ref, tokenRateLimits=[{'limit': limit, 'window': c['window']}])]})]
    docs += [resource('MaaSAuthPolicy', 'sopra-auth-only', tenant,
                      {'subjects': {'users': [principal('auth-only')]}, 'modelRefs': refs})]
    docs += [resource('MaaSSubscription', 'sopra-quota-only', tenant,
                      {'owner': {'users': [principal('quota-only')]}, 'modelRefs': [dict(ref, tokenRateLimits=[{'limit': 2000, 'window': '1m'}])]})]
    binding = resource('RoleBinding', 'sopra-model-view', ns, api='rbac.authorization.k8s.io/v1')
    binding.update({'subjects': [{'kind': 'Group', 'name': c['group'], 'apiGroup': 'rbac.authorization.k8s.io'}],
                    'roleRef': {'kind': 'ClusterRole', 'name': 'view', 'apiGroup': 'rbac.authorization.k8s.io'}})
    docs.append(binding)
    return docs


def check(c):
    print('Cluster :', oc('whoami', '--show-server'))
    versions = json.loads(oc('get', 'csv', '-n', 'redhat-ods-operator', '-o', 'json'))['items']
    versions = [o['spec']['version'] for o in versions if o['metadata']['name'].startswith('rhods-operator.')]
    if not any(v.startswith('3.5.') for v in versions):
        raise RuntimeError(f'RHOAI 3.5.x requis ; trouvé : {versions}')
    print('RHOAI :', ', '.join(versions))
    for crd in ('llminferenceservices.serving.kserve.io', 'maasmodelrefs.maas.opendatahub.io', 'maasauthpolicies.maas.opendatahub.io', 'maassubscriptions.maas.opendatahub.io', 'aitenants.maas.opendatahub.io'):
        if not get('crd', crd):
            raise RuntimeError(f'CRD absente : {crd}. Préparer la plateforme avant la démo.')
    tenant = get('aitenant', c['aitenant'], 'ai-tenants')
    if not tenant or tenant.get('status', {}).get('phase') != 'Active':
        raise RuntimeError('AITenant absent ou non Active ; consulter docs/INSTALLATION.md')
    s = tenant['status']
    if s.get('tenantNamespace') != c['tenant_namespace'] or s.get('gatewayRef') != {'name': c['gateway_name'], 'namespace': c['gateway_namespace']}:
        raise RuntimeError('Le tenant, son namespace et sa gateway ne correspondent pas à config/demo.json')
    gw = get('gateway', c['gateway_name'], c['gateway_namespace'])
    if not gw or not any(x['type'] == 'Programmed' and x['status'] == 'True' for x in gw.get('status', {}).get('conditions', [])):
        raise RuntimeError('Gateway non programmée')
    print('Tenant et gateway actifs. GPU, DNS/TLS et téléchargements restent à vérifier au déploiement.')


def assert_owned(obj):
    m = obj['metadata']
    current = get(obj['kind'], m['name'], m.get('namespace'))
    if current and current['metadata'].get('labels', {}).get('app.kubernetes.io/managed-by') != MANAGER:
        raise RuntimeError(f"Collision : {obj['kind']}/{m['name']} existe hors de ce kit ; choisir un autre nom.")


def apply(c, dry=False):
    check(c)
    docs = manifests(c)
    # Detect collisions for every existing object before the first mutation.
    for obj in docs:
        assert_owned(obj)
    if dry and not get('namespace', c['model_namespace']):
        raise RuntimeError('Namespace absent : render reste possible ; plan serveur requiert un namespace existant. apply le crée après validation de son manifeste.')
    for obj in docs:
        payload = yaml.safe_dump(obj, sort_keys=False, allow_unicode=True)
        base = ['apply', '--server-side', '--field-manager='+MANAGER, '-f', '-']
        oc(*base, '--dry-run=server', body=payload)
        if not dry:
            print(oc(*base, body=payload))
    if not dry:
        wait_ready(c)


def wait_ready(c, timeout=900):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        llm = get('llminferenceservice', c['model_name'], c['model_namespace'])
        ref = get('maasmodelref', c['model_name'], c['model_namespace'])
        s = (llm or {}).get('status', {})
        gen = (llm or {}).get('metadata', {}).get('generation')
        ready = any(x['type'] == 'Ready' and x['status'] == 'True' for x in s.get('conditions', []))
        if ready and s.get('observedGeneration') == gen and (ref or {}).get('status', {}).get('phase') == 'Ready':
            print('LLM natif et publication MaaS prêts. Valider ensuite une vraie réponse avec scripts/client.py.')
            return
        print('Attente du modèle et de sa publication...', flush=True)
        time.sleep(10)
    raise RuntimeError('Délai dépassé : inspecter pods/events. La configuration reste rejouable.')


def snapshot(c):
    records = []
    for obj in manifests(c):
        m = obj['metadata']; live = get(obj['kind'], m['name'], m.get('namespace'))
        if not live:
            raise RuntimeError(f"Ressource absente : {obj['kind']}/{m['name']}")
        content = {k: v for k, v in live.items() if k not in ('metadata', 'status')}
        records.append({'kind': obj['kind'], 'namespace': m.get('namespace'), 'name': m['name'],
                        'uid': live['metadata']['uid'], 'generation': live['metadata'].get('generation'),
                        'content_sha256': hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()})
    pods = json.loads(oc('get', 'pods', '-n', c['model_namespace'], '-o', 'json'))['items']
    return {'resources': records, 'pods': sorted(p['metadata']['uid'] for p in pods)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['render', 'check', 'plan', 'apply', 'status', 'snapshot', 'verify-idempotence'])
    p.add_argument('--config', default=str(ROOT/'config/demo.json'))
    p.add_argument('--output', default=str(ROOT/'.state/rendered.yaml'))
    a = p.parse_args(); c = load_config(a.config)
    if a.action == 'render':
        out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml.safe_dump_all(manifests(c), sort_keys=False, allow_unicode=True))
        print(out)
    elif a.action == 'check': check(c)
    elif a.action in ('apply', 'plan'): apply(c, dry=a.action == 'plan')
    elif a.action == 'status':
        print(oc('get', 'llminferenceservice,maasmodelref,pods', '-n', c['model_namespace']))
        print(oc('get', 'maassubscription,maasauthpolicy', '-n', c['tenant_namespace'], '-l', 'app.kubernetes.io/managed-by='+MANAGER))
    elif a.action == 'snapshot': print(json.dumps(snapshot(c), indent=2))
    else:
        before = snapshot(c); apply(c); after = snapshot(c)
        out = ROOT/'.state/idempotence.json'; out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({'unchanged': before == after, 'before': before, 'after': after}, indent=2))
        if before != after: raise RuntimeError(f'Etat modifié à la relance : consulter {out}')
        print('Idempotence vérifiée : mêmes UID, générations, contenus et pods.')


if __name__ == '__main__':
    try: main()
    except (RuntimeError, ValueError, OSError) as e:
        print(str(e), file=sys.stderr); sys.exit(1)
