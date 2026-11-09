"""Build the installable Fonte app (PWA) from fonte.html.

Usage: python build_app.py   (needs Pillow: pip install pillow)
Inside the GitHub repo (this file in source/), the app is written to the repo root;
elsewhere it is written to an app/ folder next to this file.
"""
import json, os, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent if ROOT.name == 'source' else ROOT / 'app'
SRC = (ROOT / 'fonte.html').read_text(encoding='utf-8')
VERSION = time.strftime('%Y%m%d%H%M%S')
BG = '#0A0B0F'

# ---------- index.html ----------
body = SRC.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
head_extra = f'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="{BG}">
<meta name="description" content="Carnet de musculation : séances, programmes, records et transformations.">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" sizes="192x192" href="icons/icon-192.png">
<link rel="apple-touch-icon" href="icons/icon-180.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Fonte">
<style>:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0;font-size:14px;overscroll-behavior:none}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
'''
# The page source starts with <title>, links and <style>; everything up to the first <div id="app"> is head material.
split = body.index('<div id="app">')
sw_reg = f'''
<script>
window.FONTE_VERSION = '{VERSION}';
// Offline support: cache the app so it opens without network.
if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {{}}));
// Ask the browser not to evict the workout log when space runs low.
try {{ navigator.storage && navigator.storage.persist && navigator.storage.persist(); }} catch(e) {{}}
// Updates: compare with the published version on launch and whenever the app comes back to the screen.
let lastCheck = 0;
window.fonteCheckUpdate = async (manual) => {{
  if (!manual && Date.now() - lastCheck < 60000) return;
  lastCheck = Date.now();
  try {{
    const r = await fetch('version.json?t=' + Date.now(), {{cache:'no-store'}});
    const v = (await r.json()).version;
    if (v && v !== window.FONTE_VERSION) {{
      if (typeof toast === 'function') toast('Mise à jour en cours…');
      try {{ const reg = await navigator.serviceWorker.getRegistration(); if (reg) await reg.update(); }} catch(e) {{}}
      try {{ sessionStorage.setItem('fonte-updated', v); }} catch(e) {{}}
      setTimeout(() => location.reload(), 600);
    }} else if (manual && typeof toast === 'function') toast('Vous avez la dernière version.');
  }} catch(e) {{ if (manual && typeof toast === 'function') toast('Pas de réseau : impossible de vérifier pour le moment.'); }}
}};
window.addEventListener('load', () => {{
  try {{ if (sessionStorage.getItem('fonte-updated')) {{ sessionStorage.removeItem('fonte-updated'); setTimeout(() => typeof toast === 'function' && toast('Fonte a été mise à jour.'), 400); }} }} catch(e) {{}}
  window.fonteCheckUpdate();
}});
document.addEventListener('visibilitychange', () => {{ if (document.visibilityState === 'visible') window.fonteCheckUpdate(); }});
</script>
'''
index = head_extra + body[:split] + '</head>\n<body>\n' + body[split:] + sw_reg + '</body>\n</html>\n'
OUT.mkdir(exist_ok=True)
(OUT / 'index.html').write_text(index, encoding='utf-8')
(OUT / 'version.json').write_text(json.dumps({'version': VERSION}), encoding='utf-8')

# ---------- manifest ----------
manifest = {
  'name': 'Fonte Musculation', 'short_name': 'Fonte', 'lang': 'fr',
  'description': 'Carnet de musculation : séances, programmes, records et transformations.',
  'start_url': './', 'scope': './', 'display': 'standalone', 'orientation': 'portrait',
  'background_color': BG, 'theme_color': BG,
  'icons': [
    {'src': 'icons/icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
    {'src': 'icons/icon-512.png', 'sizes': '512x512', 'type': 'image/png'},
    {'src': 'icons/maskable-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
  ],
}
(OUT / 'manifest.webmanifest').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

# ---------- service worker ----------
sw = f'''const CACHE = 'fonte-{VERSION}';
const CORE = ['./', './index.html', './manifest.webmanifest', './icons/icon-192.png', './icons/icon-512.png', './icons/icon-180.png'];
self.addEventListener('install', e => {{ e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting())); }});
self.addEventListener('activate', e => {{ e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); }});
self.addEventListener('fetch', e => {{
  const req = e.request; if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // Fonts: cache first, they never change.
  if (url.host.includes('fonts.googleapis.com') || url.host.includes('fonts.gstatic.com')) {{
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {{ const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); return res; }})));
    return;
  }}
  if (url.origin !== location.origin) return;
  // App files: network first (to get updates), cache when offline or slow.
  e.respondWith(new Promise(resolve => {{
    let done = false;
    const fallback = () => caches.match(req, {{ignoreSearch:true}}).then(hit => hit || caches.match('./index.html'));
    const timer = setTimeout(() => fallback().then(r => {{ if (r && !done) {{ done = true; resolve(r); }} }}), 3000);
    fetch(req).then(res => {{
      if (res.ok) {{ const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }}
      if (!done) {{ done = true; clearTimeout(timer); resolve(res); }}
    }}).catch(() => fallback().then(r => {{ if (!done) {{ done = true; clearTimeout(timer); resolve(r || Response.error()); }} }}));
  }}));
}});
'''
(OUT / 'sw.js').write_text(sw, encoding='utf-8')

# ---------- icons: a competition plate with an italic F ----------
def font(size):
    for f in ['C:/Windows/Fonts/arialbi.ttf', 'C:/Windows/Fonts/arialbd.ttf', '/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf']:
        if os.path.exists(f): return ImageFont.truetype(f, size)
    return ImageFont.load_default()

def icon(size, safe=1.0, rounded=True):
    S = size * 4
    img = Image.new('RGBA', (S, S), BG)
    c, R = S / 2, S * .36 * safe
    # soft glow behind the plate, composited so it blends into the dark background
    glow = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    for i in range(30, 0, -1):
        r = R * (1 + i / 30 * .3)
        g.ellipse([c - r, c - r, c + r, c + r], fill=(240, 67, 42, 7))
    img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img)
    # plate: gradient ring from red to orange
    steps = 120
    for k in range(steps):
        t = k / steps
        col = (int(240 + (255 - 240) * t), int(67 + (138 - 67) * t), int(42 + (61 - 42) * t), 255)
        r = R * (1 - t * .25)
        d.ellipse([c - r, c - r, c + r, c + r], fill=col)
    # grooves
    for f in (.86, .72):
        r = R * f; w = max(2, int(S * .008))
        d.ellipse([c - r, c - r, c + r, c + r], outline=(10, 11, 15, 90), width=w)
    r = R * .58
    d.ellipse([c - r, c - r, c + r, c + r], fill=(20, 22, 29, 255))
    fnt = font(int(R * .95))
    tb = d.textbbox((0, 0), 'F', font=fnt)
    d.text((c - (tb[0] + tb[2]) / 2, c - (tb[1] + tb[3]) / 2), 'F', font=fnt, fill=(255, 255, 255, 255))
    if rounded:
        mask = Image.new('L', (S, S), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * .22), fill=255)
        img.putalpha(mask)
    return img.resize((size, size), Image.LANCZOS)

(OUT / 'icons').mkdir(exist_ok=True)
icon(192).save(OUT / 'icons/icon-192.png')
icon(512).save(OUT / 'icons/icon-512.png')
icon(180, rounded=False).save(OUT / 'icons/icon-180.png')
icon(512, safe=.78, rounded=False).save(OUT / 'icons/maskable-512.png')
(OUT / '.nojekyll').write_text('')
print('App built in', OUT, 'version', VERSION)
