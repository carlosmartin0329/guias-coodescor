/* Guías Coodescor · JS local sin dependencias */
"use strict";

/* ---------- envío JSON de formularios ---------- */
async function postJSON(url, data) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  // Leer la respuesta como TEXTO PRIMERO (permite diagnosticar si el backend
  // responde con HTML/plain text en lugar de JSON). Luego intentar JSON.parse.
  const rawText = await r.text();
  let j = {};
  let jsonParseErr = null;
  try {
    j = JSON.parse(rawText);
  } catch (e) {
    jsonParseErr = (e && e.message) ? String(e.message).slice(0, 200) : "JSON inválido";
    try { console.error("[guias] postJSON: respuesta NO es JSON. status=", r.status, "url=", url, "raw_first200=", (rawText || "").slice(0, 200)); } catch (_) {}
  }
  if (!r.ok || !j.ok) {
    let msgErr = (j && (j.error || j.mensaje || j.msg));
    if (jsonParseErr || (r.ok && !j.ok && !msgErr)) {
      const preview = (rawText || "").slice(0, 140).replace(/[\r\n]+/g, " ");
      const detalle = jsonParseErr ? ` · ParseError: ${jsonParseErr}` : "";
      msgErr = msgErr || (`HTTP ${r.status} · Respuesta inválida: ${preview}${detalle}`);
    }
    msgErr = msgErr || ("HTTP " + r.status);
    alert("⚠️ " + msgErr);
    return null;
  }
  // Mensaje de éxito ACEPTAR TANTO j.mensaje COMO j.msg (backend no es 100% uniforme)
  const msjExito = (j && (j.mensaje || j.msg)) || "";
  if (msjExito) {
    // Lanzar alert después de 120ms, PERO NO BLOQUEAR el redirect.
    // Si hay redirect, el location.href se ejecutará y el alert se perderá
    // (comportamiento deseado para ir al tablero sin clicks OK por usuario)
    setTimeout(() => alert("✅ " + msjExito), 120);
  }
  return j;
}
window.postJSON = postJSON;

/* ---------- firma táctil (canvas) ---------- */
function initSig(canvas) {
  // Protección doble: no re-inicializar si ya fue inicializado (evita listeners duplicados
  // y borrar una firma ya dibujada cuando MutationObserver procesa el mismo nodo 2 veces)
  if (canvas._firmaInicializada === true) return;
  canvas._firmaInicializada = true;

  // Asegurarse que el canvas sea TOCABLE / CLICKEABLE (nunca pointer-events: none).
  // Algunos navegadores / frameworks de CSS heredan "none" accidentalmente.
  canvas.style.pointerEvents = "auto";
  canvas.style.touchAction = "none";
  canvas.style.cursor = "crosshair";

  const recalcularDPR = () => {
    const dpr = Math.max(1, window.devicePixelRatio || 1);
    const rect = canvas.getBoundingClientRect();
    // Si el ancho / alto es cero (canvas oculto en tab no activa), saltar y reintentar luego.
    if (rect.width < 10 || rect.height < 10) return false;
    // Conservar lo dibujado antes de resize:
    let imgTemporal = null;
    try {
      if (canvas.width > 0 && canvas.height > 0) {
        const cvTmp = document.createElement("canvas");
        cvTmp.width = canvas.width; cvTmp.height = canvas.height;
        cvTmp.getContext("2d").drawImage(canvas, 0, 0);
        imgTemporal = cvTmp;
      }
    } catch (_) { /* no importa */ }
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
    ctx.lineWidth = 2.4; ctx.lineCap = "round"; ctx.lineJoin = "round";
    ctx.strokeStyle = "#12244a";
    if (imgTemporal) {
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      // Escalar la imagen guardada a las nuevas dimensiones del canvas:
      ctx.drawImage(imgTemporal, 0, 0, canvas.width, canvas.height);
      ctx.restore();
    }
    return true;
  };

  // Intentar recalcular inmediatamente, y si falla (canvas oculto), reintentar en 200ms y 1s.
  const ok = recalcularDPR();
  if (!ok) {
    setTimeout(recalcularDPR, 250);
    setTimeout(recalcularDPR, 1200);
  }
  // También re-calcular en resize de ventana (responsive).
  let _rt = null;
  window.addEventListener("resize", () => {
    clearTimeout(_rt); _rt = setTimeout(recalcularDPR, 180);
  }, { passive: true });

  const ctx = canvas.getContext("2d");
  let dibujando = false, vacio = true;
  // Método público _vacio: SIEMPRE definido, incluso si initSig no hubiera corrido
  // (fallback defensive en recolectar() más abajo)
  canvas._vacio = () => vacio;

  const pos = (ev) => {
    const r = canvas.getBoundingClientRect();
    let cx = ev.clientX, cy = ev.clientY;
    // Fallback para touch events Pointer: extraer coords desde touches / changedTouches si clientX falta
    if ((cx == null || isNaN(cx)) && ev.touches && ev.touches.length) {
      cx = ev.touches[0].clientX; cy = ev.touches[0].clientY;
    } else if ((cx == null || isNaN(cx)) && ev.changedTouches && ev.changedTouches.length) {
      cx = ev.changedTouches[0].clientX; cy = ev.changedTouches[0].clientY;
    }
    return [cx - r.left, cy - r.top];
  };

  canvas.addEventListener("pointerdown", (ev) => {
    try { ev.preventDefault(); } catch(_){}
    try { canvas.setPointerCapture && canvas.setPointerCapture(ev.pointerId); } catch(_){}
    // Forzar foco visual (algunos navegadores no "activan" el canvas hasta click derecho)
    if (canvas.focus) canvas.focus({ preventScroll: true });
    // Si por alguna razón el canvas seguía 0x0 (tab no visible), recalcular antes de dibujar
    if (canvas.width < 10 || canvas.height < 10) recalcularDPR();
    dibujando = true;
    const [x, y] = pos(ev);
    ctx.beginPath();
    ctx.moveTo(x, y);
    // Dibujar un mini-punto para que incluso un "toque" registre firma (no requiere arrastrar)
    ctx.lineTo(x + 0.01, y + 0.01);
    ctx.stroke();
    vacio = false;
  }, { passive: false });

  canvas.addEventListener("pointermove", (ev) => {
    if (!dibujando) return;
    try { ev.preventDefault(); } catch(_){}
    const [x, y] = pos(ev);
    ctx.lineTo(x, y); ctx.stroke();
  }, { passive: false });

  ["pointerup", "pointercancel", "pointerleave"].forEach((t) =>
    canvas.addEventListener(t, () => { dibujando = false; }, { passive: true }));
}
window.initSig = initSig;

function limpiarCanvas(canvas) {
  const ctx = canvas.getContext("2d");
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.restore();
  // Resetear bandera de vacío (defensivo)
  if (typeof canvas._vacio === "function") {
    canvas._vacio = () => true;
  } else {
    canvas._vacio = () => true;
  }
}
window.limpiarCanvas = limpiarCanvas;

/* ---------- Observador global de firmas (soporte para canvas DINÁMICOS / TABS) ----------
 * Soluciona bug: cuando el formulario administrativo carga las pestañas (Propio / Externo)
 * via innerHTML DESPUÉS de DOMContentLoaded → initSig() NUNCA corrían sobre esos canvas
 * → cursor no dibujaba nada y no se podía capturar firma.
 * Con este MutationObserver, CUALQUIER canvas.sig que aparezca en el DOM en cualquier
 * momento (ya sea inicial o dinámico) tiene attachado initSig y su botón limpiar.
 */
function setupObservadorFirmas() {
  // 1) Pasada inicial: cualquier canvas que exista en este momento
  document.querySelectorAll("canvas.sig:not([data-firma-listo])").forEach((cv) => {
    initSig(cv); cv.setAttribute("data-firma-listo", "1");
  });
  // 2) Botones limpiar iniciales:
  document.querySelectorAll("[data-limpiar]:not([data-limpiar-listo])").forEach((b) => {
    b.addEventListener("click", () => {
      const box = b.closest(".sigbox") || b.parentElement;
      if (!box) return;
      box.querySelectorAll("canvas.sig").forEach(limpiarCanvas);
    });
    b.setAttribute("data-limpiar-listo", "1");
  });

  // 3) Observador DOM: captura nodos nuevos que el JS agrega dinámicamente
  const obs = new MutationObserver((mutations) => {
    for (const m of mutations) {
      for (const nodo of m.addedNodes) {
        if (!(nodo instanceof Element)) continue;
        // a) Si el elemento mismo ES un canvas.sig → inicializarlo
        if (nodo.matches && nodo.matches("canvas.sig:not([data-firma-listo])")) {
          initSig(nodo); nodo.setAttribute("data-firma-listo", "1");
        }
        // b) Buscar canvas.sig DENTRO del elemento agregado (innerHTML grande)
        nodo.querySelectorAll && nodo.querySelectorAll("canvas.sig:not([data-firma-listo])").forEach((cv) => {
          initSig(cv); cv.setAttribute("data-firma-listo", "1");
        });
        // c) Botones [data-limpiar] NUEVOS attachar click:
        if (nodo.matches && nodo.matches("[data-limpiar]:not([data-limpiar-listo])")) {
          nodo.addEventListener("click", () => {
            const box = nodo.closest(".sigbox") || nodo.parentElement;
            if (!box) return;
            box.querySelectorAll("canvas.sig").forEach(limpiarCanvas);
          });
          nodo.setAttribute("data-limpiar-listo", "1");
        }
        nodo.querySelectorAll && nodo.querySelectorAll("[data-limpiar]:not([data-limpiar-listo])").forEach((b) => {
          b.addEventListener("click", () => {
            const box = b.closest(".sigbox") || b.parentElement;
            if (!box) return;
            box.querySelectorAll("canvas.sig").forEach(limpiarCanvas);
          });
          b.setAttribute("data-limpiar-listo", "1");
        });
      }
    }
  });
  obs.observe(document.documentElement, { childList: true, subtree: true });
  window._obsFirmas = obs;
}
window.setupObservadorFirmas = setupObservadorFirmas;

/* ---------- Asegurar que un canvas haya sido inicializado (fallback defensivo) ---------- */
function asegurarInitSiFalta(cv) {
  if (!cv) return;
  if (!cv._vacio || typeof cv._vacio !== "function") {
    // No fue inicializado nunca (bug de attach). Correr initSig AHORA antes de recolectar.
    try { initSig(cv); } catch(_) {}
  }
}

/* ---------- foto: la comprime en el celular antes de subirla ---------- */
function fotoADataURL(file, max = 1400) {
  return new Promise((res, rej) => {
    const fr = new FileReader();
    fr.onload = () => {
      const img = new Image();
      img.onload = () => {
        const esc = Math.min(1, max / Math.max(img.width, img.height));
        const cv = document.createElement("canvas");
        cv.width = Math.round(img.width * esc);
        cv.height = Math.round(img.height * esc);
        cv.getContext("2d").drawImage(img, 0, 0, cv.width, cv.height);
        res(cv.toDataURL("image/jpeg", 0.82));
      };
      img.onerror = rej;
      img.src = fr.result;
    };
    fr.onerror = rej;
    fr.readAsDataURL(file);
  });
}

/* ---------- recolecta el formulario (inputs + firmas + fotos) ---------- */
async function recolectar(form) {
  const data = {};
  for (const el of form.querySelectorAll("input[name],select[name],textarea[name]")) {
    if (el.type === "radio") { if (el.checked) data[el.name] = el.value; continue; }
    if (el.type === "file") continue;
    if (el.type === "checkbox") {
      if (!data[el.name]) data[el.name] = el.checked ? (el.value || "1") : "";
      continue;
    }
    data[el.name] = el.value;
  }
  for (const cv of form.querySelectorAll("canvas.sig")) {
    if (!cv.dataset.name) continue;
    // 1) Fallback DEFENSIVO: si por alguna razón MutationObserver no corrió,
    //    inicializar el canvas JUSTO ANTES de recolectar (última oportunidad).
    asegurarInitSiFalta(cv);

    // 2) Leer dataURL png (OBLIGATORIO, incluso si _vacio dice que no)
    let dataURL = "";
    try { dataURL = cv.toDataURL("image/png") || ""; } catch(_) { dataURL = ""; }

    // 3) Calcular ESTADO REAL de "vacio" (más robusto que cv._vacio() por si bug attach):
    //    - Si _vacio() = true → seguro vacío
    //    - Sino: si dataURL < 150 caracteres → firma vacía (PNG transparente sin dibujar ~67-80 bytes)
    //    - Sino: comprobar que empiece por data:image/
    let estaVacia = true;
    try {
      const fnVacio = (typeof cv._vacio === "function") ? cv._vacio : null;
      if (fnVacio && fnVacio() === true) {
        estaVacia = true;
      } else if (!dataURL || typeof dataURL !== "string" || dataURL.length < 150) {
        estaVacia = true;
      } else if (!dataURL.startsWith("data:image/")) {
        estaVacia = true;
      } else {
        estaVacia = false;
      }
    } catch (_) {
      estaVacia = true;
    }

    data[cv.dataset.name] = estaVacia ? "" : dataURL;
  }
  for (const fi of form.querySelectorAll("input[type=file][data-foto]")) {
    if (fi.files && fi.files[0]) data[fi.dataset.foto] = await fotoADataURL(fi.files[0]);
  }
  return data;
}

/* ---------- Cerrar sesión (handler robusto: siempre redirige a /login) ---------- */
function cerrarSesion() {
  const irLogin = () => { location.href = "/login"; };
  try {
    postJSON("/api/logout", {})
      .then((r) => irLogin())
      .catch(() => irLogin());
    setTimeout(irLogin, 1500);
  } catch (e) {
    irLogin();
  }
}
window.cerrarSesion = cerrarSesion;

/* ---------- Purga automática de service workers / cachés obsoletos ---------- */
/* Elimina cualquier SW antiguo que cacheara app.js/style.css antiguos y que
   pudiera producir errores como 501 Unsupported method por servir páginas corruptas. */
async function purgaSWyCachesObsoletos() {
  try {
    if ("serviceWorker" in navigator) {
      const regs = await navigator.serviceWorker.getRegistrations();
      if (regs && regs.length) {
        for (const r of regs) {
          try { r.unregister(); } catch (e) {}
        }
      }
    }
  } catch (e) {}
  try {
    if ("caches" in window) {
      const ks = await caches.keys();
      for (const k of ks) {
        // Purga caches antiguos (distintos a la versión actual) y cualquier v2-v3 obsoleto
        if (!/v20260922/.test(k)) {
          try { await caches.delete(k); } catch (e) {}
        }
      }
    }
  } catch (e) {}
}
window.purgaSWyCachesObsoletos = purgaSWyCachesObsoletos;
// Llama automáticamente después de 1 segundo para no bloquear el primer paint
setTimeout(purgaSWyCachesObsoletos, 1000);

/* ---------- Checkbox Envío DIRECTO a CEDIS: resalta y enfoca campos de quién recibe ---------- */
function initEnvioDirecto() {
  const chk = document.getElementById("chk-envio-directo");
  if (!chk) return;
  const wrap = document.getElementById("envio-directo-wrap");
  const blkRecoge = document.getElementById("bloque-cliente-recoge") || document.getElementById("bloque-cliente-recibe");
  const inputRecibe = document.getElementById("input-recibe");
  function aplicar() {
    if (chk.checked) {
      wrap.classList.add("activo");
      if (blkRecoge) { blkRecoge.classList.add("resaltado"); }
      if (inputRecibe && !inputRecibe.value) {
        inputRecibe.focus();
        inputRecibe.placeholder = "👈 ¡Llena esta casilla para CEDIS! Nombre completo de quien recibe";
      }
    } else {
      wrap.classList.remove("activo");
      if (blkRecoge) blkRecoge.classList.remove("resaltado");
    }
  }
  chk.addEventListener("change", aplicar);
  aplicar();
}

/* ---------- SUMA AUTOMÁTICA: Total unidades = cajas + bolsas + cavas + sobres ---------- */
function initTotalesBultos() {
  // Por cada formulario o contenedor que tenga inputs con [data-bulto], calcular total
  function recalcular(scope) {
    const bultos = scope.querySelectorAll("input[data-bulto]");
    if (!bultos.length) return;
    let suma = 0;
    bultos.forEach((inp) => {
      const v = parseInt(inp.value || "0", 10);
      suma += isNaN(v) ? 0 : Math.max(0, v);
    });
    const totalInput = scope.querySelector("input[data-total-unidades]");
    if (totalInput) {
      totalInput.value = String(suma);
      totalInput.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }
  // Delegación: escuchar todos los inputs del documento
  document.addEventListener("input", (ev) => {
    const inp = ev.target;
    if (!inp.matches("input[data-bulto]")) return;
    const scope = inp.closest("form, fieldset, .bultos-grid, section");
    if (scope) recalcular(scope);
  });
  // Calcular al cargar (para formularios editar con valores preexistentes)
  document.querySelectorAll(".bultos-grid, form").forEach((scope) => recalcular(scope));
}

/* ---------- Renderizar chips de documentos separados por "-" ---------- */
function initDocsChips() {
  document.querySelectorAll("[data-docs-chips]").forEach((el) => {
    const texto = (el.dataset.docsChips || (el.textContent ? el.textContent.trim() : ""));
    if (!texto) return;
    const partes = texto.split("-").map((p) => p.trim()).filter((p) => p.length > 0);
    if (!partes.length) return;
    // Si solo hay 1 y no se ve separación clara, no generar nada raro
    const html = partes.map((p) => `<span class="chip-doc">${p}</span>`).join("");
    const wrap = document.createElement("div");
    wrap.className = "docs-chips";
    wrap.innerHTML = html;
    // Ocultar texto original y añadir chips al lado
    const padre = el.closest(".kv, td, p, div");
    if (padre && padre.tagName === "DIV" && padre.classList.contains("kv")) {
      const valor = padre.querySelector("b");
      if (valor) {
        valor.innerHTML = "";
        valor.appendChild(wrap);
      }
    } else {
      el.style.display = "none";
      el.insertAdjacentElement("afterend", wrap);
    }
  });
}

/* ---------- Botón "Mostrar/Ocultar formulario para editar" ---------- */
function initToggleEditar() {
  const btn = document.getElementById("btn-toggle-editar");
  const form = document.getElementById("form-editar-guia");
  if (!btn || !form) return;
  btn.addEventListener("click", () => {
    const visible = form.style.display !== "none";
    form.style.display = visible ? "none" : "grid";
    btn.textContent = visible ? "Mostrar formulario" : "Ocultar formulario";
    if (!visible) setTimeout(() => form.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  });
}

/* ---------- Autollenado de clientes desde lista JSON ---------- */
function initAutollenadoClientes() {
  const holder = document.getElementById("clientes-data");
  if (!holder) return;
  const dl = document.getElementById("lista-clientes-vta");
  const inpCliente = document.getElementById("input-cliente");
  const inpDireccion = document.getElementById("input-direccion");
  if (!dl || !inpCliente) return;
  let lista = [];
  try { lista = JSON.parse(holder.dataset.json || "[]"); } catch (e) {}
  if (!Array.isArray(lista) || !lista.length) return;
  for (const c of lista) {
    if (!c || !c.nombre) continue;
    const op = document.createElement("option");
    op.value = String(c.nombre);
    op.dataset.direccion = String(c.direccion || "");
    op.dataset.ciudad = String(c.ciudad || "");
    dl.appendChild(op);
  }
  inpCliente.addEventListener("change", () => {
    const val = inpCliente.value;
    const match = lista.find((c) => String(c.nombre) === val);
    if (match) {
      if (inpDireccion && match.direccion && !inpDireccion.value) inpDireccion.value = match.direccion;
    }
  });
}

/* ---------- Toggle PROPIO/EXTERNO y cargar transportadores (Admin Unificado) ---------- */
function initBloqueAdminUnificado() {
  const bloque = document.getElementById("bloque-admin-unificado");
  if (!bloque) return;
  const radios = bloque.querySelectorAll("input[type=radio][data-tipo-radio]");
  const wrapPropios = document.getElementById("wrap-propios");
  const wrapExterno = document.getElementById("wrap-externo");
  function aplicar() {
    const sel = bloque.querySelector("input[type=radio][data-tipo-radio]:checked");
    const tipo = sel ? sel.value : "";
    if (wrapPropios) wrapPropios.style.display = tipo === "propio" ? "block" : "none";
    if (wrapExterno) wrapExterno.style.display = tipo === "externo" ? "block" : "none";
  }
  radios.forEach((r) => r.addEventListener("change", aplicar));
  aplicar();
  // Cargar transportadores propios en el select
  const selT = document.getElementById("select-transp-propios-unif");
  if (selT) {
    fetch("/api/usuarios/rol/transportador").then(r => r.json()).then(d => {
      if (d && d.ok && d.transportadores) {
        const prev = selT.dataset.prev || "";
        selT.innerHTML = '<option value="">-- Seleccione un transportador --</option>' +
          d.transportadores.map(t =>
            `<option value="${t.id}" ${prev === String(t.id) ? "selected" : ""}>${t.nombre} (${t.usuario})</option>`
          ).join("");
      }
    }).catch(() => { selT.innerHTML = '<option value="">Error cargando transportadores</option>'; });
  }
}

/* ---------- ACORDEÓN ERP · delegación de eventos ---------- */
function initAccordion() {
  // Delegación: un solo listener en document para acordeones creados dinámicamente
  document.addEventListener("click", (ev) => {
    const header = ev.target.closest(".acc-header");
    if (!header) return;
    const acc = header.closest(".acc");
    if (!acc) return;
    ev.preventDefault();
    acc.classList.toggle("abierto");
    // Scroll suave si se abre y está cerca del borde inferior
    if (acc.classList.contains("abierto")) {
      setTimeout(() => {
        const r = acc.getBoundingClientRect();
        if (r.bottom > (window.innerHeight || document.documentElement.clientHeight) - 40) {
          acc.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }, 260);
    }
  });
  // Si se quiere que alguno venga abierto por defecto, agregar data-abierto="1"
  document.querySelectorAll(".acc[data-abierto='1']").forEach((a) => a.classList.add("abierto"));
}
window.initAccordion = initAccordion;

/* ---------- arranque ---------- */
/* ================================================================
   MULTI-DOCUMENTOS (Ventas): chips dinámicos Prefijo + N°
   Combina FV, TB, PD, TR en la misma guía; evita duplicados;
   serializa JSON + string legacy; valida antes de submit.
   ================================================================ */
function _docRowHtml(index, prefixOpts, defaultPrefix, defaultNumero) {
  const opts = prefixOpts.map(p => `<option value="${p}"${p === defaultPrefix ? ' selected' : ''}>${p}</option>`).join("");
  return (
    `<div class="doc-row" data-doc-index="${index}">
       <select name="doc_prefijo_${index}" class="doc-prefijo" aria-label="Prefijo documento ${index+1}">
         ${opts}
       </select>
       <input type="text" name="doc_numero_${index}" class="doc-numero"
              placeholder="N° ${index+1} · ej: 20929 o FV-20929"
              value="${defaultNumero || ""}"
              autocomplete="off"
              aria-label="Número documento ${index+1}">
       <button type="button" class="btn-quitar" title="Quitar este documento"
               aria-label="Quitar documento ${index+1}"${index === 0 ? ' disabled' : ''}>
         🗑️
       </button>
     </div>`
  );
}
function initMultiDocs(rootSel /* "#multi-docs-nueva-guia" */) {
  const root = document.querySelector(rootSel);
  if (!root) return;
  const prefixOpts = (root.dataset.prefixOptions || "FV,TB,PD,TR").split(",").map(s => s.trim()).filter(Boolean);
  const defaultPrefix = (root.dataset.defaultPrefix || "FV").trim();
  const wrapper = root.querySelector("#docs-wrapper");
  const btnAgregar = root.querySelector("#btn-agregar-doc");
  const inputJson    = document.getElementById("documentos_json");
  const inputPrefijo = document.getElementById("prefijo-hidden-legacy");
  const inputDocs    = document.getElementById("documentos-hidden-legacy");
  const badgeCount   = root.querySelector("#docs-count-badge");
  const validBox     = root.querySelector("#docs-validaciones");

  function _idx() { return wrapper.querySelectorAll(".doc-row").length; }
  function _renderCount() { if (badgeCount) badgeCount.textContent = String(_idx()); }

  function agregarFila(pref, num) {
    const i = _idx();
    wrapper.insertAdjacentHTML("beforeend", _docRowHtml(i, prefixOpts, pref || defaultPrefix, num || ""));
    const row = wrapper.lastElementChild;
    const btnQ = row.querySelector(".btn-quitar");
    if (btnQ) btnQ.addEventListener("click", () => {
      const rows = wrapper.querySelectorAll(".doc-row");
      if (rows.length <= 1) return;
      row.remove();
      [...wrapper.querySelectorAll(".doc-row")].forEach((r, j) => { r.dataset.docIndex = String(j); });
      [...wrapper.querySelectorAll(".doc-prefijo")].forEach((s, j) => { s.name = `doc_prefijo_${j}`; s.setAttribute("aria-label", `Prefijo documento ${j+1}`); });
      [...wrapper.querySelectorAll(".doc-numero")].forEach((s, j) => { s.name = `doc_numero_${j}`; s.setAttribute("aria-label", `Número documento ${j+1}`); s.placeholder = `N° ${j+1} · ej: 20929`; });
      [...wrapper.querySelectorAll(".btn-quitar")].forEach((b, j) => {
        b.setAttribute("aria-label", `Quitar documento ${j+1}`);
        if (j === 0) { b.disabled = true; } else { b.disabled = false; }
      });
      _renderCount();
    });
    _renderCount();
  }
  // fila inicial (por lo menos 1)
  agregarFila(defaultPrefix, "");

  if (btnAgregar) {
    btnAgregar.addEventListener("click", () => agregarFila(defaultPrefix, ""));
  }

  function _normalizarNum(s) { return String(s || "").trim().toUpperCase().replace(/[\s\-_/().]+/g, ""); }

  function validarYOcultar() {
    const errs = [];
    const rows = [...wrapper.querySelectorAll(".doc-row")];
    const items = [];
    const claves = new Set();
    rows.forEach((row, i) => {
      const p = (row.querySelector(".doc-prefijo").value || "").trim();
      const n = (row.querySelector(".doc-numero").value || "").trim();
      if (!p) errs.push(`Línea ${i+1}: prefijo vacío`);
      if (!n) errs.push(`Línea ${i+1}: número vacío`);
      if (p && n) {
        const clave = `${p}|${_normalizarNum(n)}`;
        if (claves.has(clave)) errs.push(`Documento repetido: ${p} ${n} (línea ${i+1})`);
        claves.add(clave);
        items.push({ prefijo: p, numero: n });
      }
    });
    validBox.innerHTML = errs.map(e => `<div class="err">⚠️ ${escapeHtml(e)}</div>`).join("");
    return { ok: errs.length === 0, items, errs };
  }
  function serializeHide() {
    const { ok, items } = validarYOcultar();
    if (!ok) return false;
    if (inputJson)    inputJson.value = JSON.stringify(items);
    if (inputPrefijo) inputPrefijo.value = items[0].prefijo;
    if (inputDocs)    inputDocs.value = items.map(it => `${it.prefijo} ${it.numero}`).join(" - ");
    return true;
  }

  // validación en vivo
  wrapper.addEventListener("change", validarYOcultar);
  wrapper.addEventListener("input", validarYOcultar);

  // attach al submit del formulario PADRE (nueva guía / editar guía)
  const form = root.closest("form");
  if (form) {
    form.addEventListener("submit", (ev) => {
      const ok = serializeHide();
      if (!ok) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        const firstEmpty = wrapper.querySelector(".doc-numero:placeholder-shown, .doc-numero[value='']");
        if (firstEmpty) firstEmpty.focus();
      }
    }, true);
  }
  root._multiDocs = { validarYOcultar, serializeHide, agregarFila };
}
window.initMultiDocs = initMultiDocs;

/* ---------- CAPTCHA login (refresh dinámico sin page reload) ---------- */
async function refreshCaptcha(scope) {
  const root = scope ? (typeof scope === "string" ? document.querySelector(scope) : scope) : document;
  if (!root) return false;
  const btn = root.querySelector("#btn-refresh-captcha");
  const svgWrap = root.querySelector("#captcha-svg-wrap");
  const tokInput = root.querySelector("#captcha-token");
  const respInput = root.querySelector("#captcha-input, input[name=captcha_respuesta]");
  if (!btn || !svgWrap || !tokInput) return false;
  try {
    btn.disabled = true;
    btn.style.opacity = ".6";
    btn.textContent = "⌛ Generando…";
    const res = await fetch("/api/captcha/nuevo", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: "{}",
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    if (!data || !data.svg || !data.token) throw new Error("respuesta incompleta");
    svgWrap.innerHTML = data.svg;
    tokInput.value = String(data.token || "");
    if (respInput) { respInput.value = ""; respInput.focus({ preventScroll: true }); }
    return true;
  } catch (err) {
    console.error("[captcha] refresh falló:", err);
    alert("No se pudo recargar el CAPTCHA. Refresca la página manualmente.");
    return false;
  } finally {
    btn.disabled = false;
    btn.style.opacity = "";
    btn.textContent = "🔄 Nuevo";
  }
}
function initCaptcha() {
  const btn = document.getElementById("btn-refresh-captcha");
  if (!btn) return;
  btn.addEventListener("click", (ev) => {
    ev.preventDefault();
    refreshCaptcha(document);
  });
  btn.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      refreshCaptcha(document);
    }
  });
}
window.refreshCaptcha = refreshCaptcha;
window.initCaptcha = initCaptcha;

/* ================================================================
   RESETEAR CONTRASEÑA DE OTRO USUARIO (solo panel Admin)
   El endpoint lleva el usuario en la URL, así que este formulario no
   puede usar el binder genérico de form[data-api].
   ================================================================ */
function initResetClave() {
  var form = document.getElementById("form-reset-clave");
  var boton = document.getElementById("btn-reset-clave");
  if (!form || !boton) return;

  boton.addEventListener("click", function () {
    var usuario = ((form.querySelector("#reset-clave-usuario") || {}).value || "").trim();
    var clave = ((form.querySelector('input[name="clave_nueva"]') || {}).value || "");
    if (!usuario || clave.length < 6) {
      alert("Escribe el usuario y una contraseña nueva de al menos 6 caracteres.");
      return;
    }
    if (!window.confirm(
      "Se restablecerá la contraseña de '" + usuario + "' y se cerrarán todas sus sesiones.\n\n¿Continuar?"
    )) return;

    boton.disabled = true;
    postJSON("/api/usuarios/" + encodeURIComponent(usuario) + "/restablecer_clave", { clave_nueva: clave })
      .then(function () {
        alert("Contraseña de '" + usuario + "' restablecida.");
        form.reset();
      })
      .catch(function (err) {
        alert("⚠️ " + ((err && err.message) || "No se pudo restablecer la contraseña."));
      })
      .finally(function () {
        boton.disabled = false;
      });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initAccordion();
  initCaptcha();
  // =============================================================
  // Inicializar multi-docs (nueva_guia / editar_guia)
  // =============================================================
  if (document.getElementById("multi-docs-nueva-guia")) initMultiDocs("#multi-docs-nueva-guia");
  if (document.getElementById("multi-docs-editar-guia")) initMultiDocs("#multi-docs-editar-guia");

  // ---- ATENCIÓN: NO inicializar canvas.sig con forEach() aquí directamente ----
  // El problema anterior era: los canvas del PROCESO ADMINISTRATIVO (pestañas
  // Transportador Propio / Externo) se agregaban al DOM DINÁMICAMENTE (innerHTML)
  // DESPUÉS de DOMContentLoaded → forEach() no los alcanzaba y NO tenían
  // attachado pointerdown/pointermove → cursor no dibujaba nada.
  // SOLUCIÓN: usar setupObservadorFirmas() con MutationObserver GLOBAL que detecta
  // canvas.sig NUEVOS en el DOM en CUALQUIER MOMENTO (inicial o dinámico) y
  // les attacha initSig + botón limpiar.
  setupObservadorFirmas();

  document.querySelectorAll("form[data-api]").forEach((form) => {
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      ev.stopImmediatePropagation();

      // ---- Bloqueo DOBLE de doble submit (muy importante en móviles con toque lento) ----
      if (form.dataset.procesando === "1") {
        console.warn("[guias] formulario YA está siendo procesado (doble click prevenido)");
        return;
      }
      form.dataset.procesando = "1";

      // Deshabilitar TODOS los botones del formulario (no solo submit)
      const todosBtns = form.querySelectorAll("button, input[type=submit], .btn");
      todosBtns.forEach((b) => { try { b.disabled = true; b.style.opacity = ".6"; b.style.pointerEvents = "none"; } catch(_){} });

      // Buscar también el botón que el usuario clickeó (fuera o dentro del form, si .btn)
      // No importa: ya deshabilitamos todos los .btn dentro del form.
      try {
        if (form.dataset.confirm && !confirm(form.dataset.confirm)) {
          // --- Cancelación: restaurar y salir ---
          form.dataset.procesando = "";
          todosBtns.forEach((b) => { try { b.disabled = false; b.style.opacity = ""; b.style.pointerEvents = ""; } catch(_){} });
          return;
        }
        const data = await recolectar(form);
        const j = await postJSON(form.dataset.api, data);
        // NOTA: postJSON ya se encargó de alert(err) si falló; j = null en error.
        if (!j) {
          // --- Error: restaurar estado para reintentar ---
          form.dataset.procesando = "";
          todosBtns.forEach((b) => { try { b.disabled = false; b.style.opacity = ""; b.style.pointerEvents = ""; } catch(_){} });
          return;
        }

        // --- ÉXITO: REDIRECT-after-save (SPEC P4, SPEC v1.0): SIEMPRE a /tablero ---
        // Prioridad 1: redirect explícito en el payload (string que empiece por / o http)
        let destino = null;
        if (typeof j.redirect === "string" && j.redirect.length > 0) {
          destino = j.redirect.trim();
        }
        // Prioridad 2: si el form tiene data-redirect="true" y no hubo redirect explícito,
        // redirigimos AL TABLERO POR DEFECTO (comportamiento deseado 100% de los flujos).
        if (!destino && form.dataset.redirect === "true") {
          destino = "/tablero";
        }
        // Prioridad 3: si el destino no es una ruta relativa (/algo) ni absoluta (http),
        // forzar /tablero para evitar quedarse en la misma página.
        if (destino && !(destino.startsWith("/") || destino.startsWith("http://") || destino.startsWith("https://"))) {
          destino = "/tablero";
        }

        if (destino) {
          // Forzar navegación (no .reload): location.href = ...
          // Poner un pequeño timeout para que el alert de éxito (si no hay redirect fuerte)
          // alcance a salir, pero sin bloquear.
          setTimeout(() => {
            try {
              window.location.href = destino;
            } catch (_) {
              window.location.replace(destino);
            }
          }, 50);
          return; // IMPORTANTE: no seguir para no hacer reload por accidente
        }

        // --- Solo si NO hubo ninguna indicación de redirect: recargar página actual ---
        setTimeout(() => { window.location.reload(); }, 60);
      } catch (e) {
        // --- Error inesperado (red o JSON): restaurar ---
        console.error("[guias] error submit form", e);
        try { alert("⚠️ Error inesperado al guardar. Revisa tu conexión e inténtalo de nuevo."); } catch(_){}
        form.dataset.procesando = "";
        todosBtns.forEach((b) => { try { b.disabled = false; b.style.opacity = ""; b.style.pointerEvents = ""; } catch(_){} });
      }
    });
  });
  initBloqueAdminUnificado();
  initResetClave();
  initEnvioDirecto();
  initTotalesBultos();
  initToggleEditar();
  initAutollenadoClientes();
  initDocsChips();
  initToggleTema();
  initAutocompletadoNitVentas();
});

/* ================================================================
   TOGGLE TEMA CLARO / OSCURO / AUTO  (WCAG + persistencia)
   Ciclo: light → dark → auto → light ...
   Persistencia: localStorage.theme_preference ∈ {'light','dark','auto'}
   Respeta @media (prefers-color-scheme) cuando auto.
   ================================================================ */
function initToggleTema(){
  try{
    var btn = document.getElementById('btn-toggle-tema');
    var metaTheme = document.getElementById('meta-theme-color');
    if (!btn) return;

    function _aplicarTema(){
      var pref = localStorage.getItem('theme_preference') || 'auto';
      var dark;
      if (pref === 'dark') dark = true;
      else if (pref === 'light') dark = false;
      else dark = !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
      document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
      if (metaTheme){ metaTheme.setAttribute('content', dark ? '#0b1220' : '#1d4ed8'); }
      btn.setAttribute('aria-pressed', String(dark));
      btn.title = 'Tema: ' + pref + ' (clica para cambiar)';
    }

    function _ciclarPref(){
      var actual = localStorage.getItem('theme_preference') || 'auto';
      var sig = 'auto';
      if (actual === 'light') sig = 'dark';
      else if (actual === 'dark') sig = 'auto';
      else sig = 'light';
      localStorage.setItem('theme_preference', sig);
      _aplicarTema();
    }

    btn.addEventListener('click', function(e){ e.preventDefault(); e.stopPropagation(); _ciclarPref(); });
    btn.addEventListener('keydown', function(e){ if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); _ciclarPref(); }});

    // Listener cambio tema SO cuando la preferencia es "auto" (respeta OS en tiempo real)
    if (window.matchMedia){
      var mql = window.matchMedia('(prefers-color-scheme: dark)');
      var _onChange = function(){ if ((localStorage.getItem('theme_preference') || 'auto') === 'auto') _aplicarTema(); };
      try { mql.addEventListener('change', _onChange); } catch(_){ try { mql.addListener(_onChange); } catch(__){} }
    }

    _aplicarTema();
  }catch(e){ console.warn('[tema] init fallo (no bloqueante):', e); }
}

/* ================================================================
   AUTOCOMPLETADO NIT PANEL VENTAS
   - Debounce 200ms para no spamear el servidor
   - Endpoint: GET /api/clientes/buscar?q=<texto>
   - Selección (click o Enter) rellena 5 campos:
     cliente, direccion, ciudad, telefono, email
   - Navegación teclado ↑ ↓ Enter Escape
   ================================================================ */
function initAutocompletadoNitVentas(){
  try{
    var input = document.getElementById('input-nit');
    var panel = document.getElementById('panel-nit');
    var wrap  = document.getElementById('wrap-nit');
    if (!input || !panel || !wrap) return;

    var debounceTimer = null;
    var resultadosCache = [];   // array [{nit,razon_social,direccion,ciudad,telefono,email,cliente_descubierto}...]
    var valoresAutocompletados = [];
    var activoIdx = -1;
    var requestSeq = 0;

    function $id(n){ return document.getElementById(n); }
    function _cerrarPanel(){ panel.classList.remove('visible'); input.setAttribute('aria-expanded','false'); activoIdx = -1; }
    function _abrirPanel(){ panel.classList.add('visible'); input.setAttribute('aria-expanded','true'); }
    function _normalizarNit(valor){ return String(valor || '').replace(/[^0-9]/g, '').replace(/^0+/, ''); }

    function _limpiarCamposAutocompletados(){
      valoresAutocompletados.forEach(function(item){
        if (item.element.value === item.value){
          item.element.value = '';
          _triggerChange(item.element);
        }
      });
      valoresAutocompletados = [];
    }

    function _renderItems(res, query){
      resultadosCache = res || [];
      panel.innerHTML = '';
      if (!resultadosCache.length){
        var e = document.createElement('div');
        e.className = 'ac-nit-empty';
        e.textContent = (query && query.length > 0) ? ('Sin resultados para "' + query + '". Puedes continuar ingresando los datos manualmente.') : 'Escribe NIT, razón social, ciudad, teléfono o contacto...';
        panel.appendChild(e);
        _abrirPanel();
        return;
      }
      resultadosCache.forEach(function(r, i){
        var it = document.createElement('div');
        it.className = 'ac-nit-item' + (i === activoIdx ? ' activo' : '');
        it.setAttribute('role','option');
        it.setAttribute('data-idx', String(i));
        it.setAttribute('aria-selected', i === activoIdx ? 'true' : 'false');
        var tagDesc = (r && r.cliente_descubierto) ? '<span class="tag-descubierto">descubierto</span>' : '';
        var ciudad = (r.ciudad||'').trim();
        var telef = (r.telefono||'').trim();
        var meta_parts = [];
        if (ciudad) meta_parts.push(ciudad);
        if (telef) meta_parts.push('📞 ' + telef);
        if (r.email){ var em = (r.email||'').trim(); if (em) meta_parts.push('✉ ' + (em.length > 28 ? em.slice(0,25)+'…' : em)); }
        it.innerHTML =
          '<div class="nit-row"><span class="nit"></span>' + tagDesc + '</div>' +
          '<div class="razon"></div>' +
          (meta_parts.length ? ('<div class="meta">' + meta_parts.join('  ·  ') + '</div>') : '');
        it.querySelector('.nit').textContent = r.nit || '';
        it.querySelector('.razon').textContent = r.razon_social || '(sin razón social)';
        it.addEventListener('mouseenter', function(){ _setActivo(i); });
        it.addEventListener('mousedown', function(ev){
          ev.preventDefault();
          _seleccionar(i);
        });
        panel.appendChild(it);
      });
      _abrirPanel();
    }

    function _setActivo(i){
      activoIdx = (i + resultadosCache.length) % (resultadosCache.length || 1);
      if (!resultadosCache.length) activoIdx = -1;
      Array.prototype.forEach.call(panel.querySelectorAll('.ac-nit-item'), function(el, idx){
        if (idx === activoIdx){ el.classList.add('activo'); el.setAttribute('aria-selected','true'); el.scrollIntoView({block:'nearest'}); }
        else { el.classList.remove('activo'); el.setAttribute('aria-selected','false'); }
      });
    }

    function _llenarCampos(r){
      if (!r) return;
      var fldMap = [
        ['input-cliente', 'razon_social'],
        ['input-direccion', 'direccion'],
      ];
      // Ciudad y teléfono/email: buscar por name en formulario
      var form = input.closest('form');
      fldMap.forEach(function(p){
        var el = $id(p[0]);
        if (el && r[p[1]] != null && String(r[p[1]]).trim() !== ''){
          el.value = String(r[p[1]]);
          valoresAutocompletados.push({element:el, value:el.value});
          _triggerChange(el);
        }
      });
      if (form){
        var inp = form.querySelector('input[name="ciudad"]');
        if (inp && r.ciudad){
          inp.value = String(r.ciudad);
          valoresAutocompletados.push({element:inp, value:inp.value});
          _triggerChange(inp);
        }
        var itel = form.querySelector('input[name="transportador_tel"]'); // teléfono general del form
        var iemail = form.querySelector('input[name="email"]'); // posible, no siempre
        // Los teléfonos y emails van como auxiliares del bloque cliente (no siempre existen en el form ventas): los guardamos si existe algún campo genérico
      }
    }

    function _triggerChange(el){ try { el.dispatchEvent(new Event('input',{bubbles:true})); } catch(_){} try { el.dispatchEvent(new Event('change',{bubbles:true})); } catch(_){} }

    function _seleccionar(i){
      var r = resultadosCache[i];
      if (!r) return;
      input.value = r.nit || '';
      _llenarCampos(r);
      _cerrarPanel();
      try { input.focus(); } catch(_){}
      // Saltar al siguiente campo accesible (cliente) si está vacío
      try{
        var c = $id('input-cliente');
        if (c && (!c.value || !c.value.trim())){ c.focus(); c.select && c.select(); }
      }catch(_){}
    }

    function _ejecutarBusqueda(q){
      if (!q || q.trim().length < 1){ _renderItems([], ''); return; }
      var seqAtendida = ++requestSeq;
      panel.innerHTML = '<div class="ac-nit-loading">Buscando…</div>';
      _abrirPanel();
      var url = '/api/clientes/buscar?q=' + encodeURIComponent(q.trim()) + '&limite=10';
      fetch(url, {credentials:'same-origin',cache:'no-store'})
        .then(function(resp){ return resp.json(); })
        .then(function(js){
          if (seqAtendida !== requestSeq) return; // respuesta vieja descartada
          if (js && js.ok){
            var resultados = js.resultados || [];
            var nitBuscado = _normalizarNit(q);
            var idxExacto = nitBuscado ? resultados.findIndex(function(r){
              return _normalizarNit(r && r.nit) === nitBuscado;
            }) : -1;
            if (idxExacto >= 0){
              resultadosCache = resultados;
              _seleccionar(idxExacto);
              return;
            }
            _renderItems(resultados, q);
          }
          else { _renderItems([], q); }
        })
        .catch(function(){
          if (seqAtendida !== requestSeq) return;
          panel.innerHTML = '<div class="ac-nit-empty">⚠️ No se pudo consultar clientes. Ingresa los datos manualmente.</div>';
          _abrirPanel();
        });
    }

    input.addEventListener('input', function(){
      var q = input.value || '';
      requestSeq++;
      resultadosCache = [];
      _cerrarPanel();
      _limpiarCamposAutocompletados();
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function(){ _ejecutarBusqueda(q); }, 200);
    });

    input.addEventListener('keydown', function(e){
      var visible = panel.classList.contains('visible');
      if (e.key === 'ArrowDown'){
        e.preventDefault();
        if (!visible){ _ejecutarBusqueda(input.value || ''); return; }
        _setActivo(activoIdx + 1);
      } else if (e.key === 'ArrowUp'){
        e.preventDefault();
        if (visible) _setActivo(activoIdx - 1);
      } else if (e.key === 'Enter'){
        if (visible && activoIdx >= 0 && resultadosCache[activoIdx]){
          e.preventDefault();
          _seleccionar(activoIdx);
        } else {
          // Enter normal: no haga nada, deje que el flujo siga
        }
      } else if (e.key === 'Escape'){
        if (visible){ e.preventDefault(); _cerrarPanel(); }
      } else if (e.key === 'Tab'){
        // Tab esconde panel casi inmediato
        setTimeout(_cerrarPanel, 30);
      }
    });

    input.addEventListener('focus', function(){
      if ((input.value||'').trim().length > 0) _ejecutarBusqueda(input.value);
      else _renderItems([], '');
    });

    // Cerrar al click fuera del wrap (con retardo para permitir mousedown item)
    document.addEventListener('click', function(ev){
      try {
        if (!wrap.contains(ev.target)) setTimeout(_cerrarPanel, 40);
      } catch(_){}
    }, true);
  }catch(e){
    console.warn('[autocompletar NIT] init fallo (no bloqueante):', e);
  }
}
