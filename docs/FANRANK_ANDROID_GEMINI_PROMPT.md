# FanRank Android — prompt maestro para Gemini

Versión: 1.0 · 2026-07-16

## Cómo usarlo

1. En Google AI Studio, elige **Build an Android app**.
2. Pega íntegro el bloque situado entre `INICIO DEL PROMPT` y `FIN DEL PROMPT`.
3. Si Gemini pide reducir alcance, dile: **«Implementa solo la Fase 1, pero conserva todas las fronteras, interfaces y pruebas descritas»**.
4. No pegues contraseñas, claves `service_role`, tokens ni datos privados. Si Gemini necesita configuración, debe crear únicamente nombres de variables y un archivo de ejemplo sin valores reales.

---

## INICIO DEL PROMPT

Actúa como un equipo senior formado por product manager, diseñador Android, arquitecto Kotlin, especialista en accesibilidad, ingeniero de seguridad y QA. Construye una app Android nativa llamada **FanRank**. No hagas una demo visual desechable: entrega un MVP compilable, navegable, testeable y preparado para conectarse después al backend real sin reescribir la app.

### 1. Qué es FanRank

FanRank convierte el feedback disperso de fans y clientes en ideas útiles y ordenadas para creadores, famosos, videojuegos, plataformas, IA y empresas.

- Una persona puede sugerir algo sin registrarse.
- La comunidad apoya ideas con corazones `♥`.
- La IA ayuda a clasificar, deduplicar y estimar utilidad, pero no oculta qué señal se está mostrando.
- Un perfil verificado puede tener propietario, administradores y colaboradores. Ellos expresan interés oficial con estrellas `★`, separadas del ranking orgánico.
- Una cuenta fan conserva sus aportaciones y construye un perfil de impacto que puede servir como portfolio de tester, UX, producto o comunidad.
- FanRank nunca vende una mejor puntuación, publicación, voto, exposición de una idea ni posición orgánica.

Promesa principal en español:

> Comparte una mejora en segundos. Los fans la apoyan y FanRank ayuda a que llegue ordenada a quien puede decidir.

La app debe funcionar en español e inglés desde el primer commit mediante recursos localizados, sin textos de interfaz escritos directamente en los composables.

### 2. Audiencias y trabajos que deben poder completar

#### Fan o visitante

1. Encontrar una persona, juego, plataforma o empresa.
2. Escribir una sugerencia inmediatamente, incluso antes de elegir el destinatario.
3. Añadir contexto opcional: imagen, captura, enlace HTTPS o vídeo de YouTube mediante URL y miniatura segura.
4. Enviar de forma anónima o vincularla a su cuenta.
5. Apoyar ideas con `♥`, compartir un ranking y seguir el estado de sus aportaciones.
6. Crear un perfil fan con sus mejores sugerencias, impacto y reconocimientos oficiales, manteniendo privado el contacto.

#### Propietario o equipo de un perfil verificado

1. Reclamar el perfil mediante una solicitud revisable; reclamar nunca concede permisos automáticamente.
2. Ver una bandeja privada de feedback y evidencia consentida.
3. Puntuar con estrellas oficiales: propietario de 1 a 5; cada miembro no propietario con tope individual 1 o 3 elegido por el propietario.
4. Invitar o revocar miembros según su rol, con un máximo inicial de cinco asientos no-owner con capacidad de puntuar.
5. Ordenar su bandeja por señal equilibrada, IA, fans y equipo sin modificar el ranking público.
6. Crear, editar y archivar temas para agrupar las ideas que pide a su audiencia; cada idea puede pertenecer como máximo a un tema.
7. Definir en el futuro una rúbrica estructurada de criterio, pública o privada, primero en modo sombra.

### 3. Semántica de marca obligatoria

- Marca pública y app launcher: **FanRank ♥**.
- **FanRank ★** aparece solo dentro del modo de equipo de un perfil verificado y autenticado. No es otra aplicación ni una insignia comprable.
- El logo público debe ser vectorial y escalable: corazón rojo neón integrado detrás de `FAN`; `R`, `A`, `N` sugieren un podio 2–1–3; trofeo vectorial visible a la derecha de `K`.
- No uses emojis como iconos estructurales. Corazón, estrella, trofeo, búsqueda, adjunto, perfil y navegación deben ser `ImageVector` o SVG coherentes.
- Evita por completo barridos rectangulares blancos, máscaras que corten letras o efectos que salgan del área del logo.
- Puede existir una flotación de marca muy sutil, máximo 2 dp de amplitud, solo en la cabecera, sin bloquear interacción. Desactívala con “reducir movimiento”, ahorro de batería o animaciones del sistema a 0.
- El corazón puede emitir un único pulso suave. Nada de animaciones continuas en listas, formularios o controles.
- Nunca reproduzcas audio automáticamente. Un toque explícito en el logo puede dar feedback háptico y, solo si el usuario activó “efectos de sonido”, un sonido corto.

### 4. Experiencia móvil y jerarquía

Usa Material 3 con un tema oscuro OLED legible, superficies azul noche, amarillo para la acción principal, azul/cian para navegación y rojo carmesí para el corazón. Mantén contraste WCAG AA, escalado de texto y una cuadrícula de 4/8 dp.

La navegación principal debe tener como máximo cuatro destinos:

1. **Descubrir**.
2. **Actividad**.
3. **Mi perfil**.
4. **Estudio**, solo si la sesión pertenece a un equipo verificado.

El botón global `Sugerir` puede ser un FAB o acción central persistente, pero nunca debe tapar campos, teclado, barra de gestos ni contenido.

#### Pantalla Descubrir

Orden por prioridad, no por decoración:

1. Logo compacto y acciones de cuenta/idioma.
2. Buscador con texto: `¿A quién o a qué quieres sugerirle algo?`.
3. Acción principal visible sin scroll: `♥ Hacer una sugerencia`.
4. Filtros por tipo y etiquetas: creadores de contenido, videojuegos, plataformas sociales, IA, empresas; Influencer, Streamer, YouTuber, TikToker y otras etiquetas recibidas del servidor.
5. Perfiles destacados/tendencia/activos.
6. Dos rankings globales claramente separados: `Más útiles según FanRank` y `Más apoyadas por la comunidad`.

El buscador ofrece resultados mientras se escribe, historial local borrable y estados vacíos accionables. Ejemplos iniciales de fixture: Orslok, Rubius, Ibai, Brawl Stars, Roblox, Discord, ChatGPT, Valorant y FanRank. No presentes estos fixtures como datos live.

#### Perfil de destino

- Nombre, imagen o icono, tipo `Creador de contenido`/empresa/juego/plataforma/IA y varias etiquetas simultáneas.
- Acción principal arriba: `♥ Sugerir a {nombre}`.
- Acción secundaria visible pero discreta: `¿Eres {nombre} o parte de su equipo? Reclama este perfil`.
- Tabs de ranking con descripción accesible: `Equilibrado`, `Solo IA`, `Apoyo original`, `Fans ♥` y `Equipo ★` cuando corresponda.
- Temas públicos en chips accesibles que filtran el ranking sin perder el orden elegido. Un tema archivado conserva su etiqueta en ideas históricas, pero no acepta nuevas sugerencias.
- Cada idea muestra título, resumen, categoría, evidencia, señal que explica su posición y acciones de apoyar/compartir.
- Una estrella oficial nunca se presenta como si fuera un corazón ni como garantía de número 1.

#### Compositor de sugerencias

Debe sentirse como un único flujo corto, no como dos formularios separados.

1. Campo principal grande: `¿Qué debería mejorar?`.
2. Destinatario: preseleccionado si se abrió desde un perfil; si no, se elige después de escribir.
3. Categoría opcional elegible: sugerencia, bug, contenido, accesibilidad, seguridad, rendimiento u otra. Si se omite, mostrar `FanRank la propondrá automáticamente`, siempre editable antes de publicar.
4. Contexto opcional progresivo: explicación, enlace y adjunto.
5. Tema opcional, ofrecido solo cuando el perfil seleccionado tiene temas activos. No inventes temas desde el cliente.
6. Identidad en el mismo panel: anónima públicamente por defecto; cuenta fan; o nombre privado y contacto privado con consentimiento explícito.
7. Resumen final y envío. Guardar borrador automáticamente.

Admite:

- Hasta tres pruebas combinadas entre imágenes y enlaces. En el primer contrato demo, cada imagen debe ser PNG, JPEG o WebP y ocupar como máximo 5 MB.
- Selector del sistema para galería/cámara/documento.
- Botón explícito `Pegar desde el portapapeles` que lea `ClipData` solo después del toque y muestre una vista previa antes de conservar nada.
- Recepción mediante Android Sharesheet (`ACTION_SEND`) de texto, URL o una imagen.
- URL HTTPS validada. Para YouTube acepta únicamente hosts e IDs exactos y deriva una miniatura segura; no insertes un WebView ni ejecutes HTML remoto.
- En el primer MVP no subas MP4. Muestra el límite con claridad.
- Compresión local razonable, tamaño máximo, cancelación, progreso, reintento y eliminación del adjunto antes de enviar.
- Elimina metadatos EXIF sensibles antes de una futura subida, preservando orientación y calidad visual.

Una sugerencia enviada entra en una bandeja privada con estado `received`; no aparece automáticamente como idea pública. Enseña un recibo local y la diferencia entre “enviada” y “publicada”.

#### Cuenta y perfil fan

- Permite usar el MVP sin cuenta.
- Explica el valor del registro después de una aportación, no mediante un muro previo: guardar historial, seguir estado, recibir reconocimiento y construir portfolio.
- Actividad muestra borradores, enviadas, en revisión, vinculadas a una idea pública y resueltas.
- Perfil fan público muestra solo alias, bio consentida, estadísticas agregadas y hasta tres sugerencias destacadas. Correo y contacto nunca son públicos.
- Si una empresa o creador reconoce una aportación, muestra una insignia trazable sin publicar la identidad privada de miembros del equipo.

### 5. Ranking, confianza y monetización: invariantes que el código no puede romper

Modela estas señales por separado:

- `aiScore`: utilidad base explicable.
- `fanHearts`: apoyo orgánico de fans.
- `sourceSupport`: apoyo importado o de fuente, si existe.
- `officialOwnerStars`: 0–5 del propietario.
- `officialTeamSupport`: agregado de miembros autorizados.

El orden público equilibrado actual es conceptualmente:

`organicScore = aiScore + min(fanHearts * 2, 20)`

Las estrellas del equipo ordenan una vista oficial separada y pueden ayudar a evaluar una futura rúbrica privada; no escriben ni alteran `organicScore`.

Guardas no negociables:

1. Pagar nunca cambia nota, aprobación, publicación, corazones, estrellas, exposición de una idea ni ranking orgánico.
2. Una futura tarifa de 1 € solo puede comprar un SLA de análisis privado más rápido, máximo una vez por idea, con crédito/reembolso si es spam, duplicado o no evaluable.
3. Como máximo 25 % de capacidad diaria podrá reservarse a análisis prioritario; la cola gratuita envejece para evitar inanición.
4. La moderación/publicación conserva su cola normal.
5. El criterio de una entidad será una rúbrica estructurada, versionada, con máximo ocho dimensiones y pesos validados; no un prompt libre con herramientas o red.
6. Una rúbrica privada solo ordena la bandeja privada. Una pública debe ser explicable. Ambas empiezan en shadow mode y registran versión de rúbrica/modelo, hash de entrada, fecha y resultado JSON estricto.
7. No implementes cobros, Play Billing, Stripe, workers IA ni notificaciones comerciales en el MVP. Crea interfaces y feature flags apagadas.
8. Los temas son una capacidad de organización, nunca una compra de visibilidad: `Normal=5`, `Pro=20`, `Business=100` y `Plus=200` temas activos por perfil. El servidor calcula el límite, cuenta solo los activos y lo aplica de forma atómica incluso con dos dispositivos a la vez. El cliente muestra el uso, pero jamás decide el permiso ni el cupo.

### 6. Arquitectura Android obligatoria

Tecnología:

- Kotlin actual estable.
- Jetpack Compose + Material 3.
- Single Activity, Navigation Compose y soporte de predictive back.
- Coroutines + Flow.
- Hilt para inyección.
- `collectAsStateWithLifecycle` para observar estado Compose.
- Room para borradores, caché, recibos y outbox.
- DataStore para preferencias no sensibles; Android Keystore/almacenamiento cifrado para sesión cuando corresponda.
- WorkManager únicamente para trabajos diferibles y reintentables como una outbox futura.
- Coil para imágenes.
- Un único cliente HTTP/Supabase detrás de interfaces; no mezcles dos librerías de red.
- Gradle Version Catalog, `ktlint` y `detekt` con configuración mínima que el proyecto realmente pueda ejecutar.
- `minSdk 26`, salvo evidencia concreta de que las dependencias elegidas permiten reducirlo sin degradar seguridad ni aumentar trabajo de compatibilidad.

Estructura modular propuesta:

```text
app/
core:model/
core:designsystem/
core:network/
core:database/
core:analytics/
core:common/
core:testing/
feature:discover/
feature:destination/
feature:suggest/
feature:activity/
feature:fanprofile/
feature:auth/
feature:teamstudio/
feature:settings/
```

Si el entorno de Gemini no soporta módulos Gradle múltiples de forma fiable, conserva exactamente estos límites como paquetes independientes dentro de un solo módulo y documenta la decisión. No sacrifiques un proyecto compilable por simular complejidad.

Usa flujo unidireccional de datos por pantalla:

- `UiState` inmutable.
- `UiAction`/`Intent` sellado.
- `UiEffect` solo para navegación, mensajes y acciones de una vez.
- ViewModels pequeños, sin llamadas HTTP directas desde composables.
- Modelos de dominio independientes de DTO, Room y Compose.
- Mapeadores explícitos y errores tipados recuperables.

Interfaces mínimas:

```kotlin
interface DirectoryRepository
interface RankingRepository
interface SuggestionRepository
interface FanProfileRepository
interface SessionRepository
interface TeamRepository
interface TopicRepository
interface AttachmentRepository
interface AnalyticsRepository
interface FeatureFlagRepository
```

Incluye dos implementaciones seleccionables por inyección:

- `Fake*Repository`: fixtures deterministas y fallos/latencia simulables para el MVP.
- `Supabase*Repository`: esqueleto aislado y apagado hasta pasar pruebas de contrato.

Nunca crees una clase `App.kt` gigante ni un `Repository` universal. Una feature no puede importar otra feature; ambas se comunican por modelos/core o navegación tipada.

### 7. Compatibilidad con el backend real de FanRank

El backend existente usa Supabase Auth, Postgres, RLS, Storage y Edge Functions. Sus tablas/vistas/RPC son la fuente de verdad; no inventes un esquema incompatible. Existen contratos con nombres como:

- Lectura pública: `fr_sections_stats`, `fr_ranking`.
- Escritura/revisión: `fr_submissions`, `fr_votes`, `fr_claims`.
- Recibo privado: `fr_submission_status`.
- Perfil fan: `fr_my_fan_profile`, `fr_upsert_my_fan_profile`, `fr_public_fan_profile`.
- Equipos: `fr_profile_team`, `fr_set_team_star`, `fr_my_team_stars`, `fr_set_team_star_cap`, `fr_create_profile_invite`, `fr_team_submission_inbox`.
- Temas: `fr_profile_topics_public`, los campos `topic_id`/`topic_title` de ranking y bandeja, y los RPC `fr_upsert_profile_topic`, `fr_archive_profile_topic`, `fr_set_idea_topic`.
- Consentimiento multimedia/IA: `fr_set_submission_ai_consent` y el registro de adjuntos existente.

No asumas firmas, campos ni permisos solo por estos nombres. Define DTO e interfaces desde un `BackendContract` versionado y marca cada endpoint `Unverified`, `VerifiedRead`, `VerifiedWrite` o `Disabled` hasta que una prueba contra el entorno real confirme firma, RLS y respuesta.

Restricción crítica conocida: la Edge Function web `fanrank-feedback-intake` actualmente exige un header `Origin` perteneciente a la allowlist web y rechaza un origen vacío. Una app Android nativa no debe falsificar ese header ni asumir que la subida funciona. Mantén multimedia remota en `FeatureFlag.NativeMediaUpload = false` y usa un `AttachmentRepository` adaptable hasta que exista una ruta server-side autenticada para móvil y una prueba E2E real. El MVP puede conservar el adjunto como borrador local y comunicar que se enviará cuando la integración esté disponible.

El cliente Kotlin de Supabase no debe filtrarse a features ni modelos de dominio. Aíslalo porque su evolución no puede obligar a reescribir la aplicación.

Configuración:

- Crea `local.properties.example` o mecanismo equivalente con `SUPABASE_URL=` y `SUPABASE_ANON_KEY=` vacíos.
- La anon key puede llegar al cliente bajo RLS correcto; una `service_role` jamás vive en Android, Git o logs.
- Ningún secreto ni correo real en fixtures, capturas o tests.
- El servidor/RLS decide autorización. El cliente nunca concede permisos por estado local, metadata de JWT o una bandera visual.
- Cada mutación debe tener clave de idempotencia, estado pendiente/enviado/fallido y reintento seguro.

### 8. Offline, enlaces y notificaciones

- Descubrir y rankings usan cache-first con indicador de antigüedad y refresco.
- Los borradores funcionan offline.
- La outbox no debe duplicar sugerencias al reintentar.
- Deep links previstos: perfil, idea, recibo privado, invitación de equipo y callback de Auth.
- No marques Auth como verificado hasta que un correo real abra la app en un dispositivo, importe la sesión, recupere la acción previa y no termine en `localhost`.
- Nunca pongas recibos, contactos ni tokens de invitación en logs o analytics.
- Notificaciones futuras: estado de sugerencia, reconocimiento, respuesta del equipo y análisis privado completado. Deben ser opt-in, agruparse y abrir el deep link exacto. En el MVP solo crea la interfaz y una implementación fake.

### 9. Telemetría útil y privada

Define eventos de dominio tipados, pero no escribas nombres nuevos directamente en Supabase. `AnalyticsRepository` debe mapearlos al contrato actual del servidor:

- `ScreenViewed` → `page_view`.
- `SearchSubmitted` → `search`.
- `ProfileOpened` → `profile_open`.
- `SuggestionOpened` → `suggest_open`, con origen no personal.
- `SuggestionSubmitted` → `submission`.
- `IdeaVoted` → `vote`.
- `IdeaShared` → `idea_share`.
- `ClaimSubmitted` → `claim_request`.
- `SignInStarted` → `auth_open`.
- `AuthLinkRequested` → `auth_link_requested`.
- `SignedIn` → `auth_signed_in`.
- `DraftSaved`, `ClaimOpened` y errores detallados permanecen solo en el sink local hasta que una migración añada nombres permitidos y su test de contrato pase.

Crea un enum `ServerEventName` que refleje exactamente el `fr_events_event_check` vigente; ninguna feature puede enviar strings libres. Un evento desconocido se descarta de forma visible en debug y nunca se reintenta contra producción.

No envíes texto de sugerencias, URLs privadas, correos, nombres, contacto, tokens ni imágenes a analytics. En debug/QA usa un sink local y no mezcles esos eventos con producción.

### 10. Fases de construcción y condición de parada

#### Fase 0 — contrato y esqueleto

- Crear proyecto, módulos/paquetes, design tokens, navegación tipada, modelos, interfaces y fixtures.
- Registrar en `APP_SPEC.md` esta especificación como fuente de verdad.
- Registrar decisiones irreversibles en ADR cortos; no crear un documento nuevo para cada detalle reversible.

#### Fase 1 — ejecutar ahora

Entrega un MVP totalmente navegable con repositorios fake:

1. Descubrir con buscador, filtros y rankings globales.
2. Perfil de Orslok y al menos otro destino.
3. Compositor suggestion-first con borrador, destinatario, categoría, identidad y adjunto local simulado.
4. Temas fake en perfiles y compositor, con filtro público y un gestor demo en modo equipo que represente los cuatro cupos sin fingir una compra.
5. Actividad y perfil fan de ejemplo.
6. Tema visual público `♥`, modo de equipo `★` solo mediante una feature flag de demo claramente etiquetada.
7. Estados loading, empty, error, offline y success.

Ejecútalo en checkpoints que siempre deben dejar el proyecto compilable:

- **1A · Esqueleto:** proyecto, tema, navegación, modelos, interfaces, fixtures y una pantalla mínima. Ejecuta build y tests.
- **1B · Descubrir:** buscador, filtros, rankings y perfil de Orslok. Ejecuta build, tests y una prueba UI del recorrido.
- **1C · Sugerir:** compositor, selección tardía de destinatario, validación, adjunto local fake y borrador Room. Ejecuta build, tests unitarios y prueba UI del envío demo.
- **1D · Actividad y calidad:** actividad/perfil fan fake, estados, accesibilidad y screenshots. Ejecuta build, lint y suite completa.

Si un checkpoint queda rojo, corrígelo antes de generar el siguiente; no acumules código no compilado. Para al completar 1D. No finjas conexión live, Auth, IA, pagos, uploads ni notificaciones.

#### Fases siguientes — documentar, no activar

2. Integración Supabase solo lectura con pruebas de contrato.
3. Envío anónimo/voto/recibo con idempotencia y RLS probado.
4. Auth, actividad real y perfil fan.
5. Reclamo y Estudio de equipo verificado.
6. Multimedia nativa tras resolver la frontera de `Origin`.
7. Shadow mode de rúbrica privada.
8. Validación de demanda antes de cualquier cobro.

### 11. Criterios de aceptación de la Fase 1

Funcionales:

- Compila desde cero con un comando documentado.
- No necesita credenciales para ejecutar el flavor `demo`.
- Se puede escribir primero la sugerencia y elegir después el destinatario.
- Abrir desde un perfil preselecciona correctamente el destinatario.
- Un borrador sobrevive cierre y reapertura.
- Filtros combinables funcionan con fixtures multi-etiqueta.
- Filtrar por tema no cambia la pestaña de ranking; archivar un tema lo elimina del compositor pero conserva la etiqueta histórica.
- Dos altas simultáneas simuladas nunca superan el cupo del plan; el cliente trata el límite del servidor como fuente de verdad.
- Cambiar tabs modifica el orden y explica la señal elegida.
- El modo público nunca muestra acciones privadas del equipo.

Visuales y accesibilidad:

- Sin recortes ni scroll horizontal a 320, 360, 412 y 600 dp.
- Correcto en retrato, paisaje, tablet, teclado abierto y edge-to-edge.
- Touch targets de al menos 48×48 dp y separación suficiente.
- TalkBack anuncia rol, nombre, estado, tab seleccionada y resultado de envío.
- Orden de foco coincide con el visual.
- Soporta font scale 1.3 y 2.0 sin ocultar acciones; prefiere wrap antes que truncar.
- Contraste de texto normal al menos 4.5:1.
- Reduced motion elimina flotación/pulso; las funciones siguen disponibles.
- Ningún control depende de hover, color o gesto sin alternativa visible.

Calidad:

- Tests unitarios de scoring/proyecciones, filtros, validación de URL, state reducers, borradores e idempotencia.
- Tests Compose de los cuatro flujos principales y accesibilidad semántica básica.
- Screenshot tests en 320/360/412 dp para Descubrir, perfil, compositor y error.
- Test que impida usar `FanRank ★` fuera de una sesión de equipo verificada/fake explícita.
- Test que impida sumar estrellas al ranking orgánico.
- Test que impida activar multimedia nativa mientras el contrato esté `Unverified`.
- Cero warnings críticos de lint/detekt; si una regla se suprime, justifica el alcance exacto.

### 12. Entregables y traspaso anticaos

Entrega:

1. Árbol del proyecto.
2. Código completo por archivo, no pseudocódigo ni `TODO` silenciosos.
3. `README.md` con requisitos y comandos exactos para build/test/run.
4. `APP_SPEC.md` como única fuente de verdad de producto.
5. `ARCHITECTURE.md` breve con dependencias permitidas y diagrama.
6. `IMPLEMENTATION_STATUS.md` con cada capacidad en `fake`, `local`, `verified-read`, `verified-write`, `disabled` o `future`.
7. `NEXT_SAFE_STEP.md` con una sola acción siguiente, evidencia necesaria y rollback.
8. Archivos de ejemplo de configuración sin valores.
9. Tests y fixtures.

Reglas para que otra IA o Codex pueda continuar:

- Commits pequeños por capacidad; nunca mezclar arquitectura, backend y rediseño visual en uno.
- Antes de cambiar una interfaz, actualizar su test de contrato.
- Ninguna capacidad pasa de `fake` a `verified` por narración: requiere salida de test.
- No renombrar modelos/RPCs existentes sin migración y compatibilidad.
- No duplicar documentos: actualizar la fuente existente.
- No almacenar secretos, datos personales ni evidencia privada.
- Cada feature flag debe tener dueño, estado por defecto, criterio para activarse y criterio para borrarse.
- Si algo no compila o no está conectado, dilo literalmente en el estado; nunca lo presentes como terminado.

### 13. Tu respuesta y ejecución ahora

Primero resume en diez líneas las decisiones técnicas. Después crea el proyecto e implementa **solo la Fase 1**. Ejecuta build, tests y lint si el entorno lo permite y pega la salida literal. Si no puedes ejecutar algo, indica exactamente qué falta y no lo declares validado. Termina con:

- qué funciona de verdad;
- qué usa fixtures;
- qué está deliberadamente desactivado;
- riesgos conocidos;
- un único siguiente paso seguro para conectar el backend real.

No me hagas preguntas de gusto. Elige una solución coherente con esta especificación y avanza. Pregunta solo si una decisión podría exponer secretos, gastar dinero, publicar datos reales o romper de forma irreversible el backend existente.

## FIN DEL PROMPT

---

## Nota para quien continúe FanRank

Este prompt define fronteras y criterios; no demuestra que el proyecto generado por Gemini compile ni que el backend móvil esté conectado. Antes de integrar cualquier resultado en el repositorio web o en Supabase, exigir:

1. build Android reproducible;
2. tests de la Fase 1;
3. diff revisado sin secretos;
4. prueba de contrato por cada capacidad que deje de ser fake;
5. revisión explícita de RLS y de la incompatibilidad actual de `Origin` para multimedia nativa.
