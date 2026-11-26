#!/usr/bin/env python3
"""Créer l'identité de démo uniquement dans le Keycloak local d'une sandbox."""
import base64
import json
import os
import secrets
import urllib.parse
import urllib.request
from demo import ROOT, load_config, get


def main():
    c = load_config(ROOT/'config/demo.json')
    oauth = get('oauth', 'cluster')
    domain = get('ingresses.config.openshift.io', 'cluster')['spec']['domain']
    providers = [x for x in oauth['spec'].get('identityProviders', []) if x['type'] == 'OpenID']
    if len(providers) != 1 or 'sandbox' not in domain:
        raise RuntimeError('Réservé à une sandbox avec un seul IdP OpenID local ; gérer les autres identités dans leur IdP.')
    issuer = providers[0]['openID']['issuer']
    parts = urllib.parse.urlsplit(issuer)
    if parts.scheme != 'https' or not parts.hostname.endswith('.'+domain) or '/realms/' not in parts.path:
        raise RuntimeError('IdP externe : aucune modification autorisée par cet outil.')
    route = get('route', 'keycloak', 'keycloak')
    if not route or route['spec']['host'] != parts.hostname:
        raise RuntimeError('La route Keycloak locale ne correspond pas à l’issuer OAuth.')
    realm = parts.path.split('/realms/', 1)[1]
    if not realm or '/' in realm: raise RuntimeError('Issuer inattendu')
    origin = 'https://'+parts.netloc
    credentials = get('secret', 'keycloak-initial-admin', 'keycloak')['data']
    form = urllib.parse.urlencode({'client_id': 'admin-cli', 'grant_type': 'password',
             'username': base64.b64decode(credentials['username']).decode(),
             'password': base64.b64decode(credentials['password']).decode()}).encode()
    req = urllib.request.Request(origin+'/realms/master/protocol/openid-connect/token', data=form)
    with urllib.request.urlopen(req, timeout=30) as r: token = json.load(r)['access_token']
    def call(path, body=None, method=None):
        req = urllib.request.Request(origin+'/admin/realms/'+realm+path,
                    data=json.dumps(body).encode() if body is not None else None,
                    headers={'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'}, method=method)
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read(); return json.loads(raw) if raw else None
    clients = call('/clients')
    builtin = {'account','account-console','admin-cli','broker','realm-management','security-admin-console'}
    custom = [x for x in clients if x['clientId'] not in builtin]
    if len(custom) != 1 or custom[0]['clientId'] != providers[0]['openID']['clientID']:
        raise RuntimeError('Ce realm ne semble pas réservé à l’OAuth de ce cluster.')
    query = '/users?'+urllib.parse.urlencode({'username': c['user'], 'exact': 'true'})
    if call(query):
        print('Identité existante conservée ; aucun mot de passe réinitialisé.')
        return
    password = secrets.token_urlsafe(24)
    target = ROOT/'secrets'/('sopra-user.password')
    target.parent.mkdir(mode=0o700, exist_ok=True)
    # Persist first: a lost API response must not make the new password unrecoverable.
    with os.fdopen(os.open(target, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600), 'w') as f: f.write(password)
    # Password included in creation so a partial reset cannot leave a blank account.
    call('/users', {'username': c['user'], 'enabled': True, 'firstName': 'Sopra', 'lastName': 'Démo',
                  'email': c['user']+'@demo.example.com', 'emailVerified': True, 'requiredActions': [],
                  'credentials': [{'type': 'password', 'value': password, 'temporary': False}]})
    print('Utilisateur créé sans rôle administrateur. Mot de passe : secrets/sopra-user.password (local uniquement).')


if __name__ == '__main__': main()
