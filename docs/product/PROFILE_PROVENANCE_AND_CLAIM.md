# PROFILE PROVENANCE AND CLAIM — perfiles no reclamados en FanRank

> **INVARIANTE P0: ninguna interacción de FanRank puede aparentar respaldo, colaboración o
> participación de una persona o entidad que no ha reclamado su perfil.**
>
> Origen: investigación legal (AEPD/BOE) del chat de GPT de Tony "Éxito y protección idea"
> (16-jul-2026) + regla FR-INV-010 de `PRODUCT_INVARIANTS.json` (estado PROPUESTA, pendiente de
> confirmación de Tony — regla 18 de CLAUDE.md). Este doc es el detalle operativo de esa regla.

## Qué es un perfil no reclamado
Una ficha creada por FanRank (o por fans) sobre una persona/entidad real que NO ha verificado su
identidad ni aceptado estar aquí. Es el estado por defecto de todo perfil al nacer.

## Reglas duras mientras el perfil no esté reclamado
1. **Sin insignia de verificación.** Nada que parezca un check/verificado.
2. **Sin afirmar colaboración**: prohibido "colabora con", "en FanRank", testimonios atribuidos,
   o cualquier texto que sugiera que la persona usa o aprueba la plataforma.
3. **Avatar tipográfico/genérico** (iniciales, color). Nunca una foto sin licencia comprobada
   (Google Imágenes NO es una licencia — FR-INV-008).
4. **Aviso visible**: "Perfil no reclamado — creado por fans a partir de información pública.
   ¿Eres tú? Reclámalo o pide su retirada." con enlace funcional.
5. **noindex** en la página del perfil (meta robots) hasta que se reclame.
6. **Retirada inmediata**: una solicitud verificada de la persona/entidad retira el perfil sin
   fricción ni negociación. La vía es visible en la propia página.
7. **Cero publicidad/patrocinio** en la página del perfil no reclamado (nada comercial junto a
   una identidad que no consintió).
8. **Datos**: solo información pública NO sensible, con fuente. Que algo sea accesible en
   internet no es base jurídica automática para cualquier tratamiento (criterio AEPD). Nunca
   convertir información personal en material generado que aparente asociación comercial.

## Al reclamar (flujo)
- Verificación con recorrido corto (FR-INV-006) → la entidad decide foto oficial (press kit),
  quita el aviso, puede indexarse, y accede a las funciones de equipo verificado.

## Checklist antes de publicar CUALQUIER perfil real nuevo
- [ ] ¿Sin insignia ni texto de respaldo?
- [ ] ¿Avatar tipográfico?
- [ ] ¿Aviso de no reclamado + reclamar/retirar visible?
- [ ] ¿noindex presente?
- [ ] ¿Cero ads junto a la identidad?
- [ ] ¿Todo dato mostrado tiene fuente pública no sensible?
