// static/js/pc_predeterminadas.js

document.addEventListener("DOMContentLoaded", () => {
    // Carga todos los datos iniciales cuando el documento está listo.
    cargarDatosIniciales();

    // Configura los listeners para que los filtros funcionen en tiempo real.
    document.getElementById("buscadorGlobal").addEventListener("input", filtrarPCs);
    document.getElementById("filtroEtiquetas").addEventListener("change", filtrarPCs);
    document.getElementById("filtroProgramas").addEventListener("change", filtrarPCs);
    document.getElementById("ordenarPCs").addEventListener("change", ordenarPCs);
});

// --- GLOBALES ---
let pcsGlobal = [];
let etiquetasDisponibles = [];
let programasDisponibles = [];

/**
 * Formatea un número al estilo de moneda argentina (ARS).
 */
function formatoPrecioARS(numero) {
    const numeroLimpio = parseFloat(numero) || 0;
    return new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(numeroLimpio);
}

/**
 * Carga todos los datos iniciales de la API.
 */
/**
 * [CORREGIDO] Carga todos los datos necesarios de la API al iniciar la página.
 */
async function cargarDatosIniciales() {
    try {
        // Hacemos las 3 peticiones a la vez para que sea más rápido
        const [pcsRes, etiquetasRes, programasRes] = await Promise.all([
            fetch("/api/pcs_predeterminadas"),
            fetch("/api/etiquetas_pc_predeterminadas"),
            fetch("/api/programas_pc_predeterminadas")
        ]);

        // Guardamos los resultados en nuestras variables globales
        pcsGlobal = await pcsRes.json();
        etiquetasDisponibles = await etiquetasRes.json();
        programasDisponibles = await programasRes.json();

        // Una vez que TENEMOS los datos, AHORA SÍ, dibujamos todo en la pantalla
        renderFiltros(); // <-- Esta llamada es crucial para rellenar los <select>
        renderPCs(pcsGlobal); // Y esta para mostrar las PCs

    } catch (error) {
        console.error("Error crítico al cargar datos iniciales:", error);
        document.getElementById("contenedor-pcs").innerHTML = `<div class="alert alert-danger">Error al cargar los datos. Revisa la consola del servidor para más detalles.</div>`;
    }
}

// --- RENDERIZADO PRINCIPAL ---

/**
 * Dibuja la lista completa de PCs.
 * @param {Array} pcs - La lista de PCs a mostrar.
 */
function renderPCs(pcs) {
    const contenedor = document.getElementById("contenedor-pcs");
    contenedor.innerHTML = "";

    if (pcs.length === 0) {
        contenedor.innerHTML = '<div class="text-center text-muted mt-5"><h4>No se encontraron PCs</h4></div>';
        return;
    }

    pcs.forEach(pc => {
        const pcCard = document.createElement("div");
        pcCard.className = "card card-body mb-3";
        pcCard.id = `pc-card-${pc.id}`;
        pcCard.innerHTML = generarHtmlInternoPC(pc); // Usamos una función ayudante
        contenedor.appendChild(pcCard);
    });
}

/**
 * Genera el HTML interno para una tarjeta de PC.
 * @param {Object} pc - El objeto de la PC.
 * @param {boolean} enEdicion - Si la tarjeta debe mostrarse en modo edición.
 * @returns {string} El HTML de la tarjeta.
 */
/**
 * [CORREGIDO] Genera el HTML para una única PC, controlando si está en modo edición.
 * @param {Object} pc - El objeto de la PC.
 * @param {boolean} enEdicion - Define si la vista es de edición o de solo lectura.
 * @returns {string} El HTML generado.
 */

/**
 * [CORREGIDO] Genera el HTML para una única PC, controlando si está en modo edición.
 * @param {Object} pc - El objeto de la PC.
 * @param {boolean} enEdicion - Define si la vista es de edición o de solo lectura.
 * @returns {string} El HTML generado.
 */
function generarHtmlInternoPC(pc, enEdicion = false) {
    // Definimos el bloque de información para el modo de solo lectura
    const vistaLecturaInfo = `
        <div class="col-lg-5">
            <h6 class="text-muted small">Etiquetas</h6>
            <div class="d-flex flex-wrap gap-1 mb-3">${pc.etiquetas.map(e => `<span class="badge bg-info">${e}</span>`).join('') || '<small>Sin etiquetas</small>'}</div>
            <h6 class="text-muted small">Programas / Juegos</h6>
            <div class="d-flex flex-wrap gap-1">${pc.programas.map(p => `<span class="badge bg-success">${p}</span>`).join('') || '<small>Sin programas</small>'}</div>
        </div>
    `;

    // Definimos el bloque de controles para el modo de edición
    const controlesEdicion = `
        <div class="col-lg-5">
            <div class="mb-3">
                <h6 class="text-muted">Etiquetas</h6>
                <div class="d-flex flex-wrap gap-1 mb-2">
                    ${pc.etiquetas.map(e => `<span class="badge bg-info d-flex align-items-center">${e}<button class="btn-close btn-close-white ms-1" style="font-size: 0.6em;" onclick="quitarEtiqueta(${pc.id}, '${e}')"></button></span>`).join('')}
                </div>
                <select class="form-select form-select-sm" onchange="agregarEtiqueta(event, ${pc.id})">
                    <option value="">Añadir etiqueta...</option>
                    ${etiquetasDisponibles.filter(e => !pc.etiquetas.includes(e)).map(e => `<option value="${e}">${e}</option>`).join('')}
                </select>
            </div>
            <div>
                <h6 class="text-muted">Programas / Juegos</h6>
                <div class="d-flex flex-wrap gap-1 mb-2">
                    ${pc.programas.map(p => `<span class="badge bg-success d-flex align-items-center">${p}<button class="btn-close btn-close-white ms-1" style="font-size: 0.6em;" onclick="quitarPrograma(${pc.id}, '${p}')"></button></span>`).join('')}
                </div>
                <select class="form-select form-select-sm" onchange="agregarPrograma(event, ${pc.id})">
                    <option value="">Añadir programa...</option>
                    ${programasDisponibles.filter(p => !pc.programas.includes(p)).map(p => `<option value="${p}">${p}</option>`).join('')}
                </select>
            </div>
        </div>
    `;

    // Definimos el bloque de las fechas de actualización
    const vistaFechas = `
        <div class="d-flex justify-content-end text-muted small mt-3 pt-2 border-top">
            <span class="me-4" title="Última modificación de esta PC (componentes, nombre, etc.)">
                <i class="fas fa-edit me-1"></i>
                Modificada: <strong>${formatoFecha(pc.ultima_modificacion)}</strong>
            </span>
            <span title="Fecha de la última actualización de precio de un componente en esta PC">
                <i class="fas fa-dollar-sign me-1"></i>
                Precios actualizados: <strong>${formatoFecha(pc.ultima_actualizacion_componente)}</strong>
            </span>
        </div>
    `;

    return `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <div>
                <input class="form-control fw-bold fs-4 border-0 bg-transparent p-0" value="${pc.nombre}" ${enEdicion ? '' : 'readonly'} onchange="editarNombre(${pc.id}, this.value)">
                <small class="text-muted">ID: ${pc.id}</small>
            </div>
            <div class="d-flex align-items-center">
                <h3 class="text-primary mb-0 me-4">${formatoPrecioARS(pc.total)}</h3>
                <button class="btn ${enEdicion ? 'btn-success' : 'btn-outline-secondary'}" onclick="toggleEditMode(${pc.id}, ${!enEdicion})">
                    <i class="fas ${enEdicion ? 'fa-check' : 'fa-edit'} me-2"></i>${enEdicion ? 'Finalizar' : 'Editar PC'}
                </button>
            </div>
        </div>

        <div class="row">
            <div class="col-lg-7">
                <h6 class="text-muted small">Componentes</h6>
                <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                ${enEdicion ? '<th></th>' : ''}
                                <th>Categoría</th>
                                <th>Código</th>
                                <th>Producto</th>
                                <th class="text-end">Precio</th>
                                ${enEdicion ? '<th></th>' : ''}
                            </tr>
                        </thead>
                        <tbody id="sortable-list-${pc.id}">
                            ${pc.componentes_detalle.map(c => `
                                <tr data-id="${c.pc_componente_id}" class="fs-5 align-middle">
                                    ${enEdicion ? '<td class="drag-handle" style="cursor: move; width: 30px;"><i class="fas fa-bars text-muted"></i></td>' : ''}
                                    <td style="width: 15%;"><span class="badge bg-dark">${c.categoria}</span></td>
                                    <td style="width: 15%;"><small class="text-muted">${c.codigo}</small></td>
                                    <td>${c.nombre}</td>
                                    <td class="text-end" style="width: 20%;">${formatoPrecioARS(c.precio_venta)}</td>
                                    ${enEdicion ? `<td class="text-center" style="width: 50px;"><button class="btn btn-sm text-danger p-0" title="Quitar" onclick="quitarComponente(${pc.id}, '${c.codigo}')">✖</button></td>` : ''}
                                </tr>`).join('')}
                        </tbody>
                    </table>
                </div>
                ${enEdicion ? `
                    <div class="input-group mt-2">
                        <input type="text" class="form-control" placeholder="Buscar componente para añadir..." oninput="buscarComponente(this, ${pc.id})">
                        <button class="btn btn-sm btn-danger" onclick="eliminarPC(${pc.id})"><i class="fas fa-trash-alt"></i> Eliminar PC</button>
                    </div>
                    <div id="busqueda-resultados-${pc.id}" class="list-group position-relative" style="z-index: 10;"></div>
                ` : `<div class="mt-2"><button class="btn btn-outline-dark" onclick="generarPDF(${pc.id})"><i class="fas fa-file-pdf me-2"></i>Generar Presupuesto PDF</button></div>`}
            </div>
             ${enEdicion ? controlesEdicion : vistaLecturaInfo}
        </div>
        ${vistaFechas}
    `;
}
// --- LÓGICA DE INTERACCIÓN ---

/**
 * Activa o desactiva el modo de edición para una tarjeta de PC.
 * @param {number} pcId - El ID de la PC a modificar.
 * @param {boolean} activar - True para activar la edición, false para desactivarla.
 */
function toggleEditMode(pcId, activar) {
    const pc = pcsGlobal.find(p => p.id === pcId);
    if (!pc) return;
    
    const card = document.getElementById(`pc-card-${pcId}`);
    card.innerHTML = generarHtmlInternoPC(pc, activar);

    if (activar) {
        const list = document.getElementById(`sortable-list-${pcId}`);
        new Sortable(list, {
            handle: '.drag-handle', // La clase del icono que permite arrastrar
            animation: 150,
            onEnd: async function (evt) {
                // Se ejecuta cuando soltamos el componente
                const itemIds = Array.from(evt.to.children).map(row => row.dataset.id);
                try {
                    await fetch(`/api/pcs_predeterminadas/${pcId}/componentes/orden`, {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ orden_ids: itemIds })
                    });
                    // Opcional: recargar solo esta PC para confirmar el orden visualmente
                    await cargarDatosIniciales(); // Por simplicidad, recargamos todo
                    toggleEditMode(pcId, true);
                } catch (error) {
                    console.error("Error al reordenar:", error);
                    alert("No se pudo guardar el nuevo orden.");
                }
            },
        });
    }
}


// --- FUNCIONES CRUD Y API (sin cambios mayores, solo ajustes menores) ---

async function nuevaPC() {
    const nombre = prompt("Ingresa el nombre para la nueva PC:");
    if (!nombre || !nombre.trim()) return;
    await fetch("/api/pcs_predeterminadas", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nombre }) });
    cargarDatosIniciales();
}

async function editarNombre(pcId, nuevoNombre) {
    await fetch(`/api/pcs_predeterminadas/${pcId}/nombre`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nombre: nuevoNombre }) });
    const pc = pcsGlobal.find(p => p.id === pcId);
    if (pc) pc.nombre = nuevoNombre;
}

function filtrarPCs() {
    // Esta función ahora solo tiene una responsabilidad: llamar a la función de ordenar.
    // La función ordenarPCs se encargará de leer los filtros y aplicar el orden correcto.
    ordenarPCs();
}

async function eliminarPC(pcId) {
    if (!confirm("¿Estás seguro de que quieres eliminar esta PC?")) return;
    await fetch(`/api/pcs_predeterminadas/${pcId}`, { method: "DELETE" });
    cargarDatosIniciales();
}

async function buscarComponente(input, pcId) {
    const texto = input.value.trim();
    const resultadosDiv = document.getElementById(`busqueda-resultados-${pcId}`);
    if (texto.length < 2) {
        resultadosDiv.innerHTML = "";
        return;
    }
    // [CORRECCIÓN] Apuntamos a la URL correcta del backend
    const res = await fetch(`/api/componentes?q=${encodeURIComponent(texto)}`);
    const componentes = await res.json();
    resultadosDiv.innerHTML = componentes.map(c => 
        `<button class="list-group-item list-group-item-action small" onclick="agregarComponente(${pcId}, '${c.codigo}')">
            <strong>${c.producto}</strong> (${c.codigo}) - ${formatoPrecioARS(c.precio_venta)}
        </button>`
    ).join('');
}

async function agregarComponente(pcId, codigo) {
    await fetch(`/api/pcs_predeterminadas/${pcId}/componentes`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({codigo}) });
    await cargarDatosIniciales();
    toggleEditMode(pcId, true); // Mantenemos la tarjeta en modo edición
}

async function quitarComponente(pcId, codigo) {
    await fetch(`/api/pcs_predeterminadas/${pcId}/componentes/${codigo}`, { method: 'DELETE' });
    await cargarDatosIniciales();
    toggleEditMode(pcId, true);
}

async function agregarEtiqueta(event, pcId) {
    const etiqueta = event.target.value;
    if (!etiqueta) return;
    try {
        await fetch(`/api/pcs_predeterminadas/${pcId}/etiquetas`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({etiqueta})
        });
        // Recargamos los datos y mantenemos la tarjeta en modo edición
        await cargarDatosIniciales();
        toggleEditMode(pcId, true);
    } catch(error) { 
        console.error("Error al agregar etiqueta:", error); 
    }
}

async function quitarEtiqueta(pcId, etiqueta) {
    await fetch(`/api/pcs_predeterminadas/${pcId}/etiquetas/${etiqueta}`, { method: 'DELETE' });
    await cargarDatosIniciales();
    toggleEditMode(pcId, true);
}

async function agregarPrograma(event, pcId) {
    const programa = event.target.value;
    if (!programa) return;
    try {
        await fetch(`/api/pcs_predeterminadas/${pcId}/programas`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({programa})
        });
        // Recargamos los datos y mantenemos la tarjeta en modo edición
        await cargarDatosIniciales();
        toggleEditMode(pcId, true);
    } catch(error) { 
        console.error("Error al agregar programa:", error); 
    }
}

async function quitarPrograma(pcId, programa) {
    await fetch(`/api/pcs_predeterminadas/${pcId}/programas/${programa}`, { method: 'DELETE' });
    await cargarDatosIniciales();
    toggleEditMode(pcId, true);
}

function generarPDF(pcId) {
    window.open(`/pcs_predeterminadas/${pcId}/pdf`, "_blank");
}

/**
 * Filtra la lista de PCs según los valores de los filtros.
 */
/**
 * [CORREGIDO] Filtra la lista de PCs según los valores de los filtros.
 */
function filtrarPCs() {
    const texto = document.getElementById("buscadorGlobal").value.toLowerCase();
    const etiquetaFiltro = document.getElementById("filtroEtiquetas").value;
    const programaFiltro = document.getElementById("filtroProgramas").value;

    const pcsFiltradas = pcsGlobal.filter(pc => {
        // Condición 1: El texto debe coincidir (o el campo estar vacío)
        const coincideTexto = !texto ||
            pc.nombre.toLowerCase().includes(texto) ||
            String(pc.id).includes(texto) ||
            pc.componentes_detalle.some(c => c.nombre.toLowerCase().includes(texto));

        // Condición 2: La etiqueta debe coincidir (o el filtro estar en "Todas")
        const coincideEtiqueta = !etiquetaFiltro || pc.etiquetas.includes(etiquetaFiltro);

        // Condición 3: El programa debe coincidir (o el filtro estar en "Todos")
        const coincidePrograma = !programaFiltro || pc.programas.includes(programaFiltro);

        // La PC solo se muestra si cumple las tres condiciones a la vez
        return coincideTexto && coincideEtiqueta && coincidePrograma;
    });

    // Volvemos a dibujar la lista, pero solo con las PCs que pasaron el filtro
    renderPCs(pcsFiltradas);
}
/**
 * Rellena los menús desplegables de los filtros.
 */
function renderFiltros() {
    const filtroEtiquetas = document.getElementById("filtroEtiquetas");
    const filtroProgramas = document.getElementById("filtroProgramas");

    // Limpiamos y rellenamos el filtro de etiquetas
    filtroEtiquetas.innerHTML = '<option value="">Todas las etiquetas</option>';
    etiquetasDisponibles.forEach(et => {
        filtroEtiquetas.innerHTML += `<option value="${et}">${et}</option>`;
    });

    // Limpiamos y rellenamos el filtro de programas
    filtroProgramas.innerHTML = '<option value="">Todos los programas</option>';
    programasDisponibles.forEach(pr => {
        filtroProgramas.innerHTML += `<option value="${pr}">${pr}</option>`;
    });
}

function formatoFecha(fechaString) {
    if (!fechaString) return 'Nunca';
    return new Date(fechaString).toLocaleDateString('es-AR', {
        day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
    }) + ' hs';
}

/**
 * [NUEVO] Ordena la lista de PCs según el criterio seleccionado y la vuelve a dibujar.
 */
function ordenarPCs() {
    const criterio = document.getElementById("ordenarPCs").value;
    // Hacemos una copia de la lista filtrada actual para no perder los filtros aplicados
    let pcsParaOrdenar = pcsGlobal.filter(pc => {
        // Re-aplicamos la lógica de filtro actual antes de ordenar
        const texto = document.getElementById("buscadorGlobal").value.toLowerCase();
        const etiquetaFiltro = document.getElementById("filtroEtiquetas").value;
        const programaFiltro = document.getElementById("filtroProgramas").value;
        const coincideTexto = !texto || pc.nombre.toLowerCase().includes(texto) || String(pc.id).includes(texto) || pc.componentes_detalle.some(c => c.nombre.toLowerCase().includes(texto));
        const coincideEtiqueta = !etiquetaFiltro || pc.etiquetas.includes(etiquetaFiltro);
        const coincidePrograma = !programaFiltro || pc.programas.includes(programaFiltro);
        return coincideTexto && coincideEtiqueta && coincidePrograma;
    });

    switch (criterio) {
        case 'precio_desc':
            pcsParaOrdenar.sort((a, b) => b.total - a.total);
            break;
        case 'precio_asc':
            pcsParaOrdenar.sort((a, b) => a.total - b.total);
            break;
        case 'recientes':
        default:
            pcsParaOrdenar.sort((a, b) => b.id - a.id); // IDs más altos son más recientes
            break;
    }
    // Volvemos a dibujar la lista, ahora ordenada.
    renderPCs(pcsParaOrdenar);
}