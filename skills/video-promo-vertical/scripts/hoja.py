# -*- coding: utf-8 -*-
# Hoja de contacto: miniaturas lado a lado para revisar capturas o cuadros de un vistazo
# (mucho mas barato que mirar cada imagen). Uso: python hoja.py "<patron glob>" <salida.png> [ancho]
import glob, os, sys
from PIL import Image, ImageDraw

patron, salida = sys.argv[1], sys.argv[2]
W = int(sys.argv[3]) if len(sys.argv) > 3 else 270
fs = sorted(f for f in glob.glob(patron) if '_largo' not in os.path.basename(f))
if not fs:
    sys.exit('nada con ' + patron)
ims = [Image.open(f).convert('RGB') for f in fs]
H = max(int(im.size[1] * W / im.size[0]) for im in ims)
hoja = Image.new('RGB', (W * len(fs), H + 24), 'white')
d = ImageDraw.Draw(hoja)
for i, (f, im) in enumerate(zip(fs, ims)):
    hoja.paste(im.resize((W, int(im.size[1] * W / im.size[0]))), (i * W, 24))
    d.text((i * W + 4, 4), os.path.basename(f), fill='black')
hoja.save(salida)
print(salida, hoja.size)
