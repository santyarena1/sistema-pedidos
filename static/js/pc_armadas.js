document.addEventListener("DOMContentLoaded", () => {
  cargarPCArmadas();
});

function cargarPCArmadas() {
  fetch("/api/pc_armadas")
    .then(res => res.json())
    .then(data => {
      renderizarPCArmadas(data);
      mostrarEtiquetasUnicas(data);
    })
    .catch(err => console.error("Error al cargar PCs armadas:", err));
}

function renderizarPCArmadas(pcs) {
  if (!Array.isArray(pcs)) {
    console.error("Error: respuesta no es un array", pcs);
    return;
  }

  const contenedor = document.getElementById("lista-pc_armadas");
  contenedor.innerHTML = "";

  pcs.forEach(pc => {
    const col = document.createElement("div");
    col.className = "col-md-6";

    const card = document.createElement("div");
    card.className = "card shadow-sm mb-4";

    const body = document.createElement("div");
    body.className = "card-body";

    body.innerHTML = `
      <h5 class="card-title">Presupuesto #${pc.presupuesto_id}</h5>
      <p><input value="${pc.nombre_presupuesto || ''}" class="form-control form-control-sm mb-2" onchange="editarNombrePresupuesto(${pc.id}, this.value)" placeholder="Nombre del presupuesto..." /></p>
      <p><b>Total:</b> ${formatoArgentino(pc.total_final)}</p>

      <p><b>Etiquetas:</b> ${pc.etiquetas.map(e => `<span class="badge bg-secondary me-1">${e}</span>`).join(" ") || 'Sin etiquetas'}</p>
      <div class="input-group my-2">
        <input type="text" class="form-control form-control-sm" id="input-etiqueta-${pc.id}" placeholder="Agregar etiqueta..." onkeydown="if(event.key==='Enter') agregarEtiqueta(${pc.id})">
        <button class="btn btn-outline-secondary btn-sm" onclick="agregarEtiqueta(${pc.id})">➕</button>
      </div>
      <div class="d-flex justify-content-between flex-wrap gap-2">
        <button class="btn btn-danger btn-sm" onclick="eliminarPCArmada(${pc.id})">🗑️ Eliminar</button>
        <button class="btn btn-secondary btn-sm" onclick="verDetallesPresupuesto(${pc.presupuesto_id})">🔍 Ver Detalles</button>
        <button class="btn btn-outline-primary btn-sm" onclick="window.open('/presupuestos/pdf/${pc.presupuesto_id}')">📄 Ver PDF</button>
        <button class="btn btn-warning btn-sm" onclick="window.open('/presupuestos/pdf_simple/${pc.presupuesto_id}')">📃 Simple</button>
      </div>
      <div id="detalles-${pc.presupuesto_id}" class="mt-2 text-muted small" style="display:none;">Cargando detalles...</div>
    `;

    card.appendChild(body);
    col.appendChild(card);
    contenedor.appendChild(col);
  });
}

function mostrarEtiquetasUnicas(pcs) {
  const div = document.getElementById("etiquetas-existentes");
  if (!div) return;
  const todas = new Set();
  pcs.forEach(p => p.etiquetas.forEach(et => todas.add(et)));
  div.innerHTML = Array.from(todas).sort().map(e => `<span class="badge bg-info text-dark">${e}</span>`).join(" ");
}

function agregarEtiqueta(presupuestoId) {
  const input = document.getElementById("input-etiqueta-" + presupuestoId);
  const etiqueta = input?.value?.trim();
  if (!etiqueta) return;
  fetch(`/pc_armadas/${presupuestoId}/etiquetas`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ etiqueta })
  })
    .then(res => res.json())
    .then(() => cargarPCArmadas());
}

function eliminarPCArmada(presupuestoId) {
  if (!confirm("¿Eliminar esta PC Armada?")) return;
  fetch(`/pc_armadas/${presupuestoId}`, {
    method: "DELETE"
  }).then(() => cargarPCArmadas());
}

function filtrarPCArmadas() {
  const filtro = document.getElementById("filtroEtiquetas").value.toLowerCase().trim();
  fetch("/api/pc_armadas")
    .then(res => res.json())
    .then(pcs => {
      if (!filtro) {
        renderizarPCArmadas(pcs);
        mostrarEtiquetasUnicas(pcs);
      } else {
        const filtradas = pcs.filter(pc =>
          pc.etiquetas.some(et => et.toLowerCase().includes(filtro))
        );
        renderizarPCArmadas(filtradas);
        mostrarEtiquetasUnicas(filtradas);
      }
    });
}

function verDetallesPresupuesto(presupuestoId) {
  const div = document.getElementById("detalles-" + presupuestoId);
  if (div.style.display === "block") {
    div.style.display = "none";
    return;
  }
  fetch(`/presupuestos/${presupuestoId}`)
    .then(res => res.json())
    .then(p => {
      const lista = p.items.map(i => `<li>${i.cantidad} x ${i.producto} - ${formatoArgentino(i.precio_venta)}</li>`).join("");
      div.innerHTML = `<ul>${lista}</ul>`;
      div.style.display = "block";
    });
}

function editarNombrePresupuesto(id, nuevoNombre) {
  fetch(`/pc_armadas/${id}/editar_nombre`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre_presupuesto: nuevoNombre })
  })
    .then(res => res.json())
    .then(() => cargarPCArmadas())
    .catch(err => console.error("Error al editar nombre:", err));
}

function formatoArgentino(numero) {
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS'
  }).format(numero);
}
