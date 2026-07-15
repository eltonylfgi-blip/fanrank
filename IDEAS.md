# FanRank — decisiones e ideas de producto

Este archivo es la única cola de ideas del repositorio. Una idea solo sube de prioridad si cambia una decisión real y tiene una señal externa que pueda confirmarla o refutarla.

## Estado actual publicado (hecho)

- Acceso directo con correo y contraseña una vez establecida; la recuperación permite crearla si la cuenta nació con enlace mágico.
- Sugerencias anónimas o vinculadas a una cuenta, con contacto siempre privado.
- Equipos verificados: propietario, administradores y colaboradores con corazones auditables.
- Perfil verificado de FanRank para recibir feedback sobre el propio producto.
- Estudio privado de propietario: seleccionar zona, escribir feedback, pegar/adjuntar captura, pedir perfiles y cambiar fotos.
- Fotos con metadatos de fuente, crédito y base de derechos. No se aceptan miniaturas de Google Imágenes como fuente.
- Solicitudes de promoción limitadas a perfiles: una idea concreta no puede comprar impresiones, votos indirectos, nota IA ni posición orgánica.
- Oferta FanRank Pro visible y cola privada de interés: precios por aportaciones válidas analizadas, no por riqueza, empleados ni asientos.
- Marca dual coherente: `FanRank ♥` para fans y público; `FanRank ★` únicamente dentro de un equipo verificado.

## Publicado y validado técnicamente (beneficio todavía pendiente)

- Enlaces HTTPS de apoyo y miniatura segura para vídeos concretos de YouTube, sin iframe ni subida de MP4.
- Telemetría separada de QA mediante `?qa=1` y contrato SQL alineado con los eventos emitidos.
- Bandeja privada de sugerencias y pruebas para `owner/admin` de un perfil verificado; el contacto solo aparece con consentimiento.
- Evidencia actual: 25/25 pruebas estáticas y 31/31 pruebas live; GitHub Pages desplegó `9d096c5`; una sesión productiva QA conservó `?qa=1`, rechazó un dominio falso de YouTube, creó la miniatura válida y mantuvo `fr_events` en 143→143. Esto demuestra mecanismo y despliegue, no beneficio de mercado.

## Experimento activo (máximo 72 horas)

No hay todavía un experimento de producto activo: el gate técnico ya pasó, pero hace falta uso humano posterior. El siguiente reloj empieza con exposición real, no con los tests.

### Gate previo — telemetría confiable

- Estado: `validated_mechanism`; beneficio pendiente.
- Decisión: si los eventos ya pueden seleccionar una mejora sin mezclar QA con uso real.
- Selector: contrato live acepta todos los eventos emitidos y una sesión con `?qa=1` produce cero filas.
- Deadline: 24 horas desde el despliegue; nunca más de 72 horas.

### Siguiente experimento — probar activación con personas reales

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
- Próximo aprendizaje: comparar el orden de la IA con 20 corazones de equipos verificados.
- Selector: tasa de acuerdo, ideas que el equipo considera mal ordenadas y cambios posteriores que mejoran ese acuerdo.
- Regla: una promoción nunca entra en el cálculo; un corazón del equipo aporta contexto limitado, no un número 1 automático.

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

- Estado: `validated_mechanism`; revisión visual local y productiva, Pages `9d096c5` y crítica adversaria sin P0/P1 fuera de Auth. Aceptación de Tony y beneficio siguen pendientes.
- Fuentes: corrección explícita de Tony + referencia generada por ChatGPT.
- Decisión que cambia: si la marca comunica fans + ranking + ganador sin explicación.
- Score: 76.
- Cambio mínimo: corazón carmesí detrás de `FAN`, `R-A-N` en 2-1-3, `K` legible y trofeo a la derecha.
- Selector: reconocimiento inmediato por Tony y cero overflow a 320/375/768/1440 px.
- Deadline: revisión visual y decisión dentro de 72 horas desde el despliegue.

### FR-2026-07-15-006 — retorno correcto desde Auth

- Estado: `planned_needs_identity`; prioridad P1. No se guarda aquí ningún correo, contraseña ni otro dato personal.
- Fuentes: fallo real repetido al volver desde enlaces de acceso o recuperación.
- Decisión que cambia: si una persona puede completar el acceso y regresar a FanRank con sesión válida.
- Score: 90.
- Cambio mínimo: verificar la URL pública y los redirects autorizados en Supabase; nunca incrustar credenciales ni automatizar la identidad de una persona.
- Selector: un flujo real de acceso o recuperación vuelve a la URL pública de FanRank, reconoce la sesión y no termina en localhost.
- Deadline: cerrar como validado, fallido o replanteado dentro de 72 horas desde que pueda realizarse el paso de identidad.

## Rutina `fanrank-mejora`

- Una única cola: este archivo. El estado privado solo guarda lock, hashes, IDs procesados y el experimento activo.
- Entradas: feedback real, eventos agregados confiables, fallos/tests, hasta 3 autosugerencias y una crítica externa abstracta.
- Dedupe por decisión + zona + causa y referencia canónica; una repetición suma evidencia, no crea otra tarjeta. Máximo 10 candidatas abiertas.
- Gate: score ≥70, una señal no-IA, cambio reversible, prueba que falle/pase y selector en ≤72 h.
- Límite: una implementación reversible por ciclo. Mientras se mide, la rutina solo observa o cierra el resultado.
- Nunca automatiza pagos, Auth/RLS/permisos, borrado, moderación/publicación de usuarios, datos personales ni cambios del ranking orgánico.
- Un test verde demuestra mecanismo; el beneficio solo se declara con uso, mercado o feedback posterior.

## Backlog no ránkeado

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
