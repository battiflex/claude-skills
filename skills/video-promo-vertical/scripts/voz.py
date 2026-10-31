# -*- coding: utf-8 -*-
"""
Locucion para el video: el guion ENTERO en una sola toma (la entonacion fluye como una
locucion real; frase por frase suena a robot) y despues se corta en frases detectando pausas.

  python voz.py <proyecto.json> muestras            una toma por voz candidata (Gemini)
  python voz.py <proyecto.json> edge <VozEdge>      alternativa sin clave (edge-tts), ej es-AR-TomasNeural
  python voz.py <proyecto.json> cortar <Voz>        corta muestra_<Voz>.wav -> duraciones.json
  python voz.py <proyecto.json> intercalar A,B,C    una frase de cada voz, rotando ("voz" en una frase
                                                    del guion la fija) -> muestra_Intercalada + duraciones

Gemini: clave en GEMINI_API_KEY o en ~/.gemini_api_key (nunca se imprime ni se commitea).
"""
import base64, json, os, re, subprocess, sys, urllib.request, urllib.error
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
URL = 'https://generativelanguage.googleapis.com/v1beta/interactions'

def cargar(proyecto):
    P = json.load(open(proyecto, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(proyecto))
    V = P.get('voz', {})
    out = os.path.join(base, V.get('dir', 'voz'))
    os.makedirs(out, exist_ok=True)
    return P, V, out

def texto_voz(P):
    # 'texto_voz' permite escribir fonetico solo para el audio (ej. una marca en ingles)
    return ' '.join(f.get('texto_voz', f['texto']) for f in P['guion'])

def clave():
    k = os.environ.get('GEMINI_API_KEY', '').strip()
    p = os.path.join(os.path.expanduser('~'), '.gemini_api_key')
    if not k and os.path.exists(p):
        k = open(p, encoding='utf-8-sig').read().strip()
    if not k:
        sys.exit('Falta la clave de Gemini: GEMINI_API_KEY o ~/.gemini_api_key')
    return k

def limpiar(crudo, destino):
    """a 44.1 kHz estereo, sin silencios en las puntas"""
    filtro = ('silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,'
              'areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse')
    subprocess.run([FF, '-loglevel', 'error', '-y', '-i', crudo, '-af', filtro, '-ar', '44100', '-ac', '2', destino],
                   check=True)
    subprocess.run([FF, '-loglevel', 'error', '-y', '-i', destino, '-c:a', 'aac', '-b:a', '128k',
                    destino[:-4] + '.m4a'], check=True)          # version liviana para escuchar en el celu
    return destino

def gemini(P, V, voz, destino):
    cuerpo = {
        'model': V.get('modelo', 'gemini-3.8-flash-tts'),
        'input': [{'type': 'user_input', 'content': [{
            'type': 'text', 'text': texto_voz(P),
            'annotations': [{'type': 'speech_metadata', 'style': V['estilo']}]}]}],
        'response_format': {'type': 'audio'},
        'generation_config': {'speech_config': [{'voice': voz}]},
    }
    req = urllib.request.Request(URL, data=json.dumps(cuerpo).encode('utf-8'), method='POST',
                                 headers={'x-goog-api-key': clave(), 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        sys.exit('Gemini respondio %d: %s' % (e.code, e.read().decode('utf-8', 'replace')[:600]))
    audios = [c for s in resp.get('steps', []) if s.get('type') == 'model_output'
              for c in s.get('content', []) if c.get('type') == 'audio']
    if not audios:
        sys.exit('La respuesta no trae audio: %s' % json.dumps(resp)[:600])
    crudo = destino + '.raw.wav'
    open(crudo, 'wb').write(base64.b64decode(audios[-1]['data']))
    return limpiar(crudo, destino)

def edge(P, voz, destino, rate='+0%'):
    import asyncio, edge_tts
    crudo = destino + '.raw.mp3'
    asyncio.run(edge_tts.Communicate(texto_voz(P), voz, rate=rate).save(crudo))
    return limpiar(crudo, destino)

def duracion(p):
    r = subprocess.run([FF, '-hide_banner', '-i', p], capture_output=True, text=True)
    h, m, s = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)

def silencios(p, db=-38, minimo=0.12):
    r = subprocess.run([FF, '-hide_banner', '-i', p, '-af', 'silencedetect=noise=%ddB:d=%.2f' % (db, minimo),
                        '-f', 'null', '-'], capture_output=True, text=True)
    ini = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', r.stderr)]
    fin = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r.stderr)]
    return list(zip(ini, fin))

def letras(t):
    return len(re.sub(r'[^\wáéíóúñü]', '', t.lower()))

def tramos(P, out, voz):
    """Para cada limite entre frases estima donde deberia caer segun las letras que faltan
    decir en el tiempo que queda (se adapta si la voz acelera o frena) y elige la pausa
    mas cercana, premiando un poco las largas. 'Las N pausas mas largas' falla: las comas y
    los dos puntos dentro de una frase a veces pausan mas que el final de otra.
    Devuelve (toma, total, silencios, inicio{id}, dur{id})."""
    toma = os.path.join(out, 'muestra_%s.wav' % voz)
    total = duracion(toma)
    sil = silencios(toma)
    frases = P['guion']
    # Las comas y los dos puntos de adentro tambien llevan tiempo: sin contarlos, una frase
    # como "Resultados, zonas y llaves, al toque" se estimaba corta y el corte caia en su coma.
    def peso(t):
        return letras(t) + 4 * len(re.findall(r'[,;:]', t.rstrip('.?!¿¡ ')))
    pesos = [peso(f.get('texto_voz', f['texto'])) for f in frases]
    elegidas, desde = [], 0.0
    for k in range(len(pesos) - 1):
        e = desde + (total - desde) * pesos[k] / sum(pesos[k:])
        cand = [s for s in sil if (s[0] + s[1]) / 2 > desde + 0.3 and s not in elegidas]
        if not cand:
            sys.exit('No hay pausa para el limite %d: la toma no separa bien las frases' % (k + 1))
        mejor = min(cand, key=lambda s: abs((s[0] + s[1]) / 2 - e) - 0.5 * (s[1] - s[0]))
        elegidas.append(mejor)
        desde = (mejor[0] + mejor[1]) / 2
    inicio, dur = {}, {}
    for i, f in enumerate(frases):
        a = 0.0 if i == 0 else elegidas[i - 1][1]
        b = total if i == len(frases) - 1 else elegidas[i][0]
        inicio[f['id']], dur[f['id']] = round(a, 3), round(b - a, 3)
    return toma, total, sil, inicio, dur

def cortar(P, out, voz):
    toma, total, sil, inicio, dur = tramos(P, out, voz)
    json.dump({'inicio': inicio, 'dur': dur, 'toma': toma, 'voz': voz, 'total': round(total, 3)},
              open(os.path.join(out, 'duraciones.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('toma %.2fs (%s)' % (total, voz))
    for f in P['guion']:
        print('  %-5s empieza %6.2fs  dura %5.2fs  %s' % (f['id'], inicio[f['id']], dur[f['id']], f['texto']))
    print('  todas las pausas:', [(round(a, 2), round(b - a, 2)) for a, b in sil])

def intercalar(P, out, voces, pausa=0.28):
    """Varias voces que se turnan: una frase de cada una, rotando en el orden dado, o la que
    diga "voz" en esa frase del guion (sirve para elegir quien cierra). Cada frase sale de la
    toma COMPLETA de su voz (conserva la entonacion natural); se igualan los volumenes, se
    suavizan las puntas para que el corte no haga clic y se unen con una pausa corta.
    Deja muestra_Intercalada.wav/.m4a y duraciones.json, que el render usa como una sola toma."""
    import numpy as np
    SR = 44100
    frases = P['guion']
    asignadas = [f.get('voz') or voces[i % len(voces)] for i, f in enumerate(frases)]
    datos = {}
    for v in asignadas:
        if v not in datos:
            datos[v] = tramos(P, out, v)
            print('cortes de %s: %s' % (v, ' | '.join('%s %.2f+%.2f' % (f['id'], datos[v][3][f['id']], datos[v][4][f['id']])
                                                   for f in frases)))

    def leer(toma, a, b):
        r = subprocess.run([FF, '-loglevel', 'error', '-ss', '%.3f' % a, '-t', '%.3f' % (b - a), '-i', toma,
                            '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True, check=True)
        return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32)

    partes = []
    for f, v in zip(frases, asignadas):
        toma, total, _, inicio, dur = datos[v]
        a = max(0.0, inicio[f['id']] - 0.04)
        b = min(total, inicio[f['id']] + dur[f['id']] + 0.06)
        x = leer(toma, a, b)
        hablado = x[np.abs(x) > 500]                          # el volumen se mide solo donde habla
        rms = float(np.sqrt(np.mean(hablado ** 2))) if hablado.size else 1.0
        x = x * (3500.0 / max(rms, 1.0))
        n = min(int(0.012 * SR), len(x) // 2)
        if n:
            rampa = np.linspace(0.0, 1.0, n)
            x[:n] *= rampa; x[-n:] *= rampa[::-1]
        partes.append((f, v, x))

    pico = max(float(np.max(np.abs(x))) for _, _, x in partes)
    k = min(1.0, 30000.0 / pico) if pico else 1.0             # sin recortar picos: se baja todo parejo
    silencio = np.zeros(int(pausa * SR), dtype=np.float32)
    pista, inicio, dur, t = [], {}, {}, 0.0
    for i, (f, v, x) in enumerate(partes):
        if i:
            pista.append(silencio); t += pausa
        inicio[f['id']], dur[f['id']] = round(t, 3), round(len(x) / SR, 3)
        pista.append(x * k); t += len(x) / SR
    datos_pcm = np.clip(np.concatenate(pista), -32767, 32767).astype(np.int16).tobytes()
    destino = os.path.join(out, 'muestra_Intercalada.wav')
    subprocess.run([FF, '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '-',
                    '-ac', '2', destino], input=datos_pcm, check=True)
    subprocess.run([FF, '-loglevel', 'error', '-y', '-i', destino, '-c:a', 'aac', '-b:a', '128k',
                    destino[:-4] + '.m4a'], check=True)
    total = duracion(destino)
    json.dump({'inicio': inicio, 'dur': dur, 'toma': destino, 'voz': '+'.join(dict.fromkeys(asignadas)),
               'total': round(total, 3)},
              open(os.path.join(out, 'duraciones.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('toma intercalada %.2fs' % total)
    for f, v in zip(frases, asignadas):
        print('  %-5s %-8s empieza %6.2fs  dura %5.2fs  %s' % (f['id'], v, inicio[f['id']], dur[f['id']], f['texto']))

if __name__ == '__main__':
    proyecto, modo = sys.argv[1], sys.argv[2]
    P, V, out = cargar(proyecto)
    if modo == 'muestras':
        for voz in V.get('candidatas', ['Achird', 'Puck', 'Fenrir']):
            d = gemini(P, V, voz, os.path.join(out, 'muestra_%s.wav' % voz))
            print('%-10s %.2fs  %s' % (voz, duracion(d), d[:-4] + '.m4a'))
    elif modo == 'edge':
        voz = sys.argv[3]
        d = edge(P, voz, os.path.join(out, 'muestra_%s.wav' % voz), V.get('edge_rate', '+0%'))
        print('%-10s %.2fs  %s' % (voz, duracion(d), d[:-4] + '.m4a'))
    elif modo == 'cortar':
        cortar(P, out, sys.argv[3])
    elif modo == 'intercalar':
        intercalar(P, out, [v.strip() for v in sys.argv[3].split(',') if v.strip()])
    else:
        sys.exit(__doc__)
