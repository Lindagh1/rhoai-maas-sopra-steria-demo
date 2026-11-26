#!/usr/bin/env python3
import getpass
import os
from pathlib import Path

p = Path('secrets/user.apikey')
p.parent.mkdir(mode=0o700, exist_ok=True)
key = getpass.getpass('Coller la clé créée dans le dashboard (saisie masquée) : ').strip()
if not key or '\n' in key or '\r' in key: raise SystemExit('Clé vide ou invalide')
with os.fdopen(os.open(p, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600), 'w') as f: f.write(key)
os.chmod(p, 0o600)
print('Clé enregistrée dans secrets/user.apikey, hors Git.')
