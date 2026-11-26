"""Merge only the declared fields; preserve fields injected by RHOAI webhooks.

Named Kubernetes lists are merged by name. Non-named lists are replaced only
when the desired entries are missing. This deliberately doesn't prune fields.
"""
from copy import deepcopy
import json
import subprocess

def merge_owned(live, desired):
    if isinstance(desired, dict):
        result = deepcopy(live) if isinstance(live, dict) else {}
        for key, value in desired.items():
            result[key] = merge_owned(result.get(key), value)
        return result
    if isinstance(desired, list):
        if not desired:
            return []
        if all(isinstance(x, dict) and 'name' in x for x in desired):
            result = deepcopy(live) if isinstance(live, list) else []
            for item in desired:
                index = next((i for i, x in enumerate(result) if isinstance(x, dict) and x.get('name') == item['name']), None)
                if index is None:
                    result.append(deepcopy(item))
                else:
                    result[index] = merge_owned(result[index], item)
            return result
        if isinstance(live, list) and all(x in live for x in desired):
            return deepcopy(live)
    return deepcopy(desired)

def oc(*args, data=None):
    result = subprocess.run(['oc', *args], input=data, text=True, capture_output=True)
    if result.returncode:
        # Do not include the request body (it can contain credentials).
        raise RuntimeError(f'oc {args[0]} failed: {result.stderr.strip()}')
    return result.stdout

def get(kind, name, ns=None):
    scope = ['-n', ns] if ns else []
    raw = oc('get', kind, name, *scope, '--ignore-not-found', '-o', 'json')
    return json.loads(raw) if raw.strip() else None

def reconcile(desired):
    if desired['kind'] == 'List':
        return any([reconcile(item) for item in desired['items']])
    desired = deepcopy(desired)
    if 'stringData' in desired:
        import base64
        desired['data'] = {k: base64.b64encode(v.encode()).decode() for k, v in desired.pop('stringData').items()}
    meta = desired['metadata']
    kind, name, ns = desired['kind'], meta['name'], meta.get('namespace')
    scope = ['-n', ns] if ns else []
    current = get(kind, name, ns)
    if current is None:
        oc('create', '-f', '-', data=json.dumps(desired))
        print(f'{kind}/{name} créé', flush=True)
        return True
    changed = {}
    for key, value in desired.items():
        merged = merge_owned(current.get(key), value)
        if merged != current.get(key):
            changed[key] = merged
    if changed:
        # Optimistic locking avoids silently overwriting a concurrent UI edit.
        changed.setdefault('metadata', {})['resourceVersion'] = current['metadata']['resourceVersion']
        oc('patch', kind, name, *scope, '--type=merge', '--patch-file=/dev/stdin', data=json.dumps(changed))
        print(f'{kind}/{name} mis à jour', flush=True)
        return True
    print(f'{kind}/{name} inchangé', flush=True)
    return False
