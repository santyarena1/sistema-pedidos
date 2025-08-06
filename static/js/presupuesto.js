// static/js/presupuesto.js

let pollingInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  inicializarPagina();
});

// REEMPLAZA ESTA FUNCIÓN EN: static/js/presupuesto.js
function inicializarPagina() {
  limpiarFormulario();
  cargarHistorial();

  // Listener para la barra de búsqueda de componentes
  let searchDebounce;
  document.getElementById('producto-search').addEventListener('input', (e) => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
          buscarComponentesSugeridos(e.target.value);
      }, 300);
  });

  // Listener para el input de nombre en el modal de creación (SE MANTIENE)
  let modalDebounce;
  document.getElementById('nuevo-componente-nombre').addEventListener('input', (e) => {
      clearTimeout(modalDebounce);
      modalDebounce = setTimeout(() => {
          buscarComponentesInternos(e.target.value);
      }, 300);
  });

  document.getElementById('descuento').addEventListener('input', actualizarTotales);

  // Listener para el buscador del historial
  let historialDebounce;
  document.getElementById('historial-search').addEventListener('input', (e) => {
      clearTimeout(historialDebounce);
      historialDebounce = setTimeout(() => {
          cargarHistorial(e.target.value);
      }, 400);
  });

  // INICIALIZACIÓN DE SORTABLEJS (CORRECCIÓN)
  const tbody = document.getElementById('tabla-items-presupuesto');
  if (tbody) {
      new Sortable(tbody, {
          handle: '.drag-handle', // Clase del ícono que usaremos para arrastrar
          animation: 150,
      });
  }
}

async function buscarComponenteInterno(query) {
  // Esta función es muy similar a la de sugerencias, pero crea un modal completo
  const modal = new bootstrap.Modal(document.getElementById("modalBusquedaExterna"));
  const resultsContainer = document.getElementById("resultadosBusquedaExterna");
  
  if (query.length < 2) {
      return;
  }
  
  resultsContainer.innerHTML = `<p class="text-muted">🔄 Buscando en componentes guardados...</p>`;
  modal.show();

  try {
      const response = await fetch(`/api/componentes?q=${encodeURIComponent(query)}`);
      const data = await response.json();

      if (data.error || data.length === 0) {
          resultsContainer.innerHTML = `<p class="alert alert-warning">No se encontraron componentes internos.</p>`;
          return;
      }

      resultsContainer.innerHTML = `
          <table class="table table-sm table-hover">
              <thead><tr><th>Código</th><th>Producto</th><th>Precio Venta</th><th></th></tr></thead>
              <tbody>
                  ${data.map(p => `
                      <tr>
                          <td>${p.codigo}</td>
                          <td>${p.producto}</td>
                          <td class="fw-bold">${formatoArgentino(p.precio_venta)}</td>
                          <td><button class="btn btn-sm btn-red" onclick='seleccionarProducto(${JSON.stringify(p)})'>Seleccionar</button></td>
                      </tr>
                  `).join('')}
              </tbody>
          </table>`;

  } catch (error) {
      console.error("Error en búsqueda interna:", error);
      resultsContainer.innerHTML = `<p class="alert alert-danger">Error al realizar la búsqueda interna.</p>`;
  }
}


function limpiarFormulario() {
  // Restablece los campos del formulario principal
  document.getElementById('presupuestoId').value = '';
  document.getElementById('cliente').value = 'Consumidor Final';
  
  // Establece las fechas de emisión (hoy) y validez (7 días a partir de hoy)
  const hoy = new Date().toISOString().split("T")[0];
  document.getElementById("fecha_emision").value = hoy;
  
  const en7dias = new Date();
  en7dias.setDate(en7dias.getDate() + 7);
  document.getElementById("fecha_validez").value = en7dias.toISOString().split("T")[0];

  // Restablece el descuento y el contenido de la tabla de ítems
  document.getElementById('descuento').value = '0';
  document.getElementById('tabla-items-presupuesto').innerHTML = '';
  
  // Cambia el placeholder de la barra de búsqueda para reflejar su nueva función
  document.getElementById('producto-search').placeholder = 'Buscar componente interno por nombre o código...';

  // Restablece el título del formulario y el texto de los botones
  document.getElementById('form-title').textContent = 'Nuevo Presupuesto';
  document.getElementById('btn-guardar').textContent = 'Guardar Presupuesto';
  document.getElementById('btn-cancelar-edicion').style.display = 'none';

  // Llama a la función para recalcular los totales, dejándolos en cero
  actualizarTotales();
}

// --- LÓGICA DE BÚSQUEDA Y CREACIÓN ---

// REEMPLAZAR EN: static/js/presupuesto.js

/**
 * Busca un producto en proveedores externos y muestra los resultados en un modal.
 */
async function buscarProductoExterno(query) {
  const modal = new bootstrap.Modal(document.getElementById("modalBusquedaExterna"));
  const resultsContainer = document.getElementById("resultadosBusquedaExterna");
  resultsContainer.innerHTML = `<div class="d-flex justify-content-center align-items-center p-5"><div class="spinner-border text-danger" role="status"></div><strong class="ms-3">Iniciando búsqueda en proveedores...</strong></div>`;
  modal.show();

  // Detenemos cualquier sondeo anterior
  if (pollingInterval) clearInterval(pollingInterval);

  try {
      const response = await fetch(`/comparar?producto=${encodeURIComponent(query)}&tipo=masiva`);
      const data = await response.json();

      // Si el backend responde que está actualizando, iniciamos el sondeo
      if (data.estado === 'actualizando') {
          resultsContainer.innerHTML = `<div class="alert alert-info">${data.mensaje} Por favor, espera.</div>`;
          iniciarSondeoDeResultados(query); // Llamamos a la nueva función de sondeo
      } else if (Array.isArray(data)) {
          // Si ya había resultados, los mostramos directamente
          manejarRespuestaFinalBusqueda(data, query);
      } else {
          throw new Error(data.error || "Respuesta inesperada del servidor.");
      }
  } catch (error) {
      resultsContainer.innerHTML = `<p class="alert alert-danger"><b>Error al iniciar la búsqueda:</b> ${error.message}</p>`;
  }
}
let choicesEtiquetas = null;

// REEMPLAZAR EN: static/js/presupuesto.js

async function abrirModalCrearComponente() {
  // Limpiar campos
  document.getElementById('nuevo-componente-nombre').value = '';
  document.getElementById('nuevo-componente-costo').value = '';
  document.getElementById('nuevo-componente-markup').value = '1.3';
  document.getElementById('nuevo-componente-iva').value = '10.5';
  document.getElementById('nuevo-componente-codigo').value = '';
  document.getElementById('sugerencias-componentes').style.display = 'none';

  // Poblar selects de categoría y etiquetas usando la nueva función
  await poblarSelectDinamico('nuevo-componente-categoria', '/api/categorias');
  await poblarSelectEtiquetas();
  
  // (Este listener se mantiene igual)
  document.getElementById('nuevo-componente-categoria').addEventListener('change', async (e) => {
      const categoria = e.target.value;
      if (!categoria) {
          document.getElementById('nuevo-componente-codigo').value = '';
          return;
      }
      const response = await fetch(`/api/componentes/generar-codigo?categoria=${categoria}`);
      const data = await response.json();
      document.getElementById('nuevo-componente-codigo').value = data.codigo || '';
  });
  
  const modal = new bootstrap.Modal(document.getElementById("modalCrearComponente"));
  modal.show();
}

async function poblarSelectEtiquetas() {
  const selectElement = document.getElementById('nuevo-componente-etiquetas');
  if (choicesEtiquetas) {
      choicesEtiquetas.destroy();
  }
  const response = await fetch('/api/etiquetas');
  const etiquetas = await response.json();
  const choicesData = etiquetas.map(et => ({ value: et, label: et }));
  choicesEtiquetas = new Choices(selectElement, {
      removeItemButton: true,
      choices: choicesData
  });
}
async function buscarComponentesInternos(query) {
  const suggestionsContainer = document.getElementById('sugerencias-componentes');
  if (query.length < 2) {
      suggestionsContainer.style.display = 'none';
      return;
  }
  const response = await fetch(`/api/componentes?q=${encodeURIComponent(query)}`);
  const componentes = await response.json();
  if (componentes.length > 0) {
      suggestionsContainer.innerHTML = componentes.map(c => 
          `<div class="result-item" onclick='seleccionarSugerencia(${JSON.stringify(c)})'>
              ${c.producto} <span class="text-muted">(${c.codigo})</span>
          </div>`
      ).join('');
      suggestionsContainer.style.display = 'block';
  } else {
      suggestionsContainer.style.display = 'none';
  }
}

function seleccionarSugerencia(componente) {
  document.getElementById('nuevo-componente-nombre').value = componente.producto;
  document.getElementById('nuevo-componente-costo').value = parseFloat(componente.precio_costo || 0);
  document.getElementById('nuevo-componente-markup').value = parseFloat(componente.mark_up || 1.3);
  document.getElementById('sugerencias-componentes').style.display = 'none';
  limpiarBusqueda();
}

async function crearYAgregarComponente() {
  const payload = {
      producto: document.getElementById('nuevo-componente-nombre').value.trim().toUpperCase(),
      codigo: document.getElementById('nuevo-componente-codigo').value.trim(),
      categoria: document.getElementById('nuevo-componente-categoria').value,
      precio_costo: parseFloat(document.getElementById('nuevo-componente-costo').value) || 0,
      mark_up: parseFloat(document.getElementById('nuevo-componente-markup').value) || 1.3,
      etiquetas: choicesEtiquetas.getValue(true) || []
  };

  if (!payload.producto || !payload.precio_costo || !payload.categoria || !payload.codigo) {
      return alert('Nombre, categoría, código y costo son obligatorios.');
  }
  
  payload.precio_venta = payload.precio_costo * payload.mark_up;

  const response = await fetch('/api/componentes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
  });

  if (response.ok) {
      const iva = parseFloat(document.getElementById('nuevo-componente-iva').value) || 21;
      const productoParaTabla = {
          producto: payload.producto,
          codigo: payload.codigo,
          precio: payload.precio_costo,
          iva: iva,
          mark_up: payload.mark_up
      };
      seleccionarProducto(productoParaTabla);
      bootstrap.Modal.getInstance(document.getElementById("modalCrearComponente")).hide();
  } else {
      alert('Error al crear el nuevo componente.');
  }
}

// --- LÓGICA DE LA TABLA DE ÍTEMS ---

// REEMPLAZA ESTA FUNCIÓN COMPLETA EN: static/js/presupuesto.js

function seleccionarProducto(p) {
    const tbody = document.getElementById('tabla-items-presupuesto');
    const fila = document.createElement('tr');

    // Guardamos los datos clave en el dataset para usarlos al guardar
    fila.dataset.itemId = p.id || '';
    fila.dataset.productoNombre = p.producto;

    // Asignamos los valores por defecto si no vienen del objeto 'p'
    const iva = p.iva !== undefined ? p.iva : 10.5; // IVA por defecto en 10.5%
    const costo = parsearMoneda(p.precio_costo || p.precio || 0);
    const markup = parseFloat(p.mark_up || 1.3);
    const cantidad = p.cantidad || 1;
    const precioVenta = costo * markup; // El IVA es solo visual, no afecta el cálculo

    // Construimos la fila completa con las 9 columnas correctas
    fila.innerHTML = `
        <td class="text-center align-middle drag-handle" title="Arrastrar para reordenar"><i class="fas fa-bars"></i></td>
        <td>
            <span>${p.producto}</span>
            <small class="text-muted d-block">${p.codigo || 'Ítem Temporal'}</small>
        </td>
        <td><input type="number" class="form-control form-control-sm text-center" value="${cantidad}" data-field="cantidad" oninput="actualizarTotales()"></td>
        <td><input type="text" class="form-control form-control-sm text-end" value="${formatoArgentino(costo)}" data-field="precio_costo" oninput="actualizarTotales()"></td>
        <td><input type="text" class="form-control form-control-sm text-center" value="${markup.toFixed(2).replace('.',',')}" data-field="mark_up" oninput="actualizarTotales()"></td>
        <td>
            <select class="form-select form-select-sm" data-field="iva">
                <option value="21" ${iva == 21 ? 'selected' : ''}>21%</option>
                <option value="10.5" ${iva == 10.5 ? 'selected' : ''}>10.5%</option>
                <option value="0" ${iva == 0 ? 'selected' : ''}>0%</option>
            </select>
        </td>
        <td class="precio-venta text-end align-middle fw-bold">${formatoArgentino(precioVenta)}</td>
        <td class="subtotal-item fw-bold text-end align-middle"></td>
        <td class="text-center align-middle">
            <button class="btn btn-sm" onclick="toggleVisibilidad(this.closest('tr'))" title="Ocultar/Mostrar en PDF"><i class="fas fa-eye"></i></button>
            <button class="btn btn-sm text-danger" onclick="this.closest('tr').remove(); actualizarTotales();" title="Eliminar ítem"><i class="fas fa-trash-alt"></i></button>
        </td>
    `;
    
    tbody.appendChild(fila);
    actualizarTotales();

    // Limpiamos la UI de búsqueda después de seleccionar
    document.getElementById('search-suggestions').style.display = 'none';
    document.getElementById('producto-search').value = '';

    const modalBusqueda = bootstrap.Modal.getInstance(document.getElementById("modalBusquedaExterna"));
    if (modalBusqueda) {
        const modalElement = document.getElementById("modalBusquedaExterna");
        if (modalElement && modalElement.classList.contains('show')) {
            modalBusqueda.hide();
        }
    }
}

// REEMPLAZA ESTA FUNCIÓN COMPLETA EN: static/js/presupuesto.js

function actualizarTotales() {
    let subtotalGeneral = 0;
    document.querySelectorAll("#tabla-items-presupuesto tr").forEach(fila => {
        const cantidad = parseInt(fila.querySelector('[data-field="cantidad"]').value) || 1;
        const precioCosto = parsearMoneda(fila.querySelector('[data-field="precio_costo"]').value);
        const markup = parseFloat(fila.querySelector('[data-field="mark_up"]').value.replace(',', '.')) || 1.0;
        
        // CORRECCIÓN: El precio de venta se calcula SIN el IVA.
        const precioVenta = precioCosto * markup;
        const subtotalItem = cantidad * precioVenta;
        subtotalGeneral += subtotalItem;

        fila.querySelector('.precio-venta').textContent = formatoArgentino(precioVenta);
        fila.querySelector('.subtotal-item').textContent = formatoArgentino(subtotalItem);
    });

    const descuento = parseFloat(document.getElementById('descuento').value) || 0;
    const totalFinal = subtotalGeneral - descuento;

    document.getElementById('subtotal-valor').textContent = formatoArgentino(subtotalGeneral);
    document.getElementById('descuento-valor').textContent = `- ${formatoArgentino(descuento)}`;
    document.getElementById('total-valor').textContent = formatoArgentino(totalFinal);
}

// --- FUNCIONES CRUD (API) Y DE HISTORIAL ---

// REEMPLAZA ESTA FUNCIÓN EN: static/js/presupuesto.js
async function guardarPresupuesto() {
    const presupuestoId = document.getElementById('presupuestoId').value;
    const esEdicion = !!presupuestoId;
    
    const body = {
        cliente: document.getElementById('cliente').value,
        fecha_emision: document.getElementById('fecha_emision').value,
        fecha_validez: document.getElementById('fecha_validez').value,
        descuento: parseFloat(document.getElementById('descuento').value) || 0,
        items: []
    };

    document.querySelectorAll("#tabla-items-presupuesto tr").forEach(fila => {
        const ivaField = fila.querySelector('[data-field="iva"]');
        
        body.items.push({
            id: fila.dataset.itemId ? parseInt(fila.dataset.itemId) : null,
            producto: fila.dataset.productoNombre,
            cantidad: parseInt(fila.querySelector('[data-field="cantidad"]').value),
            precio: parsearMoneda(fila.querySelector('[data-field="precio_costo"]').value),
            iva: ivaField ? parseFloat(ivaField.value) : 10.5,
            precio_venta: parsearMoneda(fila.querySelector('.precio-venta').textContent),
            // ▼▼▼ CORRECCIÓN CLAVE ▼▼▼
            // Leemos si la fila tiene la clase 'item-oculto' y enviamos el valor booleano.
            visible_en_pdf: !fila.classList.contains('item-oculto')
        });
    });

    if (body.items.length === 0) {
        return alert("No se puede guardar un presupuesto sin ítems.");
    }

    const url = esEdicion ? `/api/presupuestos/${presupuestoId}` : '/api/presupuestos';
    const method = esEdicion ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Error desconocido al guardar.');
        
        alert(`✅ ${data.mensaje}`);
        limpiarFormulario();
        cargarHistorial();
    } catch (error) {
        console.error("Error al guardar:", error);
        alert(`❌ Error al guardar: ${error.message}`);
    }
}


// REEMPLAZAR EN: static/js/presupuesto.js

async function cargarHistorial(query = '') {
  const historialContainer = document.getElementById('historial-presupuestos');
  historialContainer.innerHTML = '<p class="text-muted">Cargando historial...</p>';
  
  // Construye la URL: si hay query, la añade como parámetro.
  let url = '/api/presupuestos';
  if (query.trim()) {
      url += `?componente=${encodeURIComponent(query.trim())}`;
  }

  try {
      const response = await fetch(url);
      const presupuestos = await response.json();
      renderizarHistorial(presupuestos); // Llama a la nueva función que dibuja las tarjetas
  } catch (error) {
      console.error("Error al cargar historial:", error);
      historialContainer.innerHTML = '<div class="alert alert-danger">No se pudo cargar el historial.</div>';
  }
}

// AGREGAR EN: static/js/presupuesto.js

function renderizarHistorial(presupuestos) {
  const historialContainer = document.getElementById('historial-presupuestos');

  if (!presupuestos || presupuestos.length === 0) {
      historialContainer.innerHTML = '<p class="text-muted">No se encontraron presupuestos que coincidan con la búsqueda.</p>';
      return;
  }

  historialContainer.innerHTML = presupuestos.map(p => `
      <div class="card historial-card">
          <div class="card-header d-flex justify-content-between align-items-center" onclick="toggleDetalle(${p.id})">
              <div>
                  <strong>#${p.id}</strong> - ${p.cliente}
                  <small class="text-muted ms-2">${new Date(p.fecha_emision).toLocaleDateString()}</small>
              </div>
              <div>
                  <span class="badge bg-primary fs-6">${formatoArgentino(p.total_final)}</span>
                  <i class="fas fa-chevron-down ms-2"></i>
              </div>
          </div>
          <div class="collapse" id="detalle-${p.id}">
              <div class="card-body">Cargando...</div>
              <div class="card-footer d-flex gap-2">
                  <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); cargarParaEditar(${p.id})"><i class="fas fa-edit me-1"></i>Editar</button>
                  <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); eliminarPresupuesto(${p.id})"><i class="fas fa-trash-alt me-1"></i>Eliminar</button>
                  <div class="ms-auto">
                      <button class='btn btn-sm btn-success' onclick='event.stopPropagation(); window.open("/presupuestos/pdf/${p.id}")'><i class="fas fa-file-pdf me-1"></i>PDF Det.</button>
                      <button class='btn btn-sm btn-warning' onclick='event.stopPropagation(); window.open("/presupuestos/pdf_simple/${p.id}")'><i class="fas fa-file-alt me-1"></i>PDF Simp.</button>
                  </div>
              </div>
          </div>
      </div>
  `).join('');
}

let openedDetails = null;
function toggleDetalle(id) {
  const currentCollapse = new bootstrap.Collapse(document.getElementById(`detalle-${id}`), { toggle: false });
  
  if (openedDetails && openedDetails._element.id !== `detalle-${id}`) {
      openedDetails.hide();
  }
  
  currentCollapse.toggle();
  openedDetails = currentCollapse;
  cargarDetalle(id);
}


async function cargarDetalle(id) {
  const detalleBody = document.querySelector(`#detalle-${id} .card-body`);
  if (detalleBody.innerHTML !== 'Cargando...') return;
  try {
      const response = await fetch(`/api/presupuestos/${id}`);
      const data = await response.json();
      let itemsHtml = '<ul class="list-group list-group-flush">';
      data.items.forEach(item => {
          itemsHtml += `<li class="list-group-item d-flex justify-content-between">
              <span>${item.cantidad} x ${item.producto}</span>
              <strong>${formatoArgentino(item.precio_venta * item.cantidad)}</strong>
          </li>`;
      });
      itemsHtml += '</ul>';
      detalleBody.innerHTML = itemsHtml;
  } catch (error) {
      detalleBody.innerHTML = '<p class="text-danger">Error al cargar detalles.</p>';
  }
}

// REEMPLAZA ESTA FUNCIÓN EN: static/js/presupuesto.js
// REEMPLAZA ESTA FUNCIÓN COMPLETA EN: static/js/presupuesto.js

async function cargarParaEditar(id) {
    try {
        const response = await fetch(`/api/presupuestos/${id}`);
        const data = await response.json();
        
        // Limpia el formulario y la tabla
        document.getElementById('presupuestoId').value = data.id;
        document.getElementById('cliente').value = data.cliente;
        document.getElementById('fecha_emision').value = data.fecha_emision.split('T')[0];
        document.getElementById('fecha_validez').value = data.fecha_validez.split('T')[0];
        document.getElementById('descuento').value = data.descuento || 0;
        
        const tbody = document.getElementById('tabla-items-presupuesto');
        tbody.innerHTML = '';
        
        // CORRECCIÓN: Ahora llama a la función `seleccionarProducto` para cada ítem,
        // asegurando que se dibuje correctamente, incluyendo el IVA.
        data.items.forEach(item => seleccionarProducto(item));

        actualizarTotales();

        document.getElementById('form-title').textContent = `Editando Presupuesto #${id}`;
        document.getElementById('btn-guardar').textContent = 'Actualizar Presupuesto';
        document.getElementById('btn-cancelar-edicion').style.display = 'inline-block';
        window.scrollTo(0, 0);
    } catch (error) {
        console.error("Error al cargar para editar:", error);
        alert('Error al cargar el presupuesto para editar.');
    }
}

async function eliminarPresupuesto(id) {
  if (!confirm(`¿Estás seguro de que quieres eliminar el presupuesto #${id}?`)) return;
  try {
      const response = await fetch(`/api/presupuestos/${id}`, { method: 'DELETE' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      alert(data.mensaje);
      cargarHistorial();
  } catch (error) {
      alert(`Error: ${error.message}`);
  }
}

// --- Funciones de Utilidad ---

function formatoArgentino(numero) {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(numero || 0);
}

function parsearMoneda(texto) {
  if (typeof texto !== 'string') return parseFloat(texto) || 0;
  return parseFloat(texto.replace(/\$\s?/g, '').replace(/\./g, '').replace(',', '.')) || 0;
}

// AGREGAR EN: static/js/presupuesto.js

// REEMPLAZA ESTA FUNCIÓN EN: static/js/presupuesto.js

async function buscarComponentesSugeridos(query) {
    const suggestionsContainer = document.getElementById('search-suggestions');
    if (query.length < 2) {
        suggestionsContainer.innerHTML = '';
        suggestionsContainer.style.display = 'none';
        return;
    }
  
    // Corregimos la URL para que apunte a la API correcta de componentes
    const response = await fetch(`/api/componentes?q=${encodeURIComponent(query)}`);
    const componentes = await response.json();
    
    if (componentes.length > 0) {
        suggestionsContainer.innerHTML = componentes.map(c => 
            `<div class="result-item" onclick='seleccionarProducto(${JSON.stringify(c)})'>
                <strong>${c.producto}</strong> <span class="text-muted">(${c.codigo})</span>
                <span class="float-end text-success fw-bold">${formatoArgentino(c.precio_venta)}</span>
            </div>`
        ).join('');
        suggestionsContainer.style.display = 'block';
    } else {
        // Si no hay resultados, mostramos un mensaje simple
        suggestionsContainer.innerHTML = `<div class="result-item text-muted">No se encontraron componentes...</div>`;
        suggestionsContainer.style.display = 'block';
    }
  }

/**
* Agrega un componente desde la lista de sugerencias a la tabla del presupuesto.
*/
function seleccionarComponenteSugerido(componente) {
  // CORRECCIÓN: Pasamos el objeto 'componente' completo directamente.
  seleccionarProducto(componente);

  // Limpiamos la búsqueda después de seleccionar
  const suggestionsContainer = document.getElementById('search-suggestions');
  document.getElementById('producto-search').value = '';
  suggestionsContainer.innerHTML = '';
  suggestionsContainer.style.display = 'none';
}

/**
* Lógica del botón "Agregar": si no hay sugerencias, busca en proveedores externos.
*/
function agregarProductoDesdeBarra() {
  const query = document.getElementById('producto-search').value.trim();
  if (!query) return;

  // Si el usuario escribió algo y no seleccionó una sugerencia, busca externamente
  buscarProductoExterno(query);
}

// AGREGAR EN: static/js/presupuesto.js

/**
 * Pregunta al servidor cada 4 segundos si ya tiene los resultados de la búsqueda.
 */
function iniciarSondeoDeResultados(query) {
  let intentos = 0;
  const maxIntentos = 20; // Intentará durante 80 segundos (20 * 4s)

  pollingInterval = setInterval(async () => {
      intentos++;
      if (intentos > maxIntentos) {
          clearInterval(pollingInterval);
          manejarRespuestaFinalBusqueda({ error: "La búsqueda está tardando demasiado. Inténtalo de nuevo." });
          return;
      }

      try {
          const response = await fetch(`/comparar?producto=${encodeURIComponent(query)}&tipo=masiva`);
          const data = await response.json();

          // Si el estado ya no es 'actualizando', ¡tenemos resultados!
          if (data.estado !== 'actualizando') {
              clearInterval(pollingInterval);
              manejarRespuestaFinalBusqueda(data, query);
          }
          // Si sigue actualizando, no hacemos nada y esperamos al siguiente intervalo.
      } catch (error) {
          clearInterval(pollingInterval);
          manejarRespuestaFinalBusqueda({ error: "Se perdió la conexión durante la actualización." });
      }
  }, 4000); // Pregunta cada 4 segundos
}

/**
* Procesa y muestra la respuesta final de la búsqueda en el modal.
*/
function manejarRespuestaFinalBusqueda(data, query) {
  const resultsContainer = document.getElementById("resultadosBusquedaExterna");
  if (data.error || !Array.isArray(data)) {
      resultsContainer.innerHTML = `<p class="alert alert-danger"><b>Error:</b> ${data.error || "No se pudo completar la búsqueda."}</p>`;
      return;
  }
  
  if (data.length === 0) {
      resultsContainer.innerHTML = `<p class="alert alert-warning">No se encontraron productos para "${query}".</p>`;
      return;
  }

  data.sort((a, b) => (parsearMoneda(a.precio) || Infinity) - (parsearMoneda(b.precio) || Infinity));
  
  resultsContainer.innerHTML = `
      <table class="table table-sm table-hover">
          <thead><tr><th>Sitio</th><th>Producto</th><th>Precio</th><th></th></tr></thead>
          <tbody>
              ${data.map(p => `
                  <tr>
                      <td>${p.sitio}</td>
                      <td>${p.producto}</td>
                      <td class="fw-bold">${p.precio}</td>
                      <td><button class="btn btn-sm btn-red" onclick='seleccionarProducto(${JSON.stringify(p)})'>Seleccionar</button></td>
                  </tr>
              `).join('')}
          </tbody>
      </table>`;
}

// AGREGAR EN: static/js/presupuesto.js

/**
 * Función de ayuda para poblar un <select> desde una ruta de la API.
 */
async function poblarSelectDinamico(selectId, apiUrl) {
  try {
      const select = document.getElementById(selectId);
      select.innerHTML = '<option value="">Cargando...</option>';
      const response = await fetch(apiUrl);
      const items = await response.json();
      select.innerHTML = '<option value="">Seleccionar...</option>';
      items.forEach(item => {
          select.innerHTML += `<option value="${item}">${item}</option>`;
      });
  } catch (error) {
      console.error(`Error poblando el select ${selectId}:`, error);
      document.getElementById(selectId).innerHTML = '<option value="">Error al cargar</option>';
  }
}

// AGREGA ESTA NUEVA FUNCIÓN A: static/js/presupuesto.js

function renderizarFilaItem(item) {
    const tbody = document.getElementById('tabla-items-presupuesto');
    const fila = document.createElement('tr');
    
    // Guardamos datos clave en el dataset para usarlos al guardar
    fila.dataset.itemId = item.id || '';
    fila.dataset.productoNombre = item.producto;

    // Asignamos los valores por defecto si no vienen
    const iva = item.iva || 10.5; // Default 10.5%
    const costo = parsearMoneda(item.precio_costo || item.precio || 0);
    const markup = parseFloat(item.mark_up || 1.3);
    const cantidad = item.cantidad || 1;
    const precioVenta = costo * markup; // IVA ya no afecta el precio de venta

    fila.innerHTML = `
        <td class="text-center align-middle drag-handle" title="Arrastrar para reordenar"><i class="fas fa-bars"></i></td>
        <td>
            <span>${item.producto}</span>
            <small class="text-muted d-block">${item.codigo || 'Ítem Temporal'}</small>
        </td>
        <td><input type="number" class="form-control form-control-sm text-center" value="${cantidad}" data-field="cantidad" oninput="actualizarTotales()"></td>
        <td><input type="text" class="form-control form-control-sm text-end" value="${formatoArgentino(costo)}" data-field="precio_costo" oninput="actualizarTotales()"></td>
        <td><input type="text" class="form-control form-control-sm text-center" value="${markup.toFixed(2).replace('.',',')}" data-field="mark_up" oninput="actualizarTotales()"></td>
        <td>
            <select class="form-select form-select-sm" data-field="iva">
                <option value="21" ${iva == 21 ? 'selected' : ''}>21%</option>
                <option value="10.5" ${iva == 10.5 ? 'selected' : ''}>10.5%</option>
                <option value="0" ${iva == 0 ? 'selected' : ''}>0%</option>
            </select>
        </td>
        <td class="precio-venta text-end align-middle fw-bold">${formatoArgentino(precioVenta)}</td>
        <td class="subtotal-item fw-bold text-end align-middle"></td>
        <td class="text-center align-middle">
            <button class="btn btn-sm" onclick="toggleVisibilidad(this.closest('tr'))" title="Ocultar/Mostrar en PDF"><i class="fas fa-eye"></i></button>
            <button class="btn btn-sm text-danger" onclick="this.closest('tr').remove(); actualizarTotales();" title="Eliminar ítem"><i class="fas fa-trash-alt"></i></button>
        </td>
    `;
    tbody.appendChild(fila);
}

/**
* Cambia el estado visual de un ítem para indicar si será visible en el PDF.
*/
function toggleVisibilidad(filaElemento) {
  filaElemento.classList.toggle('item-oculto');
  const esVisible = !filaElemento.classList.contains('item-oculto');
  const eyeIcon = filaElemento.querySelector('.fa-eye, .fa-eye-slash');
  eyeIcon.className = `fas ${esVisible ? 'fa-eye' : 'fa-eye-slash'}`;
}

/**
* Sobreescribe el comportamiento del modal de "Crear Componente" para que funcione
* como un creador de ítems temporales.
*/
function abrirModalItemTemporal() {
  const query = document.getElementById('producto-search').value.trim();
  document.getElementById('nuevo-componente-nombre').value = query; // Rellenar con la búsqueda
  document.getElementById('nuevo-componente-costo').value = '';
  
  // Limpiar sugerencias y mostrar modal
  document.getElementById('search-suggestions').style.display = 'none';
  document.getElementById('producto-search').value = '';
  
  const modal = new bootstrap.Modal(document.getElementById('modalCrearComponente'));
  
  // Cambiamos el comportamiento del botón de guardado del modal
  const saveButton = document.querySelector('#modalCrearComponente .btn-primary');
  saveButton.textContent = 'Agregar Ítem Temporal al Presupuesto';
  saveButton.onclick = () => agregarItemTemporalDirecto(); // Asignamos la nueva función
  
  modal.show();
}

/**
* Recoge los datos del modal y crea un ítem temporal directamente en la tabla.
*/
function agregarItemTemporalDirecto() {
  const nombre = document.getElementById('nuevo-componente-nombre').value;
  const costo = parseFloat(document.getElementById('nuevo-componente-costo').value) || 0;
  const markup = parseFloat(document.getElementById('nuevo-componente-markup').value) || 1.3;
  
  if (!nombre) {
      alert("El nombre del producto es obligatorio.");
      return;
  }

  const item = {
      producto: nombre.toUpperCase(),
      codigo: 'TEMPORAL',
      cantidad: 1,
      precio: costo,
      precio_venta: costo * markup,
      iva: 21,
      visible_en_pdf: true
  };
  
  renderizarFilaItem(item);
  actualizarTotales();

  bootstrap.Modal.getInstance(document.getElementById('modalCrearComponente')).hide();
}

// AGREGA ESTAS NUEVAS FUNCIONES AL FINAL DE: static/js/presupuesto.js

/**
 * Renderiza una única fila en la tabla de ítems. Centraliza la creación del HTML.
 */
function renderizarFilaItem(item) {
  const tbody = document.getElementById('tabla-items-presupuesto');
  const tr = document.createElement('tr');
  
  tr.dataset.itemId = item.id || '';
  tr.dataset.productoNombre = item.producto;
  tr.classList.toggle('item-oculto', !item.visible_en_pdf);

  const markup = (item.precio > 0 ? item.precio_venta / item.precio : (item.mark_up || 1.3)).toFixed(2).replace('.', ',');
  
  tr.innerHTML = `
      <td class="text-center align-middle drag-handle" title="Arrastrar para reordenar"><i class="fas fa-bars"></i></td>
      <td>
          <span>${item.producto}</span>
          <small class="text-muted d-block">${item.codigo || 'Ítem Temporal'}</small>
      </td>
      <td><input type="number" class="form-control form-control-sm text-center" value="${item.cantidad}" data-field="cantidad" oninput="actualizarTotales()"></td>
      <td><input type="text" class="form-control form-control-sm text-end" value="${formatoArgentino(item.precio)}" data-field="precio_costo" oninput="actualizarTotales()"></td>
      <td><input type="text" class="form-control form-control-sm text-center" value="${markup}" data-field="mark_up" oninput="actualizarTotales()"></td>
      <td class="precio-venta text-end align-middle fw-bold">${formatoArgentino(item.precio_venta)}</td>
      <td class="subtotal-item fw-bold text-end align-middle"></td>
      <td class="text-center align-middle">
          <button class="btn btn-sm" onclick="toggleVisibilidad(this.closest('tr'))" title="Ocultar/Mostrar en PDF"><i class="fas ${item.visible_en_pdf ? 'fa-eye' : 'fa-eye-slash'}"></i></button>
          <button class="btn btn-sm text-danger" onclick="this.closest('tr').remove(); actualizarTotales();" title="Eliminar ítem"><i class="fas fa-trash-alt"></i></button>
      </td>
  `;
  tbody.appendChild(tr);
}

/**
* Cambia la visibilidad de un ítem en el PDF (alterna la clase CSS y el ícono).
*/
function toggleVisibilidad(filaElemento) {
  filaElemento.classList.toggle('item-oculto');
  const esVisible = !filaElemento.classList.contains('item-oculto');
  const eyeIcon = filaElemento.querySelector('.fa-eye, .fa-eye-slash');
  eyeIcon.className = `fas ${esVisible ? 'fa-eye' : 'fa-eye-slash'}`;
}

/**
* Agrega un ítem temporal usando un simple 'prompt' para el precio.
*/
function agregarItemTemporalDesdeBusqueda() {
    const nombreProducto = document.getElementById('producto-search').value.trim().toUpperCase();
    if (!nombreProducto) return;

    const precioVenta = parseFloat(prompt(`Introduce el PRECIO DE VENTA para "${nombreProducto}":`));
    if (isNaN(precioVenta) || precioVenta < 0) return;

    seleccionarProducto({
        id: null,
        producto: nombreProducto,
        codigo: 'TEMPORAL',
        precio_costo: 0,
        precio_venta: precioVenta,
        mark_up: 0
    });
}

/**
* Limpia la barra de búsqueda y oculta las sugerencias.
*/
function limpiarBusqueda() {
  document.getElementById('producto-search').value = '';
  document.getElementById('search-suggestions').style.display = 'none';
  document.getElementById('btn-crear-temporal').style.display = 'none';
}


function limpiarBusqueda() {
    document.getElementById('producto-search').value = '';
    document.getElementById('search-suggestions').style.display = 'none';
    const btnCrear = document.getElementById('btn-crear-temporal');
    if (btnCrear) {
        btnCrear.style.display = 'none';
    }
}

// AGREGA ESTAS NUEVAS FUNCIONES A: static/js/presupuesto.js

/**
 * Abre el modal simplificado para crear un ítem temporal.
 * Pre-rellena el nombre si el usuario ya escribió algo en el buscador.
 */
function abrirModalItemTemporal() {
    const nombreProducto = document.getElementById('producto-search').value.trim();
    document.getElementById('nombre-item-temporal').value = nombreProducto;
    document.getElementById('costo-item-temporal').value = '';

    new bootstrap.Modal(document.getElementById('modalCrearItemTemporal')).show();
}

/**
 * Toma los datos del modal simplificado y crea el ítem en la tabla.
 */
function agregarItemTemporalDesdeModal() {
    const nombre = document.getElementById('nombre-item-temporal').value;
    const costo = parseFloat(document.getElementById('costo-item-temporal').value) || 0;

    if (!nombre) {
        alert("El nombre del producto es obligatorio.");
        return;
    }

    seleccionarProducto({
        producto: nombre.toUpperCase(),
        precio_costo: costo
    });

    bootstrap.Modal.getInstance(document.getElementById('modalCrearItemTemporal')).hide();
}