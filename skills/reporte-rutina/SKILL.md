---
name: reporte-rutina
description: Plantilla para tareas programadas o repetitivas que recolectan datos y mandan un reporte (red, métricas, estados de servicios). Separa la recolección en un script, compara contra la corrida anterior y llama al modelo solo si hay cambios o anomalías. Usalo al crear o revisar una tarea programada diaria o periódica, o cuando el usuario pida que un reporte consuma menos tokens.
---

# reporte-rutina

Principio: el script hace lo repetitivo y el modelo solo interpreta lo que cambió. Un reporte diario que hoy releé todo el contexto cada mañana puede costar centavos si el modelo entra solo ante un desvío.

## Estructura de la tarea

```
<tarea>/
  recolectar.py      recolecta datos y escribe salida.json (solo lectura)
  estado/ultimo.json estado de la corrida anterior, para comparar
  umbrales.json      límites que disparan alerta (ver "Alertas")
  SKILL.md           instrucciones para el modelo, solo para anomalías
```

## Pasos de cada corrida

1. **Recolectar.** Ejecutar `recolectar.py`. Es solo lectura: nada de cambios en equipos, servicios ni bases. Si falla, el reporte dice que falló y en qué paso.
2. **Comparar.** Contrastar `salida.json` con `estado/ultimo.json`. Calcular solo las diferencias y los valores fuera de umbral. Hacerlo en código, no en el modelo.
3. **Decidir.** Si no hay diferencias relevantes ni anomalías, mandar un aviso corto de estado normal, o no mandar nada si así se configuró. No llamar al modelo.
4. **Interpretar.** Solo si hay anomalías, el modelo lee el resumen de diferencias (no los datos crudos) y redacta el reporte. Usar el modelo indicado en la tarea y pedir una extensión máxima.
5. **Guardar estado.** Reemplazar `estado/ultimo.json` solo si la recolección salió bien.
6. **Enviar.** Usar el canal ya configurado para la tarea. No mandar mails con la palabra "Claude" ni en asunto, cuerpo ni firma.

## Alertas

- Avisar recién a la falla número N seguida, y deduplicar: no repetir la misma alerta en cada corrida.
- Un estado normal no es un error. No mandar alertas por valores dentro de rango.
- Los umbrales viven en `umbrales.json`, no en el código ni en el prompt.

## Checklist antes de programar la tarea

- [ ] La recolección es solo lectura y tiene timeout.
- [ ] Existe una corrida de prueba que genera `salida.json` sin llamar al modelo.
- [ ] Si hay anomalías, el prompt del modelo es corto y recibe solo el resumen.
- [ ] Están definidos los umbrales y la regla de deduplicación.
- [ ] El modelo elegido es el más barato que alcanza para interpretar (Sonnet para la mayoría de los casos).
- [ ] El asunto y el cuerpo del mail no mencionan "Claude".

## Reglas

- No pasar a la tarea datos que no usa el reporte.
- No dejar el modelo recolectando datos que el script puede juntar.
- Si la tarea ya existe, cambiarla de a una etapa y medir el costo de la corrida siguiente con el reporte de tokens.
