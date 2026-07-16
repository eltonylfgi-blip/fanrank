(function(){
  "use strict";

  var COPY = {
    es:{
      studio:"Estudio",studio_title:"Estudio de propietario",studio_intro:"Control privado de FanRank. Solo aparece para cuentas autorizadas.",
      studio_note:"Tus notas, capturas y solicitudes se guardan en una cola privada. Nada se publica automáticamente.",
      feedback:"Feedback visual",feedback_copy:"Selecciona una zona y explica exactamente qué cambiar.",
      profile_request:"Añadir perfil",profile_request_copy:"Guarda un famoso, empresa, juego o plataforma para investigar.",
      photo:"Cambiar foto",photo_copy:"Sube una imagen con fuente y derechos comprobables.",queue:"Cola privada",queue_empty:"La cola está vacía.",
      select_zone:"Seleccionar zona",zone_banner:"Haz clic en la zona de FanRank que quieres comentar.",cancel:"Cancelar",close:"Cerrar",
      feedback_title:"Feedback de una zona",feedback_intro:"La captura es opcional y siempre queda privada.",zone:"Zona",priority:"Prioridad",
      normal:"Normal",high:"Alta",low:"Baja",message:"Qué quieres cambiar *",screenshot:"Captura opcional",screenshot_help:"Adjunta JPG, PNG o WebP; también puedes pegar una captura en el texto.",
      send_feedback:"Guardar feedback",feedback_ok:"Feedback guardado en la cola privada.",file_ready:"Captura preparada",done:"Marcar hecho",done_ok:"Marcado como hecho.",
      request_title:"Nuevo perfil para investigar",request_intro:"FanRank lo guarda; la imagen se buscará después en una fuente oficial o con licencia.",
      name:"Nombre *",kind:"Tipo",notes:"Notas o contexto",creator:"Creador",company:"Empresa",game:"Videojuego",social:"Red social",ai:"IA",project:"Proyecto",
      request_send:"Guardar perfil",request_ok:"Perfil añadido a la cola de investigación.",
      photo_title:"Cambiar foto de perfil",photo_intro:"No uses una miniatura de Google Imágenes. Usa la página original, un press kit o una licencia válida.",
      profile:"Perfil",image:"Imagen *",alt:"Descripción accesible *",source:"URL de la fuente",credit:"Crédito",rights:"Base de derechos *",
      official_press:"Press kit oficial",licensed:"Con licencia",public_domain:"Dominio público",owner_upload:"Subida por el titular",generated:"Generada para FanRank",
      rights_help:"Para press kit, licencia o dominio público, añade el enlace original que lo demuestra.",photo_send:"Publicar foto",photo_ok:"Foto actualizada.",
      promote:"Promocionar",promote_title:"Solicitar promoción",promote_intro:"Esto registra interés para dar visibilidad al perfil; hoy no cobra nada. Las ideas concretas no se promocionan.",placement:"Qué promocionar",profile_placement:"Perfil",idea_placement:"Idea antigua (cancelada)",
      goal:"Objetivo de la promoción",promote_rule:"La publicidad solo puede dar visibilidad a un perfil o convocatoria futura. Nunca promociona una idea ni compra votos, nota IA o posición orgánica.",
      promote_send:"Registrar interés",promote_ok:"Interés registrado. No se ha realizado ningún cobro.",owner_mode:"PROPIETARIO",verified:"Perfil verificado",unverified:"Perfil creado por fans · pendiente de verificar",
      generic_error:"No se pudo completar. Tu contenido sigue aquí.",required:"Completa los campos obligatorios.",bad_image:"Usa JPG, PNG o WebP dentro del límite de tamaño.",bad_source:"Añade una URL original válida para demostrar los derechos.",
      zones:{hero:"Cabecera y buscador",stats:"Métricas",home_directory:"Perfiles y categorías",trending:"Tendencias",request_profile:"Petición pública de perfil",profile_identity:"Cabecera del perfil",suggest_cta:"Botón de sugerencia",profile_ranking:"Filtros del ranking",podium:"Podio",profile_ideas:"Lista de ideas",footer:"Pie de página"}
    },
    en:{
      studio:"Studio",studio_title:"Owner studio",studio_intro:"Private FanRank controls. Only authorized accounts can see this.",
      studio_note:"Your notes, screenshots and requests stay in a private queue. Nothing is published automatically.",
      feedback:"Visual feedback",feedback_copy:"Select an area and describe exactly what should change.",
      profile_request:"Add profile",profile_request_copy:"Queue a creator, company, game or platform for research.",
      photo:"Change photo",photo_copy:"Upload an image with a verifiable source and rights.",queue:"Private queue",queue_empty:"The queue is empty.",
      select_zone:"Select area",zone_banner:"Click the FanRank area you want to comment on.",cancel:"Cancel",close:"Close",
      feedback_title:"Area feedback",feedback_intro:"The screenshot is optional and always stays private.",zone:"Area",priority:"Priority",
      normal:"Normal",high:"High",low:"Low",message:"What should change? *",screenshot:"Optional screenshot",screenshot_help:"Attach JPG, PNG or WebP; you can also paste an image into the text field.",
      send_feedback:"Save feedback",feedback_ok:"Feedback saved to the private queue.",file_ready:"Screenshot ready",done:"Mark done",done_ok:"Marked as done.",
      request_title:"New profile to research",request_intro:"FanRank saves it; its image will later come from an official or licensed source.",
      name:"Name *",kind:"Type",notes:"Notes or context",creator:"Creator",company:"Company",game:"Video game",social:"Social platform",ai:"AI",project:"Project",
      request_send:"Save profile",request_ok:"Profile added to the research queue.",
      photo_title:"Change profile photo",photo_intro:"Do not use a Google Images thumbnail. Use the original page, press kit or a valid license.",
      profile:"Profile",image:"Image *",alt:"Accessible description *",source:"Source URL",credit:"Credit",rights:"Rights basis *",
      official_press:"Official press kit",licensed:"Licensed",public_domain:"Public domain",owner_upload:"Rights-holder upload",generated:"Generated for FanRank",
      rights_help:"For press kits, licensed or public-domain media, add the original page that proves it.",photo_send:"Publish photo",photo_ok:"Photo updated.",
      promote:"Promote",promote_title:"Request promotion",promote_intro:"This records interest in profile visibility; no payment is taken today. Individual ideas cannot be promoted.",placement:"What to promote",profile_placement:"Profile",idea_placement:"Legacy idea request (cancelled)",
      goal:"Promotion goal",promote_rule:"Advertising may only distribute a profile or future research call. It never promotes an idea or buys votes, AI score or organic position.",
      promote_send:"Register interest",promote_ok:"Interest registered. No payment was made.",owner_mode:"OWNER",verified:"Verified profile",unverified:"Fan-created profile · awaiting verification",
      generic_error:"This could not be completed. Your content is still here.",required:"Complete the required fields.",bad_image:"Use JPG, PNG or WebP within the size limit.",bad_source:"Add a valid original URL that proves the usage rights.",
      zones:{hero:"Header and search",stats:"Metrics",home_directory:"Profiles and categories",trending:"Trending",request_profile:"Public profile request",profile_identity:"Profile header",suggest_cta:"Suggestion call to action",profile_ranking:"Ranking filters",podium:"Podium",profile_ideas:"Ideas list",footer:"Footer"}
    }
  };

  var state = {admin:false,role:null,screenshot:null,image:null,promotion:null,authListener:null,zoneHandler:null};
  function s(key){var pack=COPY[window.LANG === "es" ? "es" : "en"];return pack[key];}
  function el(id){return document.getElementById(id);}
  function escapeHtml(value){return String(value == null ? "" : value).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];});}
  function pause(ms){return new Promise(function(resolve){setTimeout(resolve,ms);});}
  function randomPart(){var data=new Uint32Array(2);crypto.getRandomValues(data);return Array.from(data).map(function(n){return n.toString(36);}).join("").slice(0,12);}
  function imageExtension(file){return {"image/jpeg":"jpg","image/png":"png","image/webp":"webp"}[file && file.type] || "";}
  function validImage(file,maxBytes){return !!(file && imageExtension(file) && file.size > 0 && file.size <= maxBytes);}
  function validHttpUrl(value){try{var url=new URL(value);return url.protocol === "https:" || url.protocol === "http:";}catch(error){return false;}}
  function profileImageUrl(path){
    if(!path){return "";}
    return window.SB_URL + "/storage/v1/object/public/fanrank-profile-images/" + String(path).split("/").map(encodeURIComponent).join("/");
  }
  function zoneName(value){var zones=s("zones") || {};return zones[value] || String(value || "").replace(/_/g," ");}
  function formatDate(value){try{return new Intl.DateTimeFormat(window.LANG === "es" ? "es-ES" : "en",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"}).format(new Date(value));}catch(error){return "";}}
  function isProfileManager(){return !!(window.membership && window.membership.status === "active" && (window.membership.role === "owner" || window.membership.role === "admin" || window.membership.role === "contributor"));}
  function canPromote(){return !!(window.session && (state.admin || isProfileManager()));}

  function injectInterface(){
    var top=el("account-btn") && el("account-btn").parentElement;
    if(top && !el("owner-studio-btn")){
      top.insertAdjacentHTML("afterbegin",'<button class="top-btn owner-studio-btn hidden" id="owner-studio-btn" type="button"><span class="owner-dot" aria-hidden="true"></span><span>'+escapeHtml(s("studio"))+'</span></button>');
    }
    var sectionView=el("section-view");
    if(sectionView && !el("profile-identity")){
      sectionView.insertAdjacentHTML("afterbegin",'<div class="profile-identity" id="profile-identity" data-feedback-zone="profile_identity"></div><div class="owner-toolbar hidden" id="owner-toolbar"><div class="owner-toolbar-copy"><span class="owner-chip">✦ '+escapeHtml(s("owner_mode"))+'</span><b>'+escapeHtml(s("studio_title"))+'</b><span>'+escapeHtml(s("studio_intro"))+'</span></div><div class="owner-toolbar-actions"><button class="secondary-btn hidden" id="owner-feedback-profile" type="button">✎ '+escapeHtml(s("feedback"))+'</button><button class="secondary-btn hidden" id="owner-photo-open" type="button">▣ '+escapeHtml(s("photo"))+'</button><button class="secondary-btn promote-interest-btn hidden" id="owner-promote-profile" type="button">↗ '+escapeHtml(s("promote"))+'</button></div></div>');
    }
    if(!el("owner-studio-dialog")){
      var html='\
<dialog id="owner-studio-dialog" aria-labelledby="owner-studio-title"><div class="dialog-card wide">\
  <button class="dialog-close" data-owner-close="owner-studio-dialog" type="button" aria-label="'+escapeHtml(s("close"))+'">×</button>\
  <h2 id="owner-studio-title">'+escapeHtml(s("studio_title"))+'</h2><p class="dialog-intro">'+escapeHtml(s("studio_intro"))+'</p>\
  <div class="studio-note"><b>✓ '+escapeHtml(s("owner_mode"))+'</b> · '+escapeHtml(s("studio_note"))+'</div>\
  <div class="studio-grid">\
    <button class="studio-action" id="studio-feedback" type="button"><span class="studio-icon">✎</span><b>'+escapeHtml(s("feedback"))+'</b><span>'+escapeHtml(s("feedback_copy"))+'</span></button>\
    <button class="studio-action" id="studio-profile-request" type="button"><span class="studio-icon">＋</span><b>'+escapeHtml(s("profile_request"))+'</b><span>'+escapeHtml(s("profile_request_copy"))+'</span></button>\
    <button class="studio-action" id="studio-photo" type="button"><span class="studio-icon">▣</span><b>'+escapeHtml(s("photo"))+'</b><span>'+escapeHtml(s("photo_copy"))+'</span></button>\
  </div><div class="section-head"><div><h2>'+escapeHtml(s("queue"))+'</h2></div></div><div class="studio-queue" id="studio-queue"></div>\
</div></dialog>\
<dialog id="owner-feedback-dialog" aria-labelledby="owner-feedback-title"><div class="dialog-card wide">\
  <button class="dialog-close" data-owner-close="owner-feedback-dialog" type="button" aria-label="'+escapeHtml(s("close"))+'">×</button>\
  <h2 id="owner-feedback-title">'+escapeHtml(s("feedback_title"))+'</h2><p class="dialog-intro">'+escapeHtml(s("feedback_intro"))+'</p>\
  <form id="owner-feedback-form" novalidate><div class="form-grid"><div class="field"><label for="owner-feedback-zone">'+escapeHtml(s("zone"))+'</label><input id="owner-feedback-zone" readonly required></div>\
  <div class="field"><label for="owner-feedback-priority">'+escapeHtml(s("priority"))+'</label><select class="inline-select" id="owner-feedback-priority"><option value="normal">'+escapeHtml(s("normal"))+'</option><option value="high">'+escapeHtml(s("high"))+'</option><option value="low">'+escapeHtml(s("low"))+'</option></select></div>\
  <div class="field full"><label for="owner-feedback-message">'+escapeHtml(s("message"))+'</label><textarea id="owner-feedback-message" maxlength="2000" required></textarea></div>\
  <div class="field full"><label class="file-drop" for="owner-feedback-file"><b>'+escapeHtml(s("screenshot"))+'</b><span class="helper">'+escapeHtml(s("screenshot_help"))+'</span><input id="owner-feedback-file" type="file" accept="image/jpeg,image/png,image/webp"></label><div class="file-preview hidden" id="owner-feedback-preview"></div></div></div>\
  <div class="form-actions"><button class="secondary-btn" id="owner-feedback-select" type="button">◎ '+escapeHtml(s("select_zone"))+'</button><button class="primary-btn" id="owner-feedback-send" type="submit">'+escapeHtml(s("send_feedback"))+'</button></div><div class="form-status" id="owner-feedback-status" role="status" aria-live="polite"></div></form>\
</div></dialog>\
<dialog id="owner-profile-dialog" aria-labelledby="owner-profile-title"><div class="dialog-card">\
  <button class="dialog-close" data-owner-close="owner-profile-dialog" type="button" aria-label="'+escapeHtml(s("close"))+'">×</button>\
  <h2 id="owner-profile-title">'+escapeHtml(s("request_title"))+'</h2><p class="dialog-intro">'+escapeHtml(s("request_intro"))+'</p>\
  <form id="owner-profile-form" novalidate><div class="form-grid"><div class="field"><label for="owner-profile-name">'+escapeHtml(s("name"))+'</label><input id="owner-profile-name" maxlength="120" required></div><div class="field"><label for="owner-profile-kind">'+escapeHtml(s("kind"))+'</label><select class="inline-select" id="owner-profile-kind"><option value="creator">'+escapeHtml(s("creator"))+'</option><option value="company">'+escapeHtml(s("company"))+'</option><option value="game">'+escapeHtml(s("game"))+'</option><option value="social">'+escapeHtml(s("social"))+'</option><option value="ai">'+escapeHtml(s("ai"))+'</option><option value="project">'+escapeHtml(s("project"))+'</option></select></div><div class="field full"><label for="owner-profile-notes">'+escapeHtml(s("notes"))+'</label><textarea id="owner-profile-notes" maxlength="1200"></textarea></div></div><div class="form-actions"><button class="primary-btn" id="owner-profile-send" type="submit">'+escapeHtml(s("request_send"))+'</button></div><div class="form-status" id="owner-profile-status" role="status" aria-live="polite"></div></form>\
</div></dialog>\
<dialog id="owner-photo-dialog" aria-labelledby="owner-photo-title"><div class="dialog-card wide">\
  <button class="dialog-close" data-owner-close="owner-photo-dialog" type="button" aria-label="'+escapeHtml(s("close"))+'">×</button>\
  <h2 id="owner-photo-title">'+escapeHtml(s("photo_title"))+'</h2><p class="dialog-intro">'+escapeHtml(s("photo_intro"))+'</p>\
  <form id="owner-photo-form" novalidate><div class="form-grid"><div class="field"><label for="owner-photo-section">'+escapeHtml(s("profile"))+'</label><select class="inline-select" id="owner-photo-section"></select></div><div class="field"><label for="owner-photo-file">'+escapeHtml(s("image"))+'</label><input id="owner-photo-file" type="file" accept="image/jpeg,image/png,image/webp" required></div><div class="field full"><div class="file-preview hidden" id="owner-photo-preview"></div></div><div class="field full"><label for="owner-photo-alt">'+escapeHtml(s("alt"))+'</label><input id="owner-photo-alt" maxlength="240" required></div><div class="field"><label for="owner-photo-rights">'+escapeHtml(s("rights"))+'</label><select class="inline-select" id="owner-photo-rights"><option value="official_press">'+escapeHtml(s("official_press"))+'</option><option value="licensed">'+escapeHtml(s("licensed"))+'</option><option value="public_domain">'+escapeHtml(s("public_domain"))+'</option><option value="owner_upload">'+escapeHtml(s("owner_upload"))+'</option><option value="generated">'+escapeHtml(s("generated"))+'</option></select></div><div class="field"><label for="owner-photo-credit">'+escapeHtml(s("credit"))+'</label><input id="owner-photo-credit" maxlength="240"></div><div class="field full"><label for="owner-photo-source">'+escapeHtml(s("source"))+'</label><input id="owner-photo-source" type="url" maxlength="700" inputmode="url"><span class="rights-warning">'+escapeHtml(s("rights_help"))+'</span></div></div><div class="form-actions"><button class="primary-btn" id="owner-photo-send" type="submit">'+escapeHtml(s("photo_send"))+'</button></div><div class="form-status" id="owner-photo-status" role="status" aria-live="polite"></div></form>\
</div></dialog>\
<dialog id="owner-promotion-dialog" aria-labelledby="owner-promotion-title"><div class="dialog-card">\
  <button class="dialog-close" data-owner-close="owner-promotion-dialog" type="button" aria-label="'+escapeHtml(s("close"))+'">×</button>\
  <h2 id="owner-promotion-title">'+escapeHtml(s("promote_title"))+'</h2><p class="dialog-intro">'+escapeHtml(s("promote_intro"))+'</p>\
  <form id="owner-promotion-form" novalidate><div class="field"><label>'+escapeHtml(s("placement"))+'</label><input id="owner-promotion-label" readonly></div><div class="field" style="margin-top:12px"><label for="owner-promotion-goal">'+escapeHtml(s("goal"))+'</label><textarea id="owner-promotion-goal" maxlength="500"></textarea></div><div class="sponsored-rule"><span aria-hidden="true">⚖</span><span><b>'+escapeHtml(s("promote"))+'</b> · '+escapeHtml(s("promote_rule"))+'</span></div><div class="form-actions"><button class="primary-btn" id="owner-promotion-send" type="submit">'+escapeHtml(s("promote_send"))+'</button></div><div class="form-status" id="owner-promotion-status" role="status" aria-live="polite"></div></form>\
</div></dialog>';
      el("toast").insertAdjacentHTML("beforebegin",html);
    }
    assignFeedbackZones();
    bindInterface();
  }

  function assignFeedbackZones(){
    [["header","hero"],["stats","stats"],[".directory-block","home_directory"],["trending","trending"],["request-panel","request_profile"],[".suggest-cta","suggest_cta"],[".profile-tools","profile_ranking"],["podium","podium"],["ideas-list","profile_ideas"],["footer","footer"]].forEach(function(pair){
      var node=el(pair[0]) || document.querySelector(pair[0]);
      if(node){node.setAttribute("data-feedback-zone",pair[1]);}
    });
  }
  function openModal(id){var node=el(id);if(node && !node.open){node.showModal();}}
  function closeModal(id){var node=el(id);if(node && node.open){node.close();}}
  function setFormStatus(id,message,type){if(window.setStatus){window.setStatus(id,message,type);}else{var node=el(id);node.textContent=message;}}
  function setButtonBusy(id,busy){var button=el(id);if(window.setBusy){window.setBusy(button,busy);}else{button.disabled=busy;}}

  function bindInterface(){
    el("owner-studio-btn").addEventListener("click",openStudio);
    el("studio-feedback").addEventListener("click",function(){closeModal("owner-studio-dialog");openFeedback();});
    el("studio-profile-request").addEventListener("click",function(){closeModal("owner-studio-dialog");openModal("owner-profile-dialog");setTimeout(function(){el("owner-profile-name").focus();},0);});
    el("studio-photo").addEventListener("click",function(){closeModal("owner-studio-dialog");openPhoto();});
    el("owner-feedback-profile").addEventListener("click",function(){openFeedback(window.SECTION ? "profile_ideas" : "home_directory");});
    el("owner-photo-open").addEventListener("click",openPhoto);
    el("owner-promote-profile").addEventListener("click",openPromotion);
    document.querySelectorAll("[data-owner-close]").forEach(function(button){button.addEventListener("click",function(){closeModal(button.dataset.ownerClose);});});
    ["owner-studio-dialog","owner-feedback-dialog","owner-profile-dialog","owner-photo-dialog","owner-promotion-dialog"].forEach(function(id){el(id).addEventListener("click",function(event){if(event.target===el(id)){closeModal(id);}});});
    el("owner-feedback-select").addEventListener("click",beginZonePick);
    el("owner-feedback-file").addEventListener("change",function(event){setScreenshot(event.target.files && event.target.files[0]);});
    el("owner-feedback-message").addEventListener("paste",capturePastedImage);
    el("owner-photo-file").addEventListener("change",function(event){setProfileImage(event.target.files && event.target.files[0]);});
    el("owner-feedback-form").addEventListener("submit",submitFeedback);
    el("owner-profile-form").addEventListener("submit",submitProfileRequest);
    el("owner-photo-form").addEventListener("submit",submitPhoto);
    el("owner-promotion-form").addEventListener("submit",submitPromotion);
    document.addEventListener("keydown",function(event){if(event.key==="Escape" && document.body.classList.contains("fr-zone-picking")){endZonePick();}});
  }

  async function refreshAccess(){
    var previousAdmin=state.admin;
    state.admin=false;state.role=null;
    if(!window.session || !window.api){updateInterface();return false;}
    try{
      var rows=await window.api("fr_platform_admins?select=user_id,role,status&user_id=eq."+encodeURIComponent(window.session.user.id)+"&status=eq.active&limit=1");
      state.admin=!!(rows && rows.length);state.role=state.admin ? rows[0].role : null;
    }catch(error){state.admin=false;state.role=null;}
    updateInterface();
    if(window.SECTION && window.secMeta && window.renderIdeas && previousAdmin!==state.admin){window.renderIdeas();}
    return state.admin;
  }
  function updateInterface(){
    if(el("owner-studio-btn")){el("owner-studio-btn").classList.toggle("hidden",!state.admin);}
    var toolbar=el("owner-toolbar");
    if(toolbar){
      toolbar.classList.toggle("hidden",!(state.admin || canPromote()));
      el("owner-feedback-profile").classList.toggle("hidden",!state.admin);
      el("owner-photo-open").classList.toggle("hidden",!state.admin);
      el("owner-promote-profile").classList.toggle("hidden",!canPromote() || !window.SECTION);
    }
    if(window.SECTION && window.secMeta){renderProfileEnhancements();}
  }
  function renderProfileEnhancements(){
    if(!window.secMeta || !el("profile-identity")){return;}
    var meta=window.secMeta;
    var identity=el("profile-identity");
    var tags=el("profile-tags");
    var claimButton=el("claim-open");
    var claimBar=claimButton ? claimButton.closest(".claim-bar") : null;
    var verified=meta.verification_status==="verified";
    identity.classList.toggle("is-verified",verified);
    var initials=String(meta.name || "?").trim().split(/\s+/).slice(0,2).map(function(part){return part.charAt(0);}).join("").toUpperCase().slice(0,3) || "?";
    var avatar=meta.image_path ? '<img src="'+escapeHtml(profileImageUrl(meta.image_path))+'" alt="'+escapeHtml(meta.image_alt || meta.name)+'" loading="eager" decoding="async">' : '<span class="profile-monogram" aria-hidden="true">'+escapeHtml(initials)+'</span>';
    var credit=meta.image_credit ? escapeHtml(meta.image_credit) : "";
    var creditHtml=credit ? (meta.image_source_url && validHttpUrl(meta.image_source_url) ? '<a class="profile-image-credit" href="'+escapeHtml(meta.image_source_url)+'" target="_blank" rel="noopener noreferrer">'+credit+' ↗</a>' : '<span class="profile-image-credit">'+credit+'</span>') : "";
    identity.innerHTML='<div class="profile-identity-main"><div class="profile-avatar">'+avatar+'</div><div class="profile-identity-copy"><strong>'+escapeHtml(meta.name)+'</strong><span class="profile-status '+(verified?'is-verified':'is-community')+'"><i aria-hidden="true"></i>'+escapeHtml(s(verified?"verified":"unverified"))+'</span>'+creditHtml+'</div></div><div class="profile-identity-detail"></div>';
    if(tags){identity.querySelector(".profile-identity-detail").appendChild(tags);}
    if(claimBar){
      claimBar.classList.add("profile-claim");
      claimBar.classList.toggle("hidden",verified);
      identity.appendChild(claimBar);
    }
    updateInterfaceShallow();
  }
  function updateInterfaceShallow(){
    var toolbar=el("owner-toolbar");if(!toolbar){return;}
    toolbar.classList.toggle("hidden",!(state.admin || canPromote()));
    el("owner-feedback-profile").classList.toggle("hidden",!state.admin);
    el("owner-photo-open").classList.toggle("hidden",!state.admin);
    el("owner-promote-profile").classList.toggle("hidden",!canPromote() || !window.SECTION);
  }

  async function openStudio(){
    if(!state.admin){return;}
    openModal("owner-studio-dialog");
    if(window.sendEvent){window.sendEvent("owner_mode_open",{section:window.SECTION || null});}
    await loadQueue();
  }
  async function loadQueue(){
    var queue=el("studio-queue");queue.innerHTML='<div class="loading"><span class="spinner"></span></div>';
    try{
      var result=await Promise.all([
        window.api("fr_owner_feedback?select=id,zone,message,priority,status,created_at&order=created_at.desc&limit=20"),
        window.api("fr_profile_requests?select=id,name,kind,status,created_at&order=created_at.desc&limit=15"),
        window.api("fr_promotion_requests?select=id,section,idea_id,placement,status,organic_rank_unchanged,created_at&order=created_at.desc&limit=15")
      ]);
      var items=[];
      (result[0]||[]).forEach(function(row){items.push({type:"feedback",id:row.id,title:zoneName(row.zone),copy:row.message,status:row.status,meta:row.priority,date:row.created_at});});
      (result[1]||[]).forEach(function(row){items.push({type:"profile",id:row.id,title:row.name,copy:s(row.kind)||row.kind,status:row.status,meta:s("profile_request"),date:row.created_at});});
      (result[2]||[]).forEach(function(row){items.push({type:"promotion",id:row.id,title:row.section,copy:row.placement==="idea"?s("idea_placement"):s("profile_placement"),status:row.status,meta:s("promote"),date:row.created_at});});
      items.sort(function(a,b){return new Date(b.date)-new Date(a.date);});
      if(!items.length){queue.innerHTML='<div class="empty-state">'+escapeHtml(s("queue_empty"))+'</div>';return;}
      queue.innerHTML=items.map(function(item){return '<article class="studio-row"><b>'+escapeHtml(item.title)+'</b><span>'+escapeHtml(item.copy || "")+'</span><span class="studio-row-meta"><i>'+escapeHtml(item.meta)+'</i><i>'+escapeHtml(item.status)+'</i><i>'+escapeHtml(formatDate(item.date))+'</i></span>'+(item.type==="feedback"&&item.status!=="done"?'<div class="form-actions"><button class="secondary-btn" type="button" data-feedback-done="'+Number(item.id)+'">'+escapeHtml(s("done"))+'</button></div>':"")+'</article>';}).join("");
      queue.querySelectorAll("[data-feedback-done]").forEach(function(button){button.addEventListener("click",function(){markFeedbackDone(Number(button.dataset.feedbackDone));});});
    }catch(error){queue.innerHTML='<div class="empty-state">'+escapeHtml(s("generic_error"))+'</div>';}
  }
  async function markFeedbackDone(id){
    try{await window.api("fr_owner_feedback?id=eq."+id,{method:"PATCH",headers:{"Prefer":"return=minimal"},body:JSON.stringify({status:"done",updated_at:new Date().toISOString()})});window.showToast(s("done_ok"),"ok");await loadQueue();}
    catch(error){window.showToast(s("generic_error"),"err");}
  }

  function openFeedback(zone){
    if(!state.admin){return;}
    var value=zone || (window.SECTION ? "profile_ideas" : "home_directory");
    el("owner-feedback-zone").value=value;
    el("owner-feedback-zone").dataset.zone=value;
    setFormStatus("owner-feedback-status","","");openModal("owner-feedback-dialog");
    setTimeout(function(){el("owner-feedback-message").focus();},0);
  }
  function beginZonePick(){
    closeModal("owner-feedback-dialog");closeModal("owner-studio-dialog");
    document.body.classList.add("fr-zone-picking");
    var banner=document.createElement("div");banner.className="fr-zone-banner";banner.id="fr-zone-banner";banner.innerHTML='<span>◎</span><span><b>'+escapeHtml(s("select_zone"))+'</b><br>'+escapeHtml(s("zone_banner"))+'</span><button class="secondary-btn" type="button">'+escapeHtml(s("cancel"))+'</button>';
    document.body.appendChild(banner);banner.querySelector("button").addEventListener("click",endZonePick);
    state.zoneHandler=function(event){
      var target=event.target.closest && event.target.closest("[data-feedback-zone]");
      if(!target){return;}event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();
      var zone=target.getAttribute("data-feedback-zone");endZonePick();openFeedback(zone);
      el("owner-feedback-zone").value=zoneName(zone);el("owner-feedback-zone").dataset.zone=zone;
    };
    document.addEventListener("click",state.zoneHandler,true);
  }
  function endZonePick(){
    document.body.classList.remove("fr-zone-picking");
    if(state.zoneHandler){document.removeEventListener("click",state.zoneHandler,true);state.zoneHandler=null;}
    var banner=el("fr-zone-banner");if(banner){banner.remove();}
  }
  function setScreenshot(file){
    state.screenshot=validImage(file,8388608)?file:null;
    var preview=el("owner-feedback-preview");preview.innerHTML="";preview.classList.toggle("hidden",!state.screenshot);
    if(state.screenshot){var url=URL.createObjectURL(state.screenshot);preview.innerHTML='<img src="'+url+'" alt=""><span>'+escapeHtml(s("file_ready"))+' · '+escapeHtml(state.screenshot.name || "clipboard.png")+'</span>';}
    else if(file){setFormStatus("owner-feedback-status",s("bad_image"),"err");}
  }
  function capturePastedImage(event){
    var items=event.clipboardData && event.clipboardData.items; if(!items){return;}
    for(var i=0;i<items.length;i+=1){if(items[i].type.indexOf("image/")===0){var file=items[i].getAsFile();if(file){setScreenshot(file);}break;}}
  }
  async function submitFeedback(event){
    event.preventDefault();if(!state.admin || !window.session){return;}
    var zone=el("owner-feedback-zone").dataset.zone || el("owner-feedback-zone").value;
    var message=el("owner-feedback-message").value.trim();
    if(!zone || message.length<3){setFormStatus("owner-feedback-status",s("required"),"err");return;}
    setButtonBusy("owner-feedback-send",true);setFormStatus("owner-feedback-status","","");
    try{
      var screenshotPath=null;
      if(state.screenshot){
        if(!validImage(state.screenshot,8388608)){throw new Error("bad image");}
        screenshotPath=window.session.user.id+"/"+Date.now()+"-"+randomPart()+"."+imageExtension(state.screenshot);
        var upload=await window.authClient.storage.from("fanrank-owner-feedback").upload(screenshotPath,state.screenshot,{contentType:state.screenshot.type,upsert:false});
        if(upload.error){throw upload.error;}
      }
      await window.postRow("fr_owner_feedback",{user_id:window.session.user.id,page_path:(location.pathname+location.search).slice(0,500),zone:zone,priority:el("owner-feedback-priority").value,message:message,screenshot_path:screenshotPath});
      if(window.sendEvent){window.sendEvent("owner_feedback",{section:window.SECTION || null,value:zone});}
      setFormStatus("owner-feedback-status",s("feedback_ok"),"ok");el("owner-feedback-message").value="";el("owner-feedback-file").value="";setScreenshot(null);
    }catch(error){setFormStatus("owner-feedback-status",s("generic_error"),"err");}
    finally{setButtonBusy("owner-feedback-send",false);}
  }

  async function submitProfileRequest(event){
    event.preventDefault();if(!state.admin || !window.session){return;}
    var name=el("owner-profile-name").value.trim();if(name.length<2){setFormStatus("owner-profile-status",s("required"),"err");return;}
    setButtonBusy("owner-profile-send",true);setFormStatus("owner-profile-status","","");
    try{await window.postRow("fr_profile_requests",{requested_by:window.session.user.id,name:name,kind:el("owner-profile-kind").value,notes:el("owner-profile-notes").value.trim()||null});if(window.sendEvent){window.sendEvent("owner_profile_request",{value:name});}el("owner-profile-form").reset();setFormStatus("owner-profile-status",s("request_ok"),"ok");}
    catch(error){setFormStatus("owner-profile-status",s("generic_error"),"err");}
    finally{setButtonBusy("owner-profile-send",false);}
  }

  function populateProfileSelect(){
    var select=el("owner-photo-section");select.innerHTML=(window.sections||[]).map(function(item){return '<option value="'+escapeHtml(item.slug)+'">'+escapeHtml(item.name)+'</option>';}).join("");
    if(window.SECTION){select.value=window.SECTION;}
  }
  function openPhoto(){if(!state.admin){return;}populateProfileSelect();setFormStatus("owner-photo-status","","");openModal("owner-photo-dialog");}
  function setProfileImage(file){
    state.image=validImage(file,5242880)?file:null;var preview=el("owner-photo-preview");preview.innerHTML="";preview.classList.toggle("hidden",!state.image);
    if(state.image){var url=URL.createObjectURL(state.image);preview.innerHTML='<img src="'+url+'" alt=""><span>'+escapeHtml(state.image.name)+'</span>';}
    else if(file){setFormStatus("owner-photo-status",s("bad_image"),"err");}
  }
  async function submitPhoto(event){
    event.preventDefault();if(!state.admin || !window.session){return;}
    var slug=el("owner-photo-section").value,alt=el("owner-photo-alt").value.trim(),rights=el("owner-photo-rights").value,source=el("owner-photo-source").value.trim();
    if(!slug || !alt || !validImage(state.image,5242880)){setFormStatus("owner-photo-status",!state.image?s("bad_image"):s("required"),"err");return;}
    if(["official_press","licensed","public_domain"].indexOf(rights)>=0 && !validHttpUrl(source)){setFormStatus("owner-photo-status",s("bad_source"),"err");return;}
    if(source && !validHttpUrl(source)){setFormStatus("owner-photo-status",s("bad_source"),"err");return;}
    setButtonBusy("owner-photo-send",true);setFormStatus("owner-photo-status","","");
    try{
      var path=slug+"/"+window.session.user.id+"/"+Date.now()+"-"+randomPart()+"."+imageExtension(state.image);
      var upload=await window.authClient.storage.from("fanrank-profile-images").upload(path,state.image,{contentType:state.image.type,upsert:false});if(upload.error){throw upload.error;}
      await window.callRpc("fr_admin_set_profile_image",{p_section:slug,p_path:path,p_alt:alt,p_source_url:source||null,p_credit:el("owner-photo-credit").value.trim()||null,p_rights:rights});
      var meta=(window.sections||[]).find(function(item){return item.slug===slug;});if(meta){meta.image_path=path;meta.image_alt=alt;meta.image_source_url=source||null;meta.image_credit=el("owner-photo-credit").value.trim()||null;meta.image_rights=rights;if(window.secMeta&&window.secMeta.slug===slug){window.secMeta=meta;}}
      if(window.SECTION===slug){renderProfileEnhancements();}else if(!window.SECTION&&window.renderSections){window.renderSections();}
      if(window.sendEvent){window.sendEvent("profile_image_updated",{section:slug,value:rights});}
      setFormStatus("owner-photo-status",s("photo_ok"),"ok");el("owner-photo-file").value="";setProfileImage(null);
    }catch(error){setFormStatus("owner-photo-status",s("generic_error"),"err");}
    finally{setButtonBusy("owner-photo-send",false);}
  }

  function openPromotion(){
    if(!canPromote() || !window.SECTION){return;}
    state.promotion={placement:"profile",ideaId:null,section:window.SECTION};
    var label=s("profile_placement")+" · "+(window.secMeta?window.secMeta.name:window.SECTION);
    el("owner-promotion-label").value=label;setFormStatus("owner-promotion-status","","");openModal("owner-promotion-dialog");
  }
  async function submitPromotion(event){
    event.preventDefault();if(!state.promotion || !canPromote()){return;}
    setButtonBusy("owner-promotion-send",true);setFormStatus("owner-promotion-status","","");
    try{await window.postRow("fr_promotion_requests",{user_id:window.session.user.id,section:state.promotion.section,idea_id:null,placement:"profile",goal:el("owner-promotion-goal").value.trim()||null});if(window.sendEvent){window.sendEvent("promotion_interest",{section:state.promotion.section,value:"profile"});}el("owner-promotion-goal").value="";setFormStatus("owner-promotion-status",s("promote_ok"),"ok");}
    catch(error){setFormStatus("owner-promotion-status",s("generic_error"),"err");}
    finally{setButtonBusy("owner-promotion-send",false);}
  }

  async function initializeAuthBridge(){
    for(var i=0;i<80&&!window.authClient;i+=1){await pause(100);}
    await refreshAccess();
    if(window.authClient){var listener=window.authClient.auth.onAuthStateChange(function(){setTimeout(refreshAccess,0);});state.authListener=listener.data && listener.data.subscription;}
    [650,1500,3000].forEach(function(delay){setTimeout(refreshAccess,delay);});
  }

  window.FanRankOwnerStudio={
    canPromote:canPromote,
    openPromotion:openPromotion,
    refreshAccess:refreshAccess,
    renderProfileEnhancements:renderProfileEnhancements,
    profileImageUrl:profileImageUrl,
    isAdmin:function(){return state.admin;}
  };
  injectInterface();
  initializeAuthBridge();
})();
