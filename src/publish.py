#!/usr/bin/env python3
"""Chiffre la page écran (build/planning-samedi.html) dans la page de déverrouillage publiée (index.html).
Usage : PLANNING_PWD=... python3 src/publish.py
AES-256-GCM, clé PBKDF2-SHA256. Le déchiffrement se fait dans le navigateur (WebCrypto).
"""
import os, sys, base64, json
from pathlib import Path
SRC = Path(__file__).resolve().parent
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITER = 600_000
pwd = os.environ['PLANNING_PWD'].encode('utf-8')
out = str(SRC.parent / 'index.html')

body = (SRC.parent / 'build' / 'planning-samedi.html').read_text(encoding='utf-8')
doc = ('<!doctype html><html lang="fr"><head><meta charset="utf-8">'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
       '<meta name="robots" content="noindex, nofollow">'
       '<style>:root{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>'
       '</head><body>' + body + '</body></html>')

salt, iv = os.urandom(16), os.urandom(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(pwd)
ct = AESGCM(key).encrypt(iv, doc.encode('utf-8'), None)
payload = json.dumps({'s': base64.b64encode(salt).decode(), 'i': base64.b64encode(iv).decode(),
                      'n': ITER, 'c': base64.b64encode(ct).decode()})

logo = (SRC / 'assets' / 'logo-jn.svg').read_text().replace('<svg ', '<svg class="logo" aria-hidden="true" ', 1)

page = f'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Planning du samedi · J&amp;N</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500&family=Jost:wght@400;500&family=Pinyon+Script&display=swap">
<style>
:root {{ --ink:#14197A; --ink-soft:#4F5488; --magenta:#DF1C76; --rule:#DCDDEA; --paper:#FFFFFF; color-scheme: light; }}
* {{ box-sizing: border-box; }}
html, body {{ height: 100%; margin: 0; background: var(--paper); color: var(--ink); font-family: 'Jost', 'Avenir Next', 'Segoe UI', sans-serif; }}
main {{ min-height: 100%; display: grid; place-items: center; padding: 24px 16px; }}
form {{ width: 100%; max-width: 360px; display: flex; flex-direction: column; align-items: center; gap: 14px; text-align: center;
        border-top: 1px solid var(--ink); border-bottom: 1px solid var(--ink); padding: 28px 0; }}
.logo {{ width: 84px; height: auto; }}
.kicker {{ font-size: 11px; letter-spacing: .16em; text-transform: uppercase; color: var(--ink-soft); }}
h1 {{ font-family: 'Cormorant Garamond', Garamond, serif; font-weight: 500; font-size: 34px; margin: 0; line-height: 1.05; }}
h1 em {{ font-style: normal; color: var(--magenta); }}
.names {{ font-family: 'Pinyon Script', cursive; color: var(--magenta); font-size: 28px; line-height: 1; }}
label {{ font-size: 13px; color: var(--ink-soft); }}
.row {{ display: flex; gap: 8px; width: 100%; }}
input {{ flex: 1; min-width: 0; font: inherit; font-size: 16px; padding: 10px 12px; border: 1px solid var(--ink); border-radius: 3px; color: var(--ink); background: var(--paper); }}
input:focus-visible, button:focus-visible {{ outline: 2px solid var(--magenta); outline-offset: 2px; }}
button {{ font: inherit; font-weight: 500; padding: 10px 16px; border: 0; border-radius: 3px; background: var(--magenta); color: var(--paper); cursor: pointer; }}
button[disabled] {{ opacity: .6; cursor: progress; }}
.msg {{ min-height: 1.4em; font-size: 13px; color: var(--magenta); margin: 0; }}
</style>
</head>
<body>
<main>
  <form id="f" autocomplete="off">
    {logo}
    <span class="kicker">Planning partagé · Château de Saulon</span>
    <h1>Samedi <em>26 juin 2027</em></h1>
    <span class="names">Jeanne &amp; Nicolas</span>
    <label for="pwd">Mot de passe</label>
    <div class="row">
      <input id="pwd" name="pwd" type="password" required autofocus>
      <button id="go" type="submit">Ouvrir</button>
    </div>
    <p class="msg" id="msg" role="status"></p>
  </form>
</main>
<script>
const P = {payload};
const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
async function unlock(pwd) {{
  const base = await crypto.subtle.importKey('raw', new TextEncoder().encode(pwd), 'PBKDF2', false, ['deriveKey']);
  const key = await crypto.subtle.deriveKey({{name: 'PBKDF2', salt: b64(P.s), iterations: P.n, hash: 'SHA-256'}},
                                            base, {{name: 'AES-GCM', length: 256}}, false, ['decrypt']);
  const plain = await crypto.subtle.decrypt({{name: 'AES-GCM', iv: b64(P.i)}}, key, b64(P.c));
  return new TextDecoder().decode(plain);
}}
function show(html) {{ document.open(); document.write(html); document.close(); }}
const KEY = 'jn-planning-pwd';
(async () => {{
  let saved = null;
  try {{ saved = sessionStorage.getItem(KEY); }} catch (e) {{}}
  if (saved) {{ try {{ show(await unlock(saved)); return; }} catch (e) {{}} }}
}})();
document.getElementById('f').addEventListener('submit', async ev => {{
  ev.preventDefault();
  const btn = document.getElementById('go'), msg = document.getElementById('msg');
  const pwd = document.getElementById('pwd').value;
  btn.disabled = true; msg.textContent = 'Ouverture…';
  try {{
    const html = await unlock(pwd);
    try {{ sessionStorage.setItem(KEY, pwd); }} catch (e) {{}}
    show(html);
  }} catch (e) {{
    btn.disabled = false;
    msg.textContent = 'Mot de passe incorrect. Vérifiez les majuscules et réessayez.';
  }}
}});
</script>
</body>
</html>
'''
open(out, 'w', encoding='utf-8').write(page)
print('écrit', out, len(page), 'octets')
