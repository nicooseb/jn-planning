# Planning du samedi · J&N

Planning partagé du samedi 26 juin 2027, publié sur https://planning.jeanne-ni.co.
La page publiée (`index.html`) est chiffrée (AES-256-GCM) et ne s'affiche qu'avec le mot de passe.

## Contenu du dépôt

| Fichier | Rôle |
|---|---|
| `index.html` | Page publiée : écran de mot de passe + planning chiffré |
| `src/data.enc` | Données du planning (colonnes, blocs, à trancher), **chiffrées** avec le même mot de passe |
| `src/template.html` | Mise en page et charte (aucune donnée du planning) |
| `src/build.py` | Construit la page écran et la version impression dans `build/` |
| `src/publish.py` | Chiffre la page écran dans `index.html` |
| `src/pdf.py` | Génère le PDF A3 paysage |
| `src/vault.py` | Chiffre / déchiffre `src/data.enc` ⇄ `src/data/planning.json` |

`src/data/` et `build/` ne sont jamais versionnés (voir `.gitignore`), et `_config.yml` exclut `src/` de la publication.

## Reconstruire

```bash
pip install cryptography playwright        # + navigateur Chromium pour le PDF
(cd src && npm install)                    # polices pour le PDF
export PLANNING_PWD='…'                    # mot de passe partagé

python3 src/vault.py unlock    # data.enc -> src/data/planning.json
# … modifier src/data/planning.json …
python3 src/vault.py lock      # src/data/planning.json -> data.enc
python3 src/build.py           # -> build/planning-samedi.html + version impression
python3 src/pdf.py             # -> build/Planning-samedi-26-juin-2027-A3.pdf
python3 src/publish.py         # -> index.html (chiffré)
git add -A && git commit -m "…" && git push
```
