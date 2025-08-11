//--- Variables Globales ---
let todosLosResultados = []; 
let productosFijados = []; 
let progressInterval = null; 
let productoParaFijar = null;
let estaBuscando = false;
// Nueva variable para controlar el intervalo de sondeo
let pollingInterval = null; 
const NORMALIZAR_TIENDA = (s) => (s || '').trim().toLowerCase();
const TGS_NAME = 'The Gamer Shop';
const PG_NAME = 'PreciosGamer';

//--- Inicialización de la Página ---
document.addEventListener("DOMContentLoaded", () => {
    // Asignamos todos los listeners de la página
    document.querySelector('.btn-red').addEventListener("click", () => buscar(true));
    document.getElementById("producto").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            buscar(true);
        }
    });
    document.getElementById("tipoBusqueda").addEventListener("change", () => buscar(true));
    document.getElementById("ordenSelect").addEventListener("change", renderizarResultados);
    document.getElementById("precioMin").addEventListener("input", renderizarResultados);
    document.getElementById("precioMax").addEventListener("input", renderizarResultados);
    
    cargarTiendasParaFiltro();
    cargarCategoriasParaCalculadora(document.getElementById('categoria-producto'));
    
    document.getElementById('costo-producto').addEventListener('input', calcularPrecioFinal);
    document.getElementById('categoria-producto').addEventListener('change', calcularPrecioFinal);
    
    const modalConfig = document.getElementById('modalConfiguracion');
    if (modalConfig) {
        modalConfig.addEventListener('show.bs.modal', cargarCategoriasYMargenes);
    }
});

/**
 * Función principal que inicia la búsqueda o renderiza resultados si no es nueva.
 * Ahora maneja la posibilidad de recibir resultados parciales junto al estado 'actualizando'.
 */
async function buscar(esNuevaBusqueda = false) {
    if (estaBuscando) {
        console.log("Búsqueda ya en progreso. Se ignora la nueva solicitud.");
        return;
    }
    if (!esNuevaBusqueda) {
        renderizarResultados();
        return;
    }

    const prodInput = document.getElementById("producto");
    const prod = prodInput.value.trim().toLowerCase();
    if (!prod) {
        document.getElementById("tabla-resultados").innerHTML = `<p>Ingrese un producto.</p>`;
        return;
    }

    estaBuscando = true;
    iniciarBarraDeCarga();

    // Detenemos cualquier sondeo anterior para empezar de cero
    if (pollingInterval) clearInterval(pollingInterval);

    try {
        const tipo = document.getElementById("tipoBusqueda").value;
        const url = `/comparar?producto=${encodeURIComponent(prod)}&tipo=${encodeURIComponent(tipo)}`;
        const response = await fetch(url);

        if (!response.ok) throw new Error(`El servidor respondió con estado ${response.status}.`);

        const data = await response.json();

        if (data.estado === 'actualizando') {
            // Si nos devuelven algunos resultados mayoristas junto al estado, los mostramos.
            if (Array.isArray(data.resultados)) {
                todosLosResultados = data.resultados;
                renderizarResultados();
            } else {
                todosLosResultados = [];
            }
            // Iniciamos el sondeo para completar los minoristas
            iniciarSondeoDeResultados(prod, tipo, data.mensaje);
        } else {
            // Si la respuesta ya es la lista final (array), la manejamos normalmente
            manejarRespuestaFinal(data, prod);
        }
    } catch (error) {
        console.error("Error en buscar():", error);
        manejarRespuestaFinal({ error: "Hubo un problema con la búsqueda." });
    }
}


/**
 * Pregunta al servidor cada 4 segundos si ya hay resultados completos.
 * Si el servidor responde con resultados finales (array), detiene el sondeo y los muestra.
 */
function iniciarSondeoDeResultados(producto, tipo, mensajeInicial) {
    const tablaDiv = document.getElementById("tabla-resultados");
    tablaDiv.innerHTML = `<p>${mensajeInicial}</p>`;

    let intentos = 0;
    const maxIntentos = 15; // Intentará durante 60 segundos (15 * 4s)

    pollingInterval = setInterval(async () => {
        intentos++;
        if (intentos > maxIntentos) {
            clearInterval(pollingInterval);
            manejarRespuestaFinal({ error: "La búsqueda está tardando más de lo esperado. Intente de nuevo." });
            return;
        }

        try {
            const url = `/comparar?producto=${encodeURIComponent(producto)}&tipo=${encodeURIComponent(tipo)}`;
            const response = await fetch(url);
            const data = await response.json();

            // Si ya no está actualizando, tenemos resultados finales
            if (data.estado !== 'actualizando') {
                clearInterval(pollingInterval);
                manejarRespuestaFinal(data, producto);
            } else if (Array.isArray(data.resultados)) {
                // Si todavía está actualizando pero llegan resultados mayoristas, los actualizamos en pantalla
                todosLosResultados = data.resultados;
                renderizarResultados();
            }
        } catch (error) {
            console.error("Error durante el sondeo:", error);
            clearInterval(pollingInterval);
            manejarRespuestaFinal({ error: "Se perdió la conexión durante la actualización." });
        }
    }, 4000); // Cada 4 segundos
}


function uniqueByKey(arr, keyFn) {
    const seen = new Set();
    return arr.filter(x => {
        const k = keyFn(x);
        if (seen.has(k)) return false;
        seen.add(k);
        return true;
    });
}
  
function roundRobinGroups(groups) {
    // groups: array de arrays (cada array = resultados de una tienda)
    const out = [];
    let added;
    let i = 0;
    do {
        added = false;
        for (const g of groups) {
        if (i < g.length) { out.push(g[i]); added = true; }
        }
        i++;
    } while (added);
    return out;
}
  
  /** Intercalado según tipo */
function intercalarSegunTipo(tipo, lista) {
    // Deduplicar por (sitio + link) normalizados
    const sinDupes = uniqueByKey(lista, it => `${NORMALIZAR_TIENDA(it.sitio)}|${(it.link||'').trim()}`);

    if (tipo === 'minoristas') {
        const tgs = sinDupes.filter(it => it.sitio === TGS_NAME);
        const pg  = sinDupes.filter(it => it.sitio === PG_NAME);
        // Intercalar TGS y PG, y al final sumar otros por si acaso
        const resto = sinDupes.filter(it => it.sitio !== TGS_NAME && it.sitio !== PG_NAME);
        return roundRobinGroups([pg, tgs]).concat(resto);
    }

    if (tipo === 'masiva') {
        const porTienda = {};
        sinDupes.forEach(it => {
        porTienda[it.sitio] = porTienda[it.sitio] || [];
        porTienda[it.sitio].push(it);
        });
        // Orden opcional por cantidad asc para balancear
        const grupos = Object.values(porTienda).sort((a,b) => a.length - b.length);
        return roundRobinGroups(grupos);
    }

    // Mayoristas u otros: devolver como vino (ya dedupeado)
    return sinDupes;
}

/**
 * NUEVA FUNCIÓN: Centraliza el manejo de la respuesta final para no repetir código.
 */
function manejarRespuestaFinal(data, prod = "") {
    finalizarBarraDeCarga(data.error);
    estaBuscando = false;
    pollingInterval = null;

    if (data.error) {
        document.getElementById("tabla-resultados").innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
        todosLosResultados = [];
    } else if (!Array.isArray(data) || data.length === 0) {
        document.getElementById("tabla-resultados").innerHTML = `<div class="alert alert-warning mt-3">No se encontraron resultados para "${prod}".</div>`;
        todosLosResultados = [];
    } else {
        todosLosResultados = data;
    }
    renderizarResultados();
}


// REEMPLAZA por completo esta función en static/js/buscador.js
function renderizarResultados() {
    const tablaDiv = document.getElementById("tabla-resultados");
    const tipo = document.getElementById("tipoBusqueda").value;

    // Normalizamos y deduplicamos resultados según tipo (minorista, mayorista, masiva)
    let resultados = intercalarSegunTipo(tipo, todosLosResultados.map(r => ({
        ...r,
        // normalizamos campos para ordenamiento y filtrado
        precio_numeric: typeof r.precio_numeric === 'number'
            ? r.precio_numeric
            : parseFloat(String(r.precio || "0").replace(/\$/g,"").replace(/\./g,"").replace(",", ".")) || 0,
        fetched_at: r.fetched_at || r.actualizado || r.updated_at || null
    })));

    // --- filtros de tienda ---
    const tiendasSeleccionadas = Array.from(document.querySelectorAll('#filtro-tiendas input:checked')).map(cb => cb.value);
    if (tiendasSeleccionadas.length > 0) {
        resultados = resultados.filter(item => tiendasSeleccionadas.includes(item.sitio));
    }

    // --- filtros de precio ---
    const precioMin = parseFloat(document.getElementById("precioMin").value) || 0;
    const precioMax = parseFloat(document.getElementById("precioMax").value) || Infinity;
    resultados = resultados.filter(item => item.precio_numeric >= precioMin && item.precio_numeric <= precioMax);

    // --- ordenamiento ---
    const orden = document.getElementById("ordenSelect").value;
    if (orden === "precio_asc") resultados.sort((a, b) => a.precio_numeric - b.precio_numeric);
    else if (orden === "precio_desc") resultados.sort((a, b) => b.precio_numeric - a.precio_numeric);
    else if (orden === "nombre_asc") resultados.sort((a, b) => (a.producto || "").localeCompare(b.producto || ""));
    else if (orden === "nombre_desc") resultados.sort((a, b) => (b.producto || "").localeCompare(a.producto || ""));

    // --- detectar minoristas esperados faltantes (solo debug) ---
    const tiendasPresentes = new Set(resultados.map(r => r.sitio));
    const esperadasMinoristas = [PG_NAME, TGS_NAME];
    const faltantes = (tipo === 'minoristas')
        ? esperadasMinoristas.filter(t => !tiendasPresentes.has(t))
        : [];

    // --- construir HTML ---
    let html = `<h4>Resultados de Búsqueda</h4>`;
    if (faltantes.length) {
        html += `<div class="alert alert-warning mb-2">⚠️ No llegaron resultados de: <b>${faltantes.join(', ')}</b>. Revisá logs/endpoint.</div>`;
    }

    if (resultados.length > 0) {
        html += `<table class="table table-hover align-middle mt-3">
            <thead>
                <tr>
                    <th style="width:5%;">Fijar</th>
                    <th style="width:10%;">Imagen</th>
                    <th style="width:15%;">Sitio</th>
                    <th style="width:40%;">Producto</th>
                    <th style="width:15%;">Precio</th>
                    <th style="width:10%;">Actualizado</th>
                    <th style="width:5%;">Link</th>
                </tr>
            </thead>
            <tbody>`;
        const dtf = new Intl.DateTimeFormat('es-AR', { dateStyle: 'short', timeStyle: 'short' });

        resultados.forEach(item => {
            const normalizadoSitio = NORMALIZAR_TIENDA(item.sitio);
            const normalizadoTGS   = NORMALIZAR_TIENDA(TGS_NAME);
            const esTGS = normalizadoSitio === normalizadoTGS || normalizadoSitio.includes('thegamershop');
            const rowClass = esTGS ? 'highlight-tgs' : '';

            // Imagen: en mayoristas dejamos un placeholder para evitar roturas
            let imagenHTML = '';
            if (tipo === 'mayoristas') {
                imagenHTML = `<div class="img-ph"></div>`;
            } else {
                const src = item.imagen && item.imagen.startsWith('http') ? item.imagen : '';
                imagenHTML = src
                    ? `<img src="${src}" alt="${item.producto}" class="img-fluid rounded" style="max-height:60px;">`
                    : `<div class="img-ph"></div>`;
            }
            const fechaTxt = item.fetched_at ? dtf.format(new Date(item.fetched_at)) : '-';

            html += `<tr class="${rowClass}">
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick='abrirModalFijar(${JSON.stringify(item)})'>
                        <i class="fas fa-thumbtack"></i>
                    </button>
                </td>
                <td>${imagenHTML}</td>
                <td>${item.sitio || "-"}</td>
                <td>${item.producto || "N/A"}</td>
                <td class="fw-bold">${item.precio || formatearComoPesoArgentino(item.precio_numeric) || "N/A"}</td>
                <td>${fechaTxt}</td>
                <td>
                    <a href="${item.link || "#"}" target="_blank" class="btn btn-sm btn-outline-secondary">Ver</a>
                </td>
            </tr>`;
        });
        html += "</tbody></table>";
    } else {
        html += `<div class="alert alert-warning mt-3">No hay resultados que coincidan con los filtros aplicados.</div>`;
    }
    tablaDiv.innerHTML = html;
}


async function abrirModalFijar(item) {
    productoParaFijar = item;
    document.getElementById('modal-producto-nombre').textContent = item.producto;
    document.getElementById('modal-producto-costo').textContent = item.precio;
    const selectCategoria = document.getElementById('modal-categoria-select');
    await cargarCategoriasParaCalculadora(selectCategoria);
    selectCategoria.onchange = calcularPrecioVentaModal;
    calcularPrecioVentaModal();
    const modal = new bootstrap.Modal(document.getElementById('modalFijarProducto'));
    modal.show();
}

function calcularPrecioVentaModal() {
    if (!productoParaFijar) return;
    const costo = productoParaFijar.precio_numeric;
    const categoriaSelect = document.getElementById('modal-categoria-select');
    const precioFinalSpan = document.getElementById('modal-producto-precio-final');
    if (categoriaSelect.selectedIndex < 0) {
        precioFinalSpan.textContent = formatearComoPesoArgentino(0);
        return;
    }
    const selectedOption = categoriaSelect.options[categoriaSelect.selectedIndex];
    const margen = parseFloat(selectedOption.dataset.margen) || 0;
    let precioFinal = 0;
    if (costo > 0 && margen > 0) {
        precioFinal = costo * (1 + (margen / 100));
    }
    precioFinalSpan.textContent = formatearComoPesoArgentino(precioFinal);
}

function confirmarFijarProducto() {
    if (!productoParaFijar) return;
    const categoriaSelect = document.getElementById('modal-categoria-select');
    const itemFijado = { ...productoParaFijar };
    const selectedOption = categoriaSelect.options[categoriaSelect.selectedIndex];
    itemFijado.categoriaNombre = selectedOption.text;
    const margen = parseFloat(selectedOption.dataset.margen) || 0;
    if(productoParaFijar.precio_numeric > 0 && margen > 0) {
        itemFijado.precioVentaCalculado = productoParaFijar.precio_numeric * (1 + (margen / 100));
    } else {
        itemFijado.precioVentaCalculado = 0;
    }
    if (!productosFijados.some(p => p.link === itemFijado.link && p.sitio === itemFijado.sitio)) {
        productosFijados.push(itemFijado);
        renderizarFijados();
    }
    const modal = bootstrap.Modal.getInstance(document.getElementById('modalFijarProducto'));
    modal.hide();
    productoParaFijar = null;
}

// REEMPLAZA esta función en static/js/buscador.js
function renderizarFijados() {
    const container = document.getElementById("productos-fijados-container");
    const divFijados = document.getElementById("productos-fijados");
    if (productosFijados.length === 0) {
        container.style.display = 'none';
        divFijados.innerHTML = '';
        return;
    }
    container.style.display = 'block';
    let html = "";
    productosFijados.forEach((item, index) => {
        const categoria = item.categoriaNombre || 'Sin Categoría';
        const precioVenta = formatearComoPesoArgentino(item.precioVentaCalculado);
        html += `
            <div class="col-md-6 col-lg-4">
                <div class="card h-100 shadow-sm">
                    <div class="card-body d-flex flex-column">
                        <div class="d-flex justify-content-between">
                            <p class="card-text small text-muted">${item.sitio}</p>
                            <span class="badge-categoria-fijado">${categoria}</span>
                        </div>
                        <h6 class="card-title flex-grow-1 my-2">${item.producto}</h6>
                        <div class="text-end">
                            <p class="mb-0 small text-muted">Costo: ${item.precio}</p>
                            <h5 class="card-subtitle text-success fw-bold">${precioVenta}</h5>
                        </div>
                        <div class="mt-auto pt-3">
                            <a href="${item.link}" target="_blank" class="btn btn-sm btn-primary">Ver Producto</a>
                            <button class="btn btn-sm btn-outline-danger" onclick="desfijarProducto(${index})">Quitar</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    // Añadimos un botón al final para enviar todos los fijados a Presupuestos
    html += `
        <div class="col-12 text-end mt-4">
            <button class="btn btn-primary" onclick="enviarFijadosAPresupuestos()">
                <i class="fas fa-paper-plane"></i> Enviar fijados a Presupuestos
            </button>
        </div>
    `;
    divFijados.innerHTML = html;
}


function desfijarProducto(index) {
    productosFijados.splice(index, 1);
    renderizarFijados();
}

async function cargarTiendasParaFiltro() {
    try {
        const response = await fetch('/api/tiendas');
        const tiendas = await response.json();
        const container = document.getElementById('filtro-tiendas');
        let html = '';
        tiendas.forEach(tienda => {
            html += `
                <div class="form-check form-check-inline">
                    <input class="form-check-input" type="checkbox" value="${tienda}" id="check-${tienda}" onchange="renderizarResultados()">
                    <label class="form-check-label" for="check-${tienda}">${tienda}</label>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (error) {
        console.error("Error al cargar tiendas:", error);
    }
}

function iniciarBarraDeCarga() {
    const loadingBar = document.getElementById("loading-bar");
    const progressBar = loadingBar.querySelector('.progress-bar');
    loadingBar.style.display = 'block';
    progressBar.style.width = '0%';
    progressBar.classList.remove('bg-warning');
    clearInterval(progressInterval);
    let width = 0;
    progressInterval = setInterval(() => {
        if (width < 95) {
            width += 2;
            progressBar.style.width = width + '%';
        } else {
            clearInterval(progressInterval);
        }
    }, 50);
}

function finalizarBarraDeCarga(error = false) {
    const loadingBar = document.getElementById("loading-bar");
    const progressBar = loadingBar.querySelector('.progress-bar');
    clearInterval(progressInterval);
    progressBar.style.width = '100%';
    if (error) {
        progressBar.classList.add('bg-warning');
    }
    setTimeout(() => { loadingBar.style.display = 'none'; }, 500);
}

async function agregarAlCarrito(item) {
    try {
        const precioLimpio = parseFloat(String(item.precio || "0").replace(/\$/g, "").replace(/\./g, "").replace(",", "."));
        const body = {
            sitio: item.sitio || "Desconocido",
            producto: item.producto || "Sin nombre",
            precio: isNaN(precioLimpio) ? 0 : precioLimpio,
            link: item.link || "#"
        };
        const response = await fetch("/carrito", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'No se pudo leer la respuesta del servidor.' }));
            throw new Error(errorData.error || 'Error desconocido al agregar al carrito');
        }
        alert("Producto agregado al carrito");
    } catch (error) {
        console.error("Error al agregar al carrito:", error);
        alert(`Error: ${error.message}`);
    }
}

async function cargarCategoriasYMargenes() {
    try {
        const response = await fetch('/api/configuracion/categorias');
        if (!response.ok) throw new Error('No se pudieron cargar las categorías.');
        
        const categorias = await response.json();
        const container = document.getElementById('lista-categorias-margen');
        
        if (categorias.length === 0) {
            container.innerHTML = '<p class="text-center text-muted">Aún no hay categorías. Agrega una para empezar.</p>';
            return;
        }

        let html = '<ul class="list-group">';
        categorias.forEach(cat => {
            html += `
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    ${cat.nombre}
                    <div class="input-group" style="width: 120px;">
                        <input type="number" class="form-control form-control-sm" value="${cat.margen}" id="margen-cat-${cat.id}" step="0.1">
                        <span class="input-group-text">%</span>
                    </div>
                </li>
            `;
        });
        html += '</ul>';
        container.innerHTML = html;
        
    } catch (error) {
        console.error("Error al cargar categorías y márgenes:", error);
        document.getElementById('lista-categorias-margen').innerHTML = 
            `<div class="alert alert-danger">Error al cargar la configuración.</div>`;
    }
}


function ampliarImagen(src) {
    const modalImg = document.getElementById('modalImagenGrandeImg');
    modalImg.src = src;
    const modal = new bootstrap.Modal(document.getElementById('modalImagenGrande'));
    modal.show();
}


async function guardarMargenes() {
    const inputs = document.querySelectorAll('#lista-categorias-margen input[type="number"]');
    const dataParaEnviar = [];
    
    inputs.forEach(input => {
        const id = input.id.replace('margen-cat-', '');
        const margen = parseFloat(input.value) || 0;
        dataParaEnviar.push({ id: parseInt(id), margen: margen });
    });

    try {
        const response = await fetch('/api/configuracion/margenes', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dataParaEnviar)
        });
        
        if (!response.ok) throw new Error('El servidor rechazó la solicitud.');

        alert('Márgenes guardados con éxito.');
        const modalEl = document.getElementById('modalConfiguracion');
        const modal = bootstrap.Modal.getInstance(modalEl);
        modal.hide();

    } catch (error) {
        console.error("Error al guardar márgenes:", error);
        alert('Hubo un error al guardar los márgenes.');
    }
}

async function agregarNuevaCategoria() {
    const input = document.getElementById('input-nueva-categoria');
    const nombre = input.value.trim();
    if (!nombre) {
        alert('Por favor, ingrese un nombre para la categoría.');
        return;
    }
    try {
        const response = await fetch('/api/configuracion/categorias', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nombre: nombre })
        });
        if (!response.ok) throw new Error('El servidor no pudo agregar la categoría.');
        input.value = '';
        await cargarCategoriasYMargenes();
    } catch (error) {
        console.error("Error al agregar categoría:", error);
        alert('Hubo un error al agregar la categoría.');
    }
}

let categoriasConMargen = [];

async function cargarCategoriasParaCalculadora(selectElement) {
    if (categoriasConMargen.length === 0) {
        try {
            const response = await fetch('/api/configuracion/categorias');
            if (!response.ok) throw new Error('No se pudieron cargar las categorías.');
            categoriasConMargen = await response.json();
        } catch (error) {
            console.error("Error crítico al cargar categorías:", error);
            if(selectElement) selectElement.disabled = true;
            return;
        }
    }
    if (selectElement) {
        selectElement.innerHTML = '<option value="-1" selected disabled>Seleccionar categoría...</option>';
        categoriasConMargen.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id;
            option.textContent = cat.nombre;
            option.dataset.margen = cat.margen;
            selectElement.appendChild(option);
        });
        selectElement.disabled = false;
    }
}

function calcularPrecioFinal() {
    const costoInput = document.getElementById('costo-producto');
    const categoriaSelect = document.getElementById('categoria-producto');
    const precioFinalInput = document.getElementById('precio-final');
    const costo = parseFloat(costoInput.value) || 0;
    const selectedOption = categoriaSelect.options[categoriaSelect.selectedIndex];
    
    if (!selectedOption || !selectedOption.dataset) {
        precioFinalInput.value = '';
        return;
    }
    
    const margen = parseFloat(selectedOption.dataset.margen) || 0;
    if (costo > 0 && margen > 0) {
        const precioFinal = costo * (1 + (margen / 100));
        precioFinalInput.value = precioFinal.toFixed(2);
    } else {
        precioFinalInput.value = '';
    }
}

function formatearComoPesoArgentino(numero) {
    if (isNaN(numero) || numero === null) {
        return '$0,00';
    }
    const formateador = new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    return formateador.format(numero);
}

// AGREGA esta función al final de static/js/buscador.js

async function enviarFijadosAPresupuestos() {
    if (productosFijados.length === 0) {
        alert('No hay productos fijados para enviar.');
        return;
    }
    // Preguntamos al usuario si quiere mantener el margen por categoría (Aceptar) o usar el coeficiente global (Cancelar)
    const mantener = confirm('¿Desea mantener el margen por categoría configurado en cada ítem?\nAceptar: mantener márgenes de categoría.\nCancelar: aplicar el coeficiente global por defecto (1.3).');

    // Construimos el payload para el backend
    const payload = {
        items: productosFijados.map(p => ({
            sitio: p.sitio,
            producto: p.producto,
            precio: p.precio_numeric,         // costo base numérico
            link: p.link,
            categoria_nombre: p.categoriaNombre || null,
            precioVentaCalculado: p.precioVentaCalculado || 0
        })),
        mantenerMarkupPorCategoria: mantener
    };

    try {
        const response = await fetch('/presupuestos/recibir-fijados', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok || data.error) {
            throw new Error(data.error || 'Error inesperado al enviar productos.');
        }
        // Limpiamos los fijados y redirigimos a la página del presupuesto
        productosFijados = [];
        renderizarFijados();
        // data.redirect_url debería indicar a dónde ir; de lo contrario usamos /presupuestos
        window.location.href = data.redirect_url || `/presupuestos?id=${data.presupuesto_id || ''}`;
    } catch (error) {
        console.error('Error al enviar fijados:', error);
        alert(`Hubo un problema al enviar los productos fijados: ${error.message}`);
    }
}


// AGREGA estas funciones al final de static/js/buscador.js

async function abrirModalMayoristas() {
    try {
        const response = await fetch('/api/mayoristas/estado');
        const data = await response.json();
        // Lista fija de mayoristas conocidos (coinciden con los scrapers)
        const sitiosConocidos = ['Invid','Newbytes','AIR','POLYTECH','The Gamer Shop'];
        // Convertimos el array en diccionario para acceso rápido por sitio
        const dictPorSitio = {};
        if (Array.isArray(data)) {
            data.forEach(row => {
                if (row && row.sitio) {
                    dictPorSitio[row.sitio] = row;
                }
            });
        }

        const tbody = document.getElementById('tabla-estado-mayoristas');
        let html = '';
        sitiosConocidos.forEach(sitio => {
            const info = dictPorSitio[sitio] || {};
            const cant = info.cantidad_productos || 0;
            const errores = info.cantidad_errores || 0;
            const fecha = info.ultima_actualizacion
                ? new Date(info.ultima_actualizacion).toLocaleString('es-AR')
                : '-';
            html += `
                <tr>
                    <td>${sitio}</td>
                    <td>${cant}</td>
                    <td>${fecha}</td>
                    <td>${errores}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="actualizarMayorista('${sitio}')">
                            Actualizar ahora
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="verProductosMayorista('{{ sitio }}')">Ver productos</button>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = html;
        const modal = new bootstrap.Modal(document.getElementById('modalMayoristas'));
        modal.show();
    } catch (error) {
        alert('Error al obtener el estado de los mayoristas: ' + error.message);
    }
}


async function actualizarMayorista(sitio) {
    try {
        // Cambiamos el texto del botón para indicar progreso
        const btn = event.target;
        const original = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Actualizando...';
        const response = await fetch(`/api/mayoristas/${encodeURIComponent(sitio)}/actualizar`, {
            method: 'POST'
        });
        const data = await response.json();
        if (data.error) {
            alert(`Error al actualizar ${sitio}: ${data.error}`);
        } else {
            alert(`${sitio} actualizado. Productos insertados: ${data.cantidad_productos}`);
        }
        // Refrescamos la tabla de mayoristas tras actualizar
        await abrirModalMayoristas();
        // Restauramos el texto del botón (en caso de que esté visible)
        btn.disabled = false;
        btn.textContent = original;
    } catch (error) {
        alert('Error al actualizar el mayorista: ' + error.message);
    }
}

async function verProductosMayorista(sitio) {
    try {
        const resp = await fetch(`/api/mayoristas/${encodeURIComponent(sitio)}/productos`);
        const data = await resp.json();
        const tbody = document.getElementById('tabla-productos-mayorista');
        let html = '';
        if (Array.isArray(data) && data.length > 0) {
            data.forEach(item => {
                const fecha = item.actualizado
                    ? new Date(item.actualizado).toLocaleString('es-AR')
                    : '-';
                html += `
                    <tr>
                        <td>${item.producto}</td>
                        <td>${formatearComoPesoArgentino(item.precio)}</td>
                        <td>${fecha}</td>
                    </tr>
                `;
            });
        } else {
            html = `<tr><td colspan="3" class="text-center text-muted">No hay productos para mostrar.</td></tr>`;
        }
        tbody.innerHTML = html;
        document.getElementById('tituloModalProductosMayorista').textContent = `Productos de ${sitio}`;
        const modal = new bootstrap.Modal(document.getElementById('modalProductosMayorista'));
        modal.show();
    } catch (error) {
        alert('Error al obtener los productos del mayorista: ' + error.message);
    }
}
