// static/js/pedidos.js

window.addEventListener("DOMContentLoaded", () => {
    const hoy = new Date().toISOString().split("T")[0];
    document.querySelector('input[name="fecha_emision"]').value = hoy;
    agregarProducto();
    agregarPago();
});

function agregarProducto() {
    const container = document.getElementById("productosContainer");
    const index = container.children.length;
    const div = document.createElement("div");
    div.className = "producto-item";
    div.innerHTML = `
        <button type="button" class="remove-btn" onclick="this.parentElement.remove()">×</button>
        <div class="row g-3">
            <div class="col-md-6">
                <input name="producto_${index}" class="form-control" placeholder="Producto" required />
            </div>
            <div class="col-md-3">
                <input name="cantidad_${index}" class="form-control" type="number" placeholder="Cantidad" value="1" required />
            </div>
            <div class="col-md-3">
                <input name="precio_${index}" class="form-control" type="number" step="0.01" placeholder="Precio Venta" required />
            </div>
        </div>
    `;
    container.appendChild(div);
}

function agregarPago() {
    const container = document.getElementById("pagosContainer");
    const index = container.children.length;
    const hoy = new Date().toISOString().split("T")[0];
    const div = document.createElement("div");
    div.className = "pago-item";
    
    // SOLUCIÓN: Se usa la función `listarFormasPago` para tener todas las opciones
    const formasPagoOptions = ["EFECTIVO", "MERCADO PAGO", "TRANSFERENCIA", "USD", "USDT", "PAGO EN TIENDA", "TARJETA", "CUENTA DNI", "CRÉDITO", "OTROS"]
        .map(fp => `<option value="${fp}">${fp}</option>`).join("");

    div.innerHTML = `
        <button type="button" class="remove-btn" onclick="this.parentElement.remove()">×</button>
        <div class="row g-3">
            <div class="col-md-4">
                <select name="metodo_${index}" class="form-select" onchange="toggleCambio(this, ${index})">
                    ${formasPagoOptions}
                </select>
            </div>
            <div class="col-md-3">
                <input name="monto_${index}" type="number" step="0.01" class="form-control" placeholder="Monto" required />
            </div>
            <div class="col-md-3">
                <input name="fecha_${index}" type="date" class="form-control" value="${hoy}" required />
            </div>
            <div class="col-md-2">
                <input name="tipo_cambio_${index}" type="number" step="0.01" class="form-control" placeholder="Cambio" style="display:none;" />
            </div>
        </div>
    `;
    container.appendChild(div);
}

function toggleCambio(select, index) {
    const valor = select.value;
    const cambioInput = document.querySelector(`input[name="tipo_cambio_${index}"]`);
    if (valor === "USD" || valor === "USDT") {
        cambioInput.style.display = "block";
    } else {
        cambioInput.style.display = "none";
        cambioInput.value = "";
    }
}

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
        productos: [],
        pagos: []
    };

    document.querySelectorAll("#productosContainer .producto-item").forEach((item, index) => {
        const producto = item.querySelector(`input[name^='producto_']`).value;
        const cantidad = item.querySelector(`input[name^='cantidad_']`).value;
        const precio = item.querySelector(`input[name^='precio_']`).value;
        if (producto && cantidad && precio) {
            pedido.productos.push({
                producto: producto,
                cantidad: parseInt(cantidad),
                precio_venta: parseFloat(precio)
            });
        }
    });

    document.querySelectorAll("#pagosContainer .pago-item").forEach((item, index) => {
        const metodo = item.querySelector(`select[name^='metodo_']`).value;
        const monto = item.querySelector(`input[name^='monto_']`).value;
        const fecha = item.querySelector(`input[name^='fecha_']`).value;
        const tipo_cambio_input = item.querySelector(`input[name^='tipo_cambio_']`);
        const tipo_cambio = tipo_cambio_input?.value ? parseFloat(tipo_cambio_input.value) : null;
        if (metodo && monto && fecha) {
            pedido.pagos.push({ metodo, monto: parseFloat(monto), tipo_cambio, fecha });
        }
    });

    return pedido;
}

// SOLUCIÓN: Usamos solo el evento 'submit' del formulario
const form = document.getElementById("pedidoForm");
form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const pedido = armarJSONPedido();
    if (pedido.productos.length === 0) {
        alert("❌ Debes agregar al menos un producto.");
        return;
    }

    const confirmacion = confirm("¿Estás seguro de guardar este pedido y generar la constancia?");
    if (!confirmacion) return;

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
            form.reset();
            // Limpiamos y re-inicializamos los contenedores
            document.getElementById('productosContainer').innerHTML = '';
            document.getElementById('pagosContainer').innerHTML = '';
            const hoy = new Date().toISOString().split("T")[0];
            document.querySelector('input[name="fecha_emision"]').value = hoy;
            agregarProducto();
            agregarPago();
        } else {
            alert("❌ Error al guardar: " + (data.error || "Desconocido"));
        }
    } catch (err) {
        console.error("Error al guardar:", err);
        alert("❌ Error de conexión al servidor.");
    }
});