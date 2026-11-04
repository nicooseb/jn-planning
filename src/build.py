#!/usr/bin/env python3
"""Construit le planning du samedi à partir de src/data/planning.json.

Sorties (dans build/, non versionné) :
  planning-samedi.html        page écran (corps d'artifact, sans <html>/<head>)
  planning-samedi-print.html  version impression A3 avec polices locales
"""
import json, re
from pathlib import Path

SRC = Path(__file__).resolve().parent
OUT = SRC.parent / 'build'
DATA = json.loads((SRC / 'data' / 'planning.json').read_text(encoding='utf-8'))

LOGO = (SRC / 'assets' / 'logo-jn.svg').read_text()
LOGO = LOGO.replace('<svg ', '<svg class="logo" role="img" aria-label="Logo Jeanne &amp; Nicolas" ', 1)

# ---------- Échelle de temps ----------
def hm(t):
    h, m = map(int, t.split(':'))
    return h * 60 + m

def fmt(mins):
    mins %= 24 * 60
    return f"{mins // 60:02d}:{mins % 60:02d}"

slots = []  # (minute de début, pas en minutes)
t = hm('09:00')
while t < hm('16:00'):
    slots.append((t, 30)); t += 30
while t < hm('24:30'):
    slots.append((t, 15)); t += 15
for s, nxt in [('00:30', '01:00'), ('01:00', '02:00'), ('02:00', '03:00'), ('03:00', '04:00'), ('04:00', '05:00')]:
    v = hm(s) + 24 * 60
    slots.append((v, hm(nxt) + 24 * 60 - v))
END_ROW_TIME = hm('05:00') + 24 * 60  # ligne finale « 05:00 »

def norm(tstr):
    v = hm(tstr)
    return v + 24 * 60 if v < hm('09:00') else v

HEAD_ROWS = 2
def row_of(tstr):
    v = norm(tstr)
    if v == END_ROW_TIME:
        return HEAD_ROWS + len(slots) + 1
    for i, (s, _) in enumerate(slots):
        if s == v:
            return HEAD_ROWS + i + 1
    raise ValueError(f"heure hors grille : {tstr}")

N_BODY = len(slots) + 1

# ---------- Colonnes ----------
COLS = [(c['key'], c['name'], c['role'], c['group']) for c in DATA['columns']]
CI = {k: i + 2 for i, (k, *_) in enumerate(COLS)}  # 1 = colonne des heures
GROUPS = [(g['key'], g['label']) for g in DATA['groups']]
ALIASES = DATA.get('aliases', {})

def span(a, b=None):
    b = b or a
    return CI[a], CI[b] + 1

# ---------- Blocs ----------
# kind : fort · ok · ind (indicatif) · cal (à caler) · slot (créneau libre 15′)
B = []
def add(start, end, a, b, kind, title, detail=''):
    if a in ALIASES:  # un alias se répète dans chacune de ses colonnes
        for k in ALIASES[a]:
            add(start, end, k, None, kind, title, detail)
        return
    B.append(dict(start=start, end=end, cols=span(a, b), kind=kind, title=title, detail=detail))

for blk in DATA['blocks']:
    add(blk['start'], blk['end'], blk['from'], blk['to'], blk['kind'], blk['title'], blk.get('detail', ''))

# ---------- Rendu ----------
def render(font_css):
    out = []
    gh = []
    for g, label in GROUPS:
        cols = [CI[k] for k, *_r in COLS if _r[2] == g]
        gh.append(f'<div class="gh gh-{g}" style="grid-column:{min(cols)}/{max(cols)+1};grid-row:1">{label}</div>')
    gh.insert(0, '<div class="gh gh-time" style="grid-column:1;grid-row:1/3"><span>Heure</span></div>')
    out += gh
    for k, name, role, g in COLS:
        out.append(f'<button type="button" class="ch ch-{g}" data-col="{CI[k]}" id="col-{k}" '
                   f'style="grid-column:{CI[k]};grid-row:2" aria-pressed="false">'
                   f'<span class="ch-name">{name}</span><span class="ch-role">{role}</span></button>')
    for i, (s, step) in enumerate(slots):
        r = HEAD_ROWS + i + 1
        hour = (s % 60 == 0)
        cls = f"t t-{step}" + (" t-hour" if hour else "")
        out.append(f'<div class="{cls}" style="grid-row:{r}"><span>{fmt(s)}</span></div>')
        for c in range(2, len(COLS) + 2):
            out.append(f'<div class="cell c{c}{" cell-hour" if hour else ""} cell-{step}" data-col="{c}" style="grid-row:{r};grid-column:{c}"></div>')
    rl = HEAD_ROWS + len(slots) + 1
    out.append(f'<div class="t t-end t-hour" style="grid-row:{rl}"><span>05:00</span></div>')
    out.append(f'<div class="blk blk-final" style="grid-row:{rl};grid-column:2/{len(COLS)+2}">'
               f'<span class="bt">{DATA["final"]}</span></div>')
    for b in B:
        r0 = row_of(b['start']); r1 = row_of(b['end'])
        c0, c1 = b['cols']
        rows = r1 - r0
        detail = f'<span class="bd">{b["detail"]}</span>' if b['detail'] else ''
        cols_attr = ' '.join(str(c) for c in range(c0, c1))
        out.append(f'<div class="blk k-{b["kind"]} h{min(rows,6)}" data-cols="{cols_attr}" '
                   f'style="grid-row:{r0}/{r1};grid-column:{c0}/{c1}">'
                   f'<span class="bt">{b["title"]}</span>{detail}</div>')
    grid = '\n'.join(out)
    todo = '\n'.join(f'<li><b>{x["topic"]}</b> {x["text"]}</li>' for x in DATA['todo'])
    tpl = (SRC / 'template.html').read_text(encoding='utf-8')
    return (tpl.replace('/*FONTS*/', font_css)
               .replace('<!--LOGO-->', LOGO)
               .replace('<!--NOTE-->', DATA['note'])
               .replace('<!--FOOTER-->', DATA['footer'])
               .replace('<!--GRID-->', grid)
               .replace('<!--TODO-->', todo)
               .replace('__NROWS__', str(N_BODY))
               .replace('__NCOLS__', str(len(COLS)))
               .replace('__ROWS__', 'auto auto ' + ' '.join(f'var(--r{st})' for _, st in slots) + ' var(--r15)'))

FP = SRC / 'node_modules' / '@fontsource'
FACES = [
    ('Cormorant Garamond', 500, 'normal', 'cormorant-garamond/files/cormorant-garamond-latin-500-normal.woff2'),
    ('Cormorant Garamond', 600, 'normal', 'cormorant-garamond/files/cormorant-garamond-latin-600-normal.woff2'),
    ('Cormorant Garamond', 500, 'italic', 'cormorant-garamond/files/cormorant-garamond-latin-500-italic.woff2'),
    ('Jost', 400, 'normal', 'jost/files/jost-latin-400-normal.woff2'),
    ('Jost', 400, 'italic', 'jost/files/jost-latin-400-italic.woff2'),
    ('Jost', 500, 'normal', 'jost/files/jost-latin-500-normal.woff2'),
    ('Jost', 600, 'normal', 'jost/files/jost-latin-600-normal.woff2'),
    ('Pinyon Script', 400, 'normal', 'pinyon-script/files/pinyon-script-latin-400-normal.woff2'),
]
LOCAL = '\n'.join(
    f"@font-face{{font-family:'{f}';font-weight:{w};" + (f"font-style:{st};" if st != 'normal' else '') +
    f"src:url('file://{FP / p}')}}" for f, w, st, p in FACES)

if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    (OUT / 'planning-samedi.html').write_text(render(''), encoding='utf-8')
    pr = re.sub(r'<link[^>]+fonts\.g[^>]+>\n?', '', render(LOCAL))
    head, body = pr.split('<!--BODY-->')
    (OUT / 'planning-samedi-print.html').write_text(
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">' + head +
        '</head><body class="printmode">' + body + '</body></html>', encoding='utf-8')
    print('ok', len(slots), 'lignes', len(B), 'blocs')
