document.addEventListener("DOMContentLoaded", () => {
    // Inicializa el formulario con la fecha correcta
    const fechaInput = document.querySelector('input[name="fecha_emision"]');
    if (fechaInput) {
        fechaInput.value = getLocalDate();
    }
    
    // Agrega el listener al campo de costo de envío
    const costoEnvioInput = document.querySelector('input[name="costo_envio"]');
    if (costoEnvioInput) {
        costoEnvioInput.addEventListener('input', actualizarTotales);
    }
    
    const form = document.getElementById("pedidoForm");
    form.addEventListener("submit", handleFormSubmit);
});

/**
 * Obtiene la fecha local actual en formato YYYY-MM-DD para evitar errores de zona horaria.
 * @returns {string}
 */
function getLocalDate() {
    const date = new Date();
    // Ajusta la fecha por la diferencia de zona horaria para obtener la fecha local correcta
    const offset = date.getTimezoneOffset();
    const localDate = new Date(date.getTime() - (offset * 60 * 1000));
    return localDate.toISOString().split('T')[0];
}

/**
 * Formatea un número como moneda de pesos argentinos (ARS).
 * @param {number} numero - El número a formatear.
 * @returns {string} - El número formateado como "$ X.XXX,XX".
 */
function formatoPeso(numero) {
    return (parseFloat(numero) || 0).toLocaleString("es-AR", {
        style: "currency",
        currency: "ARS",
    });
}

/**
 * Función para buscar productos y mostrar sugerencias.
 */
async function buscarProductos(inputElement) {
    const query = inputElement.value;
    const suggestionsContainer = inputElement.nextElementSibling;

    if (query.length < 2) {
        suggestionsContainer.innerHTML = '';
        suggestionsContainer.style.display = 'none';
        return;
    }

    try {
        const [componentesRes, stockRes] = await Promise.all([
            fetch(`/api/componentes?q=${query}`),
            fetch(`/api/stock/productos?q=${query}`)
        ]);

        const componentes = await componentesRes.json();
        const stock = await stockRes.json();
        
        const sugerencias = [
            ...componentes.map(p => ({ nombre: p.producto, precio: p.precio_venta })),
            ...stock.map(p => ({ nombre: p.nombre, precio: p.precio_venta_sugerido }))
        ].filter((v, i, a) => a.findIndex(t => (t.nombre === v.nombre)) === i); // Evita duplicados

        if (sugerencias.length === 0) {
            suggestionsContainer.style.display = 'none';
            return;
        }

        suggestionsContainer.innerHTML = sugerencias
            .map(s => `<div class="suggestion-item" onclick="seleccionarSugerencia(this, '${s.nombre.replace(/'/g, "\\'")}', ${s.precio})">${s.nombre} - <b>${formatoPeso(s.precio)}</b></div>`)
            .join('');
        suggestionsContainer.style.display = 'block';
    } catch (error) {
        console.error("Error buscando productos:", error);
        suggestionsContainer.style.display = 'none';
    }
}


/**
 * Rellena el producto y precio al seleccionar una sugerencia.
 */
function seleccionarSugerencia(suggestionElement, nombre, precio) {
    const productoItem = suggestionElement.closest('.producto-item');
    productoItem.querySelector("input[name^='producto_']").value = nombre;
    productoItem.querySelector("input[name^='precio_']").value = precio;
    
    const suggestionsContainer = suggestionElement.parentElement;
    suggestionsContainer.innerHTML = '';
    suggestionsContainer.style.display = 'none';

    actualizarTotales();
}

/**
 * Agrega una nueva fila para un producto en el formulario.
 */
function agregarProducto() {
    const container = document.getElementById("productosContainer");
    const index = container.children.length;
    const div = document.createElement("div");
    div.className = "producto-item";
    div.innerHTML = `
        <button type="button" class="remove-btn" onclick="this.parentElement.remove(); actualizarTotales();">×</button>
        <div class="row g-3">
            <div class="col-md-5 position-relative">
                <input name="producto_${index}" class="form-control" placeholder="Buscar producto..." required oninput="buscarProductos(this)" autocomplete="off" />
                <div class="suggestions-container"></div>
            </div>
            <div class="col-md-2">
                <input name="cantidad_${index}" class="form-control" type="number" placeholder="Cant." value="1" required oninput="actualizarTotales()" />
            </div>
            <div class="col-md-2">
                <input name="precio_${index}" class="form-control" type="number" step="0.01" placeholder="Precio Venta" required oninput="actualizarTotales()" />
            </div>
            <div class="col-md-3">
                <select name="estado_producto_${index}" class="form-select">${listarEstadosProducto('FALTAN ENVIOS')}</select>
            </div>
        </div>
    `;
    container.appendChild(div);
}

/**
 * Agrega una nueva fila para un pago.
 */
function agregarPago() {
    const container = document.getElementById("pagosContainer");
    const index = container.children.length;
    const div = document.createElement("div");
    div.className = "pago-item";
    
    const formasPagoOptions = ["EFECTIVO", "MERCADO PAGO", "TRANSFERENCIA", "USD", "USDT", "PAGO EN TIENDA", "TARJETA", "CUENTA DNI", "CRÉDITO", "OTROS"]
        .map(fp => `<option value="${fp}">${fp}</option>`).join("");

    div.innerHTML = `
        <button type="button" class="remove-btn" onclick="this.parentElement.remove(); actualizarTotales();">×</button>
        <div class="row g-3">
            <div class="col-md-4"><select name="metodo_${index}" class="form-select" onchange="toggleCambio(this, ${index})">${formasPagoOptions}</select></div>
            <div class="col-md-3"><input name="monto_${index}" type="number" step="0.01" class="form-control" placeholder="Monto" required oninput="actualizarTotales()" /></div>
            <div class="col-md-3"><input name="fecha_${index}" type="date" class="form-control" value="${getLocalDate()}" required /></div>
            <div class="col-md-2"><input name="tipo_cambio_${index}" type="number" step="0.01" class="form-control" placeholder="Cambio" style="display:none;" oninput="actualizarTotales()" /></div>
        </div>
    `;
    container.appendChild(div);
}

/**
 * Muestra u oculta el campo de tipo de cambio si el pago es en dólares.
 */
function toggleCambio(select, index) {
    const cambioInput = document.querySelector(`input[name="tipo_cambio_${index}"]`);
    cambioInput.style.display = (select.value === "USD" || select.value === "USDT") ? "block" : "none";
    if (cambioInput.style.display === "none") cambioInput.value = "";
    actualizarTotales();
}

/**
 * Recalcula y muestra todos los totales del pedido en tiempo real.
 */
function actualizarTotales() {
    let totalVenta = 0;
    let totalPagado = 0;

    document.querySelectorAll("#productosContainer .producto-item").forEach(item => {
        const cantidad = parseFloat(item.querySelector("[name^='cantidad_']").value) || 0;
        const precio = parseFloat(item.querySelector("[name^='precio_']").value) || 0;
        totalVenta += cantidad * precio;
    });

    const costoEnvio = parseFloat(document.querySelector("[name='costo_envio']").value) || 0;
    totalVenta += costoEnvio;

    document.querySelectorAll("#pagosContainer .pago-item").forEach(item => {
        const monto = parseFloat(item.querySelector("[name^='monto_']").value) || 0;
        const metodo = item.querySelector("[name^='metodo_']").value;
        if (metodo === 'USD' || metodo === 'USDT') {
            const tc = parseFloat(item.querySelector("[name^='tipo_cambio_']").value) || 1;
            totalPagado += monto * tc;
        } else {
            totalPagado += monto;
        }
    });

    document.getElementById('totalVenta').textContent = formatoPeso(totalVenta);
    document.getElementById('totalPagado').textContent = formatoPeso(totalPagado);
    document.getElementById('saldoRestante').textContent = formatoPeso(totalVenta - totalPagado);
}

/**
 * Genera la lista de opciones de estado para los productos.
 */
function listarEstadosProducto(seleccionado) {
    const estados = ["FALTAN ENVIOS", "PARA HACER", "LISTO", "ENTREGADO", "GARANTIA", "PEDIDO", "REVISADO", "CANCELADO", "EN LA OFICINA", "EN OTRO LOCAL", "NO COBRADO", "PROBLEMAS"];
    return estados.map(e => `<option value="${e}" ${e === seleccionado ? "selected" : ""}>${e}</option>`).join("");
}

/**
 * Recolecta todos los datos del formulario y los prepara para el envío.
 */
function armarJSONPedido() {
    const form = document.getElementById("pedidoForm");
    const formData = new FormData(form);
    const pedido = {
        nombre_cliente: formData.get("nombre_cliente"),
        dni_cliente: formData.get("dni_cliente"),
        email: formData.get("email"),
        telefono: formData.get("telefono"),
        direccion: formData.get("direccion"),
        tipo_factura: formData.get("tipo_factura"),
        fecha_emision: formData.get("fecha_emision"),
        origen_venta: formData.get("origen_venta"),
        vendedor: formData.get("vendedor"),
        forma_envio: formData.get("forma_envio"),
        costo_envio: parseFloat(formData.get("costo_envio") || 0),
        observaciones: formData.get("observaciones"),
        productos: [],
        pagos: []
    };

    document.querySelectorAll("#productosContainer .producto-item").forEach((item, index) => {
        pedido.productos.push({
            producto: item.querySelector(`[name^='producto_']`).value,
            cantidad: parseInt(item.querySelector(`[name^='cantidad_']`).value),
            precio_venta: parseFloat(item.querySelector(`[name^='precio_']`).value),
            estado_producto: item.querySelector(`[name^='estado_producto_']`).value
        });
    });

    document.querySelectorAll("#pagosContainer .pago-item").forEach((item, index) => {
        pedido.pagos.push({
            metodo: item.querySelector(`[name^='metodo_']`).value,
            monto: parseFloat(item.querySelector(`[name^='monto_']`).value),
            fecha: item.querySelector(`[name^='fecha_']`).value,
            tipo_cambio: parseFloat(item.querySelector(`[name^='tipo_cambio_']`).value) || null
        });
    });

    return pedido;
}

/**
 * Maneja el envío del formulario.
 */
async function handleFormSubmit(e) {
    e.preventDefault();
    const pedido = armarJSONPedido();

    if (!pedido.nombre_cliente || pedido.productos.length === 0) {
        alert("❌ Por favor, completa el nombre del cliente y agrega al menos un producto.");
        return;
    }

    if (!confirm("¿Estás seguro de guardar este pedido y generar la constancia?")) return;
    
    document.getElementById("generarPedidoBtn").disabled = true;
    document.getElementById("generarPedidoBtn").textContent = "Guardando...";

    try {
        const res = await fetch("/pedidos", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(pedido)
        });
        const data = await res.json();
        if (res.ok) {
            window.open(`/pedidos/sena/${data.id}`, "_blank");
            alert(`✅ Pedido N°${data.numero} guardado con éxito.`);
            window.location.href = '/pedidos/lista';
        } else {
            throw new Error(data.error || "Error desconocido");
        }
    } catch (err) {
        console.error("Error al guardar:", err);
        alert(`❌ Error al guardar: ${err.message}`);
        document.getElementById("generarPedidoBtn").disabled = false;
        document.getElementById("generarPedidoBtn").textContent = "Guardar y Generar Constancia";
    }
}