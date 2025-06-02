// static/js/componentes_presupuesto.js

let categoriasGlobal = [];
let etiquetasGlobal = [];
let editando = false;
let contadorCodigos = {}; // para código incremental por categoría

// Formateadores de moneda
function formatCurrency(valor) {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(valor || 0);
}

function parseCurrency(valor) {
    // Elimina todo menos números y comas/puntos
    valor = (valor || "").replace(/[^0-9,\.]/g, "");
  
    // Si tiene coma como separador decimal, lo convertimos
    if (valor.includes(",")) {
      valor = valor.replace(/\./g, "");         // quita miles
      valor = valor.replace(",", ".");          // cambia decimal
    } else {
      valor = valor.replace(/\./g, "");         // solo quita miles
    }
  
    return parseFloat(valor) || 0;
  }
  

document.addEventListener("DOMContentLoaded", async () => {
  await cargarCategorias();
  await cargarEtiquetas();
  await cargarComponentes();
});

async function cargarComponentes() {
  const res = await fetch("/api/componentes");
  const data = await res.json();

  data.forEach(c => {
    const pref = c.categoria.slice(0, 3).toUpperCase();
    const num = parseInt(c.codigo.slice(3)) || 0;
    if (!contadorCodigos[pref] || num >= contadorCodigos[pref]) {
      contadorCodigos[pref] = num + 1;
    }
  });

  renderTabla(data);
}

async function cargarCategorias() {
  const res = await fetch("/api/categorias");
  categoriasGlobal = await res.json();
  renderListaCategorias();
}

async function cargarEtiquetas() {
  const res = await fetch("/api/etiquetas");
  etiquetasGlobal = await res.json();
  renderListaEtiquetas();
}

function generarCodigo(categoria) {
  const prefijo = categoria.slice(0, 3).toUpperCase();
  if (!contadorCodigos[prefijo]) contadorCodigos[prefijo] = 1;
  const codigo = `${prefijo}${contadorCodigos[prefijo].toString().padStart(3, '0')}`;
  contadorCodigos[prefijo]++;
  return codigo;
}

function renderTabla(componentes) {
  const cuerpo = document.getElementById("cuerpo-tabla");
  cuerpo.innerHTML = "";

  componentes.forEach(comp => {
    const fila = document.createElement("tr");
    fila.innerHTML = `
        <td><input class="form-control form-control-sm" value="${comp.codigo}" disabled></td>
        <td>
        <select class="form-select form-select-sm" disabled>
            ${categoriasGlobal.map(cat => `<option ${comp.categoria === cat ? "selected" : ""}>${cat}</option>`).join("")}
        </select>
        </td>
        <td><input class="form-control form-control-sm" value="${comp.producto}" disabled></td>
        <td><input class="form-control form-control-sm" value="${formatCurrency(comp.precio_costo)}" disabled></td>
        <td><input class="form-control form-control-sm" value="${(comp.mark_up && comp.mark_up !== 0 ? comp.mark_up.replace(".", ",") : "1,3")}" disabled></td>
        <td><input class="form-control form-control-sm" value="${formatCurrency(comp.precio_venta)}" disabled></td>
        <td><div>${(comp.etiquetas || []).map(e => `<span class='badge bg-secondary me-1 fs-6'>${e}</span>`).join("")}</div></td>
        <td>
        <button class="btn btn-sm btn-outline-secondary" onclick="editarFila(this)">✏️</button>
        <button class="btn btn-sm btn-outline-success d-none" onclick="guardarFila(this, ${comp.id})">💾</button>
      </td>
      <td><button class="btn btn-sm btn-outline-danger" onclick="eliminarComponente(${comp.id})">🗑️</button></td>
    `;
    cuerpo.appendChild(fila);
  });
}

async function eliminarComponente(id) {
    if (!confirm("¿Eliminar componente?")) return;
    const res = await fetch(`/api/componentes/${id}`, { method: "DELETE" });
    const data = await res.json();
    if (data.error) return alert("❌ Error: " + data.error);
    
    cargarComponentes();
  }
  
async function guardarFila(btn, id) {
    const fila = btn.closest("tr");
    const inputs = fila.querySelectorAll("input, select");
    const tags = Array.from(fila.querySelectorAll("select[multiple] option:checked")).map(o => o.value);
  
    const body = {
      codigo: inputs[0].value,
      categoria: inputs[1].value,
      producto: inputs[2].value.toUpperCase(),
      precio_costo: parseCurrency(inputs[3].value),
      mark_up: parseFloat(inputs[4].value.replace(",", ".")) || 1.3,
      precio_venta: parseCurrency(inputs[5].value),
      etiquetas: tags
    };
  
    const res = await fetch(`/api/componentes/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
  
    const data = await res.json();
    if (data.error) return alert("❌ Error: " + data.error);
  
    alert("✅ Componente actualizado");
    cargarComponentes();
    editando = false;
  }

  function editarFila(btn) {
    const fila = btn.closest("tr");
    fila.querySelectorAll("input, select").forEach(el => el.disabled = false);
    btn.classList.add("d-none");
    btn.nextElementSibling.classList.remove("d-none");
    editando = true;
  
    const producto = fila.cells[2].querySelector("input");
    const costo = fila.cells[4].querySelector("input");
    const markup = fila.cells[3].querySelector("input");
    const venta = fila.cells[5].querySelector("input");
    
  
    producto.addEventListener("input", () => {
      producto.value = producto.value.toUpperCase();
    });
  
    const updateVenta = () => {
      const costoVal = parseCurrency(costo.value);
      const markupVal = parseFloat(markup.value.replace(",", ".")) || 1.3;
      const ventaVal = costoVal * markupVal;
      venta.value = formatCurrency(ventaVal);
    };
  
    // ⚠️ Importante: disparar la función al modificar costo o markup
    costo.addEventListener("input", () => {
      costo.value = formatCurrency(parseCurrency(costo.value));
      updateVenta();
    });
  
    markup.addEventListener("input", () => {
        updateVenta();
      });
      
      
    
    if (!markup.value || parseFloat(markup.value.replace(",", ".")) === 0) {
        markup.value = "1,3";
    }
    updateVenta();
            

  
  }
  
  
  

function agregarFilaNueva() {
  const cuerpo = document.getElementById("cuerpo-tabla");
  const fila = document.createElement("tr");
  fila.innerHTML = `
    <td><input class="form-control form-control-sm" placeholder="Generado" readonly></td>
    <td>
      <select class="form-select form-select-sm" onchange="asignarCodigo(this)">
        <option value="">Seleccionar</option>
        ${categoriasGlobal.map(cat => `<option>${cat}</option>`).join("")}
      </select>
    </td>
    <td><input class="form-control form-control-sm"></td>
    <td><input class="form-control form-control-sm" placeholder="$0.00"></td>
    <td><input class="form-control form-control-sm" value="1,3"></td>
    <td><input class="form-control form-control-sm" placeholder="$0.00"></td>
    <td><select class="form-select w-100 form-select-lg" multiple></select></td>
    <td><button class="btn btn-sm btn-outline-success" onclick="guardarNuevoComponente(this)">💾</button></td>
    <td><button class="btn btn-sm btn-outline-danger" onclick="this.closest('tr').remove()">❌</button></td>
  `;
  cuerpo.prepend(fila);

  
  const costo = fila.cells[4].querySelector("input");
  const markup = fila.cells[3].querySelector("input");
  const venta = fila.cells[5].querySelector("input");
  

  const updateVenta = () => {
    const costoVal = parseCurrency(costo.value);
    const markupVal = parseFloat(markup.value.replace(",", ".")) || 1.3;
    const ventaVal = costoVal * markupVal;
    venta.value = formatCurrency(ventaVal);
  };

  costo.addEventListener("input", () => {
    costo.value = formatCurrency(parseCurrency(costo.value));
    updateVenta();
  });
  markup.addEventListener("input", updateVenta);
  costo.dispatchEvent(new Event("input"));

  const etiquetasSelect = fila.querySelector("select[multiple]");
  etiquetasGlobal.forEach(et => {
    const opt = document.createElement("option");
    opt.value = et;
    opt.textContent = et;
    etiquetasSelect.appendChild(opt);
  });
  new Choices(etiquetasSelect, { removeItemButton: true, duplicateItemsAllowed: false });
}

function asignarCodigo(select) {
  const fila = select.closest("tr");
  const codigoInput = fila.querySelector("td input");
  const cat = select.value;
  if (!cat) return;
  const generado = generarCodigo(cat);
  codigoInput.value = generado;
  codigoInput.readOnly = false;
}

async function guardarNuevoComponente(btn) {
  const fila = btn.closest("tr");
  const inputs = fila.querySelectorAll("input, select");
  const tags = Array.from(inputs[6].selectedOptions).map(o => o.value);

  const body = {
    codigo: inputs[0].value,
    categoria: inputs[1].value,
    producto: inputs[2].value.toUpperCase(),
    precio_costo: parseCurrency(inputs[3].value),
    mark_up: parseFloat(inputs[4].value.replace(",", ".")) || 1.3,
    precio_venta: parseCurrency(inputs[5].value),
    etiquetas: tags
  };

  const res = await fetch("/api/componentes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await res.json();
  if (data.error) return alert("❌ Error: " + data.error);
  alert("✅ Componente agregado");
  cargarComponentes();
}

function filtrarTabla() {
  const filtro = document.getElementById("busqueda").value.toLowerCase();
  document.querySelectorAll("#cuerpo-tabla tr").forEach(tr => {
    const texto = tr.innerText.toLowerCase();
    tr.style.display = texto.includes(filtro) ? "" : "none";
  });
}

function renderListaCategorias() {
  const ul = document.getElementById("listaCategorias");
  if (!ul) return;
  ul.innerHTML = categoriasGlobal.map(cat => `
    <li class="list-group-item d-flex justify-content-between align-items-center">
      ${cat}
      <button class="btn btn-sm btn-danger" onclick="eliminarCategoria('${cat}')">🗑️</button>
    </li>
  `).join("");
}

function renderListaEtiquetas() {
  const ul = document.getElementById("listaEtiquetas");
  if (!ul) return;
  ul.innerHTML = etiquetasGlobal.map(et => `
    <li class="list-group-item d-flex justify-content-between align-items-center">
      ${et}
      <button class="btn btn-sm btn-danger" onclick="eliminarEtiqueta('${et}')">🗑️</button>
    </li>
  `).join("");
}

async function eliminarCategoria(nombre) {
  if (!confirm(`¿Eliminar la categoría "${nombre}"?`)) return;
  const res = await fetch(`/api/categorias`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre })
  });
  const data = await res.json();
  if (data.error) return alert("❌ " + data.error);
  categoriasGlobal = categoriasGlobal.filter(c => c !== nombre);
  renderListaCategorias();
  alert("✅ Categoría eliminada");
}

async function eliminarEtiqueta(nombre) {
  if (!confirm(`¿Eliminar la etiqueta "${nombre}"?`)) return;
  const res = await fetch(`/api/etiquetas`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre })
  });
  const data = await res.json();
  if (data.error) return alert("❌ " + data.error);
  etiquetasGlobal = etiquetasGlobal.filter(e => e !== nombre);
  renderListaEtiquetas();
  alert("✅ Etiqueta eliminada");
}

function crearEtiqueta() {
    const nueva = document.getElementById("inputNuevaEtiqueta").value.trim();
    if (!nueva || etiquetasGlobal.includes(nueva)) return;
    
    fetch("/api/etiquetas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre: nueva })
    }).then(res => res.json()).then(data => {
      if (data.error) return alert("❌ " + data.error);
      etiquetasGlobal.push(nueva);
      renderListaEtiquetas();
      document.getElementById("inputNuevaEtiqueta").value = "";
      alert("✅ Etiqueta agregada");
    });
  }

  function crearCategoria() {
    const nueva = document.getElementById("inputNuevaCategoria").value.trim();
    if (!nueva || categoriasGlobal.includes(nueva)) return;
  
    fetch("/api/categorias", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre: nueva })
    })
    .then(res => res.json())
    .then(data => {
      if (data.error) return alert("❌ " + data.error);
      categoriasGlobal.push(nueva);
      renderListaCategorias();
      document.getElementById("inputNuevaCategoria").value = "";
      alert("✅ Categoría agregada");
    });
  }
  
  
