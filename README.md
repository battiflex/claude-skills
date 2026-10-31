# claude-skills

Skills para Claude Code creadas por battiflex.

| Skill | Para qué sirve |
|---|---|
| [handoff](skills/handoff) | Cierra una sesión larga dejando un resumen en archivo y el prompt para la sesión nueva. |
| [reporte-rutina](skills/reporte-rutina) | Plantilla para reportes programados: el script recolecta y el modelo solo interviene ante anomalías. |
| [video-promo-vertical](skills/video-promo-vertical) | Videos promocionales verticales (1080x1920) a partir de capturas de un sitio web, con voz y música propias. |

## Instalación

Copiá la carpeta de cada skill dentro de `~/.claude/skills/`. Por ejemplo:

```bash
cp -r skills/handoff ~/.claude/skills/
```
