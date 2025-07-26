// static/js/pedidos_lista.js

let pedidosGlobal = [];

const statusColors = {
    'EN PROCESO': { bg: '#0066ffff', text: '#ffffff' },
    'PARA HACER': { bg: '#ffc107', text: '#000000' },
    'LISTO':      { bg: '#198783ff', text: '#ffffff' },
    'ENTREGADO':  { bg: '#249601ff', text: '#ffffff' },
    'CANCELADO':  { bg: '#dc3545', text: '#ffffff' },
    'RMA':        { bg: '#fd7e14', text: '#ffffff' },
    'SERVICIO TECNICO': { bg: '#6610f2', text: '#ffffff' }
};

const productStatusColors = {
    'FALTAN ENVIOS': '#fff3cd', // Amarillo claro
    'PARA HACER': '#cfe2ff',     // Azul claro
    'LISTO': '#a3f9d2ff',          // Verde claro
    'ENTREGADO': '#5baf50ff',      // Gris claro
    'GARANTIA': '#f8d7da',        // Rojo claro
    'PEDIDO': '#b4f0d5ff',
    'REVISADO': '#cfe2ff',
    'CANCELADO': '#afafafff',
    'EN LA OFICINA': '#d1e7dd',
    'EN OTRO LOCAL': '#cfe2ff',
    'NO COBRADO': '#f9c3c8ff',
    'PROBLEMAS': '#eb75f1ff'
};

/**
 * REEMPLAZAR: Se modifica para que llame a la nueva función de resumen
 * después de cargar los datos de los pedidos.
 */
document.addEventListener("DOMContentLoaded", async () => {
    try {
        const res = await fetch("/pedidos/todos");
        if (!res.ok) throw new Error(`Error del servidor: ${res.status}`);
        const data = await res.json();
        
        if (Array.isArray(data)) {
            pedidosGlobal = data;
            actualizarResumenGlobal(); // Calcula y muestra los totales
            popularFiltroEstado();
            mostrarPedidos(data);
        } else {
            console.error("La respuesta de la API no es un array:", data);
        }
    } catch (err) {
        console.error("Error al cargar pedidos:", err);
        document.getElementById("lista-pedidos").innerHTML = `<div class="alert alert-danger">No se pudieron cargar los pedidos. Revise la consola.</div>`;
    }
    document.getElementById("filtroPedidos").addEventListener("input", filtrarPedidos);
    document.getElementById("filtroEstado").addEventListener("change", filtrarPedidos);
});
function mostrarPedidos(pedidos) {
    const contenedor = document.getElementById("lista-pedidos");
    contenedor.innerHTML = "";
    pedidos.sort((a, b) => b.numero - a.numero);

    if (pedidos.length === 0) {
        contenedor.innerHTML = `<div class="text-center text-muted mt-5"><h4>No se encontraron pedidos.</h4></div>`;
        return;
    }

    pedidos.forEach(p => {
        const card = document.createElement("div");
        card.className = "pedido-card";
        card.id = `pedido-card-${p.id}`;
        card.innerHTML = generarHtmlCard(p);
        contenedor.appendChild(card);
    });
}

// static/js/pedidos_lista.js

// static/js/pedidos_lista.js

function generarHtmlInfoItem(label, value, fieldName, type = 'text', options = '', editable = false) {
    const commonAttrs = `data-campo="${fieldName}" ${editable ? '' : 'disabled'}`;
    let controlHTML = '';
    let valueText = '-';

    if (value !== null && value !== undefined) {
        if (type === 'date') {
            valueText = new Date(value).toLocaleDateString('es-AR', { timeZone: 'UTC' });
        } else if (type === 'number') {
            // Se aplica el formato a campos como "Costo Envío"
            valueText = formatoPeso(value);
        } else {
            valueText = value;
        }
    }

    if (editable) {
        if (type === 'select') {
            controlHTML = `<select class="form-select" ${commonAttrs}>${options}</select>`;
        } else if (type === 'number') {
            controlHTML = `<input type="number" step="0.01" class="form-control" value="${value || 0}" ${commonAttrs}>`;
        } else {
            controlHTML = `<input type="${type}" class="form-control" value="${type === 'date' ? formatDateForInput(value) : (value || '')}" ${commonAttrs}>`;
        }
    }

    return `
        <div class="info-item">
            <strong>${label}</strong>
            ${editable ? controlHTML : `<div class="value-text">${valueText}</div>`}
        </div>
    `;
}


function generarHtmlCard(p, enEdicion = false) {
    const estadoGeneral = p.estado_general || 'EN PROCESO';
    const colorInfo = statusColors[estadoGeneral] || { bg: '#6c757d', text: '#ffffff' };
    const facturaSubida = p.factura_base64 && p.factura_base64.length > 10;

    // Se calculan los totales asegurando que sean números.
    const totalVenta = p.total_venta || 0;
    const totalAbonado = p.total_abonado || 0;
    const debe = totalVenta - totalAbonado;

    return `
        <div class="pedido-header" style="background-color: ${colorInfo.bg}; color: ${colorInfo.text};">
            <h5>Pedido Nº ${p.numero}</h5>
            <div>
                <span class="badge">${estadoGeneral}</span>
                <button class="btn btn-sm ms-2" onclick="${enEdicion ? `guardarEdicion(${p.id})` : `activarEdicion(${p.id})`}">
                    <i class="fas ${enEdicion ? 'fa-save' : 'fa-edit'}"></i> ${enEdicion ? 'Guardar' : 'Editar'}
                </button>
                ${enEdicion ? `<button class="btn btn-sm" onclick="cancelarEdicion(${p.id})"><i class="fas fa-times"></i> Cancelar</button>` : ''}
            </div>
        </div>
        <div class="pedido-body">
             <div class="row">
                <div class="col-lg-7">
                    <div class="info-grid">
                        <div class="info-block">
                            ${generarHtmlInfoItem('Cliente', p.nombre_cliente, 'nombre_cliente', 'text', '', enEdicion)}
                            ${generarHtmlInfoItem('Teléfono', p.telefono, 'telefono', 'text', '', enEdicion)}
                            ${generarHtmlInfoItem('DNI/CUIT', p.dni_cliente, 'dni_cliente', 'text', '', enEdicion)}
                        </div>
                        <div class="info-block">
                            ${generarHtmlInfoItem('Vendedor', p.vendedor, 'vendedor', 'select', listarVendedores(p.vendedor), enEdicion)}
                            ${generarHtmlInfoItem('Envío', p.forma_envio, 'forma_envio', 'select', listarEnvios(p.forma_envio), enEdicion)}
                            ${generarHtmlInfoItem('Costo Envío', p.costo_envio, 'costo_envio', 'number', '', enEdicion)}
                        </div>
                         <div class="info-block">
                            ${generarHtmlInfoItem('Creación', p.fecha_emision, 'fecha_emision', 'date', '', enEdicion)}
                            ${generarHtmlInfoItem('Factura', p.tipo_factura, 'tipo_factura', 'select', listarTiposFactura(p.tipo_factura), enEdicion)}
                            ${generarHtmlInfoItem('Estado General', estadoGeneral, 'estado_general', 'select', listarEstadosPedido(estadoGeneral), enEdicion)}
                        </div>
                    </div>
                </div>
                <div class="col-lg-5">
                    ${generarTablaPagos(p, enEdicion)}
                    <div class="totales">
                        <p><strong>Total Venta:</strong> <span class="total-venta">${formatoPeso(totalVenta)}</span></p>
                        <p><strong>Total Abonado:</strong> <span class="total-abonado">${formatoPeso(totalAbonado)}</span></p>
                        <p><strong>Debe:</strong> <span class="total-debe text-danger">${formatoPeso(debe)}</span></p>
                    </div>
                </div>
            </div>
            <div class="row mt-2"><div class="col-12">${generarTablaProductos(p, enEdicion)}</div></div>
            <div class="acciones">
                <button class="btn btn-sm btn-outline-dark" onclick="generarConstancia(${p.id})"><i class="fas fa-file-alt me-1"></i>Constancia Entrega</button>
                <button class="btn btn-sm btn-outline-success" onclick="avisarPedido('${p.telefono}', '${p.numero}')"><i class="fab fa-whatsapp me-1"></i>Avisar Listo</button>
                <a class="btn btn-sm btn-outline-info ${facturaSubida ? '' : 'disabled'}" href="/pedidos/${p.id}/factura" download><i class="fas fa-download me-1"></i>Descargar FC</a>
                <label class="btn btn-sm btn-outline-primary position-relative">
                    ${facturaSubida ? '<span class="factura-indicator"><i class="fas fa-check-circle"></i></span>' : ''}
                    <i class="fas fa-upload me-1"></i>Subir Factura
                    <input type="file" hidden onchange="subirFactura(${p.id}, event)">
                </label>
                ${enEdicion ? `<button class="btn btn-sm btn-danger ms-auto" onclick="eliminarPedido(${p.id})"><i class="fas fa-trash me-1"></i>Eliminar Pedido</button>` : ''}
            </div>
            <p class="ultima-modif">Última modificación: ${formatearFechaHora(p.ultima_modificacion)}</p>
        </div>
    `;
}


// static/js/pedidos_lista.js

function generarTablaProductos(pedido, editable) {
    let tablaHTML = `<h6 class="section-title">Productos</h6><div class="table-responsive"><table class="table-pedidos tabla-productos"><thead><tr><th class="col-proveedor">Proveedor</th><th class="col-producto">Producto</th><th class="col-sku">SKU</th><th class="col-precio">Venta Unit.</th><th class="col-cant">Cant.</th><th class="col-estado">Estado</th><th class="col-cambio">Cambio</th>${editable ? '<th class="col-accion"></th>' : ''}</tr></thead><tbody>`;
    (pedido.productos || []).forEach((pr, idx) => {
        const estadoProducto = pr.estado_producto || 'PARA HACER';
        const colorFila = productStatusColors[estadoProducto] || 'transparent';
        tablaHTML += `<tr data-index="${idx}" style="background-color: ${colorFila};">
            <td class="col-proveedor"><select data-prod="proveedor" ${editable ? '' : 'disabled'}>${listarProveedores(pr.proveedor)}</select></td>
            <td class="col-producto"><input type="text" data-prod="producto" value="${pr.producto}" ${editable ? '' : 'disabled'}></td>
            <td class="col-sku"><input type="text" data-prod="sku" value="${pr.sku || ''}" ${editable ? '' : 'disabled'}></td>
            <td class="col-precio">
                ${editable ? `<input type="number" step="0.01" data-prod="precio_venta" value="${pr.precio_venta}">` : `<span>${formatoPeso(pr.precio_venta)}</span>`}
            </td>
            <td class="col-cant">
                 ${editable ? `<input type="number" data-prod="cantidad" value="${pr.cantidad}">` : `<span>${pr.cantidad}</span>`}
            </td>
            <td class="col-estado"><select data-prod="estado_producto" ${editable ? '' : 'disabled'}>${listarEstadosProducto(estadoProducto)}</select></td>
            <td class="col-cambio"><select data-prod="cambio" ${editable ? '' : 'disabled'}><option value="true" ${pr.cambio ? 'selected' : ''}>✅</option><option value="false" ${!pr.cambio ? 'selected' : ''}>❌</option></select></td>
            ${editable ? `<td class="col-accion"><button class="btn btn-sm text-danger p-0" onclick="this.closest('tr').remove(); recalcularTotales(this.closest('.pedido-card'))">✖</button></td>` : ''}
        </tr>`;
    });
    tablaHTML += `</tbody></table></div>`;
    if (editable) {
        tablaHTML += `<button class="btn btn-sm btn-outline-primary mt-2" onclick="agregarFilaProducto(this)"><i class="fas fa-plus me-1"></i> Agregar Producto</button>`;
    }
    return tablaHTML;
}


function actualizarResumenGlobal() {
    const ahora = new Date();
    const mesActual = ahora.getMonth();
    const anioActual = ahora.getFullYear();

    let totalVendidoMes = 0;
    let totalFaltaCobrar = 0;

    // Filtramos los pedidos que no están cancelados para los cálculos
    const pedidosActivos = pedidosGlobal.filter(p => p.estado_general !== 'CANCELADO');

    pedidosActivos.forEach(p => {
        const fechaPedido = new Date(p.fecha_emision);
        // Sumar al total del mes si el pedido es del mes y año actual
        if (fechaPedido.getUTCMonth() === mesActual && fechaPedido.getUTCFullYear() === anioActual) {
            totalVendidoMes += p.total_venta || 0;
        }

        // Sumar al total que falta cobrar
        const debe = (p.total_venta || 0) - (p.total_abonado || 0);
        totalFaltaCobrar += debe;
    });

    document.getElementById('totalVendidoMes').textContent = formatoPeso(totalVendidoMes);
    document.getElementById('totalFaltaCobrar').textContent = formatoPeso(totalFaltaCobrar);
    // El total de pedidos sí incluye los cancelados
    document.getElementById('totalPedidos').textContent = pedidosGlobal.length;
}

function generarTablaPagos(pedido, editable) {
    let tablaHTML = `<h6 class="section-title">Pagos</h6><div class="table-responsive"><table class="table-pedidos tabla-pagos"><thead><tr><th class="col-forma">Forma</th><th class="col-monto">Monto</th><th class="col-tipo-cambio">T. Cambio</th><th class="col-fecha">Fecha</th>${editable ? '<th class="col-accion"></th>' : ''}</tr></thead><tbody>`;
    (pedido.pagos || []).forEach((pg, idx) => {
        const fechaParaInput = formatDateForInput(pg.fecha);
        const fechaFormateada = pg.fecha ? new Date(pg.fecha).toLocaleDateString('es-AR', {timeZone: 'UTC'}) : '-';
        
        // SOLUCIÓN: Se crea una variable para mostrar el monto en formato ARS o USD según el método.
        let montoDisplay = formatoPeso(pg.monto);
        if(pg.metodo === 'USD' || pg.metodo === 'USDT') {
            montoDisplay = `U$S ${(pg.monto || 0).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        }

        tablaHTML += `<tr data-index="${idx}">
            <td><select data-pago="metodo" ${editable ? '' : 'disabled'}>${listarFormasPago(pg.metodo)}</select></td>
            <td class="col-monto">
                ${editable ? `<input type="number" step="0.01" data-pago="monto" value="${pg.monto}">` : `<span>${montoDisplay}</span>`}
            </td>
            <td class="col-tipo-cambio">
                ${editable ? `<input type="number" step="0.01" data-pago="tipo_cambio" value="${pg.tipo_cambio || ''}">` : `<span>${pg.tipo_cambio || '-'}</span>`}
            </td>
            <td class="col-fecha">
                 ${editable ? `<input type="date" data-pago="fecha" value="${fechaParaInput}">` : `<span>${fechaFormateada}</span>`}
            </td>
            ${editable ? `<td class="col-accion"><button class="btn btn-sm text-danger p-0" onclick="this.closest('tr').remove(); recalcularTotales(this.closest('.pedido-card'))">✖</button></td>` : ''}
        </tr>`;
    });
    tablaHTML += `</tbody></table></div>`;
    if (editable) {
        tablaHTML += `<button class="btn btn-sm btn-outline-success mt-2" onclick="agregarFilaPago(this)"><i class="fas fa-plus me-1"></i> Agregar Pago</button>`;
    }
    return tablaHTML;
}


function activarEdicion(id) {
    const card = document.getElementById(`pedido-card-${id}`);
    const pedido = pedidosGlobal.find(p => p.id === id);
    card.classList.add('edit-mode');
    card.innerHTML = generarHtmlCard(pedido, true);
    card.querySelector('input[data-campo="costo_envio"]').value = pedido.costo_envio || 0;
    card.querySelectorAll('input, select').forEach(el => {
        el.addEventListener('input', () => recalcularTotales(card));
    });
}

function cancelarEdicion(id) {
    const card = document.getElementById(`pedido-card-${id}`);
    const pedido = pedidosGlobal.find(p => p.id === id);
    card.classList.remove('edit-mode');
    card.innerHTML = generarHtmlCard(pedido, false);
}

async function guardarEdicion(id) {
    const card = document.getElementById(`pedido-card-${id}`);
    const data = {};
    card.querySelectorAll('[data-campo]').forEach(el => { data[el.dataset.campo] = el.value; });

    data.productos = Array.from(card.querySelectorAll(".tabla-productos tbody tr")).map(row => ({
        proveedor: row.querySelector('[data-prod="proveedor"]').value,
        producto: row.querySelector('[data-prod="producto"]').value,
        sku: row.querySelector('[data-prod="sku"]').value,
        precio_venta: parseFloat(row.querySelector('[data-prod="precio_venta"]').value) || 0,
        cantidad: parseInt(row.querySelector('[data-prod="cantidad"]').value) || 1,
        estado_producto: row.querySelector('[data-prod="estado_producto"]').value,
        cambio: row.querySelector('[data-prod="cambio"]').value === 'true'
    }));

    data.pagos = Array.from(card.querySelectorAll(".tabla-pagos tbody tr")).map(row => {
        // SOLUCIÓN: Se busca el input de forma segura.
        const tipoCambioInput = row.querySelector('[data-pago="tipo_cambio"]'); 
        return {
            metodo: row.querySelector('[data-pago="metodo"]').value,
            monto: parseFloat(row.querySelector('[data-pago="monto"]').value) || 0,
            // Si el input existe, se toma su valor; si no, se guarda como nulo.
            tipo_cambio: tipoCambioInput ? (parseFloat(tipoCambioInput.value) || null) : null,
            fecha: row.querySelector('[data-pago="fecha"]').value || null
        };
    });

    try {
        const res = await fetch(`/pedidos/${id}`, {
            method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error('Error al guardar');
        
        const dataRes = await fetch("/pedidos/todos").then(r => r.json());
        pedidosGlobal = dataRes;
        const pedidoActualizado = pedidosGlobal.find(p => p.id === id);
        card.classList.remove('edit-mode');
        card.innerHTML = generarHtmlCard(pedidoActualizado, false);
        alert("✅ Pedido actualizado");
    } catch(err) {
        alert("❌ Error al guardar el pedido. Revise la consola.");
        console.error(err);
    }
}

// static/js/pedidos_lista.js

function recalcularTotales(card) {
    let totalVentaProductos = 0;
    card.querySelectorAll('.tabla-productos tbody tr').forEach(row => {
        const precioInput = row.querySelector('input[data-prod="precio_venta"]');
        const cantidadInput = row.querySelector('input[data-prod="cantidad"]');
        if (precioInput && cantidadInput) {
            totalVentaProductos += (parseFloat(precioInput.value) || 0) * (parseInt(cantidadInput.value) || 0);
        }
    });

    const costoEnvio = parseFloat(card.querySelector('input[data-campo="costo_envio"]').value) || 0;
    const totalVenta = totalVentaProductos + costoEnvio;

    let totalAbonado = 0;
    card.querySelectorAll('.tabla-pagos tbody tr').forEach(row => {
        const montoInput = row.querySelector('input[data-pago="monto"]');
        const metodoSelect = row.querySelector('select[data-pago="metodo"]');
        let monto = parseFloat(montoInput.value) || 0;

        // SOLUCIÓN: Lógica de conversión de dólares en tiempo real para la edición.
        if (metodoSelect && (metodoSelect.value === 'USD' || metodoSelect.value === 'USDT')) {
            const cambioInput = row.querySelector('input[data-pago="tipo_cambio"]');
            const tipoCambio = parseFloat(cambioInput.value) || 1; // Si no hay cambio, se usa 1 para no alterar el monto.
            monto *= tipoCambio;
        }
        totalAbonado += monto;
    });
    
    // Se formatean todos los totales antes de mostrarlos.
    card.querySelector(".total-venta").textContent = formatoPeso(totalVenta);
    card.querySelector(".total-abonado").textContent = formatoPeso(totalAbonado);
    card.querySelector(".total-debe").textContent = formatoPeso(totalVenta - totalAbonado);
}

function filtrarPedidos() {
    const texto = document.getElementById("filtroPedidos").value.toLowerCase();
    const estado = document.getElementById("filtroEstado").value;

    const pedidosFiltrados = pedidosGlobal.filter(p => {
        const estadoPedido = p.estado_general || 'EN PROCESO';

        const coincideTexto = !texto || 
            p.nombre_cliente.toLowerCase().includes(texto) ||
            (p.telefono && p.telefono.includes(texto)) ||
            String(p.numero).includes(texto);
        
        const coincideEstado = !estado || estadoPedido === estado;

        return coincideTexto && coincideEstado;
    });
    mostrarPedidos(pedidosFiltrados);
}

function agregarFilaProducto(btn) {
    const tbody = btn.closest('.col-12').querySelector('.tabla-productos tbody');
    // El resto de la función es idéntica a la que ya tienes...
    const nuevaFila = document.createElement('tr');
    nuevaFila.dataset.index = Date.now();
    nuevaFila.innerHTML = `
      <td><select data-prod="proveedor">${listarProveedores()}</select></td>
      <td><input type="text" data-prod="producto" value=""></td>
      <td><input type="text" data-prod="sku" value=""></td>
      <td><input type="number" step="0.01" data-prod="precio_venta" value="0"></td>
      <td><input type="number" data-prod="cantidad" value="1"></td>
      <td><select data-prod="estado_producto">${listarEstadosProducto("PARA HACER")}</select></td>
      <td><select data-prod="cambio"><option value="true">✅</option><option value="false" selected>❌</option></select></td>
      <td><button class="btn btn-sm text-danger p-0" onclick="this.closest('tr').remove(); recalcularTotales(this.closest('.pedido-card'))">✖</button></td>
    `;
    tbody.appendChild(nuevaFila);
    nuevaFila.querySelectorAll('input, select').forEach(el => el.addEventListener('input', () => recalcularTotales(btn.closest('.pedido-card'))));
}

function agregarFilaPago(btn) {
    const tbody = btn.closest('.col-lg-5').querySelector('.tabla-pagos tbody');
    const hoy = new Date().toISOString().split('T')[0];
    const nuevaFila = document.createElement('tr');
    nuevaFila.dataset.index = Date.now();
    nuevaFila.innerHTML = `
      <td><select data-pago="metodo">${listarFormasPago()}</select></td>
      <td><input type="number" step="0.01" data-pago="monto" value="0"></td>
      <td><input type="number" step="0.01" data-pago="tipo_cambio" value=""></td>
      <td><input type="date" data-pago="fecha" value="${hoy}"></td>
      <td><button class="btn btn-sm text-danger p-0" onclick="this.closest('tr').remove(); recalcularTotales(this.closest('.pedido-card'))">✖</button></td>
    `;
    tbody.appendChild(nuevaFila);
    nuevaFila.querySelectorAll('input, select').forEach(el => el.addEventListener('input', () => recalcularTotales(btn.closest('.pedido-card'))));
}

// --- Funciones de Ayuda (Listados, formatos, etc.) ---
function listarProveedores(sel) { const p = ["TBD","AIR", "COMPRA GAMER", "FULL HARD", "GOLDENTECH", "INVID", "SENTEY", "LIONTECH", "MALDITO HARD", "MAXIMUS", "MERCADO LIBRE", "PC ARTS", "ROCKETHARD", "SLOT ONE", "SOLUTION BOX", "SOUNDTEC", "ALE", "NOSOTROS", "HYPERGAMING", "COMPUTODO", "CDKEYOFFER", "MUNDO HARDWARE", "NOXIE", "ACUARIO", "REPE", "MGM GAMES", "MEXX", "HYDRAXTREME", "PEAK COMPUTACION", "GAMERS POINT", "ECLIPSE COMPUTACION", "SCP HARDSTORE", "ARMYTECH", "GPU USADA", "SPACE", "NEW TREE", "MEGASOFT", "GEZATEK", "WIZ TECH", "GAMING CITY", "31STORE", "GRUPO NUCLEO", "MINING STORE", "HARD CORE", "NEW BYTES", "MYM COMPUTACION", "XT-PC", "ELECTROOMBU", "TGS", "DATASOFT", "HFTECNOLOGIA", "URANO STREAM", "LUCAS", "JUAMPI", "TRYHARDWARE", "SERGIO", "MIMI TECH", "TURTECH", "INTEGRADOS ARGENTINOS", "GVGMALL", "LOGG", "SANTY", "SANTY (ABUELO)", "HARDLOOTS", "GONZA", "G2A", "CUCHU", "CLICK AREQUITO", "BLACK", "MGM GAMERS", "EMA", "GAUSS", "OVERTECH", "VENEX", "TGS (WEB)", "COMPUGARDEN", "CLIENTE", "IGNATECH", "SOLARMAX", "VRACER", "REPARACION TGS", "CROSSHAIR", "GN POINT", "DISTECNA", "INTERMACO", "CEVEN", "GAMING POINT", "KATECH", "ROYALECDKEY", "THIAGO", "RMINSUMOS", "USABAIRES"]; return p.map(pv => `<option ${pv === sel ? "selected" : ""}>${pv}</option>`).join(""); }
function listarEstadosProducto(sel) { const e = ["FALTAN ENVIOS", "PARA HACER", "LISTO", "ENTREGADO", "GARANTIA", "PEDIDO", "REVISADO", "CANCELADO", "EN LA OFICINA", "EN OTRO LOCAL", "NO COBRADO", "PROBLEMAS"]; return e.map(st => `<option ${st === sel ? "selected" : ""}>${st}</option>`).join("");}
function listarEstadosPedido(sel) { const e = ["EN PROCESO", "PARA HACER", "LISTO", "ENTREGADO", "CANCELADO", "RMA", "SERVICIO TECNICO"]; return e.map(st => `<option ${st === sel ? "selected" : ""}>${st}</option>`).join("");}
function listarFormasPago(sel) { 
    const f = ["EFECTIVO", "MERCADO PAGO", "TRANSFERENCIA", "USD", "USDT", "PAGO EN TIENDA", "TARJETA", "CUENTA DNI", "CRÉDITO", "OTROS"]; 
    return f.map(fp => `<option value="${fp}" ${fp === sel ? "selected" : ""}>${fp}</option>`).join("");
}
function listarVendedores(sel) { const v = ["Santy", "Lucas", "Thiago", "Repe", "Ale"]; return v.map(vnd => `<option ${vnd === sel ? "selected" : ""}>${vnd}</option>`).join("");}
function listarEnvios(sel) { const e = ["Moto", "Dropshipping", "Andreani", "Retira"]; return e.map(env => `<option ${env === sel ? "selected" : ""}>${env}</option>`).join("");}
function listarTiposFactura(sel) { const f = ["NA", "Factura A", "Factura B"]; return f.map(fac => `<option value="${fac}" ${fac === sel ? "selected" : ""}>${fac}</option>`).join("");}
function generarConstancia(id) { window.open(`/pedidos/${id}/constancia_entrega`, "_blank"); }
function avisarPedido(tel, num) { if(!tel) {alert("El cliente no tiene un teléfono cargado."); return;} const m = `¡Hola! Tu pedido N°${num} está listo para retirar.`; window.open(`https://wa.me/549${tel}?text=${encodeURIComponent(m)}`, "_blank"); }
async function subirFactura(id, event) { const file = event.target.files[0]; if (!file) return; const formData = new FormData(); formData.append("factura", file); const res = await fetch(`/pedidos/${id}/factura`, { method: "POST", body: formData }); const data = await res.json(); alert(data.mensaje || data.error); if(res.ok) { const p = pedidosGlobal.find(p => p.id === id); if(p) p.factura_base64 = 'true'; cancelarEdicion(id); } }
function formatearFechaHora(iso) { if (!iso) return "-"; const f = new Date(iso); return f.toLocaleString("es-AR", { day: '2-digit', month: '2-digit', year: 'numeric', hour: "2-digit", minute: "2-digit" }); }
function formatoPeso(n) { return (n || 0).toLocaleString("es-AR", { style: "currency", currency: "ARS" }); }


function formatDateForInput(dateString) {
    if (!dateString) return '';
    // Intenta crear un objeto Date. Si es inválido, devuelve string vacío.
    const date = new Date(dateString);
    if (isNaN(date)) return '';
    // Obtiene los componentes de la fecha en UTC para evitar problemas de zona horaria.
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// static/js/pedidos_lista.js

/**
 * Agrega una nueva fila editable a la tabla de productos del pedido.
 */
function agregarFilaProducto(btn) {
  const tbody = btn.closest('.pedido-body').querySelector('.tabla-productos tbody');
  const nuevaFila = document.createElement('tr');
  // Se usa un timestamp para el índice para asegurar que sea único
  nuevaFila.dataset.index = Date.now(); 
  nuevaFila.innerHTML = `
    <td><select data-prod="proveedor">${listarProveedores()}</select></td>
    <td><input type="text" data-prod="producto" value=""></td>
    <td><input type="text" data-prod="sku" value=""></td>
    <td><input type="number" step="0.01" data-prod="precio_venta" value="0"></td>
    <td><input type="number" data-prod="cantidad" value="1"></td>
    <td><select data-prod="estado_producto">${listarEstadosProducto("PARA HACER")}</select></td>
    <td><select data-prod="cambio"><option value="true">✅</option><option value="false" selected>❌</option></select></td>
    <td><button class="btn btn-sm text-danger p-0" onclick="this.closest('tr').remove(); recalcularTotales(this.closest('.pedido-card'))">✖</button></td>
  `;
  tbody.appendChild(nuevaFila);
  // Se asegura que la nueva fila también recalcule los totales
  nuevaFila.querySelectorAll('input, select').forEach(el => el.addEventListener('input', () => recalcularTotales(btn.closest('.pedido-card'))));
}

/**
 * Agrega una nueva fila editable a la tabla de pagos del pedido.
 */
function agregarFilaPago(btn) {
  const tbody = btn.closest('.pedido-body').querySelector('.tabla-pagos tbody');
  const hoy = new Date().toISOString().split('T')[0];
  const nuevaFila = document.createElement('tr');
  nuevaFila.dataset.index = Date.now();
  nuevaFila.innerHTML = `
    <td><select data-pago="metodo">${listarFormasPago()}</select></td>
    <td><input type="number" step="0.01" data-pago="monto" value="0"></td>
    <td><input type="number" step="0.01" data-pago="tipo_cambio" value=""></td>
    <td><input type="date" data-pago="fecha" value="${hoy}"></td>
    <td><button class="btn btn-sm text-danger p-0" onclick="this.closest('tr').remove(); recalcularTotales(this.closest('.pedido-card'))">✖</button></td>
  `;
  tbody.appendChild(nuevaFila);
  nuevaFila.querySelectorAll('input, select').forEach(el => el.addEventListener('input', () => recalcularTotales(btn.closest('.pedido-card'))));
}

/**
 * Crea las opciones del menú desplegable para filtrar por estado.
 */
function popularFiltroEstado() {
    const select = document.getElementById('filtroEstado');
    // Asegurarse de que el elemento exista antes de continuar
    if (!select) return; 
    
    const estados = Object.keys(statusColors);
    estados.forEach(estado => {
        const option = document.createElement('option');
        option.value = estado;
        option.textContent = estado;
        select.appendChild(option);
    });
}

/**
 * Solicita confirmación y elimina un pedido.
 */
// static/js/pedidos_lista.js

async function eliminarPedido(id) {
    const pedido = pedidosGlobal.find(p => p.id === id);
    if (!pedido) return;

    const confirmacion = confirm(`¿Estás seguro de que quieres eliminar el Pedido Nº ${pedido.numero}? Esta acción no se puede deshacer.`);
    if (!confirmacion) return;

    try {
        const res = await fetch(`/pedidos/${id}`, { method: 'DELETE' });

        // SOLUCIÓN: Manejo de errores mejorado
        if (res.ok) {
            alert('✅ Pedido eliminado con éxito.');
            document.getElementById(`pedido-card-${id}`).remove();
            pedidosGlobal = pedidosGlobal.filter(p => p.id !== id);
            actualizarResumenGlobal();
        } else {
            // Intenta leer el error como texto, no como JSON
            const errorTexto = await res.text();
            throw new Error(errorTexto || `Error del servidor: ${res.status}`);
        }
    } catch (err) {
        alert(`❌ Error al eliminar: ${err.message}`);
        console.error(err);
    }
}