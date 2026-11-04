#!/usr/bin/env python3
"""Coffre des données du planning.

  PLANNING_PWD=... python3 src/vault.py lock     data/planning.json -> data.enc
  PLANNING_PWD=... python3 src/vault.py unlock   data.enc -> data/planning.json

Chiffrement AES-256-GCM, clé dérivée du mot de passe (PBKDF2-SHA256, 600 000 itérations).
Le JSON en clair (src/data/) n'est jamais versionné.
"""
import os, sys, json, base64
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

SRC = Path(__file__).resolve().parent
PLAIN = SRC / 'data' / 'planning.json'
VAULT = SRC / 'data.enc'
ITER = 600_000

def key(pwd, salt, n=ITER):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=n).derive(pwd.encode('utf-8'))

def lock(pwd):
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(key(pwd, salt)).encrypt(iv, PLAIN.read_bytes(), None)
    env = {'v': 1, 'kdf': 'pbkdf2-sha256', 'n': ITER, 's': base64.b64encode(salt).decode(),
           'i': base64.b64encode(iv).decode(), 'c': base64.b64encode(ct).decode()}
    VAULT.write_text(json.dumps(env) + '\n')
    print('chiffré ->', VAULT.relative_to(SRC.parent))

def unlock(pwd):
    env = json.loads(VAULT.read_text())
    b = lambda k: base64.b64decode(env[k])
    plain = AESGCM(key(pwd, b('s'), env['n'])).decrypt(b('i'), b('c'), None)
    PLAIN.parent.mkdir(exist_ok=True)
    PLAIN.write_bytes(plain)
    print('déchiffré ->', PLAIN.relative_to(SRC.parent))

if __name__ == '__main__':
    pwd = os.environ.get('PLANNING_PWD')
    if not pwd or len(sys.argv) != 2 or sys.argv[1] not in ('lock', 'unlock'):
        sys.exit("Usage : PLANNING_PWD=... python3 src/vault.py lock|unlock")
    {'lock': lock, 'unlock': unlock}[sys.argv[1]](pwd)
