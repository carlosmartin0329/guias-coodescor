"use strict";
/* ==========================================================================
   Módulo de administración de la base de datos · Admin → Base de datos
   Consume /api/admin/db/* (solo accesible con rol admin).
   Reglas que sigue este archivo:
     - Todo texto que viene del servidor se inserta con textContent o con un
       escape propio. Nunca se concatena HTML sin escapar.
     - Toda operación destructiva pide confirmación explícita.
     - Los errores del servidor se muestran tal cual: el backend ya devuelve
       mensajes pensados para el usuario.
   ========================================================================== */

(function () {
  const API = "/api/admin/db";

  const estado = {
    base: "guias",
    tabla: null,
    esquema: null,
    pagina: 1,
    pageSize: 50,
    busqueda: "",
    orden: "",
    dir: "asc",
    editando: null,
  };

  /* ---------------------------------------------------------------- utils */

  const $ = (sel, raiz) => (raiz || document).querySelector(sel);
  const $$ = (sel, raiz) => Array.from((raiz || document).querySelectorAll(sel));

function esc(valor) {
    if (valor === null || valor === undefined) return "";
    return String(valor)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
}

/** Nodo de texto: la forma segura de insertar contenido. */
function txt(valor) {
    return document.createTextNode(valor === null || valor === undefined ? "" : String(valor));
}

function el(tag, atributos, hijos) {
    const nodo = document.createElement(tag);
    Object.entries(atributos || {}).forEach(([k, v]) => {
      if (v === null || v === undefined || v === false) return;
      if (k === "text") nodo.appendChild(txt(v));
      else if (k === "html") nodo.innerHTML = v;
      else nodo.setAttribute(k, v);
    });
    (hijos || []).forEach((h) => h && nodo.appendChild(h));
    return nodo;
}

function celda(valor, clase) {
    return el("td", { class: clase || "", text: valor === null || valor === undefined ? "—" : valor });
}

  function aviso(mensaje, tipo) {
    const caja = $("#db-aviso");
    if (!caja) return;
    if (!mensaje) {
      caja.hidden = true;
      caja.textContent = "";
      return;
    }
    caja.hidden = false;
    caja.textContent = mensaje;
    caja.className = "db-aviso db-" + (tipo || "info");
  }

  function cargando(destino, texto) {
    $(destino).textContent = "";
    $(destino).appendChild(el("p", { class: "sin", text: texto || "Cargando…" }));
  }

  async function pedir(metodo, ruta, cuerpo) {
    const opciones = {
      method: metodo,
      credentials: "same-origin",
      cache: "no-store",
      headers: { "Accept": "application/json" },
    };
    if (cuerpo !== undefined) {
      opciones.headers["Content-Type"] = "application/json";
      opciones.body = JSON.stringify(cuerpo);
    }
    const respuesta = await fetch(API + ruta, opciones);
    let datos = {};
    try {
      datos = await respuesta.json();
    } catch (e) {
      throw new Error("El servidor devolvió una respuesta inesperada (HTTP " + respuesta.status + ").");
    }
    if (!respuesta.ok || datos.ok === false) {
      throw new Error(datos.error || "Error HTTP " + respuesta.status);
    }
    return datos;
  }

  function confirmarAccion(texto) {
    return window.confirm(texto);
  }

  function bytes(n) {
    if (!n) return "0 B";
    const unidades = ["B", "KB", "MB", "GB"];
    let i = 0;
    let v = n;
    while (v >= 1024 && i < unidades.length - 1) {
      v /= 1024;
      i += 1;
    }
    return v.toFixed(i === 0 ? 0 : 1) + " " + unidades[i];
  }

  /* --------------------------------------------------------------- resumen */

  async function cargarResumen() {
    const destino = "#db-cuerpo-resumen";
    cargando(destino);
    const datos = await pedir("GET", "/bases");
    destino.textContent = "";

    const tabla = el("table", { class: "tabla" }, [
      el("thead", {}, [
        el("tr", {}, ["Archivo", "Tamaño", "Integridad", "Páginas", "Modo journal", "Edición"].map((t) => el("th", { text: t }))),
      ]),
    ]);
    const cuerpo = el("tbody");
    datos.bases.forEach((b) => {
      cuerpo.appendChild(
        el("tr", {}, [
          celda(b.base + " · " + b.ruta, "db-ruta"),
          celda(bytes(b.bytes)),
          celda(b.integridad || "—", b.integridad === "ok" ? "db-ok" : "db-error"),
          celda(b.paginas || "—"),
          celda(b.journal || "—"),
          celda(b.editable ? "Sí" : "Solo lectura · " + b.motivo_edicion, b.editable ? "" : "db-muted"),
        ])
      );
    });
    tabla.appendChild(cuerpo);
    destino.appendChild(tabla);

    destino.appendChild(
      el("p", { class: "nota", text: "La base de receptores se lee en crudo: sus columnas personales están cifradas y aquí se muestran como «••••••»." })
    );
  }

  /* ------------------------------------------------------------ explorador */

  async function cargarExplorador() {
    const destino = "#db-cuerpo-explorador";
    destino.textContent = "";

    const selectorTabla = el("select", { id: "db-tabla-sel", class: "db-select" });
    const selectorBase = el("select", { id: "db-base-sel", class: "db-select" }, [
      el("option", { value: "guias", text: "guias.db (principal)" }),
      el("option", { value: "receptores", text: "receptores.db (cifrada)" }),
    ]);
    selectorBase.value = estado.base;
    selectorBase.addEventListener("change", () => {
      estado.base = selectorBase.value;
      estado.tabla = null;
      estado.esquema = null;
      estado.pagina = 1;
      cargarExplorador();
    });

    const buscador = el("input", {
      type: "search",
      id: "db-buscar",
      class: "db-input",
      placeholder: "Buscar en todas las columnas…",
      value: estado.busqueda,
    });
    let temporizador = null;
    buscador.addEventListener("input", () => {
      clearTimeout(temporizador);
      temporizador = setTimeout(() => {
        estado.busqueda = buscador.value.trim();
        estado.pagina = 1;
        cargarFilas();
      }, 350);
    });

    destino.appendChild(
      el("div", { class: "db-toolbar" }, [selectorBase, selectorTabla, buscador])
    );
    selectorTabla.appendChild(el("option", { value: "", text: "Cargando tablas…" }));

    const panelEsquema = el("div", { id: "db-esquema" });
    const panelFilas = el("div", { id: "db-filas" });
    destino.appendChild(panelEsquema);
    destino.appendChild(panelFilas);

    const datos = await pedir("GET", "/tablas?base=" + encodeURIComponent(estado.base));
    selectorTabla.textContent = "";
    datos.tablas.forEach((t) => {
      selectorTabla.appendChild(
        el("option", {
          value: t.nombre,
          text: t.nombre + " · " + t.filas + " filas" + (t.editable ? "" : " 🔒"),
        })
      );
    });
    selectorTabla.appendChild(el("option", { value: "__nueva__", text: "➕ Crear fila nueva…" }));

    selectorTabla.value = estado.tabla || (datos.tablas.find((t) => t.editable) || {}).nombre || "";
    selectorTabla.addEventListener("change", () => {
      if (selectorTabla.value === "__nueva__") {
        abrirEditor(null);
        selectorTabla.value = estado.tabla || "";
        return;
      }
      estado.tabla = selectorTabla.value;
      estado.pagina = 1;
      estado.orden = "";
      cargarEsquema();
      cargarFilas();
    });

    if (estado.tabla) {
      await cargarEsquema();
      await cargarFilas();
    } else {
      panelEsquema.appendChild(el("p", { class: "sin", text: "Elige una tabla para ver su esquema y sus filas." }));
    }
  }

  async function cargarEsquema() {
    const destino = $("#db-esquema");
    if (!destino || !estado.tabla) return;
    cargando(destino);
    const datos = await pedir(
      "GET",
      "/esquema?base=" + encodeURIComponent(estado.base) + "&tabla=" + encodeURIComponent(estado.tabla)
    );
    estado.esquema = datos.esquema;
    destino.textContent = "";

    const chips = el("div", { class: "db-chips" });
    datos.esquema.columnas.forEach((c) => {
      const etiqueta = c.nombre + " · " + (c.tipo || "TEXT");
      const chip = el("span", { class: "db-chip", title: c.sensible ? "Protegida: no editable desde aquí" : "" });
      chip.textContent = c.pk ? "🔑 " + etiqueta : etiqueta;
      if (c.sensible) chip.classList.add("db-chip-protegida");
      if (!c.no_nulo) chip.classList.add("db-chip-null");
      chips.appendChild(chip);
    });
    destino.appendChild(chips);

    const info = el("p", { class: "nota" });
    info.textContent =
      datos.esquema.motivo +
      " · " +
      datos.esquema.filas +
      " filas" +
      (datos.esquema.foraneas.length
        ? " · claves foráneas: " +
          datos.esquema.foraneas.map((f) => f.columna + " → " + f.tabla + "." + f.referencia).join(", ")
        : "");
    destino.appendChild(info);

    if (datos.esquema.editable) {
      const boton = el("button", { type: "button", class: "btn primario", text: "➕ Nueva fila" });
      boton.addEventListener("click", () => abrirEditor(null));
      destino.appendChild(boton);
    }
  }

  async function cargarFilas() {
    const destino = $("#db-filas");
    if (!destino || !estado.tabla) return;
    cargando(destino, "Cargando filas…");
    const parametros = new URLSearchParams({
      base: estado.base,
      tabla: estado.tabla,
      pagina: String(estado.pagina),
      page_size: String(estado.pageSize),
    });
    if (estado.busqueda) parametros.set("q", estado.busqueda);
    if (estado.orden) {
      parametros.set("orden", estado.orden);
      parametros.set("dir", estado.dir);
    }
    const datos = await pedir("GET", "/filas?" + parametros.toString());
    const info = datos.datos;
    destino.textContent = "";

    const envoltorio = el("div", { class: "tbl-wrap" });
    const tabla = el("table", { class: "tabla db-tabla" });
    const cabecera = el("tr");
    info.columnas.forEach((columna) => {
      const th = el("th", { text: columna });
      th.style.cursor = "pointer";
      th.addEventListener("click", () => {
        estado.dir = estado.orden === columna && estado.dir === "asc" ? "desc" : "asc";
        estado.orden = columna;
        cargarFilas();
      });
      cabecera.appendChild(th);
    });
    cabecera.appendChild(el("th", { text: "Acciones" }));
    tabla.appendChild(el("thead", {}, [cabecera]));

    const cuerpo = el("tbody");
    if (!info.filas.length) {
      cuerpo.appendChild(
        el("tr", {}, [el("td", { colSpan: info.columnas.length + 1, class: "sin", text: "Sin filas para mostrar." })])
      );
    }
    info.filas.forEach((fila) => {
      const tr = el("tr");
      info.columnas.forEach((columna) => {
        const valor = fila[columna];
        const definida = estado.esquema.columnas.find((c) => c.nombre === columna);
        tr.appendChild(celda(valor, definida && definida.sensible ? "db-mascarado" : ""));
      });

      const acciones = el("td");
      if (estado.esquema.editable) {
        const editar = el("button", { type: "button", class: "btn mini", text: "Editar" });
        editar.addEventListener("click", () => abrirEditor(fila));
        acciones.appendChild(editar);

        const borrar = el("button", { type: "button", class: "btn mini peligro", text: "Eliminar" });
        borrar.addEventListener("click", () => eliminarFila(fila));
        acciones.appendChild(borrar);
      } else {
        acciones.appendChild(el("span", { class: "db-muted", text: "solo lectura" }));
      }
      tr.appendChild(acciones);
      cuerpo.appendChild(tr);
    });
    tabla.appendChild(cuerpo);
    envoltorio.appendChild(tabla);
    destino.appendChild(envoltorio);

    destino.appendChild(paginacion(info));
  }

  function columnaPrimaria() {
    if (!estado.esquema) return null;
    const pk = estado.esquema.columnas.find((c) => c.pk);
    return pk ? pk.nombre : null;
  }

  function paginacion(info) {
    const caja = el("div", { class: "db-paginacion" });
    const resumen = el("span", { class: "nota" });
    resumen.textContent =
      info.total + " filas · página " + info.pagina + " de " + info.paginas + " · " + info.page_size + " por página";
    caja.appendChild(resumen);

    const selector = el("select", { class: "db-select db-page-size" }, [25, 50, 100, 200].map((n) =>
      el("option", { value: String(n), text: String(n), selected: n === info.page_size })
    ));
    selector.addEventListener("change", () => {
      estado.pageSize = Number(selector.value);
      estado.pagina = 1;
      cargarFilas();
    });
    caja.appendChild(selector);

    const anterior = el("button", { type: "button", class: "btn mini", text: "← Anterior" });
    anterior.disabled = info.pagina <= 1;
    anterior.addEventListener("click", () => {
      estado.pagina = Math.max(1, info.pagina - 1);
      cargarFilas();
    });
    caja.appendChild(anterior);

    const siguiente = el("button", { type: "button", class: "btn mini", text: "Siguiente →" });
    siguiente.disabled = info.pagina >= info.paginas;
    siguiente.addEventListener("click", () => {
      estado.pagina = Math.min(info.paginas, info.pagina + 1);
      cargarFilas();
    });
    caja.appendChild(siguiente);
    return caja;
  }

  /* ------------------------------------------------------- editor de filas */

  async function abrirEditor(fila) {
    if (!estado.esquema) return;
    const pk = columnaPrimaria();
    const modal = $("#db-modal");
    modal.textContent = "";

    const campos = estado.esquema.columnas.filter((c) => c.editable);
    const titulo = el("h3", { text: fila ? "Editar fila de " + estado.tabla : "Nueva fila en " + estado.tabla });
    modal.appendChild(titulo);

    const avisoBloqueo = el("p", { class: "db-aviso db-warn" });
    if (fila) {
      avisoBloqueo.textContent =
        "No se puede cambiar la clave primaria (" + pk + "). Para mover una fila, cree una nueva y elimine la anterior.";
    }
    modal.appendChild(avisoBloqueo);

    const formulario = el("form", { id: "db-form-fila", class: "form grid" });
    const inputs = {};
    campos.forEach((columna) => {
      const etiqueta = el("label", {}, []);
      etiqueta.appendChild(document.createTextNode(columna.nombre + (columna.no_nulo ? " *" : "") + " · " + columna.tipo));
      const valor = fila ? fila[columna.nombre] : "";
      const input = el("input", {
        name: columna.nombre,
        class: "db-input",
        value: valor === null || valor === undefined ? "" : valor,
        placeholder: columna.por_defecto ? "por defecto: " + columna.por_defecto : "",
      });
      if (fila && columna.nombre === pk) input.disabled = true;
      inputs[columna.nombre] = input;
      etiqueta.appendChild(input);
      formulario.appendChild(etiqueta);
    });
    modal.appendChild(formulario);

    const botones = el("div", { class: "db-modal-acciones" });
    const guardar = el("button", { type: "button", class: "btn primario", text: "💾 Guardar" });
    guardar.addEventListener("click", async () => {
      const valores = {};
      campos.forEach((columna) => {
        const input = inputs[columna.nombre];
        if (input.disabled) return;
        const bruto = input.value;
        if (bruto === "") {
          if (!columna.no_nulo) valores[columna.nombre] = null;
          return;
        }
        valores[columna.nombre] = bruto;
      });
      guardar.disabled = true;
      try {
        if (fila) {
          await pedir("POST", "/actualizar", {
            base: estado.base,
            tabla: estado.tabla,
            clave: fila[pk],
            valores: valores,
          });
          aviso("Fila actualizada.", "ok");
        } else {
          await pedir("POST", "/filas", { base: estado.base, tabla: estado.tabla, valores: valores });
          aviso("Fila creada.", "ok");
        }
        cerrarModal();
        await cargarEsquema();
        await cargarFilas();
      } catch (ex) {
        aviso(ex.message, "error");
      } finally {
        guardar.disabled = false;
      }
    });
    botones.appendChild(guardar);

    const cancelar = el("button", { type: "button", class: "btn", text: "Cancelar" });
    cancelar.addEventListener("click", cerrarModal);
    botones.appendChild(cancelar);
    modal.appendChild(botones);

    $("#db-modal-wrap").hidden = false;
  }

  async function eliminarFila(fila) {
    const pk = columnaPrimaria();
    if (!pk) return;
    if (!confirmarAccion("¿Eliminar esta fila de " + estado.tabla + "?\n\nSe creará un respaldo antes de borrar y la operación quedará en la auditoría.")) {
      return;
    }
    const parametros = new URLSearchParams({ base: estado.base, tabla: estado.tabla, clave: String(fila[pk]) });
    try {
      const datos = await pedir("DELETE", "/filas?" + parametros.toString());
      aviso("Fila eliminada. Respaldo previo: " + (datos.respaldo || "—"), "ok");
      await cargarEsquema();
      await cargarFilas();
    } catch (ex) {
      aviso(ex.message, "error");
    }
  }

  function cerrarModal() {
    const modal = $("#db-modal");
    if (modal) modal.textContent = "";
    const contenedor = $("#db-modal-wrap");
    if (contenedor) contenedor.hidden = true;
  }

  /* ------------------------------------------------------------ SQL editor */

  async function cargarSql() {
    const destino = $("#db-cuerpo-sql");
    if (!destino.dataset.iniciado) {
      destino.dataset.iniciado = "1";
      destino.textContent = "";

      const area = el("textarea", {
        id: "db-sql",
        class: "db-sql",
        rows: "8",
        spellcheck: "false",
        placeholder: "SELECT * FROM guias ORDER BY id DESC LIMIT 20;",
      });
      destino.appendChild(area);

      const selectorModo = el("select", { id: "db-sql-modo", class: "db-select" }, [
        el("option", { value: "0", text: "🔒 Solo lectura (SELECT / WITH)" }),
        el("option", { value: "1", text: "⚠️ Escritura (UPDATE / DELETE / INSERT)" }),
      ]);
      destino.appendChild(selectorModo);

      // El backend exige confirmación explícita: no basta con el confirm() del
      // navegador, así que la casilla debe quedar marcada en esta misma carga.
      const casillaConfirmar = el("input", { type: "checkbox", id: "db-sql-confirmar" });
      const etiquetaConfirmar = el("label", { class: "db-confirmar" }, [
        casillaConfirmar,
        el("span", { text: " Confirmo que esta consulta modifica la base y ya hice un respaldo." }),
      ]);
      etiquetaConfirmar.hidden = true;
      destino.appendChild(etiquetaConfirmar);

      selectorModo.addEventListener("change", () => {
        etiquetaConfirmar.hidden = selectorModo.value !== "1";
        if (selectorModo.value !== "1") {
          casillaConfirmar.checked = false;
        }
      });

      const ejecutar = el("button", { type: "button", class: "btn primario", text: "▶ Ejecutar" });
      ejecutar.addEventListener("click", async () => {
        const sql = area.value.trim();
        if (!sql) {
          aviso("Escribe una consulta.", "error");
          return;
        }
        const escritura = selectorModo.value === "1";
        if (escritura && !casillaConfirmar.checked) {
          aviso("Marca la casilla de confirmación para ejecutar una consulta de escritura.", "error");
          return;
        }
        if (
          escritura &&
          !confirmarAccion(
            "Vas a ejecutar una consulta que MODIFICA la base de datos.\n\n" +
              "Se creará un respaldo automático antes de ejecutarla, pero no podrás " +
              "deshacer el cambio desde aquí.\n\n¿Continuar?"
          )
        ) {
          return;
        }
        ejecutar.disabled = true;
        aviso("Ejecutando…", "info");
        try {
          const datos = await pedir("POST", "/consulta", {
            base: estado.base,
            sql: sql,
            escritura: escritura,
            confirmar: escritura && casillaConfirmar.checked,
          });
          aviso(
            "Consulta ejecutada en " + datos.duracion_ms + " ms · " +
              datos.filas.length + " filas devueltas" +
              (escritura ? " · " + datos.filas_afectadas + " modificadas" : "") +
              (datos.respaldo_previo ? " · respaldo previo: " + datos.respaldo_previo : "") +
              (datos.truncado ? " · resultado truncado" : ""),
            "ok"
          );
          casillaConfirmar.checked = false;
          pintarResultado(datos);
        } catch (ex) {
          aviso(ex.message, "error");
        } finally {
          ejecutar.disabled = false;
        }
      });
      destino.appendChild(ejecutar);

      destino.appendChild(el("div", { id: "db-sql-resultado" }));
    }
  }

  function pintarResultado(datos) {
    const caja = $("#db-sql-resultado");
    caja.textContent = "";
    if (!datos.columnas.length) {
      caja.appendChild(el("p", { class: "nota", text: "La consulta no devolvió columnas." }));
      return;
    }
    const tabla = el("table", { class: "tabla db-tabla" });
    const cabecera = el("tr");
    datos.columnas.forEach((c) => cabecera.appendChild(el("th", { text: c })));
    tabla.appendChild(el("thead", {}, [cabecera]));
    const cuerpo = el("tbody");
    datos.filas.forEach((fila) => {
      const tr = el("tr");
      fila.forEach((valor) => tr.appendChild(celda(valor)));
      cuerpo.appendChild(tr);
    });
    tabla.appendChild(cuerpo);
    caja.appendChild(el("div", { class: "tbl-wrap" }, [tabla]));
  }

  /* ------------------------------------------------------------- respaldos */

  async function cargarRespaldos() {
    const destino = "#db-cuerpo-respaldos";
    destino.textContent = "";

    const botonCrear = el("button", { type: "button", class: "btn primario", text: "💾 Crear respaldo ahora" });
    botonCrear.addEventListener("click", async () => {
      botonCrear.disabled = true;
      try {
        const datos = await pedir("POST", "/respaldo/crear", { motivo: "manual", base: estado.base });
        aviso("Respaldo creado y verificado: " + datos.archivo + " (" + bytes(datos.bytes) + ")", "ok");
        await cargarRespaldos();
      } catch (ex) {
        aviso(ex.message, "error");
      } finally {
        botonCrear.disabled = false;
      }
    });
    destino.appendChild(botonCrear);
    destino.appendChild(
      el("p", { class: "nota", text: "Los respaldos se crean con la API de copia de SQLite, así que son consistentes aunque la base esté en uso. Se conservan los " + "30 más recientes." })
    );

    const lista = el("div");
    destino.appendChild(lista);
    const datos = await pedir("GET", "/respaldos");
    if (!datos.respaldos.length) {
      lista.appendChild(el("p", { class: "sin", text: "Todavía no hay respaldos." }));
      return;
    }
    const tabla = el("table", { class: "tabla" }, [
      el("thead", {}, [
        el("tr", {}, ["Archivo", "Fecha", "Tamaño", "Acciones"].map((t) => el("th", { text: t }))),
      ]),
    ]);
    const cuerpo = el("tbody");
    datos.respaldos.forEach((r) => {
      const acciones = el("td");

      const descargar = el("a", {
        class: "btn mini",
        text: "⬇ Descargar",
        href: "/api/admin/db/respaldo/descargar?archivo=" + encodeURIComponent(r.archivo),
        download: r.archivo,
      });
      acciones.appendChild(descargar);

      const restaurar = el("button", { type: "button", class: "btn mini peligro", text: "Restaurar" });
      restaurar.addEventListener("click", async () => {
        if (!confirmarAccion("¿Restaurar la base desde '" + r.archivo + "'?\n\nSe guardará primero el estado actual como respaldo, pero la base ActIVA pasará a ser este archivo. Luego debes reiniciar el servidor.")) return;
        try {
          const resultado = await pedir("POST", "/respaldo/restaurar", { archivo: r.archivo });
          aviso("Base restaurada desde " + resultado.respaldo + ". " + resultado.aviso, "ok");
        } catch (ex) {
          aviso(ex.message, "error");
        }
      });
      acciones.appendChild(restaurar);

      const borrar = el("button", { type: "button", class: "btn mini", text: "Eliminar" });
      borrar.addEventListener("click", async () => {
        if (!confirmarAccion("¿Eliminar el respaldo '" + r.archivo + "'?")) return;
        try {
          await pedir("DELETE", "/respaldo?archivo=" + encodeURIComponent(r.archivo));
          await cargarRespaldos();
        } catch (ex) {
          aviso(ex.message, "error");
        }
      });
      acciones.appendChild(borrar);

      cuerpo.appendChild(
        el("tr", {}, [celda(r.archivo, "db-ruta"), celda(r.fecha), celda(bytes(r.bytes)), acciones])
      );
    });
    tabla.appendChild(cuerpo);
    lista.appendChild(el("div", { class: "tbl-wrap" }, [tabla]));
  }

  /* ---------------------------------------------------------- mantenimiento */

  async function cargarMantenimiento() {
    const destino = "#db-cuerpo-mantenimiento";
    destino.textContent = "";

    const operaciones = [
      ["wal_checkpoint", "Vaciar WAL", "Vuelca el registro WAL al archivo principal y lo trunca."],
      ["optimize", "Optimizar", "Actualiza las estadísticas del planificador de consultas."],
      ["analyze", "Analizar", "Recalcula los índices para acelerar las búsquedas."],
      ["vacuum", "VACUUM", "Reconstruye el archivo y recupera espacio libre. Cierra la base un instante."],
    ];
    operaciones.forEach(([clave, titulo, descripcion]) => {
      const boton = el("button", { type: "button", class: "btn", text: titulo });
      boton.addEventListener("click", async () => {
        boton.disabled = true;
        try {
          const datos = await pedir("POST", "/mantenimiento", { operacion: clave });
          aviso(titulo + " completado en " + datos.duracion_ms + " ms.", "ok");
        } catch (ex) {
          aviso(ex.message, "error");
        } finally {
          boton.disabled = false;
        }
      });
      destino.appendChild(
        el("div", { class: "db-mantenimiento" }, [boton, el("span", { class: "nota", text: titulo + " — " + descripcion })])
      );
    });

    const migraciones = el("div", { class: "db-migraciones" });
    destino.appendChild(migraciones);
    const aplicar = el("button", { type: "button", class: "btn primario", text: "Aplicar migraciones pendientes" });
    aplicar.addEventListener("click", async () => {
      if (!confirmarAccion("¿Aplicar las migraciones pendientes?\n\nSe crea un respaldo antes de empezar. Si una migración falla a mitad, ese respaldo es la forma de revertir.")) return;
      aplicar.disabled = true;
      try {
        const datos = await pedir("POST", "/migraciones/aplicar", {});
        aviso(
          datos.versiones_nuevas.length
            ? "Migraciones aplicadas: " + datos.versiones_nuevas.join(", ")
            : "No había migraciones pendientes.",
          "ok"
        );
        await cargarMantenimiento();
      } catch (ex) {
        aviso(ex.message, "error");
      } finally {
        aplicar.disabled = false;
      }
    });
    destino.appendChild(aplicar);
    migraciones.appendChild(el("p", { class: "sin", text: "Cargando migraciones…" }));

    const datos = await pedir("GET", "/migraciones");
    migraciones.textContent = "";
    const tabla = el("table", { class: "tabla" }, [
      el("thead", {}, [el("tr", {}, ["Versión", "Archivo", "Estado", "Aplicada"].map((t) => el("th", { text: t })))]),
    ]);
    const cuerpo = el("tbody");
    datos.migraciones.forEach((m) => {
      cuerpo.appendChild(
        el("tr", {}, [
          celda("V" + m.version),
          celda(m.archivo, "db-ruta"),
          el("td", {}, [el("span", { class: "chip", text: m.aplicada ? "Aplicada" : "Pendiente", style: "background:" + (m.aplicada ? "#15803d" : "#b45309") })]),
          celda(m.aplicada_en || "—"),
        ])
      );
    });
    tabla.appendChild(cuerpo);
    migraciones.appendChild(el("div", { class: "tbl-wrap" }, [tabla]));
  }

  /* ---------------------------------------------------------------- auditoría */

  async function cargarAuditoria() {
    const destino = "#db-cuerpo-auditoria";
    destino.textContent = "";
    const datos = await pedir("GET", "/auditoria?limite=200");
    const resumen = el("p", { class: "nota" });
    resumen.textContent = datos.historial.total + " operaciones registradas en total. Se muestran las 200 más recientes.";
    destino.appendChild(resumen);

    const tabla = el("table", { class: "tabla" }, [
      el("thead", {}, [
        el("tr", {}, ["Fecha", "Usuario", "Rol", "IP", "Acción", "Tabla", "Detalle"].map((t) => el("th", { text: t }))),
      ]),
    ]);
    const cuerpo = el("tbody");
    datos.historial.registros.forEach((r) => {
      const detalle = el("td", { class: "db-detalle" });
      const boton = el("button", { type: "button", class: "btn mini", text: "Ver" });
      boton.addEventListener("click", () => mostrarDetalleAuditoria(r));
      detalle.appendChild(boton);
      cuerpo.appendChild(
        el("tr", {}, [
          celda(r.en),
          celda(r.usuario),
          celda(r.rol),
          celda(r.ip),
          celda(r.accion),
          celda(r.tabla || "—"),
          detalle,
        ])
      );
    });
    tabla.appendChild(cuerpo);
    if (!datos.historial.registros.length) {
      cuerpo.appendChild(el("tr", {}, [el("td", { colSpan: "7", class: "sin", text: "Sin operaciones registradas." })]));
    }
    destino.appendChild(el("div", { class: "tbl-wrap" }, [tabla]));
  }

  function mostrarDetalleAuditoria(registro) {
    const modal = $("#db-modal");
    modal.textContent = "";
    modal.appendChild(el("h3", { text: registro.accion + " · " + (registro.tabla || "—") }));
    const meta = el("div", { class: "db-kv" });
    [
      ["Fecha", registro.en],
      ["Usuario", registro.usuario],
      ["Rol", registro.rol],
      ["IP", registro.ip],
      ["Clave", registro.clave || "—"],
      ["Filas afectadas", registro.filas_afectadas],
    ].forEach(([clave, valor]) => {
      meta.appendChild(el("div", { class: "kv" }, [el("span", { text: clave }), el("b", { text: String(valor) })]));
    });
    modal.appendChild(meta);
    modal.appendChild(el("h4", { text: "Detalle" }));
    const pre = el("pre", { class: "db-pre" });
    pre.textContent = JSON.stringify(registro.detalle, null, 2) || "(sin detalle)";
    modal.appendChild(pre);
    $("#db-modal-wrap").hidden = false;
  }

  /* ------------------------------------------------------------------ arranque */

  const CARGADORES = {
    resumen: cargarResumen,
    explorador: cargarExplorador,
    sql: cargarSql,
    respaldos: cargarRespaldos,
    mantenimiento: cargarMantenimiento,
    auditoria: cargarAuditoria,
  };

  function mostrar(seccion) {
    $$(".db-seccion").forEach((s) => {
      s.hidden = s.id !== "db-sec-" + seccion;
    });
    $$(".db-tab").forEach((b) => b.classList.toggle("activo", b.dataset.dbSeccion === seccion));
    aviso("");
    const cargador = CARGADORES[seccion];
    if (cargador) {
      Promise.resolve()
        .then(cargador)
        .catch((ex) => aviso(ex.message, "error"));
    }
  }

  function iniciar() {
    const nav = $(".db-nav");
    if (!nav) return;
    $$(".db-tab", nav).forEach((boton) => {
      boton.addEventListener("click", () => mostrar(boton.dataset.dbSeccion));
    });
    const cerrar = $("#db-modal-cerrar");
    if (cerrar) cerrar.addEventListener("click", cerrarModal);
    mostrar("resumen");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }

  window.DBAdmin = { mostrar, pedir, esc, estado };
})();