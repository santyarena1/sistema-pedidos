//--- Variables Globales ---
let todosLosResultados = []; 
let productosFijados = []; 
let progressInterval = null; 
let productoParaFijar = null;
let estaBuscando = false;
// Nueva variable para controlar el intervalo de sondeo
let pollingInterval = null; 

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

//--- Lógica de Búsqueda con Sondeo Automático ---

/**
 * Función principal que inicia la búsqueda o el sondeo.
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
        document.getElementById("tabla-resultados").innerHTML = `<div class="alert alert-secondary">Ingrese un producto.</div>`;
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
            // Si el backend está trabajando, iniciamos el sondeo
            iniciarSondeoDeResultados(prod, tipo, data.mensaje);
        } else {
            // Si hay resultados directos, los mostramos
            manejarRespuestaFinal(data, prod);
        }
    } catch (error) {
        console.error("Error en buscar():", error);
        manejarRespuestaFinal({ error: "Hubo un problema con la búsqueda." });
    }
}

/**
 * NUEVA FUNCIÓN: Pregunta al servidor cada 4 segundos si ya tiene los resultados.
 */
function iniciarSondeoDeResultados(producto, tipo, mensajeInicial) {
    const tablaDiv = document.getElementById("tabla-resultados");
    tablaDiv.innerHTML = `<div class="alert alert-info">${mensajeInicial}</div>`;
    
    let intentos = 0;
    const maxIntentos = 15; // Intentará durante 60 segundos (15 * 4s)

    pollingInterval = setInterval(async () => {
        console.log(`Intento de sondeo #${intentos + 1} para '${producto}'`);
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

            // Si el estado ya no es 'actualizando', tenemos resultados!
            if (data.estado !== 'actualizando') {
                clearInterval(pollingInterval);
                manejarRespuestaFinal(data, producto);
            }
            // Si sigue actualizando, no hacemos nada y esperamos al siguiente intervalo.
        } catch (error) {
            console.error("Error durante el sondeo:", error);
            clearInterval(pollingInterval);
            manejarRespuestaFinal({ error: "Se perdió la conexión durante la actualización." });
        }
    }, 4000); // Pregunta cada 4 segundos
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


//--- El resto de tus funciones (renderizarResultados, fijarProducto, etc.) se mantienen igual ---
// Pega aquí el resto de tu archivo buscador.js si es necesario, pero la lógica de arriba
// es la que soluciona el problema del bucle y la página "trabada".

function renderizarResultados() {
    const tablaDiv = document.getElementById("tabla-resultados");
    let resultadosFiltrados = [...todosLosResultados];
    const tiendasSeleccionadas = Array.from(document.querySelectorAll('#filtro-tiendas input:checked')).map(cb => cb.value);
    if (tiendasSeleccionadas.length > 0) {
        resultadosFiltrados = resultadosFiltrados.filter(item => tiendasSeleccionadas.includes(item.sitio));
    }
    const precioMin = parseFloat(document.getElementById("precioMin").value) || 0;
    const precioMax = parseFloat(document.getElementById("precioMax").value) || Infinity;
    resultadosFiltrados = resultadosFiltrados.filter(item => {
        const precioNum = parseFloat(String(item.precio || "0").replace(/\$/g, "").replace(/\./g, "").replace(",", "."));
        return precioNum >= precioMin && precioNum <= precioMax;
    });
    const orden = document.getElementById("ordenSelect").value;
    resultadosFiltrados.forEach(item => {
        item.precio_numeric = parseFloat(String(item.precio || "0").replace(/\$/g, "").replace(/\./g, "").replace(",", "."));
    });
    if (orden === "precio_asc") resultadosFiltrados.sort((a, b) => a.precio_numeric - b.precio_numeric);
    else if (orden === "precio_desc") resultadosFiltrados.sort((a, b) => b.precio_numeric - a.precio_numeric);
    else if (orden === "nombre_asc") resultadosFiltrados.sort((a, b) => (a.producto || "").localeCompare(b.producto || ""));
    else if (orden === "nombre_desc") resultadosFiltrados.sort((a, b) => (b.producto || "").localeCompare(a.producto || ""));
    
    let html = `<h4>Resultados de Búsqueda</h4>`;
    if (resultadosFiltrados.length > 0) {
        html += `<table class="table table-hover align-middle mt-3">
                    <thead>
                        <tr>
                            <th style="width: 5%;">Fijar</th>
                            <th style="width: 10%;">Imagen</th>
                            <th style="width: 15%;">Sitio</th>
                            <th style="width: 40%;">Producto</th>
                            <th style="width: 15%;">Precio</th>
                            <th style="width: 5%;">Link</th>
                            <th style="width: 10%;">Agregar</th>
                        </tr>
                    </thead>
                    <tbody>`;
        resultadosFiltrados.forEach(item => {
            const imagenSrc = item.imagen || 'https://via.placeholder.com/150'; 
            html += `<tr>
                <td><button class="btn btn-sm btn-outline-primary" onclick='abrirModalFijar(${JSON.stringify(item)})'><i class="fas fa-thumbtack"></i></button></td>
                <td><img src="${imagenSrc}" alt="${item.producto}" class="img-fluid rounded" style="max-height: 60px;"></td>
                <td>${item.sitio}</td>
                <td>${item.producto || "N/A"}</td>
                <td class="fw-bold">${item.precio || "N/A"}</td>
                <td><a href="${item.link || "#"}" target="_blank" class="btn btn-sm btn-outline-secondary">Ver</a></td>
                <td><button class="btn btn-sm btn-danger" onclick='agregarAlCarrito(${JSON.stringify(item)})'><i class="fas fa-cart-plus"></i></button></td>
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

function renderizarFijados() {
    const container = document.getElementById("productos-fijados-container");
    const divFijados = document.getElementById("productos-fijados");
    if (productosFijados.length === 0) {
        container.style.display = 'none';
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

