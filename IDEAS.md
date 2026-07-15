# FanRank — decisiones e ideas de producto

Este archivo es la única cola de ideas del repositorio. Una idea solo sube de prioridad si cambia una decisión real y tiene una señal externa que pueda confirmarla o refutarla.

## Estado actual (hecho)

- Acceso directo con correo y contraseña una vez establecida; la recuperación permite crearla si la cuenta nació con enlace mágico.
- Sugerencias anónimas o vinculadas a una cuenta, con contacto siempre privado.
- Equipos verificados: propietario, administradores y colaboradores con corazones auditables.
- Perfil verificado de FanRank para recibir feedback sobre el propio producto.
- Estudio privado de propietario: seleccionar zona, escribir feedback, pegar/adjuntar captura, pedir perfiles y cambiar fotos.
- Fotos con metadatos de fuente, crédito y base de derechos. No se aceptan miniaturas de Google Imágenes como fuente.
- Solicitudes de promoción limitadas a perfiles: una idea concreta no puede comprar impresiones, votos indirectos, nota IA ni posición orgánica.
- Oferta FanRank Pro visible y cola privada de interés: precios por aportaciones válidas analizadas, no por riqueza, empleados ni asientos.
- Marca única con estrella-destello; el corazón queda reservado al interés de un representante verificado.

## Siguiente ciclo (máximo 72 horas)

### 1. Probar activación con personas reales

- Decisión: mantener la portada actual o simplificarla todavía más.
- Experimento: enviar enlaces directos a 5 perfiles y pedir a 5 personas que dejen una idea sin instrucciones.
- Selector: porcentaje que abre perfil, inicia sugerencia y la completa; tiempo hasta la primera sugerencia.
- Umbral: si menos de 3 de 5 completan, arreglar el paso exacto donde abandonan antes de añadir funciones.

### 2. Cerrar el bucle empresa → idea → decisión

- Decisión: qué información necesita una empresa para convertir una idea en acción.
- Experimento: usar FanRank como primera empresa y procesar 10 notas desde el Estudio.
- Selector: notas que terminan como `planned` o `done`, y tiempo medio hasta decisión.

### 3. Fotos iniciales con derechos

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

## Cola de ideas (hipótesis)

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
- Añadir más animaciones antes de medir activación: ya existe suficiente acabado visual para probar el flujo real.
