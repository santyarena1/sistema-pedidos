// pc_predeterminadas.js

let pcs = [];
let etiquetasDisponibles = [];
let programasDisponibles = [];

async function cargarPCs() {
    await cargarEtiquetas();
    await cargarProgramas();
    const res = await fetch("/api/pcs_predeterminadas");
    pcs = await res.json();
    renderFiltros();
    renderPCs();
}
  
function renderFiltros() {
    const contenedorEtiquetas = document.getElementById("filtro-etiquetas");
    const contenedorProgramas = document.getElementById("filtro-programas");

    contenedorEtiquetas.innerHTML = etiquetasDisponibles.map(et => `
        <button class="btn btn-sm btn-outline-primary me-1" onclick="filtrarPorEtiqueta('${et}')">${et}</button>
    `).join("");

    contenedorProgramas.innerHTML = programasDisponibles.map(pr => `
        <button class="btn btn-sm btn-outline-success me-1" onclick="filtrarPorPrograma('${pr}')">${pr}</button>
    `).join("");
}
  
async function cargarEtiquetas() {
    const res = await fetch("/api/etiquetas_pc_predeterminadas");
    etiquetasDisponibles = await res.json();
}
  
async function cargarProgramas() {
    const res = await fetch("/api/programas_pc_predeterminadas");
    programasDisponibles = await res.json();
}
  
async function agregarEtiqueta(pcId, etiqueta) {
    if (!etiqueta) return;
    await fetch(`/api/pcs_predeterminadas/${pcId}/etiquetas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ etiqueta })
    });
    await cargarPCs();
}
  
async function agregarPrograma(pcId, programa) {
    if (!programa) return;
    await fetch(`/api/pcs_predeterminadas/${pcId}/programas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ programa })
    });
    await cargarPCs();
}
  
async function crearEtiqueta() {
    const nombre = document.getElementById("nuevaEtiqueta").value.trim();
    if (!nombre) return;
    await fetch("/api/etiquetas_pc_predeterminadas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ etiqueta: nombre })
    });
    document.getElementById("nuevaEtiqueta").value = "";
    await cargarEtiquetas();
    await cargarPCs();
    bootstrap.Modal.getInstance(document.getElementById("modalEtiqueta")).hide();
}
  
async function crearPrograma() {
    const nombre = document.getElementById("nuevoPrograma").value.trim();
    if (!nombre) return;
    await fetch("/api/programas_pc_predeterminadas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre })
    });
    document.getElementById("nuevoPrograma").value = "";
    await cargarProgramas();
    await cargarPCs();
    bootstrap.Modal.getInstance(document.getElementById("modalPrograma")).hide();
}
  
function abrirModalEtiqueta() {
    const modal = new bootstrap.Modal(document.getElementById("modalEtiqueta"));
    modal.show();
}
  
function abrirModalPrograma() {
    const modal = new bootstrap.Modal(document.getElementById("modalPrograma"));
    modal.show();
}
  
function renderPCs() {
  const contenedor = document.getElementById("contenedor-pcs");
  contenedor.innerHTML = "";

  pcs.forEach(pc => {
    const card = document.createElement("div");
    card.className = "card mb-4 p-3 shadow-sm";

    card.innerHTML = `
      <div class="d-flex justify-content-between align-items-center mb-2">
        <input class="form-control form-control-sm w-50 fw-bold" value="${pc.nombre}" onchange="editarNombre(${pc.id}, this.value)" />
        <div>
          <button class="btn btn-sm btn-outline-danger" onclick="eliminarPC(${pc.id})">🗑 Eliminar</button>
        </div>
      </div>

      <div class="mb-2">
        <strong>ID:</strong> ${pc.id}<br/>
        <strong>Total:</strong> $${formatoPeso(pc.total)}
      </div>

      <div class="mb-2">
        <strong>Etiquetas:</strong>
        ${(pc.etiquetas || []).map(e => `<span class="badge bg-primary me-1">${e}</span>`).join(" ")}
        <select class="form-select form-select-sm mt-1" onchange="agregarEtiqueta(${pc.id}, this.value)">
          <option selected disabled>Agregar etiqueta...</option>
          ${(etiquetasDisponibles || []).map(e => `<option value="${e}">${e}</option>`).join("")}
        </select>
      </div>

      <div class="mb-2">
        <strong>Programas:</strong>
        ${(pc.programas || []).map(p => `<span class="badge bg-success me-1">${p}</span>`).join(" ")}
        <select class="form-select form-select-sm mt-1" onchange="agregarPrograma(${pc.id}, this.value)">
          <option selected disabled>Agregar programa...</option>
          ${(programasDisponibles || []).map(p => `<option value="${p}">${p}</option>`).join("")}
        </select>
      </div>

      <div class="mb-3">
        <strong>Componentes:</strong>
        <input type="text" class="form-control form-control-sm mb-1" placeholder="Buscar componente..." oninput="buscarComponente(this, ${pc.id})" />
        <div id="busqueda-${pc.id}" class="list-group"></div>
        <table class="table table-sm table-bordered">
        <thead>
        <tr>
            <th style="width: 10%;">Código</th>
            <th style="width: 15%;">Categoría</th>
            <th style="width: 50%;">Nombre</th>
            <th style="width: 15%;">Venta</th>
            <th style="width: 10%;">Editar</th>
        </tr>
        </thead>

          <tbody>
            ${(pc.componentes_detalle || []).map(c => `
              <tr>
                <td>${c.codigo}</td>
                <td>${c.categoria}</td>
                <td>${c.nombre}</td>
                <td>$${formatoPeso(c.precio_venta)}</td>
                <td><button class="btn btn-sm btn-outline-danger" onclick="quitarComponente(${pc.id}, '${c.codigo}')">✖</button></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
        <button class="btn btn-sm btn-outline-secondary mt-2" onclick="generarPDF(${pc.id})">
            📄 Generar PDF
        </button>

        
      </div>
    `;

    contenedor.appendChild(card);
  });
}

async function editarNombre(id, nuevo) {
  await fetch(`/api/pcs_predeterminadas/${id}/nombre`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre: nuevo })
  });
}

function generarPDF(pcId) {
  window.open(`/pcs_predeterminadas/${pcId}/pdf`, "_blank");
}


async function eliminarPC(id) {
  if (!confirm("¿Eliminar esta PC?")) return;
  await fetch(`/api/pcs_predeterminadas/${id}`, { method: "DELETE" });
  await cargarPCs();
}

async function nuevaPC() {
  const nombre = prompt("Nombre de la nueva PC:");
  if (!nombre) return;
  await fetch("/api/pcs_predeterminadas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre })
  });
  await cargarPCs();
}

async function agregarComponente(pcId, codigo) {
  await fetch(`/api/pcs_predeterminadas/${pcId}/componentes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ codigo })
  });
  await cargarPCs();
}

async function quitarComponente(pcId, codigo) {
  await fetch(`/api/pcs_predeterminadas/${pcId}/componentes/${codigo}`, { method: "DELETE" });
  await cargarPCs();
}

async function buscarComponente(input, pcId) {
    const texto = input.value.trim();
    const div = document.getElementById(`busqueda-${pcId}`);
    if (texto.length < 2) return div.innerHTML = "";
  
    try {
      const res = await fetch(`/api/componentes_presupuesto?q=${encodeURIComponent(texto)}`);
      if (!res.ok) throw new Error("No se pudo obtener resultados");
      const componentes = await res.json();
  
      if (!componentes.length) {
        div.innerHTML = `<div class="list-group-item text-muted">Sin resultados</div>`;
        return;
      }
  
      div.innerHTML = componentes.map(c => `
        <button class="list-group-item list-group-item-action" onclick="agregarComponente(${pcId}, '${c.codigo}')">
          ${c.codigo} - ${c.producto} ($${formatoPeso(c.precio_venta)})
        </button>
      `).join("");
    } catch (error) {
      console.error("Error en buscarComponente:", error);
      div.innerHTML = `<div class="list-group-item text-danger">Error al buscar</div>`;
    }
}
  
  

async function cargarEtiquetas() {
  const res = await fetch("/api/etiquetas_pc_predeterminadas");
  etiquetasDisponibles = await res.json();
}

async function cargarProgramas() {
  const res = await fetch("/api/programas_pc_predeterminadas");
  programasDisponibles = await res.json();
}

async function agregarEtiqueta(pcId, etiqueta) {
  await fetch(`/api/pcs_predeterminadas/${pcId}/etiquetas`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ etiqueta })
  });
  await cargarPCs();
}

async function agregarPrograma(pcId, programa) {
  await fetch(`/api/pcs_predeterminadas/${pcId}/programas`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ programa })
  });
  await cargarPCs();
}

function formatoPeso(n) {
  return (n || 0).toLocaleString("es-AR", { minimumFractionDigits: 2 });
}

function filtrarPorEtiqueta(etiqueta) {
    const filtradas = pcs.filter(pc => pc.etiquetas.includes(etiqueta));
    renderFiltradas(filtradas);
  }
  
function filtrarPorPrograma(programa) {
    const filtradas = pcs.filter(pc => pc.programas.includes(programa));
    renderFiltradas(filtradas);
}
  
function renderFiltradas(lista) {
    const contenedor = document.getElementById("contenedor-pcs");
    contenedor.innerHTML = "";
    lista.forEach(pc => renderPCs([pc]));
}
  
function filtrarTarjetas() {
    const texto = document.getElementById("buscadorGlobal").value.toLowerCase();
    const filtradas = pcs.filter(pc => {
      const coincideNombre = pc.nombre?.toLowerCase().includes(texto);
      const coincideID = String(pc.id).includes(texto);
      const coincideEtiqueta = (pc.etiquetas || []).some(et => et.toLowerCase().includes(texto));
      const coincidePrograma = (pc.programas || []).some(pg => pg.toLowerCase().includes(texto));
      const coincideComponente = (pc.componentes_detalle || []).some(c =>
        c.nombre?.toLowerCase().includes(texto) || c.codigo?.toLowerCase().includes(texto)
      );
  
      return coincideNombre || coincideID || coincideEtiqueta || coincidePrograma || coincideComponente;
    });
  
    const contenedor = document.getElementById("contenedor-pcs");
    contenedor.innerHTML = "";
    filtradas.forEach(pc => {
      const card = document.createElement("div");
      card.className = "card mb-4 p-3 shadow-sm";
      contenedor.appendChild(card);
      // Reusar lógica de renderPCs sobre la pc
      renderPCs([pc]); // si lo modularizás por tarjeta
    });
}
  

function renderizarUnaPC(pc) {
    // Usá el mismo contenido que usás en renderPCs para una sola PC
    // (si querés, podés duplicar temporalmente esa lógica)
    // O simplemente podés llamar a renderPCs() si ya lo modularizaste bien.
    renderPCs([pc]);
    return "";
}
  
  

cargarPCs();
