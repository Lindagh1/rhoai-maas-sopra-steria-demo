#!/usr/bin/env python3
"""Recette API avec identités ServiceAccount limitées ; ne valide pas l'UI OAuth."""
import argparse
import json
from pathlib import Path
import subprocess
import time
from client import request
from demo import ROOT, get, load_config, oc


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', default=str(ROOT/'config/demo.json'))
    p.add_argument('--url', required=True)
    a = p.parse_args(); c = load_config(a.config)
    result = {'date': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'identity_type': 'ServiceAccount (non-admin)', 'checks': []}
    keys = []
    def record(name, passed, **detail):
        result['checks'].append({'name': name, 'passed': bool(passed), **detail})
        print(name, 'OK' if passed else 'ÉCHEC', flush=True)
    def token(sa):
        return oc('create', 'token', sa, '-n', c['model_namespace'], '--duration=1h')
    def mint(t, subscription=None):
        body = {'name': 'sopra-recette-'+str(time.time_ns()), 'expiresIn': '1h'}
        if subscription: body['subscription'] = subscription
        code, data, _ = request(a.url, t, '/maas-api/v1/api-keys', body)
        if code == 201 and data.get('key') and data.get('id'):
            keys.append((t, data['id']))
        return code, data
    try:
        principal = f"system:serviceaccount:{c['model_namespace']}:consumer"
        check = subprocess.run(['oc', 'auth', 'can-i', '*', '*', '--all-namespaces', '--as='+principal], text=True, capture_output=True)
        record('identité sans administration', check.returncode == 1 and check.stdout.strip() == 'no')
        t = token('consumer')
        code, key = mint(t, 'sopra-standard')
        record('création clé avec expiration et subscription', code == 201 and key.get('subscription') == 'sopra-standard' and bool(key.get('expiresAt')), http=code)
        if code != 201: raise RuntimeError(f'Création refusée : HTTP {code} {key}')
        code, catalog, _ = request(a.url, key['key'], '/v1/models')
        ids = [x['id'] for x in catalog.get('data', [])]
        expected = get('maasmodelref', c['model_name'], c['model_namespace'])['status']['resolvedModelAlias']
        record('catalogue limité au modèle autorisé', code == 200 and ids == [expected], http=code, models=ids)
        payload = {'model': expected, 'messages': [{'role': 'user', 'content': 'Explique en français à quoi sert une API, en une phrase.'}], 'max_tokens': 48, 'temperature': 0}
        code, body, headers = request(a.url, key['key'], '/v1/chat/completions', payload)
        answer = body.get('choices', [{}])[0].get('message', {}).get('content')
        record('inférence réelle', code == 200 and answer and body.get('usage', {}).get('total_tokens', 0) > 0,
               http=code, answer=answer, usage=body.get('usage'), headers=headers)
        code, _, _ = request(a.url, '', '/v1/chat/completions', payload)
        record('absence de clé refusée', code in (401, 403), http=code)
        code, low = mint(t, 'sopra-low')
        record('clé dédiée au petit quota', code == 201, http=code)
        if code == 201:
            codes = []
            for _ in range(5):
                status, _, _ = request(a.url, low['key'], '/v1/chat/completions', payload); codes.append(status)
                if status != 200: break
            record('quota épuisé HTTP 429', 429 in codes, http=codes)
        for sa, subscription in [('auth-only', None), ('quota-only', 'sopra-quota-only'), ('no-access', None)]:
            ts = token(sa); code, data = mint(ts, subscription)
            detail = {'key_creation_http': code}
            if code == 201:
                status, _, _ = request(a.url, data['key'], '/v1/chat/completions', payload)
                detail['inference_http'] = status
                passed = status in (401, 403, 429)
            else:
                passed = code in (400, 403)
                detail['error'] = data
            record('refus '+sa, passed, **detail)
        code, _, _ = request(a.url, t, '/maas-api/v1/api-keys/'+key['id'], method='DELETE')
        record('révocation de sa propre clé', code in (200, 204), http=code)
        end = time.monotonic()+120
        while True:
            code, _, _ = request(a.url, key['key'], '/v1/chat/completions', payload)
            if code in (401, 403) or time.monotonic() >= end: break
            time.sleep(5)
        record('ancienne clé inutilisable', code in (401, 403), http=code)
        code, replacement = mint(t, 'sopra-standard')
        record('nouvelle clé distincte', code == 201 and replacement.get('id') != key['id'], http=code)
        if code == 201:
            code, body, _ = request(a.url, replacement['key'], '/v1/chat/completions', payload)
            record('inférence après rotation', code == 200 and bool(body.get('choices')), http=code)
    finally:
        for t, key_id in keys:
            code, _, _ = request(a.url, t, '/maas-api/v1/api-keys/'+key_id, method='DELETE')
            if code not in (200, 204, 404): record('nettoyage clé de recette', False, http=code)
        out = ROOT/'.state/live-validation.json'; out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    if not all(x['passed'] for x in result['checks']): raise RuntimeError('Recette incomplète : consulter .state/live-validation.json')


if __name__ == '__main__': main()
