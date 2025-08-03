// static/js/presupuesto.js

let pollingInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  inicializarPagina();
});

// REEMPLAZAR EN: static/js/presupuesto.js

// REEMPLAZAR EN: static/js/presupuesto.js

function inicializarPagina() {
  limpiarFormulario();
  cargarHistorial(); // Carga el historial completo al iniciar
  
  // Listener para la barra de búsqueda de componentes
  let searchDebounce;
  document.getElementById('producto-search').addEventListener('input', (e) => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
          buscarComponentesSugeridos(e.target.value);
      }, 300);
  });
  
  // Listener para el input de nombre en el modal de creación
  let modalDebounce;
  document.getElementById('nuevo-componente-nombre').addEventListener('input', (e) => {
      clearTimeout(modalDebounce);
      modalDebounce = setTimeout(() => {
          buscarComponentesInternos(e.target.value);
      }, 300);
  });

  // Listener para el campo de descuento
  document.getElementById('descuento').addEventListener('input', actualizarTotales);

  // NUEVO Listener para el buscador del historial
  let historialDebounce;
  document.getElementById('historial-search').addEventListener('input', (e) => {
      clearTimeout(historialDebounce);
      historialDebounce = setTimeout(() => {
          cargarHistorial(e.target.value); // Llama a cargarHistorial con el término de búsqueda
      }, 400); // Espera 400ms antes de buscar
  });
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

function seleccionarProducto(p) {
  const tbody = document.getElementById('tabla-items-presupuesto');
  const newRow = document.createElement('tr');
  
  // CORRECCIÓN: Busca el precio de costo en 'p.precio' (para búsquedas externas)
  // o en 'p.precio_costo' (para componentes internos).
  const precioCosto = parsearMoneda(p.precio || p.precio_costo || 0);
  const markup = p.mark_up || 1.3;
  const precioVenta = precioCosto * markup;
  const iva = p.iva !== undefined ? p.iva : 21;

  newRow.innerHTML = `
      <td data-field="producto">${p.producto}<small class="text-muted d-block">${p.codigo || 'EXTERNO'}</small></td>
      <td><input type="number" class="form-control form-control-sm" value="1" data-field="cantidad" oninput="actualizarTotales()"></td>
      <td><input type="text" class="form-control form-control-sm" value="${formatoArgentino(precioCosto)}" data-field="precio_costo" oninput="actualizarTotales()"></td>
      <td><input type="text" class="form-control form-control-sm" value="${markup.toString().replace('.',',')}" data-field="mark_up" oninput="actualizarTotales()"></td>
      <td><select class="form-select form-select-sm" data-field="iva"><option value="21" ${iva == 21 ? 'selected' : ''}>21%</option><option value="10.5" ${iva == 10.5 ? 'selected' : ''}>10.5%</option><option value="0" ${iva == 0 ? 'selected' : ''}>0%</option></select></td>
      <td class="precio-venta" data-field="precio_venta">${formatoArgentino(precioVenta)}</td>
      <td class="subtotal-item fw-bold"></td>
      <td><button class="btn btn-sm btn-outline-danger" onclick="this.closest('tr').remove(); actualizarTotales();"><i class="fas fa-trash-alt"></i></button></td>
  `;
  
  tbody.appendChild(newRow);
  const modalBusqueda = bootstrap.Modal.getInstance(document.getElementById("modalBusquedaExterna"));
  if(modalBusqueda) modalBusqueda.hide();
  
  actualizarTotales();
}

function actualizarTotales() {
  let subtotalGeneral = 0;
  document.querySelectorAll("#tabla-items-presupuesto tr").forEach(fila => {
      const cantidad = parseInt(fila.querySelector('[data-field="cantidad"]').value) || 0;
      const precioCosto = parsearMoneda(fila.querySelector('[data-field="precio_costo"]').value);
      const markup = parseFloat(fila.querySelector('[data-field="mark_up"]').value.replace(',', '.')) || 1.0;
      
      const precioVenta = precioCosto * markup;
      const subtotalItem = cantidad * precioVenta;
      subtotalGeneral += subtotalItem;

      fila.querySelector('.precio-venta').textContent = formatoArgentino(precioVenta);
      fila.querySelector('.subtotal-item').textContent = formatoArgentino(subtotalItem);
  });

  const descuentoPorc = parseFloat(document.getElementById('descuento').value) || 0;
  const descuentoValor = subtotalGeneral * (descuentoPorc / 100);
  const totalFinal = subtotalGeneral - descuentoValor;

  document.getElementById('subtotal-valor').textContent = formatoArgentino(subtotalGeneral);
  document.getElementById('descuento-valor').textContent = `- ${formatoArgentino(descuentoValor)}`;
  document.getElementById('total-valor').textContent = formatoArgentino(totalFinal);
}

// --- FUNCIONES CRUD (API) Y DE HISTORIAL ---

// REEMPLAZAR EN: static/js/presupuesto.js

// REEMPLAZAR EN: static/js/presupuesto.js

async function guardarPresupuesto() {
  const presupuestoId = document.getElementById('presupuestoId').value;
  const esEdicion = !!presupuestoId;
  
  const items = Array.from(document.getElementById('tabla-items-presupuesto').rows).map(fila => ({
      // ▼▼▼ CORRECCIÓN CLAVE ▼▼▼
      producto: fila.cells[0].childNodes[0].nodeValue.trim().toUpperCase(),
      cantidad: parseInt(fila.querySelector('[data-field="cantidad"]').value),
      precio: parsearMoneda(fila.querySelector('[data-field="precio_costo"]').value),
      iva: parseFloat(fila.querySelector('[data-field="iva"]').value),
      precio_venta: parsearMoneda(fila.querySelector('[data-field="precio_venta"]').textContent),
  }));

  const body = {
      cliente: document.getElementById('cliente').value,
      fecha_emision: document.getElementById('fecha_emision').value,
      fecha_validez: document.getElementById('fecha_validez').value,
      descuento: parseFloat(document.getElementById('descuento').value) || 0,
      total_final: parsearMoneda(document.getElementById('total-valor').textContent),
      items: items,
  };

  const url = esEdicion ? `/api/presupuestos/${presupuestoId}` : '/api/presupuestos';
  const method = esEdicion ? 'PUT' : 'POST';

  try {
      const response = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Error al guardar.');
      alert(`✅ ${data.mensaje}`);
      limpiarFormulario();
      cargarHistorial();
  } catch (error) {
      alert(`❌ Error: ${error.message}`);
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

async function cargarParaEditar(id) {
  try {
      const response = await fetch(`/api/presupuestos/${id}`);
      const data = await response.json();
      
      document.getElementById('presupuestoId').value = data.id;
      document.getElementById('cliente').value = data.cliente;
      // La corrección del backend se encarga de que esto funcione siempre.
      document.getElementById('fecha_emision').value = data.fecha_emision.split('T')[0];
      document.getElementById('fecha_validez').value = data.fecha_validez.split('T')[0];
      document.getElementById('descuento').value = data.descuento || 0;
      
      const tbody = document.getElementById('tabla-items-presupuesto');
      tbody.innerHTML = '';
      data.items.forEach(item => {
           const itemParaTabla = {
               producto: item.producto,
               codigo: item.codigo,
               // --- CORRECCIÓN CLAVE ---
               // Se lee la propiedad 'precio' que viene de la base de datos,
               // en lugar de 'precio_costo' que no existía.
               precio: item.precio,
               iva: item.iva,
               mark_up: item.mark_up
           };
           seleccionarProducto(itemParaTabla);
           const ultimaFila = tbody.lastChild;
           ultimaFila.querySelector('[data-field="cantidad"]').value = item.cantidad;
           ultimaFila.querySelector('[data-field="mark_up"]').value = (item.mark_up || 1.3).toString().replace('.',',');
      });

      actualizarTotales();

      document.getElementById('form-title').textContent = `Editando Presupuesto #${id}`;
      document.getElementById('btn-guardar').textContent = 'Actualizar Presupuesto';
      document.getElementById('btn-cancelar-edicion').style.display = 'inline-block';
      window.scrollTo(0, 0); // Sube al inicio de la página para ver el formulario
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

/**
 * Muestra una lista de sugerencias de componentes internos debajo de la barra de búsqueda.
 */
async function buscarComponentesSugeridos(query) {
  const suggestionsContainer = document.getElementById('search-suggestions');
  if (query.length < 2) {
      suggestionsContainer.innerHTML = '';
      suggestionsContainer.style.display = 'none';
      return;
  }

  const response = await fetch(`/api/componentes?q=${encodeURIComponent(query)}`);
  const componentes = await response.json();
  
  if (componentes.length > 0) {
      suggestionsContainer.innerHTML = componentes.map(c => 
          `<div class="result-item" onclick='seleccionarComponenteSugerido(${JSON.stringify(c)})'>
              <strong>${c.producto}</strong> <span class="text-muted">(${c.codigo})</span>
              <span class="float-end text-success fw-bold">${formatoArgentino(c.precio_venta)}</span>
          </div>`
      ).join('');
      suggestionsContainer.style.display = 'block';
  } else {
      suggestionsContainer.innerHTML = `<div class="result-item text-muted">No se encontraron componentes internos. Haz clic en "Agregar" para buscar en proveedores.</div>`;
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