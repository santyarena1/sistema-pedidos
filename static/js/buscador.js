// MODIFICADO: static/js/buscador.js

document.getElementById("ordenSelect").addEventListener("change", buscar);

document.getElementById("tipoBusqueda").addEventListener("change", buscar); // Para cambiar según tipo

async function buscar() {
  const prod = document.getElementById("producto").value.trim();
  const tipo = document.getElementById("tipoBusqueda").value;
  const tablaDiv = document.getElementById("tabla");

  if (!prod) return;
  tablaDiv.innerHTML = "<p class='text-muted'>🔄 Buscando en tiendas...</p>";

  try {
    const res = await fetch(`/comparar?producto=${encodeURIComponent(prod)}&tipo=${encodeURIComponent(tipo)}`);
    const data = await res.json();

    if (!Array.isArray(data)) throw new Error("La respuesta no es una lista");

    data.forEach(item => {
      item.precio_num = parseFloat(String(item.precio || "").replace("$", "").replace(/\./g, "").replace(",", ".")) || 0;
    });

    const orden = document.getElementById("ordenSelect").value;
    if (orden === "precio_asc") data.sort((a, b) => a.precio_num - b.precio_num);
    else if (orden === "precio_desc") data.sort((a, b) => b.precio_num - a.precio_num);
    else if (orden === "nombre_asc") data.sort((a, b) => a.producto.localeCompare(b.producto));
    else if (orden === "nombre_desc") data.sort((a, b) => b.producto.localeCompare(a.producto));

    let html = `<h4>Resultados para: <span class="text-danger">${prod}</span> (${tipo})</h4>`;
    html += `<table class="table table-bordered mt-3"><thead><tr><th>Sitio</th><th>Producto</th><th>Precio</th><th>Link</th><th>Agregar</th></tr></thead><tbody>`;
    data.forEach(item => {
      html += `<tr>
        <td>${item.sitio}</td>
        <td>${item.producto || "N/A"}</td>
        <td>${item.precio || "N/A"}</td>
        <td><a href="${item.link}" target="_blank" class="btn btn-sm btn-outline-secondary">Ver</a></td>
        <td><button class="btn btn-sm btn-red" onclick='agregarAlCarrito(${JSON.stringify(item)})'><i class="fas fa-cart-plus"></i></button></td>
      </tr>`;
    });
    html += "</tbody></table>";
    tablaDiv.innerHTML = html;

  } catch (err) {
    tablaDiv.innerHTML = `<div class="alert alert-warning">❌ Error de conexión: ${err.message}</div>`;
  }
}

async function agregarAlCarrito(item) {
  const precioLimpio = parseFloat(
    String(item.precio || "").replace("$", "").replace(/\./g, "").replace(",", ".")
  );

  const body = {
    sitio: item.sitio || "Desconocido",
    producto: item.producto || "Sin nombre",
    precio: isNaN(precioLimpio) ? 0 : precioLimpio,
    link: item.link || "#"
  };

  const res = await fetch("/carrito", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });

  if (res.ok) {
    alert("✅ Producto agregado al carrito");
  } else {
    const data = await res.json();
    alert("❌ Error: " + (data?.error || "No se pudo agregar"));
  }
}
