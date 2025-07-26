// static/js/componentes_presupuesto.js

document.addEventListener("DOMContentLoaded", () => {
    // Carga todos los datos iniciales y configura los filtros
    cargarDatosIniciales();
    document.getElementById("busqueda").addEventListener("input", (e) => filtrarTabla(e.target.value));
});

// --- VARIABLES GLOBALES ---
let categoriasGlobal = [];
let etiquetasGlobal = [];
let componentesGlobal = [];
let choicesInstances = {}; // Para gestionar las instancias de la librería Choices.js

/**
 * Función principal que carga todos los datos necesarios al inicio.
 */
async function cargarDatosIniciales() {
    try {
        await Promise.all([
            cargarCategorias(),
            cargarEtiquetas(),
            cargarComponentes()
        ]);
    } catch (error) {
        console.error("Error al cargar datos iniciales:", error);
    }
}

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
 * Convierte un string de moneda a un número flotante.
/**
 * [CORREGIDO] Convierte un string de moneda a un número flotante.
 * Entiende el formato argentino (ej: "$ 91.000,50").
 */
function parseCurrency(valor) {
    if (typeof valor !== 'string') return parseFloat(valor) || 0;
    // 1. Quita el símbolo de moneda y los espacios.
    // 2. Quita los puntos de miles.
    // 3. Reemplaza la coma decimal por un punto.
    const numero = valor.replace(/\$\s?|/g, '').replace(/\./g, '').replace(',', '.');
    return parseFloat(numero) || 0;
}

/**
 * Genera un código único basado en la categoría.
 */
function generarCodigoUnico(categoria) {
    if (!categoria) return "";
    const prefijo = categoria.substring(0, 3).toUpperCase();
    let maxNum = 0;
    componentesGlobal.forEach(comp => {
        if (comp.codigo && comp.codigo.startsWith(prefijo)) {
            const num = parseInt(comp.codigo.replace(prefijo, ''), 10);
            if (!isNaN(num) && num > maxNum) {
                maxNum = num;
            }
        }
    });
    const nuevoNumero = (maxNum + 1).toString().padStart(3, '0');
    return `${prefijo}${nuevoNumero}`;
}

// --- FUNCIONES DE CARGA DE DATOS (API) ---

async function cargarComponentes() {
    const response = await fetch("/api/componentes");
    componentesGlobal = await response.json();
    renderTabla(componentesGlobal);
}

async function cargarCategorias() {
    const response = await fetch("/api/categorias");
    categoriasGlobal = await response.json();
    renderListaConfig('listaCategorias', categoriasGlobal, 'eliminarCategoria');
}

async function cargarEtiquetas() {
    const response = await fetch("/api/etiquetas");
    etiquetasGlobal = await response.json();
    renderListaConfig('listaEtiquetas', etiquetasGlobal, 'eliminarEtiqueta');
}

// --- FUNCIONES DE RENDERIZADO Y TABLA ---

function renderTabla(componentes) {
    const cuerpoTabla = document.getElementById("cuerpo-tabla");
    const cabeceraTabla = cuerpoTabla.previousElementSibling.rows[0];
    
    // Añadimos la cabecera de la columna si no existe para evitar duplicados
    if (!cabeceraTabla.querySelector('.col-fecha')) {
        const th = document.createElement('th');
        th.className = 'col-fecha';
        th.textContent = 'Últ. Modif.';
        // Insertamos la nueva columna antes de la de "Acciones"
        cabeceraTabla.insertBefore(th, cabeceraTabla.lastElementChild);
    }
    
    cuerpoTabla.innerHTML = "";
    Object.values(choicesInstances).forEach(instance => instance.destroy());
    choicesInstances = {};

    if (!componentes || componentes.length === 0) {
        cuerpoTabla.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No hay componentes para mostrar.</td></tr>';
        return;
    }

    componentes.forEach(comp => {
        const fila = document.createElement("tr");
        fila.dataset.id = comp.id;
        fila.innerHTML = `
            <td><input class="form-control form-control-sm" value="${comp.codigo || ''}" readonly></td>
            <td>
                <select class="form-select form-select-sm" disabled>
                    ${categoriasGlobal.map(cat => `<option value="${cat}" ${comp.categoria === cat ? 'selected' : ''}>${cat}</option>`).join('')}
                </select>
            </td>
            <td><input class="form-control form-control-sm" value="${comp.producto}" disabled></td>
            <td><input class="form-control form-control-sm" value="${formatoPrecioARS(comp.precio_costo)}" disabled></td>
            <td><input class="form-control form-control-sm" value="${(comp.mark_up || 1.3).toString().replace('.', ',')}" disabled></td>
            <td><input class="form-control form-control-sm" value="${formatoPrecioARS(comp.precio_venta)}" readonly></td>
            <td>
                <select class="form-control-sm" multiple>
                    ${etiquetasGlobal.map(et => `<option value="${et}" ${(comp.etiquetas || []).includes(et) ? 'selected' : ''}>${et}</option>`).join('')}
                </select>
            </td>
            <td class="text-center align-middle">${formatoFecha(comp.ultima_modificacion)}</td>
            <td class="text-center">
                <button class="btn btn-sm btn-outline-secondary" title="Editar" onclick="editarFila(this)"><i class="fas fa-edit"></i></button>
                <button class="btn btn-sm btn-success d-none" title="Guardar" onclick="guardarFila(this)"><i class="fas fa-save"></i></button>
                <button class="btn btn-sm btn-outline-danger ms-1" title="Eliminar" onclick="eliminarComponente(${comp.id})"><i class="fas fa-trash-alt"></i></button>
            </td>
        `;
        cuerpoTabla.appendChild(fila);

        const select = fila.querySelector('select[multiple]');
        choicesInstances[comp.id] = new Choices(select, {removeItemButton: true});
        choicesInstances[comp.id].disable();
    });
}

function agregarFilaNueva() {
    const cuerpo = document.getElementById("cuerpo-tabla");
    const idTemporal = `nuevo_${Date.now()}`;
    const fila = document.createElement("tr");
    fila.dataset.id = idTemporal;
    fila.innerHTML = `
        <td><input class="form-control form-control-sm" placeholder="Selecciona categoría" readonly></td>
        <td>
            <select class="form-select form-select-sm">
                <option value="">Seleccionar...</option>
                ${categoriasGlobal.map(cat => `<option value="${cat}">${cat}</option>`).join("")}
            </select>
        </td>
        <td><input class="form-control form-control-sm" placeholder="Nombre del producto"></td>
        <td><input class="form-control form-control-sm" placeholder="$ 0,00"></td>
        <td><input class="form-control form-control-sm" value="1,3"></td>
        <td><input class="form-control form-control-sm" value="$ 0,00" readonly></td>
        <td><select class="form-control-sm" multiple></select></td>
        <td class="text-center">
            <button class="btn btn-sm btn-success" title="Guardar Nuevo" onclick="guardarNuevoComponente(this)"><i class="fas fa-save"></i></button>
            <button class="btn btn-sm btn-outline-warning ms-1" title="Cancelar" onclick="this.closest('tr').remove()"><i class="fas fa-times"></i></button>
        </td>
    `;
    cuerpo.prepend(fila);

    const selectCategoria = fila.querySelector('select:not([multiple])');
    const inputCodigo = fila.querySelector('input');
    
    selectCategoria.addEventListener('change', () => {
        inputCodigo.value = generarCodigoUnico(selectCategoria.value);
    });

    const selectEtiquetas = fila.querySelector('select[multiple]');
    choicesInstances[idTemporal] = new Choices(selectEtiquetas, {removeItemButton: true});
    choicesInstances[idTemporal].setChoices(etiquetasGlobal.map(et => ({value: et, label: et})), 'value', 'label', false);

    const [_, __, inputProducto, inputCosto, inputMarkup, inputVenta] = fila.querySelectorAll("input, select");
    const calcularVenta = () => {
        const costo = parseCurrency(inputCosto.value);
        const markup = parseFloat(inputMarkup.value.replace(',', '.')) || 1.3;
        inputVenta.value = formatoPrecioARS(costo * markup);
    };
    inputCosto.addEventListener('input', calcularVenta);
    inputMarkup.addEventListener('input', calcularVenta);
}

function editarFila(btn) {
    const fila = btn.closest("tr");
    const id = fila.dataset.id;
    // Habilitamos los inputs y selects para la edición
    fila.querySelectorAll("select").forEach(el => el.disabled = false);
    fila.querySelectorAll("input").forEach((el, index) => {
        // El código (0) y precio venta (5) no se editan manualmente
        if(index !== 0 && index !== 5) el.disabled = false; 
    });

    if (choicesInstances[id]) choicesInstances[id].enable();

    // Intercambiamos los botones de "Editar" por "Guardar"
    btn.classList.add("d-none");
    btn.nextElementSibling.classList.remove("d-none");
    
    // [NUEVO] Añadimos la lógica de cálculo en tiempo real también al editar
    const inputs = fila.querySelectorAll("input");
    const inputCosto = inputs[2]; // El tercer input es el de Costo
    const inputMarkup = inputs[3]; // El cuarto es el de Mark Up
    const inputVenta = inputs[4]; // El quinto es el de Venta
    
     const calcularVenta = () => {
        const costo = parseCurrency(inputCosto.value);
        const markup = parseFloat(inputMarkup.value.replace(',', '.')) || 1.3;
        inputVenta.value = formatoPrecioARS(costo * markup);
    };

    // "Escuchamos" los cambios en los inputs para recalcular al instante
    inputCosto.addEventListener('input', calcularVenta);
    inputMarkup.addEventListener('input', calcularVenta);
}

async function guardarFila(btn) {
    const fila = btn.closest('tr');
    const id = fila.dataset.id;
    const inputs = fila.querySelectorAll('input');
    const selectCategoria = fila.querySelector('select:not([multiple])');
    const etiquetas = choicesInstances[id] ? choicesInstances[id].getValue(true) : [];

    // [CORREGIDO] Se usan los índices correctos aquí también.
    const body = {
        codigo: inputs[0].value,
        categoria: selectCategoria.value,
        producto: inputs[1].value.toUpperCase(),       // Era [2]
        precio_costo: parseCurrency(inputs[2].value), // Era [3]
        mark_up: parseFloat(inputs[3].value.replace(',', '.')), // Era [4]
        precio_venta: parseCurrency(inputs[4].value),   // Era [5]
        etiquetas: etiquetas
    };

    try {
        const res = await fetch(`/api/componentes/${id}`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
        if (!res.ok) throw new Error('Error al actualizar');
        await cargarComponentes();
    } catch (error) {
        console.error("Error al guardar:", error);
        alert("No se pudo actualizar el componente.");
    }
}

async function guardarNuevoComponente(btn) {
    const fila = btn.closest('tr');
    const inputs = fila.querySelectorAll('input');
    const selectCategoria = fila.querySelector('select:not([multiple])');
    const idTemporal = fila.dataset.id;
    const etiquetas = choicesInstances[idTemporal] ? choicesInstances[idTemporal].getValue(true) : [];

    // [CORREGIDO] Se usan los índices correctos para leer los valores de los inputs.
    const body = {
        codigo: inputs[0].value,
        categoria: selectCategoria.value,
        producto: inputs[1].value.toUpperCase(),       // Era [2]
        precio_costo: parseCurrency(inputs[2].value), // Era [3]
        mark_up: parseFloat(inputs[3].value.replace(',', '.')), // Era [4]
        precio_venta: parseCurrency(inputs[4].value),   // Era [5]
        etiquetas: etiquetas
    };

    if (!body.categoria || !body.producto) {
        return alert("Por favor, completa al menos la Categoría y el Nombre del Producto.");
    }

    try {
        const res = await fetch('/api/componentes', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.error || 'Error al crear el componente');
        }
        await cargarComponentes();
    } catch(error) {
        console.error("Error al crear:", error);
        alert(`No se pudo crear el componente: ${error.message}`);
    }
}

async function eliminarComponente(id) {
    if (!confirm("¿Estás seguro de que quieres eliminar este componente?")) return;
    try {
        const res = await fetch(`/api/componentes/${id}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Error del servidor al eliminar");
        document.querySelector(`tr[data-id='${id}']`).remove();
    } catch (error) {
        console.error("Error:", error);
        alert("No se pudo eliminar el componente.");
    }
}

function filtrarTabla(filtro) {
    const filtroLower = filtro.toLowerCase();
    const filas = document.querySelectorAll("#cuerpo-tabla tr");
    filas.forEach(fila => {
        fila.style.display = fila.textContent.toLowerCase().includes(filtroLower) ? "" : "none";
    });
}

// --- LÓGICA DEL MODAL ---

function renderListaConfig(ulId, items, funcionBorrar) {
    const ul = document.getElementById(ulId);
    ul.innerHTML = items.map(item => `
        <li class="list-group-item d-flex justify-content-between align-items-center">
            ${item}
            <button class="btn btn-sm btn-outline-danger py-0 px-1" onclick="${funcionBorrar}('${item}')"><i class="fas fa-trash-alt"></i></button>
        </li>`).join("");
}

async function crearCategoria() {
    const input = document.getElementById("inputNuevaCategoria");
    const nombre = input.value.trim();
    if (!nombre) return;
    await fetch('/api/categorias', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({nombre})});
    input.value = "";
    await cargarCategorias();
}

async function eliminarCategoria(nombre) {
    if (!confirm(`¿Eliminar la categoría "${nombre}"? Esta acción no se puede deshacer.`)) return;
    await fetch('/api/categorias', {method: 'DELETE', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({nombre})});
    await cargarCategorias();
    await cargarComponentes();
}

async function crearEtiqueta() {
    const input = document.getElementById("inputNuevaEtiqueta");
    const nombre = input.value.trim();
    if (!nombre) return;
    await fetch('/api/etiquetas', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({nombre})});
    input.value = "";
    await cargarEtiquetas();
}

async function eliminarEtiqueta(nombre) {
    if (!confirm(`¿Eliminar la etiqueta "${nombre}"?`)) return;
    await fetch('/api/etiquetas', {method: 'DELETE', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({nombre})});
    await cargarEtiquetas();
    await cargarComponentes();
}

function formatoFecha(fechaString) {
    if (!fechaString) return 'N/A';
    return new Date(fechaString).toLocaleDateString('es-AR', {
        day: '2-digit', month: '2-digit', year: 'numeric'
    });
}