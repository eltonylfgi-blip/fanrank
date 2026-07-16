# FanRank — decisiones e ideas de producto

Este archivo es la única cola de ideas del repositorio. Una idea solo sube de prioridad si cambia una decisión real y tiene una señal externa que pueda confirmarla o refutarla.

## Estado actual publicado (hecho)

- Acceso directo con correo y contraseña una vez establecida; la recuperación permite crearla si la cuenta nació con enlace mágico.
- Sugerencias anónimas o vinculadas a una cuenta, con contacto siempre privado.
- Equipos verificados: propietario, administradores y colaboradores con estrellas oficiales separadas del ranking orgánico.
- Perfil verificado de FanRank para recibir feedback sobre el propio producto.
- Estudio privado de propietario: seleccionar zona, escribir feedback, pegar/adjuntar captura, pedir perfiles y cambiar fotos.
- Fotos con metadatos de fuente, crédito y base de derechos. No se aceptan miniaturas de Google Imágenes como fuente.
- Solicitudes de promoción limitadas a perfiles: una idea concreta no puede comprar impresiones, votos indirectos, nota IA ni posición orgánica.
- Oferta FanRank Pro visible y cola privada de interés: precios por aportaciones válidas analizadas, no por riqueza, empleados ni asientos.
- Marca dual coherente: `FanRank ♥` para fans y público; `FanRank ★` únicamente dentro de un equipo verificado.
- CTA secundario de verificación desde portada que conserva `♥ Hacer una sugerencia` como acción principal y lleva a buscar/reclamar el perfil correcto.
- Temas por perfil para agrupar y filtrar ideas: Normal 5, Pro 20, Business 100 y Plus 200 activos; el cupo se aplica en servidor y ningún plan altera ranking o visibilidad.
- Descubrimiento directo por etiquetas visibles (`Influencer`, `Streamer`, `YouTuber`, `TikToker`) y tipo explícito `Creador de contenido`.
- Ranking de perfil legible y separable: `Equilibrado`, `Solo IA`, `Apoyo original`, `Fans ♥` y, cuando corresponde, `Equipo ★`.
- Contrato local versionado: `PRODUCT_INVARIANTS.json` conserva preferencias duraderas y `AGENTS.md` obliga a leerlas y probarlas antes de cada edición.
- Gramática de confianza: `♥` apoyo fan, `★` contexto oficial y `◆` resultado real verificado; ninguna señal comprada altera el ranking.

## Publicado y validado técnicamente (beneficio todavía pendiente)

- Enlaces HTTPS de apoyo y miniatura segura para vídeos concretos de YouTube, sin iframe ni subida de MP4.
- Telemetría separada de QA mediante `?qa=1` y contrato SQL alineado con los eventos emitidos.
- Bandeja privada de sugerencias y pruebas para `owner/admin` de un perfil verificado; el contacto solo aparece con consentimiento.
- Especificación Android para Gemini con checkpoints compilables, repositorios fake/real separados y guardas de ranking, pagos, Auth y multimedia nativa. Es un prompt probado, no una app construida.
- Evidencia actual: 30/30 pruebas estáticas y 36/36 al incluir límites live; la comprobación visual del logo, CTA fan y CTA de verificación pasa en 320 y 375 px sin recortar el conjunto. Esto demuestra mecanismo, no beneficio de mercado.

## Experimento activo (máximo 72 horas)

### FR-2026-07-15-007 — vista previa social que convierte un share en exposición medible

- Estado: `active`; una sola intervención reversible. Inicio: 2026-07-15 23:55 CEST. Vence: 2026-07-18 23:55 CEST.
- Decisión: mantener la tarjeta social grande o retirarla y probar un canal/mensaje distinto.
- Evidencia previa anonimizada: últimas 72 h `page_view=75` (13 visitantes), `profile_open=41` (4), `suggest_open=11` (6), `submission=1` (1), `vote=1` (1) e `idea_share=0`; desde el último pulso no llegó ningún evento ni sugerencia nueva.
- Defecto reproducible: el enlace publicado tenía `canonical` y `og:image` ausentes y `twitter:card=summary`, aunque ofrecía dos botones de compartir.
- Cambio único: tarjeta FanRank 1200×630 reproducible, `canonical`, Open Graph completo y `summary_large_image`. No cambia compositor, datos, Auth, ranking ni RLS.
- Selector técnico inmediato: HTML publicado referencia la imagen absoluta, la imagen responde 200 como PNG y mide exactamente 1200×630.
- Selector externo ≤72 h: `idea_share >= 1` y al menos 10 `page_view` con referencia `fan_share`/`idea_share`; éxito de activación si al menos 2 de esos visitantes hacen `suggest_open` o `vote`. Menos de 5 visitas referidas indica fallo de exposición/canal, no del compositor.
- Condición de parada: no iniciar otra mejora autónoma mientras el reloj siga abierto. Un test verde prueba el mecanismo; solo tráfico referido y acción posterior pueden probar efecto.
- Hipótesis distinta para el siguiente pulso si la exposición sigue en cero: colocar un único enlace directo a Orslok en una superficie propia con referencia medible; no volver a retocar la tarjeta.

### Gate previo — telemetría confiable

- Estado: `validated_mechanism`; beneficio pendiente.
- Decisión: si los eventos ya pueden seleccionar una mejora sin mezclar QA con uso real.
- Selector: contrato live acepta todos los eventos emitidos y una sesión con `?qa=1` produce cero filas.
- Deadline: 24 horas desde el despliegue; nunca más de 72 horas.

### Experimento posterior — probar activación con personas reales

- Decisión: mantener la portada actual o simplificarla todavía más.
- Experimento: enviar enlaces directos a 5 perfiles y pedir a 5 personas que dejen una idea sin instrucciones.
- Selector: porcentaje que abre perfil, inicia sugerencia y la completa; tiempo hasta la primera sugerencia.
- Umbral: si menos de 3 de 5 completan, arreglar el paso exacto donde abandonan antes de añadir funciones.

No se inicia otra mejora mientras este selector siga abierto. Los siguientes frentes quedan en la cola y se miden después:

### Cerrar el bucle empresa → idea → decisión

- Decisión: qué información necesita una empresa para convertir una idea en acción.
- Experimento: usar FanRank como primera empresa y procesar 10 notas desde el Estudio.
- Selector: notas que terminan como `planned` o `done`, y tiempo medio hasta decisión.

### Fotos iniciales con derechos

- Decisión: subir foto o mantener icono para cada perfil.
- Fuente aceptable: press kit oficial, Wikimedia Commons con licencia comprobada, dominio público, subida del titular o imagen generada para FanRank.
- Selector: apertura de perfiles con foto frente a icono y errores/reclamaciones de derechos (objetivo: cero).

## FanRank Pro — hipótesis monetizable y juez en 72 horas

Invariante: ningún pago puede modificar directa ni indirectamente el ranking orgánico. La IA privada aprende el encaje con el equipo, pero ese aprendizaje nunca reordena la clasificación pública.

Métrica de valor: **aportaciones válidas analizadas al mes**. No cuentan votos, spam ni duplicados fusionados.

- Signal · 149 €/mes: 1 perfil, 1.000 aportaciones válidas y 2 briefs trazables al mes.
- Decision · 449 €/mes: 3 perfiles, 5.000 aportaciones y 8 briefs al mes.
- Portfolio · 999 €/mes: 10 perfiles, 20.000 aportaciones y 20 briefs al mes.

Primer experimento, antes de automatizar correo, cobros o IA avanzada:

1. Oferta única: **Piloto fundador · 199 € durante 14 días**.
2. Entrega manual asistida: dos digests diferenciales, dos briefs de implementación y un perfil.
3. Cada brief enlaza evidencia, separa hechos de hipótesis e incluye alcance mínimo, experimento, métrica de éxito y condición de fracaso.
4. Confirmación: al menos 1 de 15 responsables paga y selecciona una oportunidad para investigar.
5. Refutación: 0 pagos después de 8 aperturas y 3 respuestas o conversaciones. Si nadie abre, el fallo es distribución, no precio/producto.

La cola `fr_pro_requests` registra intención y segmento sin fingir checkout. No se construyen Stripe, digests automáticos, Portfolio ni integraciones hasta que el piloto cambie esa decisión.

## Promoción pagada — solo perfiles, cobro aún no activado

La cola `fr_promotion_requests` mide demanda sin fingir que ya existe un pago. Para activar cobros reales hacen falta una cuenta de Stripe y datos bancarios del titular; esa parte requiere identidad humana.

Flujo previsto:

1. Un representante verificado elige un perfil y una meta. Nunca puede elegir una idea concreta.
2. Una función segura del servidor crea Stripe Checkout; ninguna clave secreta vive en el navegador.
3. Un webhook firmado confirma el pago y crea una campaña con presupuesto y fechas.
4. La interfaz muestra siempre `Patrocinado`, quién promociona y por qué se ve.
5. La campaña solo altera espacios publicitarios del perfil; `ai_score`, votos y ranking orgánico quedan inmutables.
6. Métricas: impresiones, aperturas del perfil y nuevas sugerencias válidas; nunca se vende una posición orgánica.

Gate de lanzamiento: no cobrar hasta que existan al menos 3 solicitudes reales de promoción o una empresa confirme intención de pago. Antes de eso, construir Checkout sería coste sin evidencia.

## Ranking IA — mejora útil, no caja negra

- Mantener visibles las señales: utilidad base, demanda de fans e interés limitado del equipo.
- Próximo aprendizaje: comparar el orden de la IA con 20 valoraciones de equipos verificados.
- Selector: tasa de acuerdo, ideas que el equipo considera mal ordenadas y cambios posteriores que mejoran ese acuerdo.
- Regla: una promoción nunca entra en el cálculo; una estrella del equipo aporta contexto oficial separado, no un número 1 automático.

## Criterio de entidad y evaluación prioritaria — especificación segura, no implementada

El criterio no será un prompt libre con poder sobre el ranking. Será una rúbrica estructurada, versionada e inmutable por evaluación, con máximo ocho dimensiones y pesos validados. Solo `owner/admin` puede editarla o activarla. La entidad elige una proyección `public` explicable o `private`; la privada solo ordena su bandeja y nunca escribe `ai_score`, votos, publicación ni ranking público.

El modelo recibe la rúbrica como datos no confiables, sin herramientas ni red, y devuelve JSON estricto. Cada resultado conserva versión de rúbrica, versión de modelo, fecha y hash de entrada. Primero funciona en `shadow mode`: se compara con estrellas reales antes de permitir que ordene la bandeja privada.

Una futura tarifa de 1 € solo podría comprar un SLA de análisis privado:

1. Nunca compra mejor nota, aprobación, publicación, exposición, corazón, estrella ni ranking.
2. Máximo una prioridad por idea; spam, duplicado o imposibilidad de evaluar implica devolución o crédito.
3. La publicación/moderación mantiene su cola normal. Como máximo el 25 % de la capacidad diaria se reserva a análisis prioritarios; el 75 % sigue siendo gratuito y envejece para evitar inanición.
4. El pago se confirma por webhook firmado e idempotente; después se crea el trabajo y una notificación privada en cuenta. El navegador nunca confirma el cobro.
5. Gate: no construir Checkout hasta tener un perfil verificado y, sobre al menos 50 exposiciones elegibles, 5 solicitudes de prioridad y 2 confirmaciones explícitas de intención de pago.

## Equipo verificado — guardas antes de abrirlo a terceros

- El propietario conserva 1–5 ★. Cada miembro no propietario tiene un límite individual de 1 o 3 ★ elegido por el propietario.
- Antes del primer equipo externo: máximo cinco asientos con voto no-owner, aplicado al aceptar invitaciones. Los asientos extra, si llegan a existir, serán solo lectura y nunca se venderá más capacidad de voto.
- Vista privada para `owner/admin` con idea, miembro, rol, estrellas y fecha. El público solo ve agregados; la identidad individual no se expone.
- Estas estrellas sirven para la pestaña oficial y para aprender el criterio privado; no modifican el orden orgánico.

## Cola IA ránkeada — 2026-07-15

Fuentes: dirección explícita de Tony, auditoría Codex de código y datos, tres revisores independientes y crítica adversaria de ChatGPT. Tres IAs repitiendo lo mismo cuentan como una hipótesis, no como tres usuarios.

Puntuación 0–100: valor para fan/entidad (25) + evidencia independiente (25) + alcance (15) + selector ≤72 h (15) + reversibilidad (10) + bajo esfuerzo (10). Una idea solo de IA no puede superar 49 ni autoimplementarse.

### FR-2026-07-15-001 — reparar telemetría y excluir QA

- Estado: `validated_mechanism`; 25/25 estáticas, 31/31 live y QA productivo 143→143. Beneficio no medido.
- Fuentes: fallo reproducible en `fr_events`; auditoría de producción.
- Decisión que cambia: si las métricas pueden seleccionar la siguiente mejora.
- Score: 96.
- Cambio mínimo: contrato SQL = eventos emitidos y `?qa=1` sin telemetría.
- Selector: cero eventos rechazados y cero filas nuevas durante una sesión QA.
- Deadline: 24 horas desde el despliegue; cierre obligatorio antes de 72 horas.

### FR-2026-07-15-002 — enlaces YouTube con miniatura segura

- Estado: `validated_mechanism`; SQL v10/v11 y Edge v3 live, Pages `9d096c5`, vista previa de Orslok y rechazo de host falso comprobados. Valor no medido.
- Fuentes: petición explícita de Tony para Orslok + revisión de seguridad.
- Decisión que cambia: si un enlace estructurado genera sugerencias más concretas para creadores.
- Score: 88.
- Cambio mínimo: HTTPS, hosts/ID exactos, miniatura derivada, sin iframe ni fetch arbitrario.
- Selector: primera sugerencia real con enlace válido; cero URL rechazada erróneamente y cero incidente de privacidad.
- Deadline: 72 horas desde el despliegue.

### FR-2026-07-15-003 — reducir abandono del compositor

- Estado: candidate.
- Fuentes: embudo histórico todavía contaminado; requiere nueva línea base limpia.
- Decisión que cambia: qué único paso del formulario simplificar.
- Score: 84.
- Cambio mínimo: solo el paso con mayor abandono, no un rediseño completo.
- Selector: `submission / suggest_open` con denominador ≥5 o tres personas independientes.

### FR-2026-07-15-004 — FanRank Lab para autosugerencias transparentes

- Estado: candidate.
- Fuentes: petición de Tony + revisión anticaos.
- Decisión que cambia: si hacer visible el razonamiento de mejora aumenta confianza o solo añade ruido.
- Score: 79.
- Cambio mínimo: mostrar ideas IA etiquetadas y separadas del ranking orgánico; jamás fingir que vienen de usuarios.
- Selector: aperturas/votos reales frente a espacio consumido; se descarta sin interacción.

### FR-2026-07-15-005 — logo corazón + podio + trofeo

- Estado: `validated_mechanism`; cuarta corrección preparada tras otro recorte visual explícito de Tony. Beneficio y aceptación final siguen pendientes.
- Fuentes: corrección explícita de Tony + geometría DOM + crítica adversaria de ChatGPT con evidencia anonimizada.
- Decisión que cambia: si la marca comunica fans + ranking + ganador sin explicación.
- Score: 76.
- Cambio mínimo: corazón carmesí detrás de `FAN`, `R-A-N` en 2-1-3, `K` legible y trofeo a la derecha.
- Defecto reproducido: además del barrido antiguo, el texto inclinado con `background-clip:text` se cortaba dentro de cada letra y la regla móvil reducía el margen de seguridad. El ancho total podía pasar aunque el contenido interno siguiera recortado.
- Prueba directa local: padding compensado por letra, margen exterior móvil y captura real tras recarga. A 320 px el conjunto ocupa x=24,7–280,9 con trofeo x=221,4–255,7 dentro de 306 px útiles; a 375 px ocupa x=30,2–330,0 dentro de 360 px útiles. Corazón, `FANRANK`, podio, trofeo y etiqueta son visibles.
- Selector: reconocimiento inmediato por Tony; la geometría ya pasa, pero no sustituye su juicio de marca.
- Deadline: revisión visual y decisión dentro de 72 horas desde el despliegue.

### FR-2026-07-15-006 — retorno correcto desde Auth

- Estado: `planned_needs_identity`; prioridad P1. No se guarda aquí ningún correo, contraseña ni otro dato personal.
- Fuentes: fallo real repetido al volver desde enlaces de acceso o recuperación.
- Decisión que cambia: si una persona puede completar el acceso y regresar a FanRank con sesión válida.
- Score: 90.
- Cambio mínimo: verificar la URL pública y los redirects autorizados en Supabase; nunca incrustar credenciales ni automatizar la identidad de una persona.
- Selector: un flujo real de acceso o recuperación vuelve a la URL pública de FanRank, reconoce la sesión y no termina en localhost.
- Deadline: cerrar como validado, fallido o replanteado dentro de 72 horas desde que pueda realizarse el paso de identidad.

### FR-2026-07-16-008 — descubrimiento y ranking sin nombres engañosos

- Estado: `validated_mechanism`; no abre un experimento nuevo y conserva el selector activo de distribución.
- Fuentes: petición explícita de Tony + auditoría UX del producto real + revisión externa con evidencia anonimizada.
- Decisión que cambia: si una persona encuentra a quién sugerirle algo y entiende qué señal está ordenando las ideas.
- Score: 91.
- Cambio mínimo: copy de intención, `Creador de contenido`, filtro visible por etiquetas y separación `Equilibrado`/`Solo IA`/`Fans`/`Equipo`.
- Prueba directa: filtro `Influencer` devuelve Rubius, Orslok e Ibai; CTA termina a 420 px en 320×667; 26/26 estáticas y 32/32 con live.
- Selector ≤72 h: con 5 personas externas, al menos 4 encuentran un creador concreto en ≤15 segundos y explican que las estrellas oficiales no alteran el ranking orgánico.

### FR-2026-07-16-009 — rúbrica de entidad y SLA privado de 1 €

- Estado: `candidate`; no implementar pago ni worker todavía.
- Fuentes: petición explícita de Tony + auditoría de fairness + crítica adversaria con evidencia anonimizada.
- Decisión que cambia: si existe demanda real para acelerar un análisis privado sin corromper el ranking.
- Score: 49 mientras solo exista señal de una persona y ninguna entidad verificada usuaria.
- Cambio mínimo siguiente: botón no cobrable de interés, solo después de Auth estable y un perfil reclamado.
- Selector: 5 solicitudes sobre 50 exposiciones elegibles y 2 confirmaciones de intención de pago; cualquier petición de “pagar para subir” refuta el encaje y obliga a aclarar la promesa.

### FR-2026-07-16-010 — límite de equipo y auditoría privada de estrellas

- Estado: `planned_before_external_team`; P1 de integridad, no bloquea el uso fan actual.
- Fuentes: inspección directa de migraciones/RPC: existen límites de valor por rol, pero no límite de miembros ni auditoría por idea para `owner/admin`.
- Decisión que cambia: si se puede abrir la colaboración verificada sin permitir inflación coordinada de la señal oficial.
- Score: 94.
- Cambio mínimo: cinco asientos votantes no-owner, `star_cap` individual 1/3 y RPC privada de auditoría; sin alterar ranking orgánico.
- Selector: test de aceptación concurrente impide el sexto asiento y owner/admin ve autor/valor/fecha de cada estrella; anon y contributors no pueden leer esa auditoría.

### FR-2026-07-16-011 — verificación visible + temas de audiencia

- Estado: `validated_mechanism`; beneficio externo pendiente y sin checkout.
- Fuentes: petición explícita de Tony + captura móvil real + crítica externa de ChatGPT con evidencia directa anonimizada.
- Decisión que cambia: si una entidad entiende el valor de reclamar su perfil sin reducir la conversión de fans, y si puede transformar una pregunta amplia en colecciones de feedback accionables.
- Cambio mínimo: CTA secundario `Solicitar verificación`, búsqueda en modo reclamo, temas públicos/privados gestionables por owner/admin y asignación desde compositor/bandeja.
- Guardas: cupos atómicos por perfil (`5/20/100/200` activos), RLS, funciones con comprobación de sesión y membresía verificada, temas archivados solo históricos y cero efecto sobre ranking/visibilidad.
- Prueba directa: migraciones live aplicadas, Edge Function activa con `topic_id`, 30/30 pruebas estáticas y 36/36 con fronteras live; anon no puede escribir ni usar RPC de gestión. Una transacción live aceptó exactamente cinco temas Normal, rechazó el sexto y el rollback dejó `rollback_residue=0`.
- Guarda de reclamo: resultados verificados ya no reciben `claim=1`; el deep link manual se limpia sin abrir Auth/formulario y un trigger live rechazó el claim incluso mediante escritura privilegiada (`verified_claim_rejected=true`, rollback sin residuo).
- Selector externo ≤72 h desde tener tráfico elegible: `owner_cta_open / page_view ≥ 10 %` con al menos 30 visitas, al menos una solicitud de perfil iniciada y caída de `suggest_open / page_view` menor de 10 % frente a la línea base. Sin 30 visitas se clasifica como falta de exposición, no fracaso de CTA.

### FR-2026-07-16-012 — identidad opaca + impacto verificado + memoria de producto

- Estado: `validated_mechanism`; aceptación visual y beneficio externo pendientes.
- Fuentes: corrección explícita de Tony + defecto reproducido en CSS/Android + comparación oficial Canny/Productboard + red-team de monetización.
- Decisión que cambia: conservar `FanRank` como marca confiable y separar el valor económico del orden público de ideas.
- Cambio mínimo: relleno opaco real en `FAN` y `RANK`, trofeo/podio mayores, `◆ Impacto verificado` explicado y contrato versionado de nueve invariantes activas.
- Guarda: no usar `FanRank$`, porcentajes automáticos ni recompensas retroactivas. Una recompensa solo puede aparecer tras acuerdo previo, atribución y pago verificables; jamás pesa en el ranking.
- Prueba directa local: computed style no transparente, podio mínimo 12/16/12 px, trofeo ≥1,25× la altura visible de `RANK`, cero overflow en 320/375/768/1440 y prueba que lee el contrato de invariantes.
- Selector ≤72 h: ≥80 % de cinco personas entiende que `◆` significa resultado confirmado y ninguna cree que se compra; las próximas tres ediciones deben preservar las reglas sin que Tony las repita.

### FR-2026-07-16-013 — el share lleva el top real y un clic directo a X (distribución)

- Estado: `validated_mechanism`; publicado en producción en `563928f` el 2026-07-16 14:05 CEST. Beneficio externo pendiente: esta implementación sirve al selector ya abierto de FR-2026-07-15-007, no abre otro experimento.
- Decisión que cambia: un share de perfil ya puede producir una exposición externa atribuible: incluye el top-3 público real, ofrece intents humanos de X/WhatsApp y aterriza en un receptor con OG propio del perfil.
- Cambio entregado, en el orden exigido: (1) top-3 ES/EN ≤255 caracteres con tercera idea elidida y fallback para <3 ideas; (2) intents X/WhatsApp con `ref=x|whatsapp` y eventos `intent_x|intent_whatsapp`; (3) head español unificado y `social-card.png?v=2`; (4) solo después de publicar 1–3 en `f22743e`, 11 stubs `/p/<slug>/` con canonical/OG propios y redirect que conserva `idea`, `ref`, `lang` y `qa`.
- Mantenimiento: al crear un perfil nuevo, ejecutar `python tools/generate_profile_stubs.py` y confirmar el nuevo `p/<slug>/index.html` antes de publicar.
- Evidencia cruda: `python tests/test_fanrank.py` → `Ran 37 tests in 0.796s` / `OK`; `python tests/test_visual_regression.py` → `Ran 10 tests in 18.025s` / `OK`; `[MEASURE] cold_anonymous_vote_seconds=1.515 viewport=320 intercepted_writes=1`; `[MEASURE] share_dialog_viewport=320 scroll_width=320 text_chars=209`; verificador rector → `[RESULTADO] CUMPLIDA=1 REQUIERE-OJO=10 INCUMPLIDA=0`.
- Producción: Pages build `1098497332` → `built`, commit `563928f07f1a4eaac6ddac03eb0639914fdcea40`; `curl` de 11/11 stubs → HTTP 200, `canonical_ok=true`, `keys_ok=true`, `redirect_ok=true`, `noscript_ok=true`, `image_v2=true` y `og_url` propio. La previsualización interactiva en metatags.io queda pendiente porque la política del navegador bloqueó esa URL; no anunciar como validada por un debugger externo hasta completar ese único check.
- Guardas: ningún bot, post automático, voto/idea falsa, etiqueta automática, pago, ranking, canvas ni marca nueva. El humano decide si publica el intent.
- Selector ≤72 h desde 2026-07-16 14:05 CEST: el de FR-2026-07-15-007 (`idea_share ≥ 1` y ≥10 `page_view` referidos), desglosando `intent_x`/`intent_whatsapp`; si no hay exposición, no confundir falta de distribución con fallo del mecanismo.

### FR-2026-07-16-014 — precios fundador invertidos (5 € fan / 15 € o libre entidad) + test de marca FAN$

- Estado: `validated_mechanism` para precios/módulo; publicado en producción en `6769e7b` el 2026-07-16 14:37:12 CEST. Beneficio externo pendiente: el test FAN$ sigue bloqueado hasta ≥100 visitantes y la marca pública continúa `FanRank ♥`. Petición explícita de Tony (16-jul, chat, aprox. literal: "mejor al revés: 5 euros para usuario normal fundador porque son los 500 primeros, y 15 para las empresas o famosos, o que puedan donar lo que quieran").
- Decisión que cambia: qué etiqueta de precio maximiza clics de interés GENUINOS por lado (fan vs entidad) — línea base actual ~0 clics, cualquier señal ya informa.
- Cambio mínimo:
  1. `Fan fundador`: 15 € → **5 € pago único**, limitado a los **primeros 500**, con promesa de insignia NUMERADA ("Fundador #N de 500") — la investigación 16-jul respalda que el número bajo convierte escasez en estatus; nada de contadores fingidos.
  2. Lado entidad: el Piloto 199 € SIGUE siendo LA señal B2B (no se toca). Se añade, como módulo separado y opcional, "Apoyo de entidad — 15 € o aportación libre", también interés-sin-cobro.
  3. TODO sigue en modo "Prueba de interés · Todavía no se cobra" (FR-INV-005 intacta; cobrar de verdad sigue bloqueado por unlock_when + Stripe/identidad = Tony).
- Test de marca FAN$ (el $ dentro de FANS, deseo reiterado de Tony 2×): FR-INV-001 exige test ANTES de renombrar, así que no se discute: SE MIDE. Gate: con ≥100 visitantes reales acumulados, probar 2 variantes del artefacto compartido (`FanRank ♥` vs `FAN$RANKS`) midiendo (a) confianza — "¿crees que pagar mejora la posición de una idea?" debe seguir <10 % sí — y (b) participación (CTR/votos por variante). Hasta pasar ese test: marca pública = FanRank ♥. El "Rango S" de Tony puede probarse ANTES como INSIGNIA de las ideas top (estética gamer S-tier, no toca la marca ni promete dinero).
- Prueba que falle antes/pase después: test estático que exige el nuevo precio/tope 500 en la oferta fan y el módulo de entidad separado con su etiqueta interés-sin-cobro.
- Evidencia cruda local: rojo previo → `Ran 38 tests in 0.727s` / `FAILED (failures=1)` solo por los seis marcadores nuevos ausentes; verificador rector final → `Ran 38 tests in 0.735s` / `OK`, `Ran 10 tests in 23.194s` / `OK`, `[MEASURE] cold_anonymous_vote_seconds=1.553 viewport=320 intercepted_writes=1` y `[RESULTADO] CUMPLIDA=1 REQUIERE-OJO=10 INCUMPLIDA=0`.
- Evidencia cruda producción: Pages build `1098541614` → `built`, commit `6769e7b9e99bcd431d939173fcdf74119c64f646`; Playwright sobre `?qa=1` a 320/375 px → HTTP 200, `fan_card_count=3`, botones mínimos `68/44 px`, entidad `68/68 px`, `no_horizontal_overflow=true`, `fake_counter_nodes=0`, `checkout_nodes=0`, ambos `aria-pressed=true`, `page_errors=[]`, `failures=[]`. La primera aserción del script de producción dio falsos negativos por codificación de literales Unicode en la tubería PowerShell; el DOM ya devolvía el texto correcto y la repetición con escapes ASCII cerró el fallo del instrumento.
- Corte de línea base: 2026-07-16 14:37:12 CEST, SHA `6769e7b`; no mezclar `fan_founder_15_once` anterior con `fan_founder_5_once` ni `entity_support_15_or_open`. Selector ≤72 h: impresiones `offer_seen:fan_offers` / `offer_seen:entity_support` y clics únicos seudónimos por valor; un test verde solo valida mecanismo, no demanda.

## Rutina `fanrank-mejora`

- Una única cola: este archivo. El estado privado solo guarda lock, hashes, IDs procesados y el experimento activo.
- Entradas: feedback real, eventos agregados confiables, fallos/tests, hasta 3 autosugerencias y una crítica externa abstracta.
- Dedupe por decisión + zona + causa y referencia canónica; una repetición suma evidencia, no crea otra tarjeta. Máximo 10 candidatas abiertas.
- Gate: score ≥70, una señal no-IA, cambio reversible, prueba que falle/pase y selector en ≤72 h.
- Límite: una implementación reversible por ciclo. Mientras se mide, la rutina solo observa o cierra el resultado.
- Nunca automatiza pagos, Auth/RLS/permisos, borrado, moderación/publicación de usuarios, datos personales ni cambios del ranking orgánico.
- Un test verde demuestra mecanismo; el beneficio solo se declara con uso, mercado o feedback posterior.

## Backlog no ránkeado

- Tarjeta canvas descargable por perfil (PNG 1080×1920, piel "papeleta/setlist", nombre enorme, top-3 con barras, #1 truncada, URL impresa en la imagen; logo con corazón intacto). Detrás de los stubs: el PNG no arregla lo que ven los crawlers. Variante posterior: tarjeta de estatus del fan ("Mi idea es #N de M" / "Fundador #N") — la investigación 16-jul la señala como el share de mayor conversión (identidad del que comparte, no del producto).
- Umbrales estilo LEGO Ideas (una idea necesita N apoyos en X días para seguir listada; con dueño verificado pasa a "en revisión") + métrica de salud pública "ideas con respuesta del dueño" — los tablones de marca muertos (Starbucks/Dell) murieron de ideas sin responder y podredumbre de duplicados.
- Leaderboard de rivalidad entre fandoms ("qué fandom mueve más su tablón") — BLOQUEADO hasta tener anti-abuso (rate-limit por IP/fingerprint + pesos de voto): es el canal gratuito más potente encontrado Y garantiza boteo que rompería FR-INV-005.
- Detección semántica de duplicados antes de enviar, con explicación y opción de votar la existente.
- Resumen semanal para equipos: 5 cambios con mayor beneficio esperado y evidencia enlazada.
- Estado público de una idea: recibido, estudiando, planificado, lanzado; el contacto del autor sigue privado.
- Importación oficial desde Discord/X/YouTube cuando la plataforma o creador autorice el canal.
- Perfiles reclamables con dominio/correo oficial y revisión humana, sin verificaciones automáticas débiles.
- Página pública de campañas de perfiles patrocinados para auditar gasto, anunciante e impresiones.

## Ideas descartadas por ahora

- Copiar fotos encontradas en Google: riesgo de derechos y atribución; solo se usa Google para descubrir la fuente original.
- Vender un mejor ranking de IA: destruye confianza y mezcla utilidad con dinero.
- Promocionar una idea concreta: las impresiones compradas podrían generar votos y comprar ranking de forma indirecta.
- Automatizar la creación de cuentas o usar contraseñas del titular: riesgo de identidad; el usuario siempre escribe sus credenciales.
- Añadir más animaciones decorativas aparte de la corrección solicitada del logo: el siguiente juez es activación real, no más brillo.
