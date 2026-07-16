# FanRank — Auditoría de primera visita (fan de Brawl Stars, 19 años, desde Reddit)

**Fecha:** 16-jul-2026 · **URLs:** `https://eltonylfgi-blip.github.io/fanrank/` y `?s=brawl-stars`
**Método:** WebFetch + HTML crudo (copy i18n embebido + orden del DOM). NO se editó nada (experimento "medición sin cambios" respetado).

## Qué SE entiende

- **Home:** el hero sí responde la pregunta 2 en parte: "**Mejora lo que usas y sigues.** Ideas para creadores, videojuegos, empresas y plataformas, **ordenadas por fans e IA**." + badges "Anónimo si quieres / La IA agrupa y ordena / El famoso o su equipo valora ideas".
- **Perfil (?s=brawl-stars):** arriba "Ideas de fans para **Brawl Stars**", CTA "¿Qué debería mejorar ahora? — Escribe una frase" + botón "Proponer una mejora", y botones **VOTAR** en la lista. La acción está clara: votar o proponer.
- **La estrella SÍ está explicada... dos veces:** signal strip sobre la lista ("**Equipo ★** valoración oficial **separada del ranking**") y footer ("las estrellas del equipo verificado... **nunca alteran ese ranking orgánico**"). Existe, pero ver "Qué NO se entiende".
- Hay un **claim bar** en perfiles no verificados: "PERFIL DE FANS NO VERIFICADO — Hecho por fans, no es oficial. Si formas parte del equipo, reclámalo...".

## Qué NO se entiende (en los primeros 5 segundos)

1. **"Sin cuenta" es invisible.** "Gratis, sin registro" solo vive en el `<meta description>` (lo ve Google/Reddit, NO el visitante). En pantalla lo más parecido es "Anónima por defecto · unos 30 segundos" (solo home) y "Anónima públicamente" (ya DENTRO del compositor, tras el clic). Mientras, arriba a la derecha hay un botón "Entrar" que sugiere lo contrario. Verifiqué el código: el voto es anónimo vía localStorage (`fr_voter`) — funciona sin cuenta, pero el usuario no lo sabe hasta atreverse a tocar. Un 19-añero quemado de sign-up walls puede rebotar sin probar.
2. **La estrella se explica en jerga o en letra pequeña.** "Valoración oficial separada del ranking" es compacto pero no llano ("¿separada = no cuenta?"). La versión clara ("nunca alteran ese ranking orgánico") está en el footer a 0.78rem, donde nadie llega. Además existe una pestaña "**Equipo ★**" que SÍ ordena por estrellas — a primera vista parece contradecir el "no alteran el ranking" (son vistas distintas; el default Equilibrado es el orgánico, pero eso no se dice ahí).
3. **CONFIRMADO: falta el disclaimer de Supercell.** "Supercell" aparece SOLO como etiqueta de categoría (tag_labels). No existe en ninguna parte "proyecto fan, no oficial, no respaldado por Supercell". El claim bar dice "no es oficial" pero es genérico, solo sale en perfiles no verificados, y está enmarcado como pitch de "reclámalo", no como aviso. La Fan Content Policy de Supercell exige una fórmula específica de no-afiliación; no está.

## Mi primera acción y qué me frenaría (rol: fan de 19)

- **Haría:** tocar VOTAR en una idea del podio que me suene (coste percibido ~0). Proponer la mía sería lo segundo.
- **Me frenaría:** (a) no saber si el voto cuenta sin cuenta (el "Entrar" me hace sospechar un muro); (b) si el ranking de Brawl Stars está vacío o flojo, no hay nada que votar y me voy; (c) no veo qué pasa después de votar (¿lo verá alguien de Supercell? el claim bar dice que el perfil NI está verificado — eso baja la motivación de votar "para que llegue").

## 3 arreglos concretos, priorizados (para DESPUÉS del 18-jul)

1. **Disclaimer Supercell (legal + confianza), footer + claim bar:** añadir la fórmula de la Fan Content Policy: "Este contenido no está afiliado, respaldado, patrocinado ni aprobado por Supercell y Supercell no es responsable de él." (ES/EN). Es el único punto con riesgo real (takedown/queja), no solo UX.
2. **Subir "sin cuenta" a la UI visible:** micro-texto ya redactado en el meta — ponerlo bajo "Proponer una mejora" y junto a los botones VOTAR: "Gratis, sin registro · 1 toque". Es la promesa nº1 de conversión y hoy solo la ve el buscador.
3. **Estrella en llano donde se mira:** signal strip → "Equipo ★ = opinión oficial · no mueve posiciones", y en la pestaña "Equipo ★" una línea "Vista aparte: el ranking real lo deciden fans e IA". El footer ya lo dice bien; nadie baja hasta ahí.

## Límite honesto

No ejecuté JavaScript: WebFetch solo ve el shell estático (renderiza casi vacío), así que todo sale del copy i18n y el orden del DOM embebidos en los 335 KB del HTML. NO pude verificar: si el perfil brawl-stars tiene ideas/votos vivos (datos vienen de Supabase en runtime), si el claim bar se muestra para ese perfil concreto, ni la jerarquía visual real en pantalla (tamaños/contraste). La conclusión "sin cuenta invisible en 5s" es sólida por ausencia de la cadena en el copy; la de "footer que nadie lee" es heurística UX, no medición.
