// static/js/simulador.js

(() => {
    const endpoints = window.__SIMULADOR_ENDPOINTS__;
    const elPrecio = document.getElementById('precioBase');
    const filaMpBasico = document.getElementById('fila-mp-basico');
    const filaMpCuotas = document.getElementById('fila-mp-cuotas');
    const filaBbva = document.getElementById('fila-bbva');
  
    const configList = document.getElementById('configList');
    const btnGuardar = document.getElementById('btnGuardarConfig');
  
    const fmtARS = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' });
  
    // Estructura en memoria
    let planes = []; // [{proveedor, plan_codigo, plan_nombre, cuotas, porcentaje, activo}]
  
    // Orden forzado / grupos por fila
    const ORDEN_FILA_1 = ['mp_debito', 'mp_credito'];
    const ORDEN_FILA_2 = ['mp_3', 'mp_6', 'mp_12'];
    const ORDEN_FILA_3 = ['bbva_credito', 'bbva_3_sin', 'bbva_6_sin'];
  
    function cargarConfig() {
      return fetch(endpoints.get)
        .then(r => r.json())
        .then(data => {
          planes = Array.isArray(data) ? data : [];
          renderFilas();
          renderConfig();
        })
        .catch(() => {
          planes = [];
          renderFilas();
          renderConfig();
        });
    }
  
    function getPlan(codigo) {
      return planes.find(p => p.plan_codigo === codigo && p.activo);
    }
  
    function renderFilas() {
      filaMpBasico.innerHTML = '';
      filaMpCuotas.innerHTML = '';
      filaBbva.innerHTML = '';
  
      // FILA 1
      ORDEN_FILA_1.forEach(code => {
        const p = getPlan(code);
        if (p) filaMpBasico.appendChild(crearCard(p));
      });
      // FILA 2
      ORDEN_FILA_2.forEach(code => {
        const p = getPlan(code);
        if (p) filaMpCuotas.appendChild(crearCard(p));
      });
      // FILA 3
      ORDEN_FILA_3.forEach(code => {
        const p = getPlan(code);
        if (p) filaBbva.appendChild(crearCard(p));
      });
  
      recalcular();
    }
  
    function crearCard(plan) {
      const col = document.createElement('div');
      col.className = 'col-12 col-md-6 col-xl-4';
      col.innerHTML = cardHTML(plan);
      return col;
    }
  
    function cardHTML(plan) {
      const badge = plan.proveedor === 'MERCADO_PAGO' ? 'badge-mp' : 'badge-bbva';
      return `
        <div class="card card-plan shadow-sm h-100">
          <div class="card-body">
            <div class="d-flex align-items-center mb-2">
              <span class="badge ${badge} me-2">${plan.proveedor.replace('_', ' ')}</span>
              <h5 class="mb-0">${plan.plan_nombre}</h5>
            </div>
            <div class="small text-muted mb-2">
              ${plan.cuotas > 1 ? (Number(plan.porcentaje) === 0 ? 'SIN INTERÉS' : `${plan.porcentaje}% de recargo`) : `${plan.porcentaje}% de recargo`}
            </div>
            <div class="totales" data-plan="${plan.plan_codigo}">
              <div class="d-flex justify-content-between">
                <span>Total</span>
                <strong class="total-val">—</strong>
              </div>
              ${plan.cuotas > 1 ? `
              <div class="d-flex justify-content-between">
                <span>Cuotas (${plan.cuotas}×)</span>
                <strong class="cuota-val">—</strong>
              </div>` : ``}
            </div>
          </div>
        </div>
      `;
    }
  
    function recalcular() {
      const base = parseFloat(elPrecio.value || '0') || 0;
      document.querySelectorAll('.totales').forEach(div => {
        const codigo = div.dataset.plan;
        const plan = planes.find(p => p.plan_codigo === codigo);
        if (!plan) return;
        const recargo = (parseFloat(plan.porcentaje) || 0) / 100.0;
        const total = base * (1 + recargo);
  
        const elTotal = div.querySelector('.total-val');
        elTotal.textContent = fmtARS.format(total);
  
        const elCuota = div.querySelector('.cuota-val');
        if (elCuota) {
          const c = Math.max(parseInt(plan.cuotas || 1, 10), 1);
          elCuota.textContent = fmtARS.format(total / c);
        }
      });
    }
  
    function renderConfig() {
      // Editor simple agrupado por proveedor
      const grupos = { MERCADO_PAGO: [], BBVA: [] };
      planes.forEach(p => {
        if (grupos[p.proveedor]) grupos[p.proveedor].push(p);
      });
  
      let html = '';
      Object.keys(grupos).forEach(prov => {
        if (!grupos[prov].length) return;
        html += `<h6 class="mt-3">${prov.replace('_',' ')}</h6>`;
        html += `<div class="row g-2">`;
        // Ordenar por cuotas (1,3,6,12)
        grupos[prov].sort((a,b)=> a.cuotas - b.cuotas).forEach(p => {
          html += `
          <div class="col-12 col-md-6">
            <div class="border rounded p-2 d-flex align-items-center gap-2">
              <div class="form-check form-switch me-2">
                <input class="form-check-input cfg-activo" type="checkbox" data-codigo="${p.plan_codigo}" ${p.activo ? 'checked':''}>
              </div>
              <div class="flex-grow-1">
                <div class="small text-muted">${p.plan_nombre} (${p.cuotas}x)</div>
                <div class="input-group input-group-sm">
                  <span class="input-group-text">%</span>
                  <input type="number" class="form-control cfg-porcentaje" data-codigo="${p.plan_codigo}" value="${p.porcentaje}" step="0.1">
                </div>
              </div>
            </div>
          </div>`;
        });
        html += `</div>`;
      });
      configList.innerHTML = html;
    }
  
    function tomarConfigDesdeUI() {
      const porcs = Array.from(document.querySelectorAll('.cfg-porcentaje'));
      const actvs = Array.from(document.querySelectorAll('.cfg-activo'));
      const mapPorc = Object.fromEntries(porcs.map(i => [i.dataset.codigo, parseFloat(i.value || '0') || 0]));
      const mapAct = Object.fromEntries(actvs.map(i => [i.dataset.codigo, !!i.checked]));
      return planes.map(p => ({
        proveedor: p.proveedor,
        plan_codigo: p.plan_codigo,
        plan_nombre: p.plan_nombre,
        cuotas: p.cuotas,
        porcentaje: mapPorc[p.plan_codigo],
        activo: mapAct[p.plan_codigo]
      }));
    }
  
    // Eventos
    elPrecio.addEventListener('input', recalcular);
    btnGuardar.addEventListener('click', () => {
      const payload = tomarConfigDesdeUI();
      fetch(endpoints.put, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      })
      .then(r => r.json())
      .then(() => cargarConfig())
      .then(() => {
        recalcular();
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalConfiguracion'));
        modal && modal.hide();
      })
      .catch(() => alert('No se pudo guardar la configuración.'));
    });
  
    // Init
    cargarConfig();
  })();
  