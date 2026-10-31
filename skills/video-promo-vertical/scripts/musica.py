# -*- coding: utf-8 -*-
# Base musical propia (sin derechos de terceros): house 124 BPM en La menor, Am-F-C-G.
# Uso: python musica.py <segundos> <salida.wav> [bpm] [tono] [progresion] [semilla]
#   tono: semitonos a transponer (0 = La menor); progresion: menor (Am-F-C-G), mayor (C-G-Am-F),
#   oscura (Am-G-F-G) o epica (Am-C-G-F); semilla: varia los platillos y el riser.
#   Sin los opcionales sale igual que siempre (las pistas viejas se pueden regenerar).
import sys, wave
import numpy as np

SR = 44100
BPM = float(sys.argv[3]) if len(sys.argv) > 3 else 124.0
TONO = int(sys.argv[4]) if len(sys.argv) > 4 else 0
PROGRESION = sys.argv[5] if len(sys.argv) > 5 else 'menor'
SEMILLA = int(sys.argv[6]) if len(sys.argv) > 6 else 7
BEAT = 60.0 / BPM
largo = float(sys.argv[1]) if len(sys.argv) > 1 else 18.0
salida = sys.argv[2] if len(sys.argv) > 2 else 'musica.wav'
N = int(SR * (largo + 1.5))
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(SEMILLA)

def env(n, ataque, caida):
    t = np.arange(n) / SR
    e = np.exp(-t / caida)
    a = max(1, int(ataque * SR)); e[:a] *= np.linspace(0, 1, a)
    return e

def lp(x, fc):                       # pasa bajos de un polo
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc; y[i] = acc
    return y

def hp(x, fc):
    return x - lp(x, fc)

def poner(sig, t, gl=1.0, gr=1.0):
    i = int(t * SR)
    if i >= N: return
    n = min(len(sig), N - i)
    L[i:i + n] += sig[:n] * gl; R[i:i + n] += sig[:n] * gr

# ---- sonidos --------------------------------------------------------------------------
n = int(0.32 * SR); tt = np.arange(n) / SR
f = 45 + 95 * np.exp(-tt / 0.035)
KICK = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.12) * 0.95

n = int(0.22 * SR)
CLAP = hp(rng.standard_normal(n), 900) * env(n, 0.002, 0.06) * 0.35

n = int(0.06 * SR)
HAT = hp(hp(rng.standard_normal(n), 6000), 6000) * env(n, 0.0005, 0.015) * 0.18
n = int(0.18 * SR)
OPENHAT = hp(hp(rng.standard_normal(n), 5000), 5000) * env(n, 0.001, 0.06) * 0.12

def saw(freq, dur, voces=3, det=0.012):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for v in range(voces):
        fv = freq * (1 + det * (v - (voces - 1) / 2))
        s += 2 * ((t * fv) % 1.0) - 1
    return s / voces

def nota(midi):
    return 440.0 * 2 ** ((midi - 69) / 12.0)

AM, F_, C_, G_ = (45, [57, 60, 64]), (41, [57, 60, 65]), (48, [55, 60, 64]), (43, [55, 59, 62])
PROGRESIONES = {
    'menor': [AM, F_, C_, G_],
    'mayor': [C_, G_, AM, F_],
    'oscura': [AM, G_, F_, G_],
    'epica': [AM, C_, G_, F_],
}
ACORDES = [(r + TONO, [m + TONO for m in t]) for r, t in PROGRESIONES[PROGRESION]]  # (raiz del bajo, triada) en MIDI

compases = int(np.ceil(largo / (4 * BEAT)))
for c in range(compases):
    raiz, triada = ACORDES[c % 4]
    t0 = c * 4 * BEAT
    intro = (c == 0)
    for b in range(4):
        tb = t0 + b * BEAT
        if tb > largo: break
        if not intro:
            poner(KICK, tb)
            if b in (1, 3): poner(CLAP, tb, 0.9, 1.0)
            poner(OPENHAT if b == 3 else HAT, tb + BEAT / 2, 0.8, 1.0)
            poner(HAT * 0.6, tb + BEAT / 4, 1.0, 0.7)
            poner(HAT * 0.6, tb + 3 * BEAT / 4, 1.0, 0.7)
            # bajo en contratiempo
            bajo = lp(saw(nota(raiz), BEAT * 0.45, 2, 0.004), 380) * env(int(BEAT * 0.45 * SR), 0.004, 0.16) * 0.55
            poner(bajo, tb + BEAT / 2)
    # acordes: stabs sincopados, posiciones en tiempos dentro del compas (en la intro, filtrados)
    dur = BEAT * 0.35
    stab = sum(saw(nota(m), dur) for m in triada) / 3
    stab = lp(stab, 1200 if intro else 2600) * env(int(dur * SR), 0.003, 0.09) * (0.34 if intro else 0.26)
    if intro:   # riser: ruido que crece en la segunda mitad de la entrada
        nr = int(2 * BEAT * SR)
        riser = hp(rng.standard_normal(nr), 2500) * np.linspace(0, 1, nr) ** 2 * 0.22
        poner(riser, t0 + 2 * BEAT)
    for pos in (0.5, 1.5, 2.75, 3.5):
        if t0 + pos * BEAT < largo:
            poner(stab, t0 + pos * BEAT, 1.0, 0.85)

# golpe final + cola
fin = compases * 4 * BEAT
t_fin = min(largo - 0.1, fin)
poner(KICK * 1.1, t_fin)
raiz, triada = ACORDES[0]
cola = sum(saw(nota(m), 1.4) for m in triada + [raiz + 12]) / 4
poner(lp(cola, 1800) * env(int(1.4 * SR), 0.005, 0.45) * 0.35, t_fin)

# master: recorte al largo, fade out, soft clip, normalizado
M = np.stack([L, R], axis=1)[: int(SR * largo)]
fo = int(0.6 * SR); M[-fo:] *= np.linspace(1, 0, fo)[:, None]
M = np.tanh(M * 1.3)
M = M / np.max(np.abs(M)) * 0.89
pcm = (M * 32767).astype(np.int16)
with wave.open(salida, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('musica', salida, '%.2fs' % largo)
