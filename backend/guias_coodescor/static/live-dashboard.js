"use strict";

(() => {
  const notificationRoot = document.getElementById("global-notificaciones");
  const isDashboard = document.querySelector(".kpis");
  if (!notificationRoot) return;

  const role = notificationRoot.dataset.role || "";
  const readKey = `guias.notificaciones.leidas:${notificationRoot.dataset.userId}:${role}`;
  const readIds = new Set();
  let activeNotifications = [];
  let previousIds = new Set();
  let notificationsLoaded = false;
  let notificationSignature = "";
  let refreshingNotifications = false;
  let refreshingBoard = false;
  let notificationTimer;
  let boardTimer;

  try {
    JSON.parse(localStorage.getItem(readKey) || "[]").forEach((id) => readIds.add(id));
  } catch (error) {
    console.warn("No se pudieron leer las notificaciones guardadas:", error);
  }

  const saveReadIds = () => {
    try {
      localStorage.setItem(readKey, JSON.stringify([...readIds].slice(-300)));
    } catch (error) {
      console.warn("No se pudieron guardar las notificaciones leídas:", error);
    }
  };

  function renderNotifications(items) {
    activeNotifications = items.filter((item) => !readIds.has(item.id));
    const button = document.getElementById("global-notificaciones-bell");
    const badge = document.getElementById("global-notificaciones-badge");
    const list = document.getElementById("global-notificaciones-lista");
    const ids = activeNotifications.map((item) => item.id);
    badge.textContent = String(ids.length);
    badge.hidden = ids.length === 0;
    button.classList.toggle("has-new", ids.length > 0);

    const signature = activeNotifications.map((item) => `${item.id}:${item.cliente}`).join("|");
    if (signature === notificationSignature) return;
    notificationSignature = signature;
    list.replaceChildren();

    if (!activeNotifications.length) {
      const empty = document.createElement("p");
      empty.className = "global-notificaciones-vacio";
      empty.textContent = "No hay tareas pendientes para tu perfil.";
      list.appendChild(empty);
      return;
    }

    activeNotifications.forEach((item) => {
      const link = document.createElement("a");
      link.className = "global-notificaciones-item";
      link.href = `/guia/${encodeURIComponent(item.guia_id)}`;
      const title = document.createElement("strong");
      title.textContent = `Guía #${item.consecutivo || item.guia_id}`;
      const detail = document.createElement("span");
      detail.textContent = `${item.estado} · ${item.cliente || "Sin cliente"} · ${item.ciudad || "Sin ciudad"}`;
      link.append(title, detail);
      link.addEventListener("click", () => {
        readIds.add(item.id);
        saveReadIds();
      }, { once: true });
      list.appendChild(link);
    });
  }

  function showToast(item) {
    document.getElementById("global-notificacion-toast")?.remove();
    const toast = document.createElement("div");
    toast.id = "global-notificacion-toast";
    toast.className = "global-notificacion-toast";
    const open = document.createElement("a");
    open.className = "global-notificacion-toast-link";
    open.href = `/guia/${encodeURIComponent(item.guia_id)}`;
    const copy = document.createElement("span");
    const title = document.createElement("strong");
    title.textContent = `Guía #${item.consecutivo || item.guia_id} pendiente`;
    const detail = document.createElement("small");
    detail.textContent = `${item.estado} · ${item.cliente || "Sin cliente"}`;
    copy.append(title, detail);
    const close = document.createElement("button");
    close.type = "button";
    close.setAttribute("aria-label", "Cerrar aviso");
    close.textContent = "×";
    close.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toast.remove();
    });
    open.appendChild(copy);
    toast.append(open, close);
    document.body.appendChild(toast);
    window.setTimeout(() => toast.remove(), 8000);

    if ("Notification" in window && Notification.permission === "granted") {
      try {
        new Notification(title.textContent, { body: detail.textContent, tag: item.id });
      } catch (error) {
        console.warn("No se pudo mostrar la notificación del navegador:", error);
      }
    }
  }

  async function refreshNotifications() {
    if (refreshingNotifications) return;
    refreshingNotifications = true;
    try {
      const response = await fetch("/api/notificaciones/pendientes", {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!data.ok) throw new Error(data.error || "Respuesta de notificaciones inválida");
      const received = data.notificaciones || [];
      if (notificationsLoaded) {
        const arrived = received.find((item) => (
          !previousIds.has(item.id) && !readIds.has(item.id)
        ));
        if (arrived) showToast(arrived);
      }
      previousIds = new Set(received.map((item) => item.id));
      notificationsLoaded = true;
      renderNotifications(received);
      notificationRoot.classList.remove("sin-conexion");
    } catch (error) {
      notificationRoot.classList.add("sin-conexion");
      console.error("No se pudo actualizar el centro de notificaciones:", error);
    } finally {
      refreshingNotifications = false;
    }
  }

  const notificationButton = document.getElementById("global-notificaciones-bell");
  const notificationPanel = document.getElementById("global-notificaciones-panel");
  notificationButton.addEventListener("click", () => {
    notificationPanel.hidden = !notificationPanel.hidden;
    notificationButton.setAttribute("aria-expanded", String(!notificationPanel.hidden));
    if (!notificationPanel.hidden && "Notification" in window && Notification.permission === "default") {
      Notification.requestPermission().catch((error) => {
        console.warn("No se pudo solicitar permiso de notificaciones:", error);
      });
    }
  });
  document.getElementById("global-notificaciones-leer").addEventListener("click", () => {
    activeNotifications.forEach((item) => readIds.add(item.id));
    saveReadIds();
    renderNotifications([]);
  });
  document.addEventListener("click", (event) => {
    if (!notificationRoot.contains(event.target)) {
      notificationPanel.hidden = true;
      notificationButton.setAttribute("aria-expanded", "false");
    }
  });

  const stateColors = {
    CREADA: "#b45309",
    RECIBIDA_ADMIN: "#2563eb",
    EN_CEDIS: "#7c3aed",
    EN_RUTA: "#0284c7",
    ENTREGADA: "#15803d",
    ANULADA: "#b91c1c",
  };

  function createGuideCard(guide) {
    const item = document.createElement("div");
    item.className = "item-live";
    const open = document.createElement("a");
    open.className = "item-live-main";
    open.href = `/guia/${encodeURIComponent(guide.id)}`;
    const number = document.createElement("b");
    number.textContent = `No. ${guide.consecutivo || guide.id}`;
    const client = document.createElement("span");
    client.textContent = guide.cliente || "";
    const meta = document.createElement("small");
    meta.textContent = `${guide.ciudad || ""} · ${guide.creada_en || ""}`;
    const state = document.createElement("span");
    state.className = "chip";
    state.style.background = stateColors[guide.estado] || "#64748b";
    state.textContent = guide.estado || "";
    open.append(number, client, meta, state);
    item.appendChild(open);

    if (["admin", "ventas", "administrativo", "cedis"].includes(role)) {
      const print = document.createElement("a");
      print.className = "btn mini item-live-print";
      print.href = `/guia/${encodeURIComponent(guide.id)}/imprimir`;
      print.target = "_blank";
      print.rel = "noopener";
      print.textContent = "🖨️";
      print.setAttribute("aria-label", `Imprimir guía ${guide.consecutivo || guide.id}`);
      item.appendChild(print);
    }
    return item;
  }

  async function refreshBoard() {
    if (refreshingBoard || document.hidden || !isDashboard) return;
    refreshingBoard = true;
    try {
      const response = await fetch("/api/guias?limite=500", {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!data.ok) throw new Error(data.error || "Respuesta del tablero inválida");
      const guides = data.guias || [];
      (data.conteo_por_estado || []).forEach((count) => {
        const kpi = isDashboard.querySelector(`.kpi[kpi-estado="${count.estado}"] b`);
        if (kpi) kpi.textContent = String(count.n);
      });

      document.querySelectorAll(".acc[data-dashboard-state]").forEach((section) => {
        const state = section.dataset.dashboardState;
        const limit = Number(section.dataset.dashboardLimit) || 10;
        const matching = guides.filter((guide) => guide.estado === state).slice(0, limit);
        const signature = matching.map((guide) => `${guide.id}:${guide.estado}:${guide.creada_en}`).join("|");
        if (section.dataset.liveSignature === signature) return;
        section.dataset.liveSignature = signature;

        const body = section.querySelector(".acc-body");
        body.querySelector(".lista")?.remove();
        body.querySelector(".sin")?.remove();
        if (!matching.length) {
          const empty = document.createElement("p");
          empty.className = "sin";
          empty.textContent = "Sin pendientes 🎉";
          body.appendChild(empty);
        } else {
          const list = document.createElement("div");
          list.className = "lista lista-viva";
          matching.forEach((guide) => list.appendChild(createGuideCard(guide)));
          body.appendChild(list);
        }
        const badge = section.querySelector(".acc-badge");
        if (badge) {
          badge.textContent = matching.length
            ? `${matching.length} guía${matching.length === 1 ? "" : "s"}`
            : "vacía";
        }
      });

      const status = document.getElementById("tablero-sincronizacion");
      const statusText = document.getElementById("tablero-sincronizacion-texto");
      if (status && statusText) {
        status.classList.remove("sin-conexion");
        statusText.textContent = `Actualizado a las ${new Date().toLocaleTimeString()}`;
      }
    } catch (error) {
      const status = document.getElementById("tablero-sincronizacion");
      const statusText = document.getElementById("tablero-sincronizacion-texto");
      if (status && statusText) {
        status.classList.add("sin-conexion");
        statusText.textContent = "No se pudo actualizar; se reintentará automáticamente.";
      }
      console.error("No se pudo actualizar el tablero:", error);
    } finally {
      refreshingBoard = false;
    }
  }

  void refreshNotifications();
  notificationTimer = window.setInterval(() => {
    if (!document.hidden) void refreshNotifications();
  }, 2000);
  if (isDashboard) {
    void refreshBoard();
    boardTimer = window.setInterval(refreshBoard, 2000);
    document.addEventListener("visibilitychange", refreshBoard);
  }
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) void refreshNotifications();
  });
  window.addEventListener("pagehide", () => {
    window.clearInterval(notificationTimer);
    window.clearInterval(boardTimer);
  }, { once: true });
})();
