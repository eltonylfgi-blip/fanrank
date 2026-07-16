# FanRank — contrato local para agentes

Antes de modificar producto, interfaz, datos o copy, lee completo `PRODUCT_INVARIANTS.json` y clasifica el cambio contra sus reglas activas.

- El feedback explícito y duradero de Tony se fusiona en `PRODUCT_INVARIANTS.json`; no se deja solo en el chat.
- No debilites una regla activa sin feedback explícito posterior, selector medible y prueba actualizada.
- Toda corrección repetible debe añadir o endurecer una prueba antes de publicarse.
- Trabaja FanRank en rondas sustanciales de extremo a extremo: prioriza una mejora de alta palanca, llévala por producto, visual, pruebas y producción, y concentra el efecto wow donde aumente comprensión o deseo de actuar; evita microcambios dispersos o adorno sin función.
- Mantén `♥` fans, `★` entidad verificada y `◆` impacto verificado como señales separadas.
- Ningún pago, recompensa o plan puede alterar directa o indirectamente el ranking orgánico.
- Verifica como mínimo 320, 375, 768 y 1440 px, foco visible y `prefers-reduced-motion`.
- Antes de cada commit o publicación ejecuta `git status --short`; si `PRODUCT_INVARIANTS.json` cambió fuera del parche actual, reléelo e integra su ciclo de vida en vez de sobrescribirlo. Dentro de MADRE ejecuta además `python ..\..\INVARIANTES\verificar.py fanrank`.
- Antes de afirmar que está listo ejecuta `python tests/test_fanrank.py` y `python tests/test_visual_regression.py`, y conserva la salida real.

Las reglas globales de MADRE siguen vigentes; este archivo solo añade el contrato específico de FanRank.
