/* Guías Coodescor · JS local sin dependencias */
"use strict";

/* ---------- envío JSON de formularios ---------- */
async function postJSON(url, data) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  let j = {};
  try { j = await r.json(); } catch (e) {}
  if (!r.ok || !j.ok) {
    alert("⚠️ " + (j.error || "error " + r.status));
    return null;
  }
  if (j.mensaje) setTimeout(() => alert("✅ " + j.mensaje), 150);
  return j;
}
window.postJSON = postJSON;

/* ---------- firma táctil (canvas) ---------- */
function initSig(canvas) {
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.lineWidth = 2.4; ctx.lineCap = "round"; ctx.lineJoin = "round";
  ctx.strokeStyle = "#12244a";
  let dibujando = false, vacio = true;
  canvas._vacio = () => vacio;
  const pos = (ev) => {
    const r = canvas.getBoundingClientRect();
    return [ev.clientX - r.left, ev.clientY - r.top];
  };
  canvas.addEventListener("pointerdown", (ev) => {
    ev.preventDefault();
    canvas.setPointerCapture(ev.pointerId);
    dibujando = true;
    const [x, y] = pos(ev);
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 0.01, y + 0.01); ctx.stroke();
    vacio = false;
  });
  canvas.addEventListener("pointermove", (ev) => {
    if (!dibujando) return;
    const [x, y] = pos(ev);
    ctx.lineTo(x, y); ctx.stroke();
  });
  ["pointerup", "pointercancel", "pointerleave"].forEach((t) =>
    canvas.addEventListener(t, () => { dibujando = false; }));
}

function limpiarCanvas(canvas) {
  const ctx = canvas.getContext("2d");
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.restore();
  canvas._vacio = () => true;
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
    if (cv.dataset.name) data[cv.dataset.name] = cv._vacio && cv._vacio() ? "" : cv.toDataURL("image/png");
  }
  for (const fi of form.querySelectorAll("input[type=file][data-foto]")) {
    if (fi.files && fi.files[0]) data[fi.dataset.foto] = await fotoADataURL(fi.files[0]);
  }
  return data;
}

/* ---------- Checkbox Envío DIRECTO a CEDIS: resalta y enfoca campos de quién recibe ---------- */
function initEnvioDirecto() {
  const chk = document.getElementById("chk-envio-directo");
  if (!chk) return;
  const wrap = document.getElementById("envio-directo-wrap");
  const blkRecibe = document.getElementById("bloque-cliente-recibe");
  const inputRecibe = document.getElementById("input-recibe");
  function aplicar() {
    if (chk.checked) {
      wrap.classList.add("activo");
      if (blkRecibe) { blkRecibe.classList.add("resaltado"); }
      if (inputRecibe && !inputRecibe.value) {
        inputRecibe.focus();
        inputRecibe.placeholder = "👈 ¡Llena esta casilla para CEDIS! Nombre de quien recibe en cliente";
      }
    } else {
      wrap.classList.remove("activo");
      if (blkRecibe) blkRecibe.classList.remove("resaltado");
    }
  }
  chk.addEventListener("change", aplicar);
  aplicar();
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

/* ---------- arranque ---------- */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("canvas.sig").forEach(initSig);
  document.querySelectorAll("[data-limpiar]").forEach((b) =>
    b.addEventListener("click", () => {
      const box = b.closest(".sigbox") || b.parentElement;
      box.querySelectorAll("canvas.sig").forEach(limpiarCanvas);
    }));
  document.querySelectorAll("form[data-api]").forEach((form) => {
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const btn = form.querySelector("button[type=submit],button.btn");
      if (btn) btn.disabled = true;
      if (form.dataset.confirm && !confirm(form.dataset.confirm)) { if (btn) btn.disabled = false; return; }
      const data = await recolectar(form);
      const j = await postJSON(form.dataset.api, data);
      if (btn) btn.disabled = false;
      if (!j) return;
      if (form.dataset.redirect === "true" && j.redirect) location.href = j.redirect;
      else if (j.redirect) location.href = j.redirect;
      else location.reload();
    });
  });
  initEnvioDirecto();
  initToggleEditar();
  initAutollenadoClientes();
});
