// static/js/pedidos_lista.js

let pedidosGlobal = [];

window.addEventListener("DOMContentLoaded", async () => {
  try {
    const res = await fetch("/pedidos/todos");
    const data = await res.json();
    if (Array.isArray(data)) {
      pedidosGlobal = data;
      mostrarPedidos(data);
    } else {
      console.error("Respuesta inválida:", data);
    }
  } catch (err) {
    console.error("Error cargando pedidos:", err);
  }
});

function mostrarPedidos(pedidos) {
  const contenedor = document.getElementById("lista-pedidos");
  contenedor.innerHTML = "";

  // Ordenar pedidos del número más grande al más chico
  pedidos.sort((a, b) => b.numero - a.numero);

  pedidos.forEach(p => {
    const card = document.createElement("div");
    card.className = "pedido-card";

    card.innerHTML = `
      <div class="pedido-header">
        <h5>Pedido Nº ${p.numero}</h5>
        <div class="pedido-botones">
          <button class="editar-btn" onclick="activarEdicion(${p.id})">EDITAR</button>
          <button class="guardar-btn" onclick="guardarEdicion(${p.id})" style="display:none;">GUARDAR</button>
        </div>
      </div>

      <div class="pedido-datos">
        <div>
          <p><strong>Cliente:</strong> <input type="text" data-campo="nombre_cliente" value="${p.nombre_cliente}" disabled></p>
          <p><strong>Teléfono:</strong> <input type="text" data-campo="telefono" value="${p.telefono}" disabled></p>
          <p><strong>DNI:</strong> <input type="text" data-campo="dni_cliente" value="${p.dni_cliente || ''}" disabled></p>
        </div>

        <div>
          <p><strong>Mail:</strong> <input type="email" data-campo="email" value="${p.email}" disabled></p>
          <p><strong>Envío:</strong> 
            <select data-campo="forma_envio" disabled>
              <option ${p.forma_envio === 'Moto' ? 'selected' : ''}>Moto</option>
              <option ${p.forma_envio === 'Dropshipping' ? 'selected' : ''}>Dropshipping</option>
              <option ${p.forma_envio === 'Andreani' ? 'selected' : ''}>Andreani</option>
              <option ${p.forma_envio === 'Retira' ? 'selected' : ''}>Retira</option>
            </select>
          </p>
          <p><strong>Precio envío:</strong> <input type="number" step="0.01" data-campo="costo_envio" value="${p.costo_envio}" disabled></p>
        </div>

        <div>
          <p><strong>Vendedor:</strong> 
            <select data-campo="vendedor" disabled>
              <option ${p.vendedor === 'Santy' ? 'selected' : ''}>Santy</option>
              <option ${p.vendedor === 'Lucas' ? 'selected' : ''}>Lucas</option>
              <option ${p.vendedor === 'Thiago' ? 'selected' : ''}>Thiago</option>
              <option ${p.vendedor === 'Repe' ? 'selected' : ''}>Repe</option>
              <option ${p.vendedor === 'Ale' ? 'selected' : ''}>Ale</option>
            </select>
          </p>
          <p><strong>Origen Venta:</strong> <input type="text" data-campo="origen_venta" value="${p.origen_venta}" disabled></p>
          <p><strong>Tipo de factura:</strong> 
            <select data-campo="tipo_factura" disabled>
              <option value="NA" ${p.tipo_factura === 'NA' ? 'selected' : ''}>NA</option>
              <option value="Factura A" ${p.tipo_factura === 'Factura A' ? 'selected' : ''}>Factura A</option>
              <option value="Factura B" ${p.tipo_factura === 'Factura B' ? 'selected' : ''}>Factura B</option>
            </select>
          </p>
        </div>

        <div>
          <p><strong>Fecha de creación:</strong> ${formatearFecha(p.fecha_emision)}</p>
          <p><strong>Fecha límite de entrega:</strong> ${calcularFechaLimite(p.fecha_emision)}</p>
          <p><strong>Estado del Pedido:</strong> 
            <select data-campo="estado_general" disabled>
              ${listarEstadosPedido(p.estado_general)}
            </select>
          </p>
        </div>
      </div>

      ${generarTablaProductos(p.productos)}
      ${generarTablaPagos(p.pagos)}
      ${generarTotales(p)}

      <div class="acciones">
        <button onclick="generarConstancia(${p.id})">Constancia de entrega</button>
        <button onclick="avisarPedido('${p.telefono}', '${p.numero}')">AVISAR PEDIDO LISTO</button>
        <a href="/pedidos/${p.id}/factura" download>DESCARGAR FC</a>
        <label>SUBIR FACTURA<input type="file" hidden onchange="subirFactura(${p.id}, event)"></label>
      </div>

      <p class="ultima-modif">Última modificación: ${formatearFechaHora(p.ultima_modificacion)}</p>
    `;
    contenedor.appendChild(card);
    recalcularTotales(card);


    // ⚡ Activar recalculo de totales
    agregarListenersEdicion(card);
  });
}



function calcularFechaLimite(fechaISO) {
  if (!fechaISO) return "-";
  const fecha = new Date(fechaISO);
  let diasAgregados = 0;
  while (diasAgregados < 5) {
    fecha.setDate(fecha.getDate() + 1);
    if (fecha.getDay() !== 0 && fecha.getDay() !== 6) { // 0 = domingo, 6 = sábado
      diasAgregados++;
    }
  }
  return fecha.toLocaleDateString('es-AR');
}


function formatearFecha(fechaISO) {
  if (!fechaISO) return "-";
  const f = new Date(fechaISO);
  return f.toLocaleDateString("es-AR");
}


function generarTablaProductos(productos) {
  return `
    <div class="productos">
      <h6>PRODUCTOS</h6>
      <table class="tabla-productos">
        <thead>
          <tr>
            <th>PROVEEDOR</th>
            <th>PRODUCTO</th>
            <th>SKU</th>
            <th>VENTA UNIT</th>
            <th>CANT</th>
            <th>ESTADO</th>
            <th>CAMBIO</th>
          </tr>
        </thead>
        <tbody>
          ${productos.map((pr, idx) => `
            <tr>
              <td>
                <select data-prod="proveedor-${idx}" disabled>
                  ${listarProveedores(pr.proveedor)}
                </select>
              </td>
              <td><input type="text" data-prod="producto-${idx}" value="${pr.producto}" disabled></td>
              <td><input type="text" data-prod="sku-${idx}" value="${pr.sku || ''}" disabled></td>
              <td><input type="number" step="0.01" data-prod="precio_venta-${idx}" value="${pr.precio_venta}" disabled></td>
              <td><input type="number" data-prod="cantidad-${idx}" value="${pr.cantidad}" disabled></td>
              <td>
                <select data-prod="estado_producto-${idx}" disabled>
                  ${listarEstadosProducto(pr.estado_producto)}
                </select>
              </td>
              <td>
                <select data-prod="cambio-${idx}" disabled>
                  <option value="true" ${pr.cambio ? 'selected' : ''}>✅</option>
                  <option value="false" ${!pr.cambio ? 'selected' : ''}>❌</option>
                </select>
              </td>
            </tr>`).join("")}
        </tbody>
      </table>
      <button class="agregar-producto-btn" style="display:none;" onclick="agregarFilaProducto(this)">+ Agregar Producto</button>
    </div>
  `;
}

function agregarFilaProducto(btn) {
  const card = btn.closest(".pedido-card");
  const tbody = card.querySelector(".tabla-productos tbody");
  const idx = tbody.querySelectorAll("tr").length;

  const nuevaFila = document.createElement("tr");
  nuevaFila.innerHTML = `
    <td><select data-prod="proveedor-${idx}">${listarProveedores()}</select></td>
    <td><input type="text" data-prod="producto-${idx}" value=""></td>
    <td><input type="text" data-prod="sku-${idx}" value=""></td>
    <td><input type="number" step="0.01" data-prod="precio_venta-${idx}" value=""></td>
    <td><input type="number" data-prod="cantidad-${idx}" value="1"></td>
    <td><select data-prod="estado_producto-${idx}">${listarEstadosProducto()}</select></td>
    <td>
      <select data-prod="cambio-${idx}">
        <option value="true">✅</option>
        <option value="false">❌</option>
      </select>
    </td>
  `;
  tbody.appendChild(nuevaFila);

  // 👉 Agregar listener a inputs nuevos
  nuevaFila.querySelectorAll('input, select').forEach(input => {
    input.addEventListener('input', () => recalcularTotales(card));
  });

  recalcularTotales(card);
}

function agregarFilaPago(btn) {
  const card = btn.closest(".pedido-card");
  const tbody = card.querySelector(".tabla-pagos tbody");
  const idx = tbody.querySelectorAll("tr").length;

  const hoy = new Date().toISOString().split('T')[0];

  const nuevaFila = document.createElement("tr");
  nuevaFila.innerHTML = `
    <td><select data-pago="metodo-${idx}">${listarFormasPago()}</select></td>
    <td><input type="number" step="0.01" data-pago="monto-${idx}" value=""></td>
    <td><input type="number" step="0.01" data-pago="tipo_cambio-${idx}" value=""></td>
    <td><input type="date" data-pago="fecha-${idx}" value="${hoy}"></td>
  `;
  tbody.appendChild(nuevaFila);

  // 👉 Agregar listener a inputs nuevos
  nuevaFila.querySelectorAll('input, select').forEach(input => {
    input.addEventListener('input', () => recalcularTotales(card));
  });

  recalcularTotales(card);
}



function generarTablaPagos(pagos) {
  return `
    <div class="pagos">
      <h6>PAGOS</h6>
      <table class="tabla-pagos">
        <thead>
          <tr>
            <th>FORMA</th>
            <th>MONTO</th>
            <th>TIPO CAMBIO</th>
            <th>FECHA</th>
          </tr>
        </thead>
        <tbody>
          ${pagos.map((pg, i) => `
            <tr>
              <td>
                <select data-pago="metodo-${i}" disabled>
                  ${listarFormasPago(pg.metodo)}
                </select>
              </td>
              <td><input type="number" step="0.01" data-pago="monto-${i}" value="${pg.monto}" disabled></td>
              <td><input type="number" step="0.01" data-pago="tipo_cambio-${i}" value="${pg.tipo_cambio || ''}" disabled></td>
              <td><input type="date" data-pago="fecha-${i}" value="${pg.fecha ? pg.fecha.split('T')[0] : ''}" disabled></td>
            </tr>`).join("")}
        </tbody>
      </table>
      <button class="agregar-pago-btn" style="display:none;" onclick="agregarFilaPago(this)">+ Agregar Pago</button>
    </div>
  `;
}


function generarTotales(pedido) {
  return `
    <div class="totales">
      <p><strong>Total Venta:</strong> $<span class="total-venta">${formatoPeso(pedido.total_venta)}</span></p>
      <p><strong>Total Abonado:</strong> $<span class="total-abonado">${formatoPeso(pedido.total_abonado)}</span></p>
      <p><strong>Debe:</strong> $<span class="total-debe">${formatoPeso(pedido.total_venta - pedido.total_abonado)}</span></p>
    </div>
  `;
}

function listarProveedores(seleccionado = "") {
  const proveedores = [
    "TBD","AIR", "COMPRA GAMER", "FULL HARD", "GOLDENTECH", "INVID", "SENTEY", "LIONTECH", "MALDITO HARD", "MAXIMUS",
    "MERCADO LIBRE", "PC ARTS", "ROCKETHARD", "SLOT ONE", "SOLUTION BOX", "SOUNDTEC", "ALE", "NOSOTROS",
    "HYPERGAMING", "COMPUTODO", "CDKEYOFFER", "MUNDO HARDWARE", "NOXIE", "ACUARIO", "REPE", "MGM GAMES", "MEXX",
    "HYDRAXTREME", "PEAK COMPUTACION", "GAMERS POINT", "ECLIPSE COMPUTACION", "SCP HARDSTORE", "ARMYTECH",
    "GPU USADA", "SPACE", "NEW TREE", "MEGASOFT", "GEZATEK", "WIZ TECH", "GAMING CITY", "31STORE", "GRUPO NUCLEO",
    "MINING STORE", "HARD CORE", "NEW BYTES", "MYM COMPUTACION", "XT-PC", "ELECTROOMBU", "TGS", "DATASOFT",
    "HFTECNOLOGIA", "URANO STREAM", "LUCAS", "JUAMPI", "TRYHARDWARE", "SERGIO", "MIMI TECH", "TURTECH",
    "INTEGRADOS ARGENTINOS", "GVGMALL", "LOGG", "SANTY", "SANTY (ABUELO)", "HARDLOOTS", "GONZA", "G2A", "CUCHU",
    "CLICK AREQUITO", "BLACK", "MGM GAMERS", "EMA", "GAUSS", "OVERTECH", "VENEX", "TGS (WEB)", "COMPUGARDEN",
    "CLIENTE", "IGNATECH", "SOLARMAX", "VRACER", "REPARACION TGS", "CROSSHAIR", "GN POINT", "DISTECNA",
    "INTERMACO", "CEVEN", "GAMING POINT", "KATECH", "ROYALECDKEY", "THIAGO", "RMINSUMOS", "USABAIRES"
  ];
  return proveedores.map(pv => `<option ${pv === seleccionado ? "selected" : ""}>${pv}</option>`).join("");
}

function listarEstadosProducto(seleccionado = "") {
  const estadosProducto = [
    "FALTAN ENVIOS", "PARA HACER", "LISTO", "ENTREGADO", "GARANTIA",
    "PEDIDO", "REVISADO", "CANCELADO", "EN LA OFICINA", 
    "EN OTRO LOCAL", "NO COBRADO", "PROBLEMAS"
  ];
  return estadosProducto.map(st => `<option ${st === seleccionado ? "selected" : ""}>${st}</option>`).join("");
}

function listarEstadosPedido(seleccionado = "") {
  const estadosPedido = [
    "EN PROCESO", "PARA HACER", "LISTO", "ENTREGADO", 
    "CANCELADO", "RMA", "SERVICIO TECNICO"
  ];
  return estadosPedido.map(st => `<option ${st === seleccionado ? "selected" : ""}>${st}</option>`).join("");
}

function listarFormasPago(seleccionado = "") {
  const formas = [
    "EFECTIVO", "MERCADOPAGO", "TRANSFERENCIA", "DÓLARES", "PAGO EN TIENDA", "TARJETA", "CUENTA DNI", "CRÉDITO", "OTROS"
  ];
  return formas.map(f => `<option ${f === seleccionado ? "selected" : ""}>${f}</option>`).join("");
}

function recalcularTotales(card) {
  let totalVenta = 0;
  let totalAbonado = 0;

  card.querySelectorAll('tbody tr').forEach((row) => {
    const precioInput = row.querySelector('input[data-prod^="precio_venta-"]');
    const cantidadInput = row.querySelector('input[data-prod^="cantidad-"]');

    if (precioInput && cantidadInput) {
      const precio = parseFloat(precioInput.value) || 0;
      const cantidad = parseInt(cantidadInput.value) || 0;
      totalVenta += precio * cantidad;
    }
  });

  card.querySelectorAll('tbody tr').forEach((row) => {
    const montoInput = row.querySelector('input[data-pago^="monto-"]');
    if (montoInput) {
      totalAbonado += parseFloat(montoInput.value) || 0;
    }
  });

  card.querySelector(".total-venta").textContent = formatoPeso(totalVenta);
  card.querySelector(".total-abonado").textContent = formatoPeso(totalAbonado);
  card.querySelector(".total-debe").textContent = formatoPeso(totalVenta - totalAbonado);
}


function agregarListenersEdicion(card) {
  card.querySelectorAll('input[data-prod], input[data-pago]').forEach(input => {
    input.addEventListener('input', () => recalcularTotales(card));
  });
}

contenedor.appendChild(card);
recalcularTotales(card);
agregarListenersEdicion(card);


function agregarProducto(pedidoIdx) {
  const tbody = document.getElementById(`productos-${pedidoIdx}`);
  const idx = tbody.querySelectorAll("tr").length; // Nuevo índice basado en cantidad de filas

  const nuevaFila = document.createElement("tr");
  nuevaFila.innerHTML = `
    <td><select data-prod="proveedor-${idx}">${[
      "TBD", "AIR", "COMPRA GAMER", "FULL HARD", "GOLDENTECH", "INVID", "SENTEY", "LIONTECH", "MERCADO LIBRE",
      "PC ARTS", "SOLUTION BOX", "SOUNDTEC", "ALE", "NOSOTROS", "HYPERGAMING", "COMPUTODO", "ACUARIO", "REPE"
    ].map(pv => `<option value="${pv}">${pv}</option>`).join("")}</select></td>
    <td><input type="text" data-prod="producto-${idx}" value=""></td>
    <td><input type="text" data-prod="sku-${idx}" value=""></td>
    <td><input type="number" step="0.01" data-prod="precio_venta-${idx}" value=""></td>
    <td><input type="number" data-prod="cantidad-${idx}" value=""></td>
    <td><input type="text" data-prod="estado_producto-${idx}" value=""></td>
    <td>
      <select data-prod="cambio-${idx}">
        <option value="true">✅</option>
        <option value="false">❌</option>
      </select>
    </td>
  `;
  tbody.appendChild(nuevaFila);
}

function agregarPago(pedidoIdx) {
  const tbody = document.getElementById(`pagos-${pedidoIdx}`);
  const idx = tbody.querySelectorAll("tr").length; // Nuevo índice basado en cantidad de filas

  const nuevaFila = document.createElement("tr");
  nuevaFila.innerHTML = `
    <td><select data-pago="metodo-${idx}">${[
      "TRANSFERENCIA", "EFECTIVO", "MERCADOPAGO", "DEBITO", "CREDITO", "DOLAR BILLETE", "DOLAR TRANSFERENCIA"
    ].map(fp => `<option value="${fp}">${fp}</option>`).join("")}</select></td>
    <td><input type="number" step="0.01" data-pago="monto-${idx}" value=""></td>
    <td><input type="number" step="0.01" data-pago="tipo_cambio-${idx}" value=""></td>
    <td><input type="date" data-pago="fecha-${idx}" value="${obtenerFechaHoy()}"></td>
  `;
  tbody.appendChild(nuevaFila);
}

function obtenerFechaHoy() {
  const hoy = new Date();
  return hoy.toISOString().split('T')[0]; // Formato yyyy-mm-dd
}



function activarEdicion(id) {
  const card = document.querySelector(`.pedido-card:has(button[onclick="guardarEdicion(${id})"])`);
  card.querySelectorAll('input, select').forEach(el => el.disabled = false);
  card.querySelector('.editar-btn').style.display = 'none';
  card.querySelector('.guardar-btn').style.display = 'inline-block';

  // 👉 Mostrar botones de agregar producto y pago
  card.querySelector('.agregar-producto-btn').style.display = 'inline-block';
  card.querySelector('.agregar-pago-btn').style.display = 'inline-block';

  agregarListenersEdicion(card);
}



function guardarEdicion(id) {
  const card = document.querySelector(`.pedido-card:has(button[onclick="guardarEdicion(${id})"])`);
  
  const data = {};
  card.querySelectorAll('[data-campo]').forEach(el => {
    const key = el.dataset.campo;
    data[key] = key === 'costo_envio' ? parseFloat(el.value) : el.value;
  });

  data.productos = [];
  const filasProd = card.querySelectorAll(".tabla-productos tbody tr");
  filasProd.forEach((row, idx) => {
    data.productos.push({
      proveedor: row.querySelector(`[data-prod="proveedor-${idx}"]`).value,
      producto: row.querySelector(`[data-prod="producto-${idx}"]`).value,
      sku: row.querySelector(`[data-prod="sku-${idx}"]`).value,
      precio_venta: parseFloat(row.querySelector(`[data-prod="precio_venta-${idx}"]`).value) || 0,
      cantidad: parseInt(row.querySelector(`[data-prod="cantidad-${idx}"]`).value) || 1,
      estado_producto: row.querySelector(`[data-prod="estado_producto-${idx}"]`).value,
      cambio: row.querySelector(`[data-prod="cambio-${idx}"]`).value === 'true'
    });
  });

  data.pagos = [];
  const filasPago = card.querySelectorAll(".tabla-pagos tbody tr");
  filasPago.forEach((row, idx) => {
    data.pagos.push({
      metodo: row.querySelector(`[data-pago="metodo-${idx}"]`).value,
      monto: parseFloat(row.querySelector(`[data-pago="monto-${idx}"]`).value),
      tipo_cambio: parseFloat(row.querySelector(`[data-pago="tipo_cambio-${idx}"]`).value) || null,
      fecha: row.querySelector(`[data-pago="fecha-${idx}"]`).value || null
    });
  });

  fetch(`/pedidos/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  })
    .then(res => res.json())
    .then(json => {
      if (json.mensaje) {
        alert("✅ Pedido actualizado");
        card.querySelectorAll('input, select').forEach(el => el.disabled = true);
        card.querySelector('.editar-btn').style.display = 'inline-block';
        card.querySelector('.guardar-btn').style.display = 'none';

        // 👉 Ocultar botones de agregar producto y pago
        card.querySelector('.agregar-producto-btn').style.display = 'none';
        card.querySelector('.agregar-pago-btn').style.display = 'none';

        // 👉 Actualizar fecha de última modificación
        const ahora = new Date();
        card.querySelector('.ultima-modif').textContent = 
          "Última modificación: " + ahora.toLocaleDateString("es-AR") + " " + ahora.toLocaleTimeString("es-AR", { hour: '2-digit', minute: '2-digit' });
      } else {
        alert("❌ Error al guardar");
      }
    })
    .catch(err => alert("❌ Error inesperado"));
}


function generarConstancia(id) {
  window.open(`/pedidos/${id}/constancia_entrega`, "_blank");
}

function avisarPedido(telefono, numero) {
  const mensaje = `¡Hola! Tu pedido N°${numero} está listo para retirar.`;
  window.open(`https://wa.me/549${telefono}?text=${encodeURIComponent(mensaje)}`, "_blank");
}

function subirFactura(id, event) {
  const archivo = event.target.files[0];
  if (!archivo) return;

  const formData = new FormData();
  formData.append("factura", archivo);

  fetch(`/pedidos/${id}/factura`, {
    method: "POST",
    body: formData
  })
    .then(res => res.json())
    .then(data => {
      if (data.mensaje) alert("✅ Factura subida correctamente");
      else alert("❌ Error al subir factura");
    })
    .catch(() => alert("❌ Error al subir factura"));
}

function formatearFecha(fechaISO) {
  if (!fechaISO) return "-";
  const f = new Date(fechaISO);
  return f.toLocaleDateString("es-AR");
}

function formatearFechaHora(fechaISO) {
  if (!fechaISO) return "-";
  const f = new Date(fechaISO);
  return f.toLocaleDateString("es-AR") + " " + f.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
}

function formatoPeso(n) {
  return (n || 0).toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function filtrarPedidos() {
  const texto = document.getElementById("filtroPedidos").value.toLowerCase();
  const pedidosFiltrados = pedidosGlobal.filter(p => {
    return (
      p.nombre_cliente.toLowerCase().includes(texto) ||
      p.telefono.toLowerCase().includes(texto)
    );
  });
  mostrarPedidos(pedidosFiltrados);
}
