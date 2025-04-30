document.addEventListener("DOMContentLoaded", () => {
  const hoy = new Date().toISOString().split("T")[0];
  document.getElementById("fecha_emision").value = hoy;
  const en7dias = new Date();
  en7dias.setDate(en7dias.getDate() + 7);
  document.getElementById("fecha_validez").value = en7dias.toISOString().split("T")[0];
  cargarHistorial();
});

function abrirModalCrear() {
  const modal = new bootstrap.Modal(document.getElementById("modalCrearProducto"));
  document.getElementById("nuevoNombre").value = "";
  document.getElementById("nuevoPrecio").value = "";
  document.getElementById("nuevoIVA").value = "21";
  modal.show();
}

function crearProducto() {
  const producto = document.getElementById("nuevoNombre").value.trim();
  const precio = parseFloat(document.getElementById("nuevoPrecio").value) || 0;
  const iva = parseFloat(document.getElementById("nuevoIVA").value) || 0;

  if (!producto || precio <= 0) {
    alert("Por favor completá todos los campos correctamente.");
    return;
  }

  seleccionarProducto({ producto, precio, iva });
  bootstrap.Modal.getInstance(document.getElementById("modalCrearProducto")).hide();
}

function buscarProducto() {
  const query = document.getElementById("productoInput").value.trim();
  if (!query) return;
  const modal = new bootstrap.Modal(document.getElementById("modalBusqueda"));
  modal.show();
  document.getElementById("resultadosModal").innerHTML = "<p class='text-muted'>🔄 Cargando resultados...</p>";

  fetch(" /comparar?producto=" + encodeURIComponent(query))
    .then(res => res.json())
    .then(data => {
      if (!Array.isArray(data) || data.length === 0) {
        document.getElementById("resultadosModal").innerHTML = `
          <p>No se encontraron productos.</p>
          <button class="btn btn-red" data-bs-dismiss="modal" onclick="agregarManual()">Cargar manualmente</button>
        `;
        return;
      }

      data.sort((a, b) => {
        const p1 = parseFloat((a.precio || "").replace("$", "").replace(/\./g, "").replace(",", ".")) || Infinity;
        const p2 = parseFloat((b.precio || "").replace("$", "").replace(/\./g, "").replace(",", ".")) || Infinity;
        return p1 - p2;
      });

      let html = "<table class='table table-striped'><thead><tr><th>Sitio</th><th>Producto</th><th>Precio</th><th></th></tr></thead><tbody>";
      data.forEach(p => {
        html += `<tr>
          <td>${p.sitio}</td>
          <td>${p.producto}</td>
          <td>${p.precio}</td>
          <td><button class='btn btn-sm btn-red' data-bs-dismiss='modal' onclick='seleccionarProducto(${JSON.stringify(p)})'>Seleccionar</button></td>
        </tr>`;
      });
      html += "</tbody></table>";
      document.getElementById("resultadosModal").innerHTML = html;
    });
}

function agregarManual() {
  seleccionarProducto({ producto: prompt("Nombre del producto:"), precio: "0" });
}

function seleccionarProducto(p) {
  const precio = parseFloat(typeof p.precio === "string"
    ? p.precio.replace("$", "").replace(/\./g, "").replace(",", ".")
    : p.precio) || 0;

  const fila = document.createElement("tr");
  fila.innerHTML = `
    <td><input value="${p.producto}" class="form-control form-control-sm" /></td>
    <td><input type="number" value="1" class="form-control form-control-sm" onchange="actualizarTotales()"></td>
    <td><input type="number" value="${precio}" class="form-control form-control-sm" onchange="actualizarTotales()"></td>
    <td><input type="number" value="0" class="form-control form-control-sm" onchange="actualizarTotales()"></td>
    <td class="subtotal">$0.00</td>
    <td>
      <select class="form-select form-select-sm" onchange="actualizarTotales()">
        <option value="0" ${p.iva == 0 ? "selected" : ""}>0%</option>
        <option value="21" ${p.iva == 21 ? "selected" : ""}>21%</option>
        <option value="10.5" ${p.iva == 10.5 ? "selected" : ""}>10.5%</option>
      </select>
    </td>
    <td class="venta">$0.00</td>
    <td><button class="btn btn-sm btn-danger" onclick="this.closest('tr').remove(); actualizarTotales()">🗑️</button></td>
  `;
  document.getElementById("tabla-presupuesto").appendChild(fila);
  document.getElementById("productoInput").value = "";
  actualizarTotales();
}

function actualizarTotales() {
  let total = 0;
  const coef = parseFloat(document.getElementById("coef_venta").value) || 1.3;

  document.querySelectorAll("#tabla-presupuesto tr").forEach(row => {
    const cantidad = parseFloat(row.cells[1].querySelector("input").value) || 0;
    const precio = parseFloat(row.cells[2].querySelector("input").value) || 0;
    const descuento = parseFloat(row.cells[3].querySelector("input").value) || 0;
    const bruto = cantidad * precio;
    const desc = bruto * (descuento / 100);
    const sub = bruto - desc;
    const precioVenta = precio * coef;

    row.querySelector(".subtotal").innerText = formatoArgentino(sub);
    row.querySelector(".venta").innerText = formatoArgentino(precioVenta);

    total += precioVenta * cantidad;
  });

  const descGlobal = parseFloat(document.getElementById("descuentoGlobal").value) || 0;
  const totalFinal = total * (1 - descGlobal / 100);
  document.getElementById("totalFinal").innerText = formatoArgentino(totalFinal);
}

function guardarPresupuesto() {
  const items = [];
  document.querySelectorAll("#tabla-presupuesto tr").forEach(row => {
    const producto = row.cells[0].querySelector("input").value;
    const cantidad = parseFloat(row.cells[1].querySelector("input").value) || 0;
    const precio = parseFloat(row.cells[2].querySelector("input").value) || 0;
    const descuento = parseFloat(row.cells[3].querySelector("input").value) || 0;
    const iva = parseFloat(row.cells[5].querySelector("select").value) || 0;
    const coef = parseFloat(document.getElementById("coef_venta").value) || 1.3;
    const precio_venta = precio * coef;

    items.push({ producto, cantidad, precio, descuento, iva, precio_venta });
  });

  const body = {
    cliente: document.getElementById("cliente").value,
    fecha_emision: document.getElementById("fecha_emision").value,
    fecha_validez: document.getElementById("fecha_validez").value,
    coef_venta: parseFloat(document.getElementById("coef_venta").value),
    descuento: parseFloat(document.getElementById("descuentoGlobal").value),
    total_final: parsearMonedaArg(document.getElementById("totalFinal").innerText),
    items
  };

  fetch(" /presupuestos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  }).then(res => res.json()).then(data => {
    if (data.error) return alert("❌ Error: " + data.error);
    alert("✅ Presupuesto guardado");
    document.getElementById("tabla-presupuesto").innerHTML = "";
    cargarHistorial();
  });
}

function cargarHistorial() {
  fetch(" /presupuestos")
    .then(res => res.json())
    .then(data => {
      const div = document.getElementById("historial");
      if (!Array.isArray(data)) return div.innerHTML = "Error cargando historial.";
      let html = "<table class='table'><thead><tr><th></th><th>ID</th><th>Cliente</th><th>Emisión</th><th>Total</th><th></th></tr></thead><tbody>";
      data.forEach(p => {
        html += `
        <tr>
          <td><button class="btn btn-sm btn-outline-dark" onclick="verDetalles(${p.id}, this)">🔽</button></td>
          <td>${p.id}</td>
          <td>${p.cliente}</td>
          <td>${p.fecha_emision}</td>
          <td>${formatoArgentino(p.total_final)}</td>
          <td>
            <button class='btn btn-sm btn-danger' onclick='eliminarPresupuesto(${p.id})'>🗑️</button>
            <button class='btn btn-sm btn-secondary' onclick='editarPresupuesto(${p.id})'>✏️</button>
            <button class='btn btn-sm btn-success' onclick='window.open(" /presupuestos/pdf/${p.id}")'>📄</button>
            <button class='btn btn-sm btn-warning' onclick='window.open(" /presupuestos/pdf_simple/${p.id}")'>📃 Simple</button>
          </td>
        </tr>
        <tr class="detalle" id="detalle-${p.id}"><td colspan="6"><em>Cargando...</em></td></tr>`;
      });
      html += "</tbody></table>";
      div.innerHTML = html;
    });
}

function verDetalles(id, btn) {
  const fila = document.getElementById("detalle-" + id);
  if (fila.style.display === "table-row") {
    fila.style.display = "none";
    btn.textContent = "🔽";
  } else {
    fila.style.display = "table-row";
    btn.textContent = "🔼";
    fetch(" /presupuestos/" + id)
      .then(res => res.json())
      .then(p => {
        let html = "<ul>";
        p.items.forEach(i => {
          html += `<li>${i.cantidad} x ${i.producto} - ${formatoArgentino(i.precio_venta)}</li>`;
        });
        html += "</ul>";
        fila.innerHTML = `<td colspan="6">${html}</td>`;
      });
  }
}

function eliminarPresupuesto(id) {
  if (!confirm("¿Eliminar presupuesto #" + id + "?")) return;
  fetch(" /presupuestos/" + id, { method: "DELETE" })
    .then(() => cargarHistorial());
}

function formatoArgentino(numero) {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(numero);
}

function parsearMonedaArg(str) {
  return parseFloat(str.replace(/\./g, '').replace(',', '.').replace(/[^\d.-]/g, '')) || 0;
}

