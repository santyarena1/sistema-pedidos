// Variable global para saber en qué producto estamos trabajando en los modales
let productoSeleccionado = null;
let snEgresoList = [];

/**
 * [NUEVO] Formatea un número al estilo de moneda argentina (ARS).
 * @param {number} numero El número a formatear.
 * @returns {string} El número formateado como un precio.
 */
function formatoPrecioARS(numero) {
    const numeroLimpio = parseFloat(numero) || 0;
    return new Intl.NumberFormat('es-AR', {
        style: 'currency', currency: 'ARS', minimumFractionDigits: 2, maximumFractionDigits: 2
    }).format(numeroLimpio);
}

// --- AGREGA ESTA VARIABLE GLOBAL ---
let currentSort = {
    by: 'nombre',
    order: 'asc'
};

document.getElementById('modalEgresoRapido').addEventListener('show.bs.modal', () => {
    snEgresoList = [];
    document.getElementById('tabla-egreso-items').innerHTML = '';
    document.getElementById('lectorSnEgreso').value = '';
});

// Capturamos el Enter en el lector de SN
document.getElementById('lectorSnEgreso').addEventListener('keydown', async (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        const sn = event.target.value.trim();
        if (!sn) return;
        // Validamos que no esté ya en la lista
        if (snEgresoList.find(item => item.serial_number === sn)) {
            alert('Ese SN ya está en la lista.');
            event.target.value = '';
            return;
        }
        try {
            const resp = await fetch(`/api/stock/items/sn/${sn}`);
            const data = await resp.json();
            if (!resp.ok) {
                alert(data.error);
            } else {
                snEgresoList.push(data); // data contiene id, serial_number, producto, estado
                renderTablaEgreso();
            }
        } catch (err) {
            console.error(err);
            alert('Error al buscar el SN.');
        } finally {
            event.target.value = '';
        }
    }
});

document.addEventListener("DOMContentLoaded", () => {
    poblarFiltros();
    cargarProductos();

    // Listeners para filtros y ordenamiento
    document.getElementById('filtro-marca').addEventListener('change', cargarProductos);
    document.getElementById('filtro-categoria').addEventListener('change', cargarProductos);
    document.getElementById('filtro-deposito').addEventListener('change', cargarProductos);
    document.getElementById('filtro-disponibles').addEventListener('change', cargarProductos);
    document.getElementById('btn-limpiar-filtros').addEventListener('click', limpiarFiltros);
    document.getElementById('buscador-general').addEventListener('input', cargarProductos);

    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', function() {
            const sortBy = this.dataset.sort;
            if (currentSort.by === sortBy) {
                currentSort.order = currentSort.order === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.by = sortBy;
                currentSort.order = 'asc';
            }
            cargarProductos();
        });
    });

    // Eventos para el lector de SKU y las acciones asociadas
    document.getElementById('lectorSku').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            buscarPorSku();
        }
    });
    document.getElementById('btnEgresarSku').addEventListener('click', egresarPorSku);
    document.getElementById('btnExportarExcel').addEventListener('click', exportarStock);
    document.getElementById('btnImportarExcel').addEventListener('click', () => {
        document.getElementById('archivoExcelInput').click();
    });
    document.getElementById('archivoExcelInput').addEventListener('change', importarStock);
});

//--- FUNCIONES DE LA VISTA PRINCIPAL (TIPOS DE PRODUCTO) ---
async function cargarProductos() {
    const params = new URLSearchParams();
    const marca = document.getElementById('filtro-marca').value;
    const categoria = document.getElementById('filtro-categoria').value;
    const deposito = document.getElementById('filtro-deposito').value;
    const disponibles = document.getElementById('filtro-disponibles').checked;
    const busqueda = document.getElementById('buscador-general').value;
    if (busqueda) {
        params.append('q', busqueda);
    }

    if (marca) params.append('marca', marca);
    if (categoria) params.append('categoria', categoria);
    if (deposito) params.append('deposito', deposito);
    if (disponibles) params.append('disponibles', 'true');
    
    params.append('sortBy', currentSort.by);
    params.append('sortOrder', currentSort.order);
    
    const url = `/api/stock/productos?${params.toString()}`;
    const tbody = document.getElementById('tabla-stock-productos');
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Cargando...</span></div></td></tr>';

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Error de red al cargar productos.');
        
        const productos = await response.json();
        tbody.innerHTML = '';

        if (productos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">No se encontraron productos con los filtros seleccionados.</td></tr>';
        } else {
            productos.forEach(p => {
                const fechaModif = p.ultima_modificacion ? new Date(p.ultima_modificacion).toLocaleString('es-AR') : '-';
                const nombreEscapado = p.nombre.replace(/'/g, "\\'");
                const precioFormateado = formatoPrecioARS(p.precio_venta_sugerido);
                tbody.innerHTML += `
                    <tr id="producto-row-${p.id}">
                        <td>${p.sku || 'N/A'}</td>
                        <td><strong>${p.nombre}</strong></td>
                        <td>${p.marca || 'N/A'}</td>
                        <td>${p.categoria || 'N/A'}</td>
                        <td class="text-center"><span class="badge bg-primary rounded-pill fs-6">${p.cantidad_disponible || 0}</span></td>
                        <td>${precioFormateado}</td>
                        <td>${fechaModif}</td>
                        <td class="text-end">
                            <button class="btn btn-sm btn-outline-secondary btn-accion" title="Editar Producto" onclick='abrirModalEditarProducto(${JSON.stringify(p)})'><i class="fas fa-edit"></i></button>
                            <button class="btn btn-sm btn-outline-primary btn-accion ms-1" title="Gestionar Items" onclick="abrirModalItems(${p.id}, '${nombreEscapado}')"><i class="fas fa-barcode"></i></button>
                            <button class="btn btn-sm btn-outline-info btn-accion ms-1" title="Imprimir Etiquetas" onclick="imprimirEtiquetas(${p.id})"><i class="fas fa-print"></i></button>
                            <button class="btn btn-sm btn-outline-danger btn-accion ms-1" title="Eliminar Producto" onclick="eliminarProducto(${p.id}, '${nombreEscapado}')"><i class="fas fa-trash-alt"></i></button>
                        </td>
                    </tr>
                `;
            });
        }
        actualizarIconosSort();
        mostrarFiltrosActivos();
    } catch (error) {
        console.error("Error en cargarProductos:", error);
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger py-4">Error al cargar los productos. Revise la consola.</td></tr>';
    }
}

function renderTablaEgreso() {
    const tbody = document.getElementById('tabla-egreso-items');
    tbody.innerHTML = '';
    snEgresoList.forEach((item, index) => {
        tbody.innerHTML += `
            <tr>
                <td>${item.serial_number}</td>
                <td>${item.producto}</td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="quitarSnDeEgreso(${index})">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </td>
            </tr>`;
    });
}

function quitarSnDeEgreso(idx) {
    snEgresoList.splice(idx, 1);
    renderTablaEgreso();
}

// Confirma el egreso de todos los SN de la lista
document.getElementById('btnConfirmarEgreso').addEventListener('click', async () => {
    if (snEgresoList.length === 0) {
        alert('No hay items para egresar.');
        return;
    }
    const motivo = prompt('Motivo del egreso (VENTA, DEVOLUCIÓN, MERMA, etc.):', 'VENTA') || 'VENTA';
    const serial_numbers = snEgresoList.map(item => item.serial_number);
    try {
        const resp = await fetch('/api/stock/items/salida', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ serial_numbers, motivo })
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || 'Error al egresar');
        alert(`Se egresaron ${data.items} items.`);
        // Refrescamos la interfaz y vaciamos la lista
        snEgresoList = [];
        renderTablaEgreso();
        cargarProductos();
        abrirModalHistorial();
        // Cerramos el modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalEgresoRapido'));
        modal.hide();
    } catch (err) {
        console.error(err);
        alert(err.message);
    }
});


async function eliminarProducto(productoId, nombreProducto) {
    if (!confirm(`¿Estás seguro de que quieres eliminar "${nombreProducto}"?\n\n¡ATENCIÓN! Se borrarán todos sus items y números de serie asociados.`)) return;
    
    try {
        const response = await fetch(`/api/stock/productos/${productoId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error("El servidor no pudo eliminar el producto.");
        
        cargarProductos();
        abrirModalHistorial(); // Actualizamos el historial para ver el cambio
    } catch (error) {
        console.error("Error en eliminarProducto:", error);
        alert("No se pudo eliminar el producto.");
    }
}

//--- FUNCIONES PARA EL MODAL DE AGREGAR/EDITAR TIPO DE PRODUCTO ---
async function poblarSelect(selectId, tipoConfig, valorSeleccionado = '') {
    const select = document.getElementById(selectId);
    select.innerHTML = '<option value="">Seleccione...</option>';
    const response = await fetch(`/api/config/stock/${tipoConfig}`);
    const items = await response.json();
    items.forEach(item => {
        const esSeleccionado = item.nombre === valorSeleccionado ? 'selected' : '';
        select.innerHTML += `<option value="${item.nombre}" ${esSeleccionado}>${item.nombre}</option>`;
    });
}

async function abrirModalNuevoProducto() {
    document.getElementById('modalProductoTitle').textContent = 'Agregar Nuevo Tipo de Producto';
    document.getElementById('editProductId').value = '';
    document.getElementById('nuevoSku').value = '';
    document.getElementById('nuevoNombre').value = '';
    document.getElementById('nuevoPrecio').value = '';
    
    await poblarSelect('nuevaMarca', 'marcas');
    await poblarSelect('nuevaCategoria', 'categorias');
    
    const modal = new bootstrap.Modal(document.getElementById('modalAgregarProducto'));
    modal.show();
}

async function abrirModalEditarProducto(producto) {
    document.getElementById('modalProductoTitle').textContent = 'Editar Producto';
    document.getElementById('editProductId').value = producto.id;
    document.getElementById('nuevoSku').value = producto.sku;
    document.getElementById('nuevoNombre').value = producto.nombre;
    document.getElementById('nuevoPrecio').value = parseFloat(producto.precio_venta_sugerido || 0).toFixed(2);

    await poblarSelect('nuevaMarca', 'marcas', producto.marca);
    await poblarSelect('nuevaCategoria', 'categorias', producto.categoria);
    
    const modal = new bootstrap.Modal(document.getElementById('modalAgregarProducto'));
    modal.show();
}

async function guardarProducto() {
    const productoId = document.getElementById('editProductId').value;
    const esEdicion = !!productoId;

    const payload = {
        sku: document.getElementById('nuevoSku').value.trim(),
        nombre: document.getElementById('nuevoNombre').value.trim(),
        marca: document.getElementById('nuevaMarca').value,
        categoria: document.getElementById('nuevaCategoria').value,
        precio_venta_sugerido: parseFloat(document.getElementById('nuevoPrecio').value) || 0
    };

    if (!payload.nombre) {
        return alert("El nombre del producto es obligatorio.");
    }
    
    const url = esEdicion ? `/api/stock/productos/${productoId}` : '/api/stock/productos';
    const method = esEdicion ? 'PATCH' : 'POST';

    await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    // Cerramos el modal de alta/edición
    bootstrap.Modal.getInstance(document.getElementById('modalAgregarProducto')).hide();

    // Recargamos la lista de productos
    cargarProductos();

    // Ya no abrimos el historial automáticamente
    // abrirModalHistorial();
}


//--- FUNCIONES PARA LECTOR DE CÓDIGO DE BARRAS ---
async function buscarPorSku() {
    const sku = document.getElementById('lectorSku').value.trim();
    const panelAccion = document.getElementById('panelAccionSku');
    const alerta = document.getElementById('alertaSku');

    if (!sku) {
        panelAccion.classList.add('d-none');
        alerta.classList.add('d-none');
        return;
    }

    try {
        const response = await fetch(`/api/stock/sku/${sku}`);
        const producto = await response.json();

        if (!response.ok) throw new Error(producto.error || "Producto no encontrado.");
        
        productoSeleccionado = producto; 
        document.getElementById('nombreProductoSku').textContent = producto.nombre;
        alerta.classList.add('d-none');
        panelAccion.classList.remove('d-none');
    } catch (error) {
        productoSeleccionado = null;
        alerta.textContent = error.message;
        alerta.classList.remove('d-none');
        panelAccion.classList.add('d-none');
    }
}

function ingresarStockPorSku() {
    if (!productoSeleccionado) return;
    const serial_number = prompt(`Ingresa el Número de Serie (SN) para:\n${productoSeleccionado.nombre}`);
    if (serial_number && serial_number.trim()) {
        const costo = prompt("Ingresa el costo del item (opcional):");
        guardarNuevosItems(productoSeleccionado.id, [serial_number.trim()], costo);
    }
}

function verItemsPorSku() {
    if (!productoSeleccionado) return;
    abrirModalItems(productoSeleccionado.id, productoSeleccionado.nombre);
}

// REEMPLAZA tu función abrirModalItems en: static/js/stock.js

async function abrirModalItems(productoId, nombreProducto) {
    productoSeleccionado = { id: productoId, nombre: nombreProducto };
    document.getElementById('nombreProductoEnModal').textContent = nombreProducto;
    await poblarSelect('nuevoDepositoItem', 'depositos');

    try {
        const response = await fetch(`/api/stock/productos/${productoId}/items`);
        const items = await response.json();
        const tbody = document.getElementById('tabla-items-individuales');
        tbody.innerHTML = '';

        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Aún no hay items individuales para este producto.</td></tr>';
        } else {
            items.forEach(item => {
                const fechaModif = item.ultima_modificacion ? new Date(item.ultima_modificacion).toLocaleString('es-AR') : '-';
                const itemString = JSON.stringify(item).replace(/'/g, "\\'");

                tbody.innerHTML += `
                    <tr>
                        <td>${item.id}</td>
                        <td>${item.serial_number || 'N/A'}</td>
                        <td><span class="badge estado-${(item.estado || 'N/A').toLowerCase().replace(' ', '-')}">${item.estado || 'N/A'}</span></td>
                        <td>${formatoPrecioARS(item.costo)}</td>
                        <td>${item.deposito || 'N/A'}</td>
                        <td>${fechaModif}</td>
                        <td class="text-end">
                            <button class="btn btn-sm btn-outline-secondary py-0 px-1" title="Editar Item" onclick='editarItem(${itemString})'><i class="fas fa-edit"></i></button>
                            <button class="btn btn-sm btn-outline-danger py-0 px-1 ms-1" title="Eliminar Item" onclick="eliminarItem(${item.id}, '${item.serial_number}')"><i class="fas fa-trash-alt"></i></button>
                        </td>
                    </tr>`;
            });
        }

        const modal = new bootstrap.Modal(document.getElementById('modalVerItems'));
        modal.show();

    } catch (error) {
        console.error("Error al cargar los items individuales:", error);
    }
}



// REEMPLAZA tu función guardarNuevosItems en: static/js/stock.js

async function guardarNuevosItems() {
    const snsTexto = document.getElementById('nuevosSns').value.trim();
    if (!snsTexto) {
        return alert("Debes ingresar al menos un número de serie.");
    }

    const serial_numbers = snsTexto.split('\n').map(sn => sn.trim()).filter(sn => sn);
    if (serial_numbers.length === 0) {
        return alert("Debes ingresar al menos un número de serie válido.");
    }

    const payload = {
        producto_id: productoSeleccionado.id,
        serial_numbers: serial_numbers,
        costo: parseFloat(document.getElementById('nuevoCosto').value) || 0,
        deposito: document.getElementById('nuevoDepositoItem').value
    };

    try {
        const response = await fetch('/api/stock/items', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error('El servidor no pudo guardar los items.');
        }

        document.getElementById('nuevosSns').value = '';
        document.getElementById('nuevoCosto').value = '';

        abrirModalItems(productoSeleccionado.id, productoSeleccionado.nombre);
        cargarProductos();

    } catch (error) {
        console.error("Error al guardar nuevos items:", error);
        alert("No se pudieron guardar los nuevos items.");
    }
}

//--- FUNCIÓN PARA EL HISTORIAL DE MOVIMIENTOS ---
/**
 * [REVISADO] Carga y muestra el historial de movimientos en su modal.
 */
async function abrirModalHistorial() {
    try {
        const response = await fetch('/api/stock/historial');
        if (!response.ok) {
            throw new Error('No se pudo obtener la respuesta del servidor para el historial.');
        }

        const historial = await response.json();
        const tbody = document.getElementById('tabla-historial-body');
        tbody.innerHTML = ''; // Limpiamos la tabla

        if (historial.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Aún no hay movimientos registrados.</td></tr>';
        } else {
            historial.forEach(mov => {
                const fecha = new Date(mov.fecha).toLocaleString('es-AR');
                // Si detalles es un objeto, lo mostramos bonito, si no, como texto.
                const detalles = typeof mov.detalles === 'object' ? JSON.stringify(mov.detalles) : mov.detalles;
                tbody.innerHTML += `
                    <tr>
                        <td>${fecha}</td>
                        <td><span class="badge bg-secondary">${mov.accion}</span></td>
                        <td>${mov.producto_nombre}</td>
                        <td>${detalles}</td>
                    </tr>
                `;
            });
        }
        
        // Abrimos el modal
        const modal = new bootstrap.Modal(document.getElementById('modalHistorial'));
        modal.show();

    } catch (error) {
        console.error("Error al cargar historial:", error);
        alert("No se pudo cargar el historial de movimientos.");
    }
}


// --- FUNCIONES PARA EL MODAL DE CONFIGURACIÓN ---
const modalConfigStock = document.getElementById('modalConfiguracionStock');
if (modalConfigStock) {
    modalConfigStock.addEventListener('show.bs.modal', () => {
        cargarConfig('marca');
        cargarConfig('categoria');
        cargarConfig('deposito');
    });
}

/**
 * Carga la lista de un tipo de configuración en su respectivo <ul>.
 */
async function cargarConfig(tipo) {
    try {
        // Le agregamos la 's' para que coincida con la ruta del backend (ej: /api/config/stock/marcas)
        const response = await fetch(`/api/config/stock/${tipo}s`);
        if (!response.ok) {
            console.error(`No se pudo cargar la configuración de ${tipo}.`);
            return;
        }
        
        const data = await response.json();
        // Buscamos la lista correcta (ej: lista-marcas)
        const ul = document.getElementById(`lista-${tipo}s`);
        ul.innerHTML = ''; // Limpiamos la lista antes de llenarla
        data.forEach(item => {
            ul.innerHTML += `<li class="list-group-item">${item.nombre}</li>`;
        });
    } catch (error) {
        console.error(`Error en la función cargarConfig para '${tipo}':`, error);
    }
}



/**
 * [CORREGIDO] Agrega un nuevo elemento de configuración (marca, categoría o depósito).
 */
async function agregarConfig(tipo) {
    // La corrección clave está aquí: se usan acentos graves (`) para crear el ID dinámicamente.
    const input = document.getElementById(`nueva-${tipo}`);
    
    // Verificamos que el input exista para evitar errores.
    if (!input) {
        console.error(`Error: No se encontró el elemento con ID 'nueva-${tipo}'.`);
        return;
    }
    
    const nombre = input.value.trim();
    if (!nombre) {
        alert('El nombre no puede estar vacío.');
        return;
    }

    try {
        const response = await fetch(`/api/config/stock/${tipo}s`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nombre: nombre })
        });

        if (response.ok) {
            input.value = ''; // Limpiamos el input al tener éxito
            // La función de abajo se asegura de recargar la lista correcta
            await cargarConfig(tipo); 
        } else {
            const errorData = await response.json();
            alert(`Error al agregar: ${errorData.error || 'Ocurrió un problema en el servidor.'}`);
        }
    } catch (error) {
        console.error(`Error en la función agregarConfig para '${tipo}':`, error);
        alert('No se pudo conectar con el servidor.');
    }
}


/**
 * [REESCRITO] Prepara y abre el modal para editar un item individual.
 */
async function editarItem(item) {
    // Guardamos los datos del item que estamos editando
    document.getElementById('editItemId').value = item.id;
    document.getElementById('editItemSn').textContent = item.serial_number;

    // 1. Poblamos el desplegable de Estados
    const selectEstado = document.getElementById('editItemEstado');
    const estados = ['Disponible', 'Vendido', 'Reservado', 'RMA', 'Defectuoso'];
    selectEstado.innerHTML = '';
    estados.forEach(estado => {
        const esSeleccionado = estado === item.estado ? 'selected' : '';
        selectEstado.innerHTML += `<option value="${estado}" ${esSeleccionado}>${estado}</option>`;
    });

    // 2. Poblamos el desplegable de Depósitos usando la función que ya tenemos
    // y seleccionamos el depósito actual del item.
    await poblarSelect('editItemDeposito', 'depositos', item.deposito);

    // 3. Mostramos el modal
    const modal = new bootstrap.Modal(document.getElementById('modalEditarItem'));
    modal.show();
}

/**
 * [NUEVO] Guarda los cambios de un item editado.
 */
async function guardarCambiosItem() {
    const itemId = document.getElementById('editItemId').value;
    
    const payload = {
        estado: document.getElementById('editItemEstado').value,
        deposito: document.getElementById('editItemDeposito').value
    };

    try {
        const response = await fetch(`/api/stock/items/${itemId}`, {
            method: 'PATCH', // Usamos PATCH para actualizar parcialmente
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'El servidor no pudo actualizar el item.');
        }
        
        // Cerramos el modal de edición
        bootstrap.Modal.getInstance(document.getElementById('modalEditarItem')).hide();
        
        // Recargamos el modal principal (el de la lista) y la tabla de productos
        abrirModalItems(productoSeleccionado.id, productoSeleccionado.nombre);
        cargarProductos();

    } catch (error) {
        alert(`Error al actualizar: ${error.message}`);
        console.error(error);
    }
}
/**
 * [NUEVO] Elimina un item individual previa confirmación.
 */
async function eliminarItem(itemId, serialNumber) {
    if (!confirm(`¿Estás seguro de que quieres eliminar el item con SN: "${serialNumber}"?\n\nEsta acción no se puede deshacer.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/stock/items/${itemId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('El servidor no pudo eliminar el item.');
        }

        // Recargamos para ver que el item desapareció.
        abrirModalItems(productoSeleccionado.id, productoSeleccionado.nombre);
        cargarProductos();

    } catch (error) {
        alert("Error al eliminar el item.");
        console.error(error);
    }
}

// --- 2. AGREGA ESTA NUEVA FUNCIÓN (puede ir al final de tu archivo) ---
/**
 * [NUEVO] Llama al backend para generar y mostrar el PDF de etiquetas.
 * @param {number} productoId El ID del producto del cual imprimir etiquetas.
 */
function imprimirEtiquetas(productoId) {
    // Abrimos la URL en una nueva pestaña. El navegador se encargará de mostrar el PDF.
    window.open(`/api/stock/productos/${productoId}/imprimir_etiquetas`, '_blank');
}

// --- 2. AGREGA ESTA NUEVA FUNCIÓN (puede ir junto a la otra de imprimir) ---
/**
 * [NUEVO] Llama al backend para generar y mostrar el PDF de una sola etiqueta.
 * @param {number} itemId El ID del item (SN) específico a imprimir.
 */
function imprimirEtiquetaIndividual(itemId) {
    window.open(`/api/stock/items/${itemId}/imprimir_etiqueta`, '_blank');
}

async function poblarFiltros() {
    const poblarSelect = async (elementId, endpoint) => {
        try {
            const response = await fetch(`/api/stock/${endpoint}`);
            if (!response.ok) return;
            const data = await response.json();
            const select = document.getElementById(elementId);
            data.forEach(item => {
                const option = new Option(item, item);
                select.add(option);
            });
        } catch (error) { console.error(`Error poblando ${endpoint}:`, error); }
    };
    await Promise.all([
        poblarSelect('filtro-marca', 'marcas'),
        poblarSelect('filtro-categoria', 'categorias'),
        poblarSelect('filtro-deposito', 'depositos')
    ]);
}

function limpiarFiltros() {
    document.getElementById('buscador-general').value = '';
    document.getElementById('filtro-marca').value = '';
    document.getElementById('filtro-categoria').value = '';
    document.getElementById('filtro-deposito').value = '';
    document.getElementById('filtro-disponibles').checked = false;
    currentSort = { by: 'nombre', order: 'asc' }; // Opcional: resetear orden al limpiar
    cargarProductos();
}

function mostrarFiltrosActivos() {
    const container = document.getElementById('filtros-activos-container');
    const pillsContainer = document.getElementById('filtros-activos');
    pillsContainer.innerHTML = '';
    let hayFiltros = false;

    const agregarPill = (label, valor, limpiarFn) => {
        if (valor) {
            pillsContainer.innerHTML += `
                <span class="badge bg-primary d-flex align-items-center">
                    ${label}: ${valor}
                    <button type="button" class="btn-close btn-close-white ms-2" style="font-size: 0.6em;" onclick="${limpiarFn}"></button>
                </span>`;
            hayFiltros = true;
        }
    };

    agregarPill('Búsqueda', document.getElementById('buscador-general').value, "limpiarFiltro('buscador-general')");
    agregarPill('Marca', document.getElementById('filtro-marca').value, "limpiarFiltro('filtro-marca')");
    agregarPill('Categoría', document.getElementById('filtro-categoria').value, "limpiarFiltro('filtro-categoria')");
    agregarPill('Depósito', document.getElementById('filtro-deposito').value, "limpiarFiltro('filtro-deposito')");
    
    
    if (document.getElementById('filtro-disponibles').checked) {
        pillsContainer.innerHTML += `
            <span class="badge bg-success d-flex align-items-center">
                Solo con stock
                <button type="button" class="btn-close btn-close-white ms-2" style="font-size: 0.6em;" onclick="limpiarFiltro('filtro-disponibles')"></button>
            </span>`;
        hayFiltros = true;
    }
    container.style.display = hayFiltros ? 'block' : 'none';
}

function limpiarFiltro(elementId) {
    const element = document.getElementById(elementId);
    if (element.type === 'checkbox') { element.checked = false; } 
    else { element.value = ''; }
    
    if (element.type === 'text') { // Esto sirve para el buscador
        element.value = '';
    }
    cargarProductos();
}

function actualizarIconosSort() {
    document.querySelectorAll('.sortable').forEach(header => {
        const sortIcon = header.querySelector('i');
        const column = header.dataset.sort;
        sortIcon.classList.remove('fa-sort', 'fa-sort-up', 'fa-sort-down');
        if (column === currentSort.by) {
            sortIcon.classList.add(currentSort.order === 'asc' ? 'fa-sort-up' : 'fa-sort-down');
        } else {
            sortIcon.classList.add('fa-sort');
        }
    });
}

// AGREGA esta función en: static/js/stock.js

async function buscarPorSku() {
    const sku = document.getElementById('lectorSku').value.trim();
    const panelAccion = document.getElementById('panelAccionSku');
    const alerta = document.getElementById('alertaSku');

    if (!sku) {
        panelAccion.classList.add('d-none');
        alerta.classList.add('d-none');
        return;
    }

    try {
        const response = await fetch(`/api/stock/sku/${sku}`);
        const producto = await response.json();

        if (!response.ok) throw new Error(producto.error || "Producto no encontrado.");

        productoSeleccionado = producto;
        document.getElementById('nombreProductoSku').textContent = producto.nombre;
        alerta.classList.add('d-none');
        panelAccion.classList.remove('d-none');
    } catch (error) {
        productoSeleccionado = null;
        alerta.textContent = error.message;
        alerta.classList.remove('d-none');
        panelAccion.classList.add('d-none');
    }
}

// AGREGA estas funciones en: static/js/stock.js

async function editarItem(item) {
    document.getElementById('editItemId').value = item.id;
    document.getElementById('editItemSn').textContent = item.serial_number;

    const selectEstado = document.getElementById('editItemEstado');
    const estados = ['Disponible', 'Vendido', 'Reservado', 'RMA', 'Defectuoso'];
    selectEstado.innerHTML = '';
    estados.forEach(estado => {
        const esSeleccionado = estado === item.estado ? 'selected' : '';
        selectEstado.innerHTML += `<option value="${estado}" ${esSeleccionado}>${estado}</option>`;
    });

    await poblarSelect('editItemDeposito', 'depositos', item.deposito);

    const modal = new bootstrap.Modal(document.getElementById('modalEditarItem'));
    modal.show();
}

async function guardarCambiosItem() {
    const itemId = document.getElementById('editItemId').value;
    const payload = {
        estado: document.getElementById('editItemEstado').value,
        deposito: document.getElementById('editItemDeposito').value
    };

    try {
        const response = await fetch(`/api/stock/items/${itemId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'El servidor no pudo actualizar el item.');
        }

        bootstrap.Modal.getInstance(document.getElementById('modalEditarItem')).hide();
        abrirModalItems(productoSeleccionado.id, productoSeleccionado.nombre);
        cargarProductos();

    } catch (error) {
        alert(`Error al actualizar: ${error.message}`);
        console.error(error);
    }
}

async function eliminarItem(itemId, serialNumber) {
    if (!confirm(`¿Estás seguro de que quieres eliminar el item con SN: "${serialNumber}"?\n\nEsta acción no se puede deshacer.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/stock/items/${itemId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('El servidor no pudo eliminar el item.');
        }

        abrirModalItems(productoSeleccionado.id, productoSeleccionado.nombre);
        cargarProductos();

    } catch (error) {
        alert("Error al eliminar el item.");
        console.error(error);
    }
}

async function exportarStock() {
    try {
        const resp = await fetch('/api/stock/export');
        if (!resp.ok) throw new Error('Error en la exportación');
        const blob = await resp.blob();
        // Obtenemos el nombre del archivo del header Content-Disposition si existe
        const disposition = resp.headers.get('Content-Disposition');
        let filename = 'stock.xlsx';
        if (disposition) {
            const match = disposition.match(/filename=\"?([^\";]+)\"?/);
            if (match) filename = match[1];
        }
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (err) {
        console.error(err);
        alert('No se pudo exportar el stock.');
    }
}

async function importarStock(event) {
    const file = event.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
        const resp = await fetch('/api/stock/import', {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || 'Error en la importación');
        alert(`Importación finalizada: ${data.mensaje}`);
        cargarProductos();
        abrirModalHistorial();
    } catch (err) {
        console.error(err);
        alert(err.message);
    } finally {
        // Limpiamos el input para permitir volver a subir el mismo archivo si se desea
        event.target.value = '';
    }
}

async function egresarPorSku() {
    if (!productoSeleccionado) return;
    const serialInput = prompt('Ingrese los números de serie a egresar, uno por línea:');
    if (!serialInput) return;
    const serial_numbers = serialInput.split('\n').map(sn => sn.trim()).filter(sn => sn);
    if (serial_numbers.length === 0) return;

    const motivo = prompt('Motivo del egreso (VENTA, DEVOLUCIÓN, MERMA, etc.):', 'VENTA') || 'VENTA';

    try {
        const resp = await fetch('/api/stock/items/salida', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ serial_numbers, motivo })
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || 'Error al registrar la salida');
        alert(`${data.items} items egresados correctamente.`);
        cargarProductos();
        abrirModalHistorial();
    } catch (err) {
        console.error(err);
        alert(err.message);
    }
}