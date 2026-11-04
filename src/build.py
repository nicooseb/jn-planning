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
MICRO = 2  # colonne « Au micro », visible seulement pendant le zoom
CI = {k: i + 3 for i, (k, *_) in enumerate(COLS)}  # 1 = heures, 2 = Au micro
LAST = len(COLS) + 3  # ligne de fin de grille (exclusive)
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

# ---------- Cérémonie (zoom) ----------
CER = DATA['ceremonie']
CER_START = CER['start']
CER_MIN = CER['max_min']
CER_END = fmt(hm(CER_START) + CER_MIN)
LEAD = fmt(hm(CER_START) - 15)          # ligne d'amorce (installation, rappel des colonnes)
ZROWS = 2 * CER_MIN                      # une ligne de zoom = 30 s

def row_track(s, st):
    if s == hm(LEAD):
        return 'var(--rlead)'
    if hm(CER_START) <= s < hm(CER_END):
        return 'var(--rcer)'
    return f'var(--r{st})'

def mmss(sec):
    m, s_ = divmod(int(sec), 60)
    return f"{m}′{s_:02d}" if s_ else f"{m}′"

def hms(sec_from_start):
    t = hm(CER_START) * 60 + int(sec_from_start)
    h, r = divmod(t, 3600); m, s_ = divmod(r, 60)
    return f"{h:02d}:{m:02d}" + (f":{s_:02d}" if s_ else '')

def timeline():
    """Place chaque séquence. Les durées inconnues se partagent le temps restant, sans heure affichée."""
    seqs = CER['sequences']
    known = sum(s['duration'] for s in seqs if s['duration'])
    unknown = [s for s in seqs if not s['duration']]
    share = max(120, (CER_MIN * 60 - known) / len(unknown)) if unknown else 0
    t, exact, out = 0, True, []
    for s in seqs:
        d = s['duration'] or share
        out.append(dict(seq=s, start=t, dur=d, timed=exact and bool(s['duration'])))
        if not s['duration']:
            exact = False
        t += d
    return out, known, len(unknown)

def lane_cols(lane):
    a, b = lane['from'], lane.get('to') or lane['from']
    a = ALIASES.get(a, [a])[0]; b = ALIASES.get(b, [b])[-1]
    return CI[a], CI[b] + 1

def zrow(sec):
    return 2 + round(sec / 30)

def render_zoom():
    items, known, n_unknown = timeline()
    z = []
    # amorce : rappel des colonnes + installation
    z.append('<div class="zlead-t" style="grid-row:1;grid-column:1"><span>Avant</span></div>')
    z.append(f'<div class="blk zblk k-cal zinst" data-cols="{MICRO}" style="grid-row:1;grid-column:{MICRO}">'
             f'<span class="bt">{CER["installation"]["title"]}</span>'
             f'<span class="bd">{CER["installation"]["detail"]}</span></div>')
    for k, name, role, g in COLS:
        z.append(f'<div class="zname zname-{g}" data-cols="{CI[k]}" style="grid-row:1;grid-column:{CI[k]}">{name}</div>')
    # graduation à la minute, libellé toutes les 5 min
    for m in range(CER_MIN):
        r = zrow(m * 60)
        five = m % 5 == 0
        z.append(f'<div class="ztick{" ztick5" if five else ""}" style="grid-row:{r};grid-column:1/{LAST}"></div>')
        if five:
            z.append(f'<div class="zt" style="grid-row:{r}/span 2;grid-column:1"><span>{hms(m * 60)}</span></div>')
    # séquences
    for it in items:
        s, r0, r1 = it['seq'], zrow(it['start']), zrow(it['start'] + it['dur'])
        r1 = min(r1, 2 + ZROWS)
        when = (f'{hms(it["start"])} → {hms(it["start"] + it["dur"])} · {mmss(it["dur"])}' if it['timed']
                else 'Durée à définir')
        kind = 'k-' + s.get('status', 'cal')
        title = s['title']
        if s.get('speaker'):
            title = f'{title} · {s["speaker"]}'
        detail = '' if s.get('surprise') else (f'<span class="bd">{s["detail"]}</span>' if s.get('detail') else '')
        z.append(f'<div class="blk zblk zmicro {kind}" data-cols="{MICRO}" style="grid-row:{r0}/{r1};grid-column:{MICRO}">'
                 f'<span class="zwhen">{when}</span><span class="bt">{title}</span>{detail}</div>')
        for lane in s.get('lanes', []):
            c0, c1 = lane_cols(lane)
            ld = '' if s.get('surprise') else (f'<span class="bd">{lane["detail"]}</span>' if lane.get('detail') else '')
            music = lane.get('music')
            if music and not s.get('surprise'):
                bits = [x for x in (music.get('title'), music.get('artist'), music.get('mode'), music.get('cue')) if x]
                ld += f'<span class="zmus">{" · ".join(bits)}</span>' if bits else ''
            cols_attr = ' '.join(str(c) for c in range(c0, c1))
            z.append(f'<div class="blk zblk {kind}" data-cols="{cols_attr}" style="grid-row:{r0}/{r1};grid-column:{c0}/{c1}">'
                     f'<span class="bt">{lane["title"]}</span>{ld}</div>')
    r0 = row_of(LEAD); r1 = row_of(CER_END)
    return (f'<div class="cz" id="cz" aria-label="Cérémonie laïque minute par minute" '
            f'style="grid-row:{r0}/{r1};grid-column:1/{LAST};grid-template-rows:var(--rlead) repeat({ZROWS},minmax(0,1fr))" inert>' + '\n'.join(z) + '</div>')

def render_zbar():
    items, known, n_unknown = timeline()
    used = known / 60
    pct = min(100, used / CER_MIN * 100)
    over = used > CER_MIN
    end = hms(sum(i['dur'] for i in items)) if n_unknown == 0 else CER_END
    state = (f'{n_unknown} durée{"s" if n_unknown > 1 else ""} à définir' if n_unknown else
             ('Dépassement' if over else f'Fin {end}'))
    return (f'<div class="zbar{" zover" if over else ""}" id="zbar" role="region" aria-label="Chrono de la cérémonie">'
            f'<div class="zb-title"><span class="zb-k">Cérémonie laïque</span><span class="zb-t">{CER_START} → {CER_END}</span></div>'
            f'<div class="zb-gauge"><div class="zb-lbl"><span>Durées connues <b>{mmss(known)}</b> / {CER_MIN}′</span>'
            f'<span>{state}</span></div><div class="zb-track"><div class="zb-fill" style="width:{pct:.1f}%"></div></div></div>'
            f'<button type="button" class="zb-out" id="zout">Dézoomer</button></div>')

# ---------- Rendu ----------
def render(font_css):
    out = []
    gh = []
    for g, label in GROUPS:
        cols = [CI[k] for k, *_r in COLS if _r[2] == g]
        gh.append(f'<div class="gh gh-{g}" style="grid-column:{min(cols)}/{max(cols)+1};grid-row:1">{label}</div>')
    gh.insert(0, '<div class="gh gh-time" style="grid-column:1;grid-row:1/3"><span>Heure</span></div>')
    gh.insert(1, f'<div class="gh gh-micro" style="grid-column:{MICRO};grid-row:1">Cérémonie</div>')
    gh.append(f'<div class="ch ch-micro" style="grid-column:{MICRO};grid-row:2"><span class="ch-name">Au micro</span><span class="ch-role">Fil de la cérémonie</span></div>')
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
        for c in range(MICRO, LAST):
            cm = ' cm' if c == MICRO else ''
            out.append(f'<div class="cell c{c}{cm}{" cell-hour" if hour else ""} cell-{step}" data-col="{c}" style="grid-row:{r};grid-column:{c}"></div>')
    rl = HEAD_ROWS + len(slots) + 1
    out.append(f'<div class="t t-end t-hour" style="grid-row:{rl}"><span>05:00</span></div>')
    out.append(f'<div class="blk blk-final" style="grid-row:{rl};grid-column:{MICRO}/{LAST}">'
               f'<span class="bt">{DATA["final"]}</span></div>')
    for b in B:
        r0 = row_of(b['start']); r1 = row_of(b['end'])
        c0, c1 = b['cols']
        rows = r1 - r0
        detail = f'<span class="bd">{b["detail"]}</span>' if b['detail'] else ''
        cols_attr = ' '.join(str(c) for c in range(c0, c1))
        cer = b['start'] == CER_START and b['end'] == CER_END
        zattr = (' data-zoom role="button" tabindex="0" aria-controls="cz" '
                 'aria-label="Voir la cérémonie minute par minute"') if cer else ''
        chip = '<span class="zchip">Voir minute par minute</span>' if cer and c1 - c0 > 3 else ''
        out.append(f'<div class="blk k-{b["kind"]} h{min(rows,6)}{" cer" if cer else ""}" data-cols="{cols_attr}"{zattr} '
                   f'style="grid-row:{r0}/{r1};grid-column:{c0}/{c1}">'
                   f'<span class="bt">{b["title"]}</span>{detail}{chip}</div>')
    out.append(render_zoom())
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
               .replace('__ROWS__', 'auto auto ' + ' '.join(row_track(s, st) for s, st in slots) + ' var(--r15)')
               .replace('<!--ZBAR-->', render_zbar()))

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
