---
name: video-promo-vertical
description: Arma videos promocionales verticales (1080x1920, formato reel/historia/TikTok) a partir de capturas reales de un sitio o app web, con voz en off natural (Gemini TTS en una sola toma, estilo pedido con palabras), musica propia sin derechos y textos animados sincronizados con la voz. Usala siempre que pidan un video, reel, historia, publicidad, promo o "algo para redes" que muestre un producto web, aunque no digan "vertical" ni "skill"; tambien para rehacer, acortar, cambiar la voz o agregar frases a un video ya armado con este flujo.
---

# Videos promocionales verticales

Pipeline probado: capturas reales en formato celular -> guion -> locucion en una toma -> cortes por
frase -> escenas animadas sincronizadas -> musica propia -> mezcla a -14 LUFS -> MP4 1080x1920.
Todo sale de un `proyecto.json` (ver `assets/ejemplo_proyecto.json`, que reproduce un video real).

Scripts en `scripts/` (llamarlos con la ruta absoluta de esta skill):

| Script | Hace |
|---|---|
| `capturar.mjs <proyecto>` | capturas con emulacion movil real (Chrome + DevTools), sin avisos |
| `voz.py <proyecto> muestras` | una toma del guion por cada voz candidata de Gemini (.wav + .m4a) |
| `voz.py <proyecto> edge <Voz>` | alternativa sin clave (edge-tts), mas robotica |
| `voz.py <proyecto> cortar <Voz>` | corta la toma elegida en frases -> `voz/duraciones.json` |
| `render.py <proyecto> --previews` | un cuadro por escena + hoja de contacto, para revisar rapido |
| `render.py <proyecto>` | video final con musica y voz |
| `hoja.py "<glob>" <salida>` | hoja de contacto de cualquier grupo de imagenes |

Dependencias: Python con `Pillow`, `numpy`, `imageio-ffmpeg` (trae ffmpeg), `edge-tts` solo para la
alternativa; Node 22+ (WebSocket nativo); Chrome o Edge. Instalar lo que falte con pip antes de empezar.

## Un video nuevo = un proyecto nuevo
Nada del contenido esta en el codigo: guion, URLs, escenas, voz, colores, logo y musica salen del
`proyecto.json`. Para cada video:
1. Crear una carpeta de trabajo (en el scratchpad o donde diga el usuario) y copiar ahi
   `assets/ejemplo_proyecto.json` como `proyecto.json`.
2. Cambiar `capturas` (o poner capturas propias en `capturas_dir` con el mismo nombre + `_largo`),
   `guion`, `voz.estilo` y `escenas` (una por frase, con su `"frase": id`).
3. Opcionales: `logo` (sin logo, el cierre centra frase y web), `colores`, `bpm`, `"musica": false`,
   `"marca": true` (logo fijo arriba en todas las escenas + titulo + telefono grande: diseño parejo,
   sin franjas vacias; recomendado, y darle titulo o etiqueta a cada escena de telefono).
   Sin locucion: sacar `voz` y darle `"dur"` en segundos a cada escena.
Todo lo relativo se resuelve contra la carpeta del proyecto.

## Flujo

### 1. Brief (una sola ronda de preguntas, solo lo que no se sepa)
- Que se promociona, para que red y duracion. "Express" = 15-25 s; mas de 40 s ya aburre en reels.
- Pantallas reales a mostrar (URLs publicas) y logo. Colores de marca (si no, salen del logo).
- Tono y publico. Para Argentina: voseo ("organizás", "compartila") y lenguaje de la calle ("al toque", "el celu").
- Guion: frases cortas, una idea por frase, 7-9 frases para ~20 s. Cada frase va a ser una escena.

**Sobre lo que dice el video:** son afirmaciones publicas. Promocionar en positivo lo propio
(anos de experiencia, clientes, funciones que existen) y **no** insinuar cosas de un competidor
("es una copia", "lo hizo una IA") sin prueba: si no se sostiene, se da vuelta y hasta puede traer
un reclamo. Si el usuario lo pide, decirlo en una linea, ofrecer la version positiva
("no somos los nuevos") y seguir. Cada funcion que se nombra tiene que existir de verdad.

### 2. Capturas
```
node <skill>/scripts/capturar.mjs proyecto.json
python <skill>/scripts/hoja.py "capturas/*.png" capturas/hoja.png
```
Mirar la hoja de contacto antes de seguir. Por que asi:
- **Emulacion movil real (DevTools)**, no `chrome --headless --window-size`: sin ella la pagina no
  aplica su viewport movil y el contenido sale cortado a la derecha.
- Se ocultan avisos de Google (AdSense) e iframes: se colaban en la grilla y el calendario.
  Si queda algo ajeno, agregar selectores en `"ocultar_css"` del proyecto.
- Galerias con carga diferida: dar `"espera"` larga (20-25 s) y usar la captura `_largo`.
- Lo que haria un clic (sacar un filtro, cerrar un cartel, cambiar de pestaña) va en `"js"` de esa
  captura: se evalua en la pagina antes de capturar (y `"espera_js"` ms despues, 1500 por defecto).
- Si el script avisa `(desborda: revisar)`, esa pagina es mas ancha que el celular.
- Las capturas muestran nombres y fotos de gente real y marcas de clientes: avisarle al usuario
  que para publicidad conviene tener el visto bueno (o difuminar).

### 3. Voz
La que menos suena a IA es **una persona real** (el usuario grabandose con la grabadora del celu,
no con audio de WhatsApp). Si la graba, dejar el archivo como `voz/muestra_<Nombre>.wav` y saltar
directo a `cortar`. Si no, **Gemini TTS**:

1. Clave gratis en https://aistudio.google.com/apikey (Create API key). Que la guarde el usuario en
   `~/.gemini_api_key` (abrirle el archivo en el Bloc de notas/editor) en vez de pegarla en el chat.
   Nunca mostrarla, loguearla ni commitearla.
2. `python <skill>/scripts/voz.py proyecto.json muestras` y pasarle al usuario los `.m4a` para que elija.
   No se pueden escuchar desde aca: el juicio sobre acento y naturalidad es del usuario.
3. `python <skill>/scripts/voz.py proyecto.json cortar <Voz>` y **leer la lista de pausas** que imprime:
   cada limite tiene que caer al final de una frase, no en una coma o en dos puntos.
4. Varias voces turnandose (suena a varios jugadores/clientes contando lo suyo):
   `voz.py proyecto.json intercalar Achird,Puck,Fenrir` despues de `muestras`. Rota una frase por voz
   (o la de `"voz"` en esa frase del guion, util para elegir quien cierra); cada frase sale de la toma
   completa de su voz, iguala volumenes y deja `muestra_Intercalada` + `duraciones.json`. Correr antes
   `cortar` con cada voz y revisar sus cortes: un corte malo de una voz arruina su frase.

Por que asi:
- **El guion entero en una toma**: frase por frase la entonacion arranca de cero en cada una y suena a robot.
- **Estilo con palabras** en `voz.estilo` (acento, energia, ritmo, "nada robotico"). Si `gemini-3.8-flash-tts` se cuelga (timeout), usar `"modelo": "gemini-3.8-flash-lite-tts"`
  (los 2.5/3.1 rechazan las anotaciones del script). Voces que funcionaron
  en espanol rioplatense: Achird (amigable), Puck (animada), Fenrir (entusiasta).
- **Pronunciacion**: si una palabra sale mal (marcas en ingles), usar `"texto_voz"` en esa frase con
  la version fonetica ("Organáiser"); en pantalla queda `"texto"`.
- **Cortes**: "las N pausas mas largas" falla porque una coma a veces pausa mas que un final de frase.
  `cortar` estima donde deberia terminar cada frase segun las letras que faltan en el tiempo que queda
  y elige la pausa mas cercana. Si un corte queda mal, mirar la lista de pausas y la cuenta de letras.
- edge-tts (`es-AR-TomasNeural`) sirve de borrador sin clave; acelerada (+12%) suena mas robotica.
- Alternativas si Gemini no alcanza: ElevenLabs (pago desde USD 6, uso comercial desde Starter),
  Chatterbox (gratis, local, clona una voz con ~10 s de muestra; lento sin GPU).

### 4. Escenas
En `"escenas"`, una por frase del guion (`"frase": id`). Tipos: `texto`, `telefono`, `rafaga`, `chips`,
`contador`, `medalla`, `cierre` (detalle de campos en el encabezado de `render.py`). Pautas que dieron
buen resultado:
- Abrir con una pregunta que interpele en texto grande (escena `texto`).
- **Las capturas ocupan toda la pantalla**: `telefono`, `pantalla` y `rafaga` van sin marco y sin franjas
  de fondo, que es lo que se ve bien en un reel. El texto va encima sobre un degradé y `velo` oscurece
  para preguntas grandes. Para volver al telefono con marco sobre el fondo: `"marco": true` en la escena.
  Usar la captura corta si la página tiene paneles fijos (la `_largo` muestra lo de abajo del panel).
- `alto_max` en pantalla completa va en pixeles de la captura escalada a 1080 de ancho (con marco, a 860):
  al pasar una escena de marco a pantalla hay que multiplicarlo por 1080/860.
- Mostrar el producto con scroll suave; varias pantallas seguidas en `rafaga` con etiqueta.
- Datos duros con `contador` ("+15") y reconocimiento con `medalla`: sin logos de terceros sin permiso.
- Cerrar con `cierre`: logo, una frase y la web.
- Los textos se achican solos si no entran; igual, mas de ~20 caracteres por linea se lee mal.

### 5. Revisar antes de renderizar entero
```
python <skill>/scripts/render.py proyecto.json --previews
```
Mirar `salida/previews/hoja_escenas.png`. Un cuadro al 75% de cada escena puede agarrar algo en plena
animacion (texto a medio aparecer): no es un error.

### 6. Render y verificacion
```
python <skill>/scripts/render.py proyecto.json
```
Verificar siempre, sin suponer:
- duracion y que haya pista de audio (`ffmpeg -i`),
- volumen integrado ~-14 LUFS (`-af ebur128`), el estandar de Instagram/TikTok,
- 3-4 cuadros sueltos (`ffmpeg -ss <t> -frames:v 1`) en cortes y en el cierre, y la hoja de contacto.

Errores que ya pasaron y el render actual evita: la mezcla cortaba el video donde terminaba la voz
(por eso `apad` hasta el total), carteles de abajo que al crecer desde el centro de la pantalla se
salian del borde (crecen desde su propio centro), texto de cierre cortado de golpe (fundidos).

### 7. Entregar
Mandar el MP4 con la herramienta de archivos (se ve en el celu). Decir en claro que no se pudo ver ni
escuchar entero y que chequee: que cada texto aparezca cuando la voz lo dice, la pronunciacion y la
musica. La musica es sintetizada y basica: si la quiere mas pro, en Instagram/TikTok puede poner un
tema de su biblioteca y bajar esta. Para cambios (texto, voz, orden), editar el proyecto y re-renderizar.

## Notas de entorno (Windows)
- En Python dentro de un heredoc de bash los `\\` se colapsan: escribir scripts con la herramienta de
  archivos, no con heredoc, si tienen barras invertidas.
- `/tmp` de bash no es el mismo lugar que ve Python en Windows: usar rutas absolutas del scratchpad.
- Renderizar ~25 s a 1080x1920 tarda 2-3 min en una PC comun: correrlo con timeout largo.
