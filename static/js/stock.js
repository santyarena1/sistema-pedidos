document.addEventListener("DOMContentLoaded", () => {
    cargarStock();
  });
  
  async function cargarStock() {
    try {
      const res = await fetch("/api/stock");
      const data = await res.json();
      renderizarStock(data);
    } catch (err) {
      console.error("Error al cargar stock:", err);
    }
  }
  
  function renderizarStock(lista) {
    const tbody = document.getElementById("tabla-stock");
    tbody.innerHTML = "";
  
    lista.forEach(item => {
      const fila = document.createElement("tr");
  
      fila.innerHTML = `
        <td>
          <div class="d-flex justify-content-center align-items-center">
            <button class="btn btn-sm btn-outline-secondary me-1" onclick="modificarCantidad(${item.id}, -1)">-</button>
            <input type="number" class="form-control form-control-sm text-center" value="${item.cantidad}" disabled style="width: 60px;">
            <button class="btn btn-sm btn-outline-secondary ms-1" onclick="modificarCantidad(${item.id}, 1)">+</button>
          </div>
        </td>
        <td><input class="form-control form-control-sm" value="${item.codigo || ''}" disabled></td>
        <td><input class="form-control form-control-sm" value="${item.producto || ''}" disabled></td>
        <td><input class="form-control form-control-sm" value="${item.deposito || ''}" disabled></td>
        <td><input type="number" class="form-control form-control-sm" value="${item.precio_venta || ''}" disabled></td>
        <td>${formatearFecha(item.ultima_modificacion)}</td>
        <td><button class="btn btn-sm btn-secondary" onclick="activarEdicion(this, ${item.id})">Editar</button></td>
      `;
  
      fila.dataset.id = item.id;
      tbody.appendChild(fila);
    });
  }
  
  function activarEdicion(btn, id) {
    const fila = btn.closest("tr");
    const inputs = fila.querySelectorAll("input");
    inputs.forEach(input => input.disabled = false);
  
    btn.textContent = "Guardar";
    btn.classList.remove("btn-secondary");
    btn.classList.add("btn-success");
    btn.onclick = () => guardarEdicion(fila, id);
  
    const cancelar = document.createElement("button");
    cancelar.className = "btn btn-sm btn-outline-danger ms-1";
    cancelar.textContent = "Cancelar";
    cancelar.onclick = () => cargarStock();
    btn.parentNode.appendChild(cancelar);
  }
  
  async function guardarEdicion(fila, id) {
    const inputs = fila.querySelectorAll("input");
    const [cantidadInput, codigoInput, productoInput, depositoInput, precioInput] = inputs;
  
    if (!confirm("¿Estás seguro de guardar los cambios?")) return;
  
    const payload = {
      cantidad: parseInt(cantidadInput.value) || 0,
      codigo: codigoInput.value.trim(),
      producto: productoInput.value.trim(),
      deposito: depositoInput.value.trim(),
      precio_venta: parseFloat(precioInput.value) || 0
    };
  
    const res = await fetch(`/api/stock/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  
    if (res.ok) cargarStock();
    else alert("Error al guardar cambios");
  }
  
  function modificarCantidad(id, delta) {
    const fila = document.querySelector(`tr[data-id='${id}']`);
    const input = fila.querySelector("td input[type='number']");
    input.value = parseInt(input.value) + delta;
  }
  
  function filtrarStock() {
    const texto = document.getElementById("busquedaStock").value.toLowerCase();
    const filas = document.querySelectorAll("#tabla-stock tr");
  
    filas.forEach(fila => {
      const celdas = fila.querySelectorAll("input");
      const coincide = Array.from(celdas).some(input => input.value.toLowerCase().includes(texto));
      fila.style.display = coincide ? "" : "none";
    });
  }
  
  function abrirModalProducto() {
    const modal = new bootstrap.Modal(document.getElementById("modalProducto"));
    document.getElementById("nuevoCodigo").value = "";
    document.getElementById("nuevoProducto").value = "";
    document.getElementById("nuevoDeposito").value = "";
    document.getElementById("nuevoCantidad").value = "";
    document.getElementById("nuevoPrecio").value = "";
    modal.show();
  }
  
  async function confirmarAgregarProducto() {
    if (!confirm("¿Estás seguro de agregar este producto?")) return;
  
    const payload = {
      codigo: document.getElementById("nuevoCodigo").value.trim(),
      producto: document.getElementById("nuevoProducto").value.trim(),
      deposito: document.getElementById("nuevoDeposito").value.trim(),
      cantidad: parseInt(document.getElementById("nuevoCantidad").value) || 0,
      precio_venta: parseFloat(document.getElementById("nuevoPrecio").value) || 0
    };
  
    const res = await fetch("/api/stock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  
    if (res.ok) {
      bootstrap.Modal.getInstance(document.getElementById("modalProducto")).hide();
      cargarStock();
    } else {
      alert("Error al agregar producto");
    }
  }
  
  async function confirmarEliminarProducto() {
    const codigo = document.getElementById("nuevoCodigo").value.trim();
    if (!codigo) return alert("Ingresá un código para eliminar");
    if (!confirm("¿Estás seguro de eliminar este producto?")) return;
  
    const res = await fetch(`/api/stock?codigo=${encodeURIComponent(codigo)}`, { method: "DELETE" });
    if (res.ok) {
      bootstrap.Modal.getInstance(document.getElementById("modalProducto")).hide();
      cargarStock();
    } else {
      alert("No se pudo eliminar el producto");
    }
  }
  
  function abrirModalHistorial() {
    fetch("/api/stock/historial")
      .then(res => res.json())
      .then(data => {
        const tbody = document.getElementById("tabla-historial");
        tbody.innerHTML = "";
        data.forEach(mov => {
          const fila = document.createElement("tr");
          fila.innerHTML = `
            <td>${formatearFecha(mov.fecha)}</td>
            <td>${mov.accion}</td>
            <td>${mov.producto}</td>
            <td>${mov.codigo}</td>
            <td>${mov.campo}</td>
            <td>${mov.valor_anterior || "-"}</td>
            <td>${mov.valor_nuevo || "-"}</td>
          `;
          tbody.appendChild(fila);
        });
        new bootstrap.Modal(document.getElementById("modalHistorial")).show();
      });
  }
  
  function formatearFecha(fechaISO) {
    if (!fechaISO) return "-";
    const f = new Date(fechaISO);
    return f.toLocaleDateString("es-AR") + " " + f.toLocaleTimeString("es-AR", { hour: '2-digit', minute: '2-digit' });
  }