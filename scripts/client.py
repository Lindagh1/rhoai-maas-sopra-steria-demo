#!/usr/bin/env python3
"""Appels MaaS sans oc ni droits administrateur ; clé lue depuis un fichier privé."""
import argparse
import json
import os
from pathlib import Path
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(base, key, path, body=None, method=None):
    u = urlsplit(base)
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError('URL HTTPS sans identifiants, paramètres ou fragment requise')
    if any(x in key for x in '\r\n'):
        raise ValueError('Clé invalide')
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    req = urllib.request.Request(base.rstrip('/')+path, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None, method=method)
    context = ssl.create_default_context(cafile=os.getenv('MAAS_CA_FILE'))
    opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))
    try:
        response = opener.open(req, timeout=120)
    except urllib.error.HTTPError as e:
        response = e
    with response:
        raw = response.read().decode()
        try: data = json.loads(raw)
        except ValueError: data = {'message': raw[:500]}
        # Rate-limit headers may be absent on a particular build.
        limits = {k: v for k, v in response.headers.items() if k.lower().startswith(('x-ratelimit', 'ratelimit', 'retry-after'))}
        return response.status, data, limits


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url', required=True, help='Origine de la gateway, sans /v1')
    p.add_argument('--key-file', required=True)
    p.add_argument('--model', help='ID exact renvoyé par /v1/models ; omission = catalogue seulement')
    p.add_argument('--expect', type=int, default=200)
    a = p.parse_args(); key = Path(a.key_file).read_text().strip()
    if not key: p.error('Fichier de clé vide')
    path, payload = '/v1/models', None
    if a.model:
        path = '/v1/chat/completions'
        payload = {'model': a.model, 'messages': [{'role': 'user', 'content': 'Explique en une phrase ce que fait une API.'}], 'max_tokens': 64, 'temperature': 0}
    code, data, limits = request(a.url, key, path, payload)
    print(json.dumps({'http': code, 'rate_limit_headers': limits, 'response': data}, indent=2, ensure_ascii=False))
    if code != a.expect: return 1
    if a.model and code == 200:
        return 0 if data.get('choices') and data['choices'][0].get('message', {}).get('content') and data.get('usage', {}).get('total_tokens', 0) > 0 else 1
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except (OSError, ValueError) as e: print(str(e), file=sys.stderr); sys.exit(1)
