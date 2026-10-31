# -*- coding: utf-8 -*-
"""
Video vertical 1080x1920 a 30 fps desde un proyecto.json: escenas por tipo, sincronizadas con la
locucion (duraciones.json de voz.py), musica propia (musica.py) y mezcla a -14 LUFS.

  python render.py <proyecto.json> --previews     un cuadro por escena + hoja de contacto
  python render.py <proyecto.json>                video completo

Tipos de escena (cada una con "frase": id del guion; sin locucion, usar "dur" en segundos):
  texto     lineas: [{"t", "tam": gigante|grande|medio|chico, "color": blanco|acento|primario|gris, "en", "espacio"}]
  telefono  captura a PANTALLA COMPLETA (sin marco, sin huecos: es el default) con scroll;
            [titulo: lineas], [pill], [pill_color], [alto_max], [zoom], [foco_x], [desde]/[hasta], [velo].
            Con "marco": true vuelve el telefono con marco sobre el fondo.
  rafaga    items: [{"captura", "etiqueta", "alto_max"}], [pill_final]; tambien a pantalla completa
            salvo "marco": true (en la escena o en el item).
  chips     items: ["texto", ...]
  contador  numero, [prefijo], lineas: ["...", "..."]
  medalla   lineas: [{"t", "color"}]
  cierre    [tagline], [url]
  pantalla  lo mismo que "telefono": captura a pantalla completa. El texto va encima sobre un degradé:
            [titulo: lineas] arriba, [pill] abajo, [zoom] (1.0-2.0) y [foco_x] (0-1) para acercar,
            [desde]/[hasta] (0-1) para recorrer solo una parte del alto, [velo] (0-1) oscurece la captura.
            OJO con "alto_max": va en pixeles de la captura escalada al ANCHO DE PANTALLA (1080), no al del telefono.

Proyecto: "marca": true -> logo fijo arriba en todas las escenas, titulo debajo, telefono mas grande
hasta abajo, pill sobre el borde del telefono y cierre centrado (sin huecos arriba ni abajo).
"alto_max" de telefono/rafaga va en pixeles de la captura ya escalada al ancho del telefono.
"""
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import imageio_ffmpeg

W, H, FPS = 1080, 1920, 30
FF = imageio_ffmpeg.get_ffmpeg_exe()
AQUI = os.path.dirname(os.path.abspath(__file__))

PROYECTO = os.path.abspath(sys.argv[1])
BASE = os.path.dirname(PROYECTO)
P = json.load(open(PROYECTO, encoding='utf-8'))
def ruta(r): return r if os.path.isabs(r) else os.path.join(BASE, r)

def hexrgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
C = {'primario': '#2FA84F', 'acento': '#F7B150', 'oscuro': '#1D6E36'}
C.update(P.get('colores', {}))
COL = {k: hexrgb(v) for k, v in C.items()}
COL.update({'blanco': (255, 255, 255), 'gris': (170, 180, 190), 'negro': (20, 20, 20)})

# ---------- fuente gruesa ----------------------------------------------------------------
CANDIDATAS = [P.get('fuente', ''), r'C:\Windows\Fonts\seguibl.ttf', r'C:\Windows\Fonts\ariblk.ttf',
              r'C:\Windows\Fonts\arialbd.ttf', '/System/Library/Fonts/Supplemental/Arial Black.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
FUENTE = next(f for f in CANDIDATAS if f and os.path.exists(f))
_f = {}
def fuente(tam):
    if tam not in _f: _f[tam] = ImageFont.truetype(FUENTE, tam)
    return _f[tam]
TAM = {'gigante': 150, 'grande': 118, 'medio': 92, 'chico': 62, 'numero': 380}

def suave(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

# ---------- fondo y telefono ---------------------------------------------------------------
def armar_fondo():
    bg = Image.new('RGB', (W, H), (10, 14, 20))
    glow = Image.new('RGB', (W, H), (0, 0, 0)); d = ImageDraw.Draw(glow)
    p, a = COL['primario'], COL['acento']
    d.ellipse((-300, -350, 900, 750), fill=tuple(int(c * 0.45) for c in p))
    d.ellipse((350, 1250, 1450, 2250), fill=tuple(int(c * 0.45) for c in a))
    return Image.blend(bg, glow.filter(ImageFilter.GaussianBlur(220)), 0.55).convert('RGBA')
FONDO = armar_fondo()

# "marca": true en el proyecto: el logo fijo arriba en todas las escenas (mismo lugar y tamano),
# el titulo debajo y un telefono mas grande hasta abajo; el cartel (pill) apoyado sobre el borde
# inferior del telefono y el cierre centrado. Sin "marca", el diseño de siempre.
MARCA = bool(P.get('marca')) and bool(P.get('logo'))
if MARCA:
    PH_W, PH_H, BORDE = 860, 1270, 16
    PH_X, PH_Y = (W - PH_W) // 2, 500
    LOGO_ANCHO, LOGO_Y, TITULO_Y, ETIQ_Y = 560, 64, 205, 225
    PILL_Y = PH_Y + PH_H - 59
else:
    PH_W, PH_H, BORDE = 800, 1180, 16
    PH_X, PH_Y = (W - PH_W) // 2, 610
    LOGO_ANCHO, LOGO_Y, TITULO_Y, ETIQ_Y = 500, 95, 250, 330
    PILL_Y = 1640
def mascara(w, h, r):
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255); return m
MASK = mascara(PH_W, PH_H, 44)
MARCO = Image.new('RGBA', (PH_W + 2 * BORDE, PH_H + 2 * BORDE), (0, 0, 0, 0))
ImageDraw.Draw(MARCO).rounded_rectangle((0, 0, MARCO.size[0] - 1, MARCO.size[1] - 1), 58, fill=(24, 28, 34, 255),
                                        outline=(70, 78, 88, 255), width=3)
SOMBRA = Image.new('RGBA', (W, H), (0, 0, 0, 0))
ImageDraw.Draw(SOMBRA).rounded_rectangle((PH_X - BORDE + 10, PH_Y - BORDE + 30, PH_X + PH_W + BORDE + 10,
                                          PH_Y + PH_H + BORDE + 30), 60, fill=(0, 0, 0, 170))
SOMBRA = SOMBRA.filter(ImageFilter.GaussianBlur(30))

CAP = ruta(P.get('capturas_dir', 'capturas'))
_cap = {}
def captura(nombre):
    if nombre not in _cap:
        im = Image.open(os.path.join(CAP, nombre + '.png')).convert('RGB')
        _cap[nombre] = im.resize((PH_W, int(im.size[1] * PH_W / im.size[0])), Image.LANCZOS)
    return _cap[nombre]

def telefono(base, nombre, avance, alto_max=None):
    im = captura(nombre)
    tope = im.size[1] if alto_max is None else min(im.size[1], int(alto_max))
    y = int((tope - PH_H) * suave(avance)) if tope > PH_H else 0
    base.alpha_composite(SOMBRA)
    base.alpha_composite(MARCO, (PH_X - BORDE, PH_Y - BORDE))
    base.paste(im.crop((0, y, PH_W, y + PH_H)), (PH_X, PH_Y), MASK)

_capw = {}
def captura_w(nombre, ancho):
    if (nombre, ancho) not in _capw:
        im = Image.open(os.path.join(CAP, nombre + '.png')).convert('RGB')
        _capw[(nombre, ancho)] = im.resize((ancho, int(im.size[1] * ancho / im.size[0])), Image.LANCZOS)
    return _capw[(nombre, ancho)]

def degrade(alto, arriba=True, maximo=215):
    g = Image.new('L', (1, alto))
    for y in range(alto):
        k = (1 - y / alto) if arriba else (y / alto)
        g.putpixel((0, y), int(maximo * suave(k)))
    capa_ = Image.new('RGBA', (W, alto), (6, 9, 14, 255)); capa_.putalpha(g.resize((W, alto))); return capa_
DEG_ARRIBA, DEG_ABAJO = degrade(760, True, 245), degrade(600, False, 235)

def pantalla(base, nombre, avance, zoom=1.0, foco_x=0.5, desde=0.0, hasta=1.0, alto_max=None):
    """captura a pantalla completa: ancho = W*zoom, recorte horizontal en foco_x, scroll vertical suave"""
    ancho = int(W * max(1.0, zoom)); im = captura_w(nombre, ancho)
    tope = im.size[1] if alto_max is None else min(im.size[1], int(alto_max * ancho / W))
    x = int((ancho - W) * min(1, max(0, foco_x)))
    rango = max(0, tope - H)
    y = int(rango * (desde + (hasta - desde) * suave(avance)))
    lienzo = Image.new('RGB', (W, H), im.getpixel((min(im.size[0] - 1, x + 5), im.size[1] - 1)))
    lienzo.paste(im.crop((x, y, x + W, min(im.size[1], y + H))), (0, 0))
    base.paste(lienzo, (0, 0))

LOGO = Image.open(ruta(P['logo'])).convert('RGB') if P.get('logo') else None
def logo(base, k, ancho, y):
    if LOGO is None: return
    w = int(ancho); h = int(LOGO.size[1] * w / LOGO.size[0])
    im = LOGO.resize((w, h), Image.LANCZOS).convert('RGBA')
    im.putalpha(mascara(w, h, 36).point(lambda v: int(v * k)))
    base.alpha_composite(im, ((W - w) // 2, int(y)))

# ---------- textos animados ----------------------------------------------------------------
TXT = {}
def capa(clave, dibujar):
    if clave not in TXT:
        c = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dibujar(ImageDraw.Draw(c)); TXT[clave] = c
    return TXT[clave]

def centrado(d, y, txt, tam, color, sombra=True):
    f = fuente(tam)
    while d.textlength(txt, font=f) > W - 90 and tam > 30:      # que nunca se salga de la pantalla
        tam -= 4; f = fuente(tam)
    w = d.textlength(txt, font=f)
    if sombra: d.text(((W - w) / 2 + 5, y + 6), txt, font=f, fill=(0, 0, 0, 150))
    d.text(((W - w) / 2, y), txt, font=f, fill=color)

def pill(d, y, txt, fondo, color=(255, 255, 255)):
    tam = 64; f = fuente(tam)
    while d.textlength(txt, font=f) > W - 200 and tam > 30:
        tam -= 4; f = fuente(tam)
    w = d.textlength(txt, font=f)
    d.rounded_rectangle(((W - w) / 2 - 50, y, (W + w) / 2 + 50, y + 118), 59, fill=fondo)
    d.text(((W - w) / 2, y + 59 - tam * 0.66), txt, font=f, fill=color)

def pop(base, c, t, t0, dur=0.22, desde=1.35, cy=None):
    """aparece creciendo desde 'desde' hasta 1, centrado en su propia altura cy"""
    k = suave((t - t0) / dur)
    if k <= 0: return
    esc = desde + (1 - desde) * k; im = c
    if abs(esc - 1) > 0.001:
        cw, ch = int(W * esc), int(H * esc)
        im = c.resize((cw, ch), Image.BILINEAR)
        cy = H / 2 if cy is None else cy
        top = int(cy * esc - cy)
        im = im.crop(((cw - W) // 2, top, (cw - W) // 2 + W, top + H))
    if k < 1:
        im = im.copy(); im.putalpha(im.getchannel('A').point(lambda a: int(a * k)))
    base.alpha_composite(im)

def punch(c, t, dur=0.22, desde=1.10):
    esc = desde + (1 - desde) * suave(t / dur)
    if esc - 1 < 0.002: return c
    cw, ch = int(W * esc), int(H * esc)
    return c.resize((cw, ch), Image.BILINEAR).crop(((cw - W) // 2, (ch - H) // 2, (cw - W) // 2 + W, (ch - H) // 2 + H))

def lineas_norm(lineas, tam_def='medio'):
    out = []
    for l in lineas:
        if isinstance(l, str): l = {'t': l}
        out.append({'t': l['t'], 'tam': TAM.get(l.get('tam', tam_def), 92), 'color': COL.get(l.get('color', 'blanco')),
                    'en': l.get('en'), 'espacio': l.get('espacio', 0)})
    return out

def bloque(b, clave, lineas, t, y0=None, ritmo=0.35, t0=0.05, tam_def='medio'):
    L = lineas_norm(lineas, tam_def)
    altos = [int(l['tam'] * 1.22) + l['espacio'] for l in L]
    y = (H * 0.44 - sum(altos) / 2) if y0 is None else y0
    for i, l in enumerate(L):
        yy = y + l['espacio']            # 'espacio': aire extra ARRIBA de esa linea
        pop(b, capa('%s_%d' % (clave, i), lambda d, l=l, yy=yy: centrado(d, yy, l['t'], l['tam'], l['color'])),
            t, l['en'] if l['en'] is not None else t0 + i * ritmo, cy=yy + l['tam'] / 2)
        y += altos[i]

def medalla(d, cx, cy, r):
    d.polygon([(cx - r * 0.55, cy - r * 2.1), (cx - r * 0.1, cy - r * 0.8), (cx - r * 0.95, cy - r * 0.8)], fill=COL['oscuro'])
    d.polygon([(cx + r * 0.55, cy - r * 2.1), (cx + r * 0.1, cy - r * 0.8), (cx + r * 0.95, cy - r * 0.8)], fill=COL['primario'])
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=COL['acento'], outline=(255, 214, 140), width=10)
    pts = [(cx + r * (0.55 if i % 2 == 0 else 0.23) * math.cos(-math.pi / 2 + i * math.pi / 5),
            cy + r * (0.55 if i % 2 == 0 else 0.23) * math.sin(-math.pi / 2 + i * math.pi / 5)) for i in range(10)]
    d.polygon(pts, fill=COL['blanco'])

# ---------- escenas ------------------------------------------------------------------------
def e_texto(b, s, t, d, k):
    bloque(b, k, s['lineas'], t, ritmo=s.get('ritmo', 0.35), tam_def='grande')

def e_pantalla(b, s, t, d, k):
    pantalla(b, s['captura'], t / d, s.get('zoom', 1.0), s.get('foco_x', 0.5), s.get('desde', 0.0), s.get('hasta', 1.0),
             s.get('alto_max'))
    if s.get('velo'):                       # oscurece toda la captura (0-1) para textos grandes encima
        b.alpha_composite(Image.new('RGBA', (W, H), (6, 9, 14, int(255 * s['velo']))))
    b.alpha_composite(DEG_ARRIBA, (0, 0)); b.alpha_composite(DEG_ABAJO, (0, H - DEG_ABAJO.size[1]))
    if s.get('titulo'):
        # Con "marca" el logo esta fijo arriba: el titulo arranca debajo, nunca encima de el.
        bloque(b, k + 't', s['titulo'], t, y0=s.get('titulo_y', TITULO_Y if MARCA else 120),
               ritmo=s.get('ritmo', 0.5), t0=0.1)
    if s.get('pill'):
        color = COL.get(s.get('pill_color', 'oscuro'))
        yp = H - 250
        pop(b, capa(k + 'p', lambda dr: pill(dr, yp, s['pill'], color)), t, s.get('pill_en', 0.45), cy=yp + 59)

def e_telefono(b, s, t, d, k):
    # Por defecto la captura ocupa TODA la pantalla: sin marco y sin franjas de fondo arriba
    # y abajo, que es lo que se ve bien en un reel. El telefono con marco queda para quien lo
    # pida con "marco": true.
    if not s.get('marco'):
        return e_pantalla(b, s, t, d, k)
    telefono(b, s['captura'], t / d, s.get('alto_max'))
    if s.get('logo_arriba') and not MARCA:
        logo(b, suave(t / 0.5), LOGO_ANCHO, LOGO_Y)
    if s.get('titulo'):
        bloque(b, k + 't', s['titulo'], t, y0=TITULO_Y, ritmo=s.get('ritmo', 0.8), t0=0.1)
    if s.get('pill'):
        color = COL.get(s.get('pill_color', 'oscuro'))
        pop(b, capa(k + 'p', lambda dr: pill(dr, PILL_Y, s['pill'], color)), t, 0.45, cy=PILL_Y + 59)

def e_rafaga(b, s, t, d, k):
    items = s['items']; tramo = d / len(items)
    i = min(len(items) - 1, int(t / tramo)); tl = t - i * tramo; it = items[i]
    sub = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # Igual que "telefono": pantalla completa salvo que pidan el marco ("completa" se sigue
    # aceptando en los proyectos viejos, ahora es lo que pasa sin decir nada).
    completa = not (s.get('marco') or it.get('marco'))
    if completa:
        pantalla(sub, it['captura'], tl / tramo if it.get('scroll', True) else 0, it.get('zoom', 1.0), it.get('foco_x', 0.5),
                 it.get('desde', 0.0), it.get('hasta', 1.0), it.get('alto_max'))
        sub.alpha_composite(DEG_ARRIBA, (0, 0)); sub.alpha_composite(DEG_ABAJO, (0, H - DEG_ABAJO.size[1]))
    else:
        telefono(sub, it['captura'], tl / tramo if it.get('scroll', True) else 0, it.get('alto_max'))
    b.alpha_composite(punch(sub, tl))
    if it.get('etiqueta'):
        ey = (TITULO_Y if MARCA else 140) if completa else ETIQ_Y
        pop(b, capa('%s_%d_%d' % (k, i, ey), lambda dr: centrado(dr, ey, it['etiqueta'], 92, COL['blanco'])), tl, 0.0, 0.18, 1.5,
            cy=ey + 46)
    if s.get('pill_final') and i == len(items) - 1:
        py = H - 250 if completa else PILL_Y
        pop(b, capa(k + 'p', lambda dr: pill(dr, py, s['pill_final'], COL['acento'], COL['negro'])), tl, 0.15,
            cy=py + 59)

def e_chips(b, s, t, d, k):
    items = s['items']; paso = min(0.62, max(0.3, (d - 0.5) / len(items)))
    y0 = int(H * 0.44 - len(items) * 230 / 2)
    for i, txt in enumerate(items):
        def dib(dr, i=i, txt=txt):
            y = y0 + i * 230; tam = 62; f = fuente(tam)
            while dr.textlength(txt, font=f) > W - 260 and tam > 30:
                tam -= 4; f = fuente(tam)
            w = dr.textlength(txt, font=f)
            dr.rounded_rectangle(((W - w) / 2 - 110, y, (W + w) / 2 + 60, y + 150), 75,
                                 fill=(255, 255, 255, 28), outline=(255, 255, 255, 70), width=3)
            cx = (W - w) / 2 - 50
            dr.ellipse((cx - 32, y + 43, cx + 32, y + 107), fill=COL['primario'])
            dr.line((cx - 15, y + 76, cx - 3, y + 90, cx + 17, y + 60), fill=COL['blanco'], width=9)
            dr.text(((W - w) / 2 + 10, y + 75 - tam * 0.66), txt, font=f, fill=COL['blanco'])
        pop(b, capa('%s_%d' % (k, i), dib), t, 0.1 + i * paso, 0.2, 1.25, cy=y0 + i * 230 + 75)

def e_contador(b, s, t, d, k):
    n = int(round(s['numero'] * suave(t / 0.7)))
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    centrado(ImageDraw.Draw(c), 470, '%s%d' % (s.get('prefijo', ''), n), TAM['numero'], COL['acento'])
    b.alpha_composite(c)
    bloque(b, k, s.get('lineas', []), t, y0=930, ritmo=0.25, t0=0.35)

def e_medalla(b, s, t, d, k):
    pop(b, capa(k + 'm', lambda dr: medalla(dr, W / 2, 610, 150)), t, 0.05, 0.25, 1.4, cy=560)
    bloque(b, k, s['lineas'], t, y0=860, ritmo=0.35, t0=0.3)

def e_cierre(b, s, t, d, k):
    q = suave(t / 0.28)
    if MARCA:                                     # logo, frase y web como un bloque centrado
        logo(b, 1.0, 920 * (1.25 - 0.25 * q), 640 - 60 * (1 - q))
        t0 = 0.45
        if s.get('tagline'):
            pop(b, capa(k + 't', lambda dr: centrado(dr, 930, s['tagline'], 92, COL['primario'])), t, t0, cy=976)
        if s.get('url'):
            pop(b, capa(k + 'u', lambda dr: pill(dr, 1100, s['url'], COL['oscuro'])), t, t0 + 0.35, cy=1159)
        return
    logo(b, 1.0, 900 * (1.25 - 0.25 * q), 360 - 60 * (1 - q))
    dy = 0 if LOGO is not None else -380          # sin logo, frase y web van al centro
    t0 = 0.45 if LOGO is not None else 0.1
    if s.get('tagline'):
        pop(b, capa(k + 't', lambda dr: centrado(dr, 1200 + dy, s['tagline'], 92, COL['primario'])), t, t0, cy=1246 + dy)
    if s.get('url'):
        pop(b, capa(k + 'u', lambda dr: pill(dr, 1400 + dy, s['url'], COL['oscuro'])), t, t0 + 0.35, cy=1459 + dy)

TIPOS = {'pantalla': e_pantalla, 'texto': e_texto, 'telefono': e_telefono, 'rafaga': e_rafaga, 'chips': e_chips,
         'contador': e_contador, 'medalla': e_medalla, 'cierre': e_cierre}

# ---------- linea de tiempo ----------------------------------------------------------------
ESC = P['escenas']
LEAD, COLA = P.get('lead', 0.35), P.get('cola', 1.7)
VOZ = None
if P.get('voz', {}).get('dir'):
    dj = os.path.join(ruta(P['voz']['dir']), 'duraciones.json')
    if os.path.exists(dj):
        VOZ = json.load(open(dj, encoding='utf-8'))
if VOZ:
    INI = [LEAD + VOZ['inicio'][s['frase']] for s in ESC]
    TOTAL = LEAD + VOZ['total'] + COLA
else:
    INI, acc = [], LEAD
    for s in ESC:
        INI.append(acc); acc += s.get('dur', 3.0)
    TOTAL = acc + COLA
CORTES = [0.0] + [x - 0.12 for x in INI[1:]] + [TOTAL]

def cuadro(tg):
    i = max(j for j in range(len(ESC)) if CORTES[j] <= min(tg, TOTAL - 1e-6))
    t, d = tg - CORTES[i], CORTES[i + 1] - CORTES[i]
    s = ESC[i]
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    TIPOS[s['tipo']](c, s, t, d, 'e%d' % i)
    b = FONDO.copy()
    b.alpha_composite(c if (i == 0 or s['tipo'] == 'rafaga') else punch(c, t))
    if MARCA and s['tipo'] != 'cierre':        # fijo: fuera del "punch", no salta en los cortes
        logo(b, suave(t / 0.4) if i == 0 else 1.0, LOGO_ANCHO, LOGO_Y)
    if i > 0 and t < 0.12:                                     # destello en cada corte
        b.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(110 * (1 - t / 0.12)))))
    return b.convert('RGB')

# ---------- salida ------------------------------------------------------------------------
SALIDA = ruta(P.get('salida', 'video.mp4'))
def render():
    sin_audio = SALIDA[:-4] + '_sin_audio.mp4'
    n = int(TOTAL * FPS)
    p = subprocess.Popen([FF, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
                          '-pix_fmt', 'yuv420p', sin_audio], stdin=subprocess.PIPE)
    for k in range(n):
        p.stdin.write(cuadro(k / FPS).tobytes())
    p.stdin.close(); p.wait()
    return sin_audio

def mezclar(sin_audio):
    args = [FF, '-y', '-loglevel', 'error', '-i', sin_audio]
    fil, entradas = [], 1
    if P.get('musica', True):
        wav = SALIDA[:-4] + '_musica.wav'
        subprocess.run([sys.executable, os.path.join(AQUI, 'musica.py'), '%.3f' % TOTAL, wav, str(P.get('bpm', 124))],
                       check=True)
        args += ['-i', wav]; mus = entradas; entradas += 1
    if VOZ:
        args += ['-i', VOZ['toma']]; vz = entradas; entradas += 1
        ms = int(LEAD * 1000)
        fil.append('[%d:a]adelay=%d|%d,volume=1.6,apad=whole_dur=%.3f,asplit=2[voz][llave]' % (vz, ms, ms, TOTAL))
    if P.get('musica', True) and VOZ:
        fil.append('[%d:a]volume=0.55[mus]' % mus)
        fil.append('[mus][llave]sidechaincompress=threshold=0.02:ratio=8:attack=10:release=280[mdk]')  # la musica baja cuando habla
        fil.append('[mdk][voz]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]')
    elif VOZ:
        fil.append('[voz]anull,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]'); fil.append('[llave]anullsink')
    elif P.get('musica', True):
        fil.append('[%d:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]' % mus)
    else:
        os.replace(sin_audio, SALIDA); return
    args += ['-filter_complex', ';'.join(fil), '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac',
             '-b:a', '192k', '-shortest', '-movflags', '+faststart', SALIDA]
    subprocess.run(args, check=True)

if __name__ == '__main__':
    print('duracion %.2fs  cortes %s' % (TOTAL, [round(c, 2) for c in CORTES]))
    if '--previews' in sys.argv:
        dp = os.path.join(os.path.dirname(SALIDA), 'previews'); os.makedirs(dp, exist_ok=True)
        for i in range(len(ESC)):
            a, z = CORTES[i], CORTES[i + 1]
            cuadro(a + (z - a) * 0.75).save(os.path.join(dp, 'escena_%02d.png' % (i + 1)))
        subprocess.run([sys.executable, os.path.join(AQUI, 'hoja.py'), os.path.join(dp, 'escena_*.png'),
                        os.path.join(dp, 'hoja_escenas.png')], check=True)
        sys.exit()
    mezclar(render())
    print('listo', SALIDA, os.path.getsize(SALIDA) // 1024, 'KB')
