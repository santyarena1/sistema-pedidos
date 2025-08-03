// static/js/pedidos_lista.js

// --- VARIABLES GLOBALES ---
let pedidosGlobal = [];
const estadosProductoUnicos = new Set();
const proveedoresUnicos = new Set();

// Paletas de colores para los diferentes estados
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
    'FALTAN ENVIOS': '#fff3cd', 'PARA HACER': '#cfe2ff', 'LISTO': '#a3f9d2ff',
    'ENTREGADO': '#d1e7dd', 'GARANTIA': '#f8d7da', 'PEDIDO': '#b4f0d5ff',
    'REVISADO': '#cfe2ff', 'CANCELADO': '#e9ecef', 'EN LA OFICINA': '#d1e7dd',
    'EN OTRO LOCAL': '#cfe2ff', 'NO COBRADO': '#f9c3c8ff', 'PROBLEMAS': '#eb75f1ff'
};

// --- INICIALIZACIÓN DE LA PÁGINA ---
document.addEventListener("DOMContentLoaded", () => {
    cargarYRenderizarPedidos();
    inicializarListeners();
});

/**
 * Carga todos los pedidos desde el servidor y lanza el primer renderizado.
 */
async function cargarYRenderizarPedidos() {
    try {
        const res = await fetch("/pedidos/todos");
        if (!res.ok) {
            throw new Error(`Error del servidor: ${res.status} - ${res.statusText}`);
        }
        
        pedidosGlobal = await res.json();
        
        if (!Array.isArray(pedidosGlobal)) {
             throw new Error("La respuesta de la API no es un array válido.");
        }

        // Extraer datos únicos para los filtros de la modal
        estadosProductoUnicos.clear();
        proveedoresUnicos.clear();
        pedidosGlobal.forEach(p => {
            (p.productos || []).forEach(prod => {
                if(prod.estado_producto) estadosProductoUnicos.add(prod.estado_producto);
                if(prod.proveedor) proveedoresUnicos.add(prod.proveedor);
            });
        });
        
        popularFiltroEstadoGeneral();
        popularFiltrosDelModal();
        aplicarFiltros(); // Llama a los filtros por primera vez para mostrar todo

    } catch (err) {
        console.error("Error al cargar y procesar los pedidos:", err);
        const errorContainer = document.getElementById("lista-pedidos");
        if (errorContainer) {
            errorContainer.innerHTML = `<div class="alert alert-danger mt-4"><h3>Error Crítico</h3><p>No se pudieron cargar los pedidos. Revisa la consola del navegador (F12) para ver el error detallado.</p><pre>${err.message}</pre></div>`;
        }
    }
}

// Reemplaza tu función inicializarListeners por esta
function inicializarListeners() {
    // Listeners de la página principal (sin cambios)
    document.getElementById("filtroPedidos").addEventListener("input", aplicarFiltros);
    document.getElementById("filtroEstado").addEventListener("change", aplicarFiltros);
    document.getElementById("filtroPeriodo").addEventListener("change", () => {
        togglePeriodoPersonalizado();
        aplicarFiltros();
    });
    document.getElementById("fechaInicio").addEventListener("change", aplicarFiltros);
    document.getElementById("fechaFin").addEventListener("change", aplicarFiltros);
    const aplicarBtn = document.querySelector('button[onclick="aplicarFiltros()"]');
    if (aplicarBtn) {
       aplicarBtn.addEventListener('click', aplicarFiltros);
    }
    
    // Listeners del modal
    const modal = document.getElementById('modalGestionProductos');
    if(modal) {
        modal.addEventListener('show.bs.modal', renderizarProductosEnModal);
    }
    // SOLUCIÓN: Se agregan los listeners para los filtros del modal
    document.getElementById("modalFiltroEstado").addEventListener("change", renderizarProductosEnModal);
    document.getElementById("modalFiltroProveedor").addEventListener("change", renderizarProductosEnModal);
    document.getElementById("modalFiltroPeriodo").addEventListener("change", () => {
        togglePeriodoPersonalizadoModal();
        renderizarProductosEnModal();
    });
    document.getElementById("modalFechaInicio").addEventListener("change", renderizarProductosEnModal);
    document.getElementById("modalFechaFin").addEventListener("change", renderizarProductosEnModal);
}


// --- LÓGICA DE FILTRADO Y RENDERIZADO ---

/**
 * Filtra los pedidos según TODOS los criterios seleccionados y los muestra.
 */
function aplicarFiltros() {
    const filtroTexto = document.getElementById("filtroPedidos").value.toLowerCase();
    const filtroEstado = document.getElementById("filtroEstado").value;
    const { inicio, fin } = obtenerFechasDelPeriodo();

    const pedidosFiltrados = pedidosGlobal.filter(p => {
        // 1. Filtrado por fecha
        const fechaPedido = new Date(p.fecha_emision + 'T00:00:00'); 
        if (fechaPedido < inicio || fechaPedido > fin) return false;

        // 2. Filtrado por estado general
        const estadoPedido = p.estado_general || 'EN PROCESO';
        if (filtroEstado && estadoPedido !== filtroEstado) return false;
        
        // 3. Filtrado por texto libre
        if (filtroTexto) {
            const busquedaEnProductos = (p.productos || []).some(prod => (prod.producto || '').toLowerCase().includes(filtroTexto));
            const busquedaGeneral = [
                p.numero.toString(), 
                (p.nombre_cliente || ''), 
                (p.telefono || '')
            ].join(' ').toLowerCase().includes(filtroTexto);
            if (!busquedaGeneral && !busquedaEnProductos) return false;
        }

        // Si pasa todos los filtros, se incluye
        return true;
    });
    
    mostrarPedidos(pedidosFiltrados); 
    actualizarResumenGlobal(pedidosFiltrados);
}

/**
 * Renderiza las tarjetas de los pedidos en el DOM.
 */
function mostrarPedidos(pedidos) {
    const contenedor = document.getElementById("lista-pedidos");
    contenedor.innerHTML = "";
    pedidos.sort((a, b) => b.numero - a.numero);

    if (pedidos.length === 0) {
        contenedor.innerHTML = `<div class="text-center text-muted mt-5"><h4>No se encontraron pedidos con los filtros aplicados.</h4></div>`;
        return;
    }

    pedidos.forEach(p => {
        // Se usa `createRange` para parsear el HTML de forma segura y eficiente
        const cardFragment = document.createRange().createContextualFragment(generarHtmlCard(p));
        contenedor.appendChild(cardFragment);
    });
}

/**
 * Actualiza las tarjetas de resumen con los totales de los pedidos filtrados.
 */
// En: pedidos_lista.js
// En: pedidos_lista.js

// En: pedidos_lista.js

function actualizarResumenGlobal(pedidosFiltrados) {
    let totalVendidoPeriodo = 0;
    let faltaCobrarPeriodo = 0;

    pedidosFiltrados.forEach(p => {
        if (p.estado_general !== 'CANCELADO') {
            // SOLUCIÓN: Se usa parseFloat() para asegurar que la suma sea matemática y no de texto.
            const totalVenta = parseFloat(p.total_venta) || 0;
            const totalAbonado = parseFloat(p.total_abonado) || 0;
            
            totalVendidoPeriodo += totalVenta;

            const debe = totalVenta - totalAbonado;
            if (debe > 0) {
                faltaCobrarPeriodo += debe;
            }
        }
    });

    document.getElementById('totalVendidoMes').textContent = formatoPeso(totalVendidoPeriodo);
    document.getElementById('totalFaltaCobrar').textContent = formatoPeso(faltaCobrarPeriodo);
    document.getElementById('totalPedidos').textContent = pedidosFiltrados.length;
}


// --- SECCIÓN DE GENERACIÓN DE HTML ---

/**
 * Crea el HTML completo para la tarjeta de un pedido.
 * Esta versión usa la estructura correcta con `info-block`.
 */
// En: pedidos_lista.js
function generarHtmlCard(p, enEdicion = false) {
    const estadoGeneral = p.estado_general || 'EN PROCESO';
    const colorInfo = statusColors[estadoGeneral] || { bg: '#6c757d', text: '#ffffff' };
    const facturaSubida = p.factura_base64 && p.factura_base64.length > 10;
    const totalVenta = p.total_venta || 0;
    const totalAbonado = p.total_abonado || 0;
    const debe = totalVenta - totalAbonado;

    // SOLUCIÓN: Lógica condicional para las observaciones
    let observacionesHtml = '';
    if (enEdicion) {
        observacionesHtml = `
            <h6 class="section-title" style="margin-top: 1rem;">Observaciones (Editar)</h6>
            <textarea class="form-control" data-campo="observaciones" rows="3">${p.observaciones || ''}</textarea>
        `;
    } else if (p.observaciones) {
        observacionesHtml = `<div class="observaciones-lista"><strong>Observaciones:</strong> ${p.observaciones}</div>`;
    }

    const infoGrid = `
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
    `;

    return `
    <div class="pedido-card ${enEdicion ? 'edit-mode' : ''}" id="pedido-card-${p.id}">
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
                    ${infoGrid}
                    ${observacionesHtml}
                </div>
                <div class="col-lg-5">
                    ${generarTablaPagos(p, enEdicion)}
                    <div class="totales">
                        <p><strong>Total Venta:</strong> <span class="total-venta">${formatoPeso(totalVenta)}</span></p>
                        <p><strong>Total Abonado:</strong> <span class="total-abonado text-success">${formatoPeso(totalAbonado)}</span></p>
                        <p><strong>Debe:</strong> <span class="total-debe text-danger">${formatoPeso(debe)}</span></p>
                    </div>
                </div>
            </div>
            <div class="row mt-2"><div class="col-12">${generarTablaProductos(p, enEdicion)}</div></div>
            <div class="acciones">
                <button class="btn btn-sm btn-outline-dark" onclick="generarConstancia(${p.id})"><i class="fas fa-file-alt me-1"></i>Constancia</button>
                <button class="btn btn-sm btn-outline-success" onclick="avisarPedido('${p.telefono}', '${p.numero}')"><i class="fab fa-whatsapp me-1"></i>Avisar Listo</button>
                <a class="btn btn-sm btn-outline-info ${facturaSubida ? '' : 'disabled'}" href="/pedidos/${p.id}/factura" download><i class="fas fa-download me-1"></i>Descargar FC</a>
                <label class="btn btn-sm btn-outline-primary position-relative">${facturaSubida ? '<span class="factura-indicator"><i class="fas fa-check-circle"></i></span>' : ''}<i class="fas fa-upload me-1"></i>Subir Factura<input type="file" hidden onchange="subirFactura(${p.id}, event)"></label>
                ${enEdicion ? `<button class="btn btn-sm btn-danger ms-auto" onclick="eliminarPedido(${p.id})"><i class="fas fa-trash me-1"></i>Eliminar</button>` : ''}
            </div>
            <p class="ultima-modif">Última modificación: ${formatearFechaHora(p.ultima_modificacion)}</p>
        </div>
    </div>
    `;
}

function generarHtmlInfoItem(label, value, fieldName, type = 'text', options = '', editable = false) {
    let valueText = (value === null || value === undefined) ? '-' : value;

    if (type === 'date' && value) {
        valueText = new Date(value + 'T00:00:00').toLocaleDateString('es-AR', { timeZone: 'UTC' });
    } else if (type === 'number' && typeof value === 'number') {
        valueText = formatoPeso(value);
    }
    
    let controlHTML = `<div class="value-text">${valueText}</div>`;

    if (editable) {
        if (type === 'select') {
            controlHTML = `<select class="form-select form-select-sm" data-campo="${fieldName}">${options}</select>`;
        } else {
            const inputValue = (type === 'date') ? formatDateForInput(value) : (value || (type === 'number' ? 0 : ''));
            controlHTML = `<input type="${type}" class="form-control form-control-sm" value="${inputValue}" data-campo="${fieldName}">`;
        }
    }
    return `<strong>${label}</strong>${controlHTML}`;
}


// En: pedidos_lista.js
function generarTablaProductos(pedido, editable) {
    // SOLUCIÓN: Se agregan las clases a los th para controlar su ancho
    let tablaHTML = `<h6 class="section-title">Productos</h6><div class="table-responsive"><table class="table-pedidos tabla-productos"><thead><tr><th class="col-proveedor">Proveedor</th><th class="col-producto">Producto</th><th class="col-sku">SKU</th><th class="col-precio">Venta Unit.</th><th class="col-cant">Cant.</th><th class="col-estado">Estado</th><th class="col-cambio">Cambio</th>${editable ? '<th class="col-accion"></th>' : ''}</tr></thead><tbody>`;
    
    (pedido.productos || []).forEach((pr, idx) => {
        const estadoProducto = pr.estado_producto || 'PARA HACER';
        // SOLUCIÓN: Se restaura el color de fondo de la fila
        const colorFila = productStatusColors[estadoProducto] || 'transparent';
        
        // SOLUCIÓN: Se agregan las clases a los td para controlar su ancho
        tablaHTML += `<tr data-index="${idx}" style="background-color: ${colorFila};">
            <td class="col-proveedor"><select data-prod="proveedor" class="form-select form-select-sm" ${editable ? '' : 'disabled'}>${listarProveedores(pr.proveedor)}</select></td>
            <td class="col-producto"><input type="text" class="form-control form-control-sm" data-prod="producto" value="${pr.producto || ''}" ${editable ? '' : 'disabled'}></td>
            <td class="col-sku"><input type="text" class="form-control form-control-sm" data-prod="sku" value="${pr.sku || ''}" ${editable ? '' : 'disabled'}></td>
            <td class="col-precio">${editable ? `<input type="number" step="0.01" class="form-control form-control-sm" data-prod="precio_venta" value="${pr.precio_venta || 0}">` : `<span>${formatoPeso(pr.precio_venta)}</span>`}</td>
            <td class="col-cant">${editable ? `<input type="number" class="form-control form-control-sm" data-prod="cantidad" value="${pr.cantidad || 1}">` : `<span>${pr.cantidad}</span>`}</td>
            <td class="col-estado"><select data-prod="estado_producto" class="form-select form-select-sm" ${editable ? '' : 'disabled'}>${listarEstadosProducto(estadoProducto)}</select></td>
            <td class="col-cambio"><select data-prod="cambio" class="form-select form-select-sm" ${editable ? '' : 'disabled'}><option value="true" ${pr.cambio ? 'selected' : ''}>✅</option><option value="false" ${!pr.cambio ? 'selected' : ''}>❌</option></select></td>
            ${editable ? `<td class="col-accion"><button class="btn btn-sm text-danger p-0" onclick="this.closest('tr').remove(); recalcularTotales(this.closest('.pedido-card'))">✖</button></td>` : ''}
        </tr>`;
    });
    tablaHTML += `</tbody></table></div>`;
    if (editable) {
        tablaHTML += `<button class="btn btn-sm btn-outline-primary mt-2" onclick="agregarFilaProducto(this)"><i class="fas fa-plus me-1"></i> Agregar Producto</button>`;
    }
    return tablaHTML;
}

function generarTablaPagos(pedido, editable) {
    let tablaHTML = `<h6 class="section-title">Pagos</h6><div class="table-responsive"><table class="table table-sm table-pedidos tabla-pagos"><thead><tr><th>Forma</th><th>Monto</th><th>T. Cambio</th><th>Fecha</th>${editable ? '<th></th>' : ''}</tr></thead><tbody>`;
    (pedido.pagos || []).forEach((pg, idx) => {
        let montoDisplay = formatoPeso(pg.monto);
        if(['USD', 'USDT'].includes(pg.metodo)) {
            montoDisplay = `U$S ${(pg.monto || 0).toLocaleString('es-AR', {minimumFractionDigits: 2})}`;
        }
        const isEditableAttr = !editable ? 'disabled' : '';

        tablaHTML += `<tr data-index="${idx}">
            <td><select data-pago="metodo" class="form-select form-select-sm" ${isEditableAttr}>${listarFormasPago(pg.metodo)}</select></td>
            <td>${editable ? `<input type="number" step="0.01" class="form-control form-control-sm" data-pago="monto" value="${pg.monto || 0}">` : `<span>${montoDisplay}</span>`}</td>
            <td>${editable ? `<input type="number" step="0.01" class="form-control form-control-sm" data-pago="tipo_cambio" value="${pg.tipo_cambio || ''}">` : `<span>${pg.tipo_cambio || '-'}</span>`}</td>
            <td>${editable ? `<input type="date" class="form-control form-control-sm" data-pago="fecha" value="${formatDateForInput(pg.fecha)}">` : `<span>${pg.fecha ? new Date(pg.fecha + 'T00:00:00').toLocaleDateString('es-AR', {timeZone: 'UTC'}) : '-'}</span>`}</td>
            ${editable ? `<td><button class="btn btn-sm text-danger p-0" onclick="this.closest('tr').remove(); recalcularTotales(this.closest('.pedido-card'))">✖</button></td>` : ''}
        </tr>`;
    });
    tablaHTML += `</tbody></table></div>`;
    if (editable) {
        tablaHTML += `<button class="btn btn-sm btn-outline-success mt-2" onclick="agregarFilaPago(this)"><i class="fas fa-plus me-1"></i> Agregar Pago</button>`;
    }
    return tablaHTML;
}


// --- SECCIÓN DE LÓGICA DE EDICIÓN ---
function activarEdicion(id) {
    const pedido = pedidosGlobal.find(p => p.id === id);
    const cardNode = document.getElementById(`pedido-card-${id}`);
    if (!cardNode) return;
    
    cardNode.innerHTML = generarHtmlCard(pedido, true);
    
    cardNode.querySelectorAll('input[data-campo], select[data-campo]').forEach(el => {
        el.addEventListener('input', () => recalcularTotales(cardNode));
    });
    cardNode.querySelectorAll('.tabla-productos input, .tabla-productos select, .tabla-pagos input, .tabla-pagos select').forEach(el => {
        el.addEventListener('input', () => recalcularTotales(cardNode));
    });
}

function cancelarEdicion(id) {
    const pedidoOriginal = pedidosGlobal.find(p => p.id === id);
    const cardNode = document.getElementById(`pedido-card-${id}`);
    if (cardNode) {
        cardNode.innerHTML = generarHtmlCard(pedidoOriginal, false);
    }
}

async function guardarEdicion(id) {
    const card = document.getElementById(`pedido-card-${id}`);
    const data = { productos: [], pagos: [] };
    
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

    data.pagos = Array.from(card.querySelectorAll(".tabla-pagos tbody tr")).map(row => ({
        metodo: row.querySelector('[data-pago="metodo"]').value,
        monto: parseFloat(row.querySelector('[data-pago="monto"]').value) || 0,
        tipo_cambio: parseFloat(row.querySelector('[data-pago="tipo_cambio"]').value) || null,
        fecha: row.querySelector('[data-pago="fecha"]').value || null
    }));

    try {
        const res = await fetch(`/pedidos/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
        if (!res.ok) throw new Error('Error al guardar los cambios en el servidor.');
        
        alert("✅ Pedido actualizado correctamente.");
        await cargarYRenderizarPedidos();

    } catch(err) {
        alert(`❌ Error al guardar el pedido. Revise la consola para más detalles.`);
        console.error(err);
    }
}


function recalcularTotales(card) {
    let totalVentaProductos = 0;
    card.querySelectorAll('.tabla-productos tbody tr').forEach(row => {
        const precio = parseFloat(row.querySelector('[data-prod="precio_venta"]').value) || 0;
        const cant = parseInt(row.querySelector('[data-prod="cantidad"]').value) || 1;
        totalVentaProductos += precio * cant;
    });

    const costoEnvio = parseFloat(card.querySelector('[data-campo="costo_envio"]').value) || 0;
    const totalVenta = totalVentaProductos + costoEnvio;

    let totalAbonado = 0;
    card.querySelectorAll('.tabla-pagos tbody tr').forEach(row => {
        let monto = parseFloat(row.querySelector('[data-pago="monto"]').value) || 0;
        if (['USD', 'USDT'].includes(row.querySelector('[data-pago="metodo"]').value)) {
            const tc = parseFloat(row.querySelector('[data-pago="tipo_cambio"]').value) || 1;
            monto *= tc;
        }
        totalAbonado += monto;
    });
    
    card.querySelector(".total-venta").textContent = formatoPeso(totalVenta);
    card.querySelector(".total-abonado").textContent = formatoPeso(totalAbonado);
    card.querySelector(".total-debe").textContent = formatoPeso(totalVenta - totalAbonado);
}

// --- SECCIÓN DE FUNCIONES AUXILIARES ---
function obtenerFechasDelPeriodo() {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    // Corrección de bug de declaración
    let inicio = new Date(hoy);
    let fin = new Date(hoy);
    fin.setHours(23, 59, 59, 999);

    const periodo = document.getElementById("filtroPeriodo").value;

    switch (periodo) {
        case "mes_actual":
            inicio = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
            fin = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0, 23, 59, 59, 999);
            break;
        case "semana_actual":
            const primerDiaSemana = hoy.getDate() - hoy.getDay() + (hoy.getDay() === 0 ? -6 : 1);
            inicio = new Date(hoy.getFullYear(), hoy.getMonth(), primerDiaSemana);
            fin = new Date(inicio);
            fin.setDate(inicio.getDate() + 6);
            fin.setHours(23, 59, 59, 999);
            break;
        case "dia_actual":
            // 'inicio' y 'fin' ya están seteados para hoy por defecto
            break;
        case "personalizado":
            const fechaInicioStr = document.getElementById("fechaInicio").value;
            const fechaFinStr = document.getElementById("fechaFin").value;
            inicio = fechaInicioStr ? new Date(fechaInicioStr + 'T00:00:00') : new Date('1970-01-01');
            fin = fechaFinStr ? new Date(fechaFinStr + 'T23:59:59') : new Date('2999-12-31');
            break;
        default: // "Todos"
             inicio = new Date('1970-01-01');
             fin = new Date('2999-12-31');
    }
    return { inicio, fin };
}

function togglePeriodoPersonalizado() {
    const display = document.getElementById("filtroPeriodo").value === "personalizado" ? "flex" : "none";
    document.getElementById("periodoPersonalizado").style.display = display;
}

function popularFiltrosDelModal() {
    const modalFiltroEstado = document.getElementById("modalFiltroEstado");
    const modalFiltroProveedor = document.getElementById("modalFiltroProveedor");
    if(!modalFiltroEstado || !modalFiltroProveedor) return;
    
    modalFiltroEstado.innerHTML = '<option value="">-- Todos los Estados --</option>' + [...estadosProductoUnicos].sort().map(e => `<option value="${e}">${e}</option>`).join('');
    modalFiltroProveedor.innerHTML = '<option value="">-- Todos los Proveedores --</option>' + [...proveedoresUnicos].sort().map(e => `<option value="${e}">${e}</option>`).join('');
}

// Reemplaza tu función renderizarProductosEnModal por esta
function renderizarProductosEnModal() {
    // SOLUCIÓN: Se obtienen los valores de TODOS los filtros del modal
    const estadoFiltro = document.getElementById("modalFiltroEstado").value;
    const proveedorFiltro = document.getElementById("modalFiltroProveedor").value;
    const { inicio, fin } = obtenerFechasDelPeriodoModal(); // <-- Se usa la nueva función de fechas
    
    const tbody = document.getElementById("modalTablaProductosBody");
    if(!tbody) return;
    
    let productosFiltrados = [];
    pedidosGlobal.forEach(pedido => {
        // SOLUCIÓN: Se añade la validación por fecha
        const fechaPedido = new Date(pedido.fecha_emision + 'T00:00:00');
        const pasaFiltroFecha = (fechaPedido >= inicio && fechaPedido <= fin);

        if (pasaFiltroFecha) {
            (pedido.productos || []).forEach(prod => {
                const pasaFiltroEstado = !estadoFiltro || prod.estado_producto === estadoFiltro;
                const pasaFiltroProveedor = !proveedorFiltro || prod.proveedor === proveedorFiltro;
                
                if (pasaFiltroEstado && pasaFiltroProveedor) {
                    productosFiltrados.push({ ...prod, numero_pedido: pedido.numero, pedido_id: pedido.id });
                }
            });
        }
    });

    let montoTotalFiltrado = 0;
    tbody.innerHTML = productosFiltrados.map(p => {
        montoTotalFiltrado += (p.cantidad || 1) * (p.precio_venta || 0);
        return `
            <tr>
                <td><span class="badge bg-primary">${p.numero_pedido}</span></td>
                <td>${p.cantidad}</td>
                <td>${p.producto}</td>
                <td>${p.proveedor || 'N/A'}</td>
                <td><select class="form-select form-select-sm" data-pedido-id="${p.pedido_id}" data-producto-id="${p.id}" onchange="actualizarEstadoProductoDesdeModal(this)">${listarEstadosProducto(p.estado_producto)}</select></td>
                <td>${formatoPeso(p.precio_venta)}</td>
            </tr>
        `;
    }).join('');
    
    document.getElementById("modalTotalProductos").textContent = productosFiltrados.length;
    document.getElementById("modalMontoTotal").textContent = formatoPeso(montoTotalFiltrado);
}

async function actualizarEstadoProductoDesdeModal(selectElement) {
    const pedidoId = parseInt(selectElement.dataset.pedidoId);
    const productoId = parseInt(selectElement.dataset.productoId);
    const nuevoEstado = selectElement.value;

    try {
        const response = await fetch(`/pedidos/producto/${productoId}/estado`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ estado: nuevoEstado })
        });
        if (!response.ok) throw new Error("Falló la actualización en el servidor.");
        
        const pedido = pedidosGlobal.find(p => p.id === pedidoId);
        const producto = pedido?.productos.find(prod => prod.id === productoId);
        if(producto) producto.estado_producto = nuevoEstado;

        console.log(`Estado del producto ${productoId} actualizado a ${nuevoEstado}.`);
        aplicarFiltros();

    } catch (error) {
        console.error("Error al actualizar estado desde modal:", error);
        alert("No se pudo guardar el cambio.");
        cargarYRenderizarPedidos();
    }
}

function agregarFilaProducto(btn) {
    const tbody = btn.closest('.pedido-body').querySelector('.tabla-productos tbody');
    const nuevaFila = document.createElement('tr');
    nuevaFila.dataset.index = Date.now();
    nuevaFila.style.backgroundColor = productStatusColors['PARA HACER'];
    nuevaFila.innerHTML = `
        <td><select data-prod="proveedor" class="form-select form-select-sm">${listarProveedores()}</select></td>
        <td><input type="text" data-prod="producto" class="form-control form-control-sm" value=""></td>
        <td><input type="text" data-prod="sku" class="form-control form-control-sm" value=""></td>
        <td><input type="number" step="0.01" data-prod="precio_venta" class="form-control form-control-sm" value="0"></td>
        <td><input type="number" data-prod="cantidad" class="form-control form-control-sm" value="1"></td>
        <td><select data-prod="estado_producto" class="form-select form-select-sm">${listarEstadosProducto("PARA HACER")}</select></td>
        <td><select data-prod="cambio" class="form-select form-select-sm"><option value="true">✅</option><option value="false" selected>❌</option></select></td>
        <td><button class="btn btn-sm text-danger p-0" onclick="this.closest('tr').remove(); recalcularTotales(this.closest('.pedido-card'))">✖</button></td>`;
    tbody.appendChild(nuevaFila);
    nuevaFila.querySelectorAll('input, select').forEach(el => el.addEventListener('input', () => recalcularTotales(btn.closest('.pedido-card'))));
}

function agregarFilaPago(btn) {
    const tbody = btn.closest('.pedido-body').querySelector('.tabla-pagos tbody');
    const hoy = new Date().toISOString().split('T')[0];
    const nuevaFila = document.createElement('tr');
    nuevaFila.dataset.index = Date.now();
    nuevaFila.innerHTML = `
        <td><select data-pago="metodo" class="form-select form-select-sm">${listarFormasPago()}</select></td>
        <td><input type="number" step="0.01" data-pago="monto" class="form-control form-control-sm" value="0"></td>
        <td><input type="number" step="0.01" data-pago="tipo_cambio" class="form-control form-control-sm" value=""></td>
        <td><input type="date" data-pago="fecha" class="form-control form-control-sm" value="${hoy}"></td>
        <td><button class="btn btn-sm text-danger p-0" onclick="this.closest('tr').remove(); recalcularTotales(this.closest('.pedido-card'))">✖</button></td>`;
    tbody.appendChild(nuevaFila);
    nuevaFila.querySelectorAll('input, select').forEach(el => el.addEventListener('input', () => recalcularTotales(btn.closest('.pedido-card'))));
}

async function eliminarPedido(id) {
    const pedido = pedidosGlobal.find(p => p.id === id);
    if (!pedido) return;
    if (!confirm(`¿Estás seguro de que quieres eliminar el Pedido Nº ${pedido.numero}? Esta acción no se puede deshacer.`)) return;
    try {
        const res = await fetch(`/pedidos/${id}`, { method: 'DELETE' });
        if (res.ok) {
            alert('✅ Pedido eliminado con éxito.');
            document.getElementById(`pedido-card-${id}`).remove();
            pedidosGlobal = pedidosGlobal.filter(p => p.id !== id);
            aplicarFiltros();
        } else {
            const errorTexto = await res.text();
            throw new Error(errorTexto || `Error del servidor: ${res.status}`);
        }
    } catch (err) {
        alert(`❌ Error al eliminar: ${err.message}`);
        console.error(err);
    }
}

function popularFiltroEstadoGeneral() {
    const select = document.getElementById('filtroEstado');
    if (!select) return;
    const estados = Object.keys(statusColors);
    select.innerHTML = '<option value="">-- Filtrar por Estado General --</option>'; // Limpiar
    estados.forEach(estado => {
        const option = document.createElement('option');
        option.value = estado;
        option.textContent = estado;
        select.appendChild(option);
    });
}

function generarConstancia(id) { window.open(`/pedidos/${id}/constancia_entrega`, "_blank"); }
function avisarPedido(tel, num) { if(!tel) {alert("El cliente no tiene un teléfono cargado."); return;} const m = `¡Hola! Tu pedido N°${num} está listo para retirar.`; window.open(`https://wa.me/549${tel}?text=${encodeURIComponent(m)}`, "_blank"); }
async function subirFactura(id, event) { const file = event.target.files[0]; if (!file) return; const formData = new FormData(); formData.append("factura", file); try { const res = await fetch(`/pedidos/${id}/factura`, { method: "POST", body: formData }); const data = await res.json(); alert(data.mensaje || data.error); if(res.ok) { const p = pedidosGlobal.find(p => p.id === id); if(p) p.factura_base64 = 'true'; cancelarEdicion(id); } } catch(err){ alert('Error al subir archivo'); console.error(err); }}
function formatearFechaHora(iso) { if (!iso) return "-"; return new Date(iso).toLocaleString("es-AR", { day: '2-digit', month: '2-digit', year: 'numeric', hour: "2-digit", minute: "2-digit" }); }
function formatoPeso(n) { return (parseFloat(n) || 0).toLocaleString("es-AR", { style: "currency", currency: "ARS" }); }
function formatDateForInput(dateString) { if (!dateString) return ''; try { const date = new Date(dateString); return isNaN(date.getTime()) ? '' : date.toISOString().split('T')[0]; } catch(e) { return ''; } }

// Funciones que retornan listas de opciones para los <select>
function listarProveedores(sel) { const p = ["TBD","AIR", "COMPRA GAMER", "FULL HARD", "GOLDENTECH", "INVID", "SENTEY", "LIONTECH", "MALDITO HARD", "MAXIMUS", "MERCADO LIBRE", "PC ARTS", "ROCKETHARD", "SLOT ONE", "SOLUTION BOX", "SOUNDTEC", "ALE", "NOSOTROS", "HYPERGAMING", "COMPUTODO", "CDKEYOFFER", "MUNDO HARDWARE", "NOXIE", "ACUARIO", "REPE", "MGM GAMES", "MEXX", "HYDRAXTREME", "PEAK COMPUTACION", "GAMERS POINT", "ECLIPSE COMPUTACION", "SCP HARDSTORE", "ARMYTECH", "GPU USADA", "SPACE", "NEW TREE", "MEGASOFT", "GEZATEK", "WIZ TECH", "GAMING CITY", "31STORE", "GRUPO NUCLEO", "MINING STORE", "HARD CORE", "NEW BYTES", "MYM COMPUTACION", "XT-PC", "ELECTROOMBU", "TGS", "DATASOFT", "HFTECNOLOGIA", "URANO STREAM", "LUCAS", "JUAMPI", "TRYHARDWARE", "SERGIO", "MIMI TECH", "TURTECH", "INTEGRADOS ARGENTINOS", "GVGMALL", "LOGG", "SANTY", "SANTY (ABUELO)", "HARDLOOTS", "GONZA", "G2A", "CUCHU", "CLICK AREQUITO", "BLACK", "MGM GAMERS", "EMA", "GAUSS", "OVERTECH", "VENEX", "TGS (WEB)", "COMPUGARDEN", "CLIENTE", "IGNATECH", "SOLARMAX", "VRACER", "REPARACION TGS", "CROSSHAIR", "GN POINT", "DISTECNA", "INTERMACO", "CEVEN", "GAMING POINT", "KATECH", "ROYALECDKEY", "THIAGO", "RMINSUMOS", "USABAIRES"]; return p.map(pv => `<option value="${pv}" ${pv === sel ? "selected" : ""}>${pv}</option>`).join(""); }
function listarEstadosProducto(sel) { const e = ["FALTAN ENVIOS", "PARA HACER", "LISTO", "ENTREGADO", "GARANTIA", "PEDIDO", "REVISADO", "CANCELADO", "EN LA OFICINA", "EN OTRO LOCAL", "NO COBRADO", "PROBLEMAS"]; return e.map(st => `<option value="${st}" ${st === sel ? "selected" : ""}>${st}</option>`).join("");}
function listarEstadosPedido(sel) { const e = ["EN PROCESO", "PARA HACER", "LISTO", "ENTREGADO", "CANCELADO", "RMA", "SERVICIO TECNICO"]; return e.map(st => `<option value="${st}" ${st === sel ? "selected" : ""}>${st}</option>`).join("");}
function listarFormasPago(sel) { const f = ["EFECTIVO", "MERCADO PAGO", "TRANSFERENCIA", "USD", "USDT", "PAGO EN TIENDA", "TARJETA", "CUENTA DNI", "CRÉDITO", "OTROS"]; return f.map(fp => `<option value="${fp}" ${fp === sel ? "selected" : ""}>${fp}</option>`).join("");}
function listarVendedores(sel) { const v = ["Santy", "Lucas", "Thiago", "Repe", "Ale"]; return v.map(vnd => `<option value="${vnd}" ${vnd === sel ? "selected" : ""}>${vnd}</option>`).join("");}
function listarEnvios(sel) { const e = ["MOTO", "DROPSHIPPING", "ANDREANI", "RETIRA"]; return e.map(env => `<option value="${env.toUpperCase()}" ${env.toUpperCase() === sel ? "selected" : ""}>${env}</option>`).join("");}
function listarTiposFactura(sel) { const f = ["NA", "Factura A", "Factura B"]; return f.map(fac => `<option value="${fac}" ${fac === sel ? "selected" : ""}>${fac === 'NA' ? 'Sin Factura' : fac}</option>`).join("");}

// Agrega esta nueva función en cualquier parte de la sección de "Funciones Auxiliares"
function obtenerFechasDelPeriodoModal() {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    let inicio = new Date(hoy);
    let fin = new Date(hoy);
    fin.setHours(23, 59, 59, 999);

    const periodo = document.getElementById("modalFiltroPeriodo").value;

    switch (periodo) {
        case "mes_actual":
            inicio = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
            fin = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0, 23, 59, 59, 999);
            break;
        case "semana_actual":
            const primerDiaSemana = hoy.getDate() - hoy.getDay() + (hoy.getDay() === 0 ? -6 : 1);
            inicio = new Date(hoy.getFullYear(), hoy.getMonth(), primerDiaSemana);
            fin = new Date(inicio);
            fin.setDate(inicio.getDate() + 6);
            fin.setHours(23, 59, 59, 999);
            break;
        case "dia_actual":
            break; // 'inicio' y 'fin' ya están seteados para hoy
        case "personalizado":
            const fechaInicioStr = document.getElementById("modalFechaInicio").value;
            const fechaFinStr = document.getElementById("modalFechaFin").value;
            inicio = fechaInicioStr ? new Date(fechaInicioStr + 'T00:00:00') : new Date('1970-01-01');
            fin = fechaFinStr ? new Date(fechaFinStr + 'T23:59:59') : new Date('2999-12-31');
            break;
        default: // "Todos"
             inicio = new Date('1970-01-01');
             fin = new Date('2999-12-31');
    }
    return { inicio, fin };
}

// Agrega esta nueva función
function togglePeriodoPersonalizadoModal() {
    const display = document.getElementById("modalFiltroPeriodo").value === "personalizado" ? "flex" : "none";
    document.getElementById("modalPeriodoPersonalizado").style.display = display;
}