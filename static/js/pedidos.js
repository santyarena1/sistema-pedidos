// static/js/pedidos.js

// Cargar fecha actual automáticamente
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
  div.className = "row mb-2 align-items-center";
  div.innerHTML = `
    <div class="col-md-6">
      <input name="producto_${index}" class="form-control" placeholder="Producto" required />
    </div>
    <div class="col-md-3">
      <input name="cantidad_${index}" class="form-control" type="number" placeholder="Cantidad" value="1" required />
    </div>
    <div class="col-md-3">
      <input name="precio_${index}" class="form-control" type="number" placeholder="Precio Venta" required />
    </div>
  `;
  container.appendChild(div);
}

function agregarPago() {
  const container = document.getElementById("pagosContainer");
  const index = container.children.length;

  const div = document.createElement("div");
  div.className = "row mb-2 align-items-center";
  div.innerHTML = `
    <div class="col-md-4">
      <select name="metodo_${index}" class="form-select" onchange="toggleCambio(this, ${index})">
        <option>EFECTIVO</option>
        <option>MERCADO PAGO</option>
        <option>TRANSFERENCIA</option>
        <option>USD</option>
        <option>USDT</option>
      </select>
    </div>
    <div class="col-md-4">
      <input name="monto_${index}" type="number" class="form-control" placeholder="Monto" required />
    </div>
    <div class="col-md-4">
      <input name="tipo_cambio_${index}" type="number" class="form-control" placeholder="Tipo de cambio (si aplica)" style="display:none;" />
    </div>
  `;
  container.appendChild(div);
}

function toggleCambio(select, index) {
  const valor = select.value;
  const cambioInput = select.parentElement.parentElement.querySelector(`input[name="tipo_cambio_${index}"]`);
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

  // productos
  document.querySelectorAll("#productosContainer > .row").forEach(row => {
    const [producto, cantidad, precio] = row.querySelectorAll("input");
    pedido.productos.push({
      producto: producto.value,
      cantidad: parseInt(cantidad.value),
      precio_venta: parseFloat(precio.value)
    });
  });

  // pagos
  document.querySelectorAll("#pagosContainer > .row").forEach(row => {
    const metodo = row.querySelector("select").value;
    const monto = parseFloat(row.querySelector("input[name^='monto_']").value);
    const tipo_cambio_input = row.querySelector("input[name^='tipo_cambio_']");
    const tipo_cambio = tipo_cambio_input?.value ? parseFloat(tipo_cambio_input.value) : null;
    pedido.pagos.push({ metodo, monto, tipo_cambio });
  });

  return pedido;
}



// Manejar el envío del formulario
const form = document.getElementById("pedidoForm");
form.addEventListener("submit", async function (e) {
  e.preventDefault();

  const pedido = armarJSONPedido(); // Usamos la función correcta que incluye productos y pagos

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
      alert("✅ Pedido guardado con éxito.");
      form.reset();
    } else {
      alert("❌ Error al guardar: " + (data.error || "Desconocido"));
    }
  } catch (err) {
    console.error("Error al guardar:", err);
    alert("❌ Error de conexión");
  }
});


document.getElementById("generarPedidoBtn").addEventListener("click", async () => {
  const pedido = armarJSONPedido(); // Esto debería generar el JSON con todos los datos del pedido

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
      // Abrir PDF en nueva pestaña
      const pdfURL = `/pedidos/sena/${data.id}`;
      window.open(pdfURL, "_blank");

      alert("✅ Pedido guardado con éxito.");
    } else {
      alert("❌ Error al guardar: " + (data.error || "Desconocido"));
    }
  } catch (err) {
    console.error("Error al guardar:", err);
    alert("❌ Error de conexión");
  }
});

