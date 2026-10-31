---
name: handoff
description: Cierra una sesión larga o que cambia de tema dejando un resumen en archivo y el prompt para arrancar una sesión nueva con poco contexto. Usalo cuando la conversación pase unos 300.000 tokens de contexto, cuando el usuario pida cerrar o pasar la tarea a otra sesión, o cuando vaya a empezar un tema distinto dentro de la misma sesión.
---

# handoff

Objetivo: que la sesión nueva arranque con lo justo para seguir, sin releer toda esta conversación. Cada turno de una sesión larga relee todo el historial, así que el resumen ahorra tokens en cada turno que siga.

## Pasos

1. Confirmá el tema y el próximo paso concreto. Si no hay un próximo paso claro, preguntá una sola vez antes de escribir.
2. Escribí el archivo en `C:\Users\mynam\.claude\handoffs\AAAA-MM-DD-tema.md` (tema en minúsculas, con guiones).
3. Usá esta estructura, sin volcar transcripciones ni salidas largas:

```markdown
# Handoff: <tema>

## Objetivo
Qué se quiere lograr, en dos o tres líneas.

## Estado
- Hecho y verificado: ...
- Hecho pero sin verificar: ...
- Pendiente: ...

## Decisiones y motivos
- Decisión: motivo.

## Archivos y lugares tocados
- Ruta absoluta: qué cambió.

## Próximo paso
Una acción concreta, con el archivo o comando exacto.

## Riesgos y cuidados
Lo que puede romperse o las reglas que aplican (por ejemplo, no tocar producción).
```

4. No escribas credenciales, claves, tokens ni contraseñas. Si hacen falta, indicá dónde están (archivo o variable), no el valor.
5. Dejá el prompt de arranque para pegar en la sesión nueva:

```
Leé C:\Users\mynam\.claude\handoffs\AAAA-MM-DD-tema.md y seguí desde "Próximo paso". Confirmá con una línea lo que entendiste antes de tocar nada.
```

6. Respondé al usuario con la ruta del archivo y el prompt de arranque. Nada más.

## Reglas

- El archivo no pasa de unas 150 líneas. Si necesita más, resumí.
- Si la sesión sigue en el mismo tema con poco contexto, no hace falta handoff; usá `/compact` si el contexto crece.
- Si el usuario pide que la sesión nueva siga automáticamente, usá la herramienta de sesiones, no este skill.
