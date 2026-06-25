// =============================================
// MEDICITA - EDITAR CITA (con disponibilidad dinámica)
// =============================================

let especialidadesData = [];
let medicosData        = [];
let citasExistentes    = [];
let selected           = {};
let currentCalendarDateEdit;
let diasDisponiblesEdit  = [];
let horasDisponiblesEdit = [];

document.addEventListener('DOMContentLoaded', function () {
    especialidadesData = JSON.parse(document.getElementById('especialidades-data').textContent);
    medicosData        = JSON.parse(document.getElementById('medicos-data').textContent);
    citasExistentes    = JSON.parse(document.getElementById('citas-existentes-data').textContent);

    selected = {
        especialidad_id: citaActual.especialidad_id,
        medico_id:       citaActual.medico_id,
        fecha:           citaActual.fecha,
        hora:            citaActual.hora
    };

    renderMedicosSelect(selected.especialidad_id, selected.medico_id);

    document.getElementById('select-especialidad').addEventListener('change', function (e) {
        const espId = parseInt(e.target.value);
        selected.especialidad_id = espId;
        document.getElementById('input-especialidad').value = espId;
        renderMedicosSelect(espId, null);
    });

    document.getElementById('select-medico').addEventListener('change', function (e) {
        selected.medico_id = parseInt(e.target.value);
        document.getElementById('input-medico').value = selected.medico_id;
        // Recargar calendario con el nuevo médico
        renderCalendarEdit();
    });

    const [y, m] = citaActual.fecha.split('-').map(Number);
    currentCalendarDateEdit = new Date(y, m - 1, 1);

    renderCalendarEdit();
});

// ==================== MÉDICOS POR ESPECIALIDAD ====================
function renderMedicosSelect(especialidadId, medicoIdToSelect) {
    const select = document.getElementById('select-medico');
    select.innerHTML = '';

    const filtered = medicosData.filter(m => m.especialidad_id == especialidadId);

    if (filtered.length === 0) {
        select.innerHTML = '<option value="">No hay médicos disponibles</option>';
        selected.medico_id = null;
        document.getElementById('input-medico').value = '';
        return;
    }

    filtered.forEach(med => {
        const opt = document.createElement('option');
        opt.value       = med.id;
        opt.textContent = `Dr/a. ${med.nombre}`;
        select.appendChild(opt);
    });

    let medicoFinal = filtered.find(m => m.id == medicoIdToSelect) || filtered[0];
    select.value = medicoFinal.id;
    selected.medico_id = medicoFinal.id;
    document.getElementById('input-medico').value = medicoFinal.id;

    renderCalendarEdit();
}

// ==================== CALENDARIO ====================
async function cargarDiasDisponiblesEdit(year, month) {
    if (!selected.medico_id) return;
    const url = `/citas/api/disponibilidad/${selected.medico_id}/${year}/${month}/`;
    try {
        const resp = await fetch(url);
        const data = await resp.json();
        diasDisponiblesEdit = data.disponibles || [];
    } catch (e) {
        diasDisponiblesEdit = [];
        console.error('Error cargando disponibilidad:', e);
    }
}

async function renderCalendarEdit() {
    const grid    = document.getElementById('calendar-grid-edit');
    const titleEl = document.getElementById('calendar-title-edit');
    if (!grid || !titleEl) return;

    const year  = currentCalendarDateEdit.getFullYear();
    const month = currentCalendarDateEdit.getMonth();

    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:1rem;color:var(--mc-text-muted);"><i class="fas fa-spinner fa-spin"></i></div>';

    await cargarDiasDisponiblesEdit(year, month + 1);

    grid.innerHTML = '';

    const monthNames = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                        'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    titleEl.textContent = `${monthNames[month]} ${year}`;

    ['L','M','M','J','V','S','D'].forEach(d => {
        const h = document.createElement('div');
        h.className   = 'text-center fw-bold small py-1';
        h.style.color = 'var(--mc-text-muted)';
        h.textContent = d;
        grid.appendChild(h);
    });

    const firstDay    = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const startOffset = firstDay === 0 ? 6 : firstDay - 1;

    for (let i = 0; i < startOffset; i++) grid.appendChild(document.createElement('div'));

    const today = new Date(); today.setHours(0,0,0,0);

    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(month+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
        const dayEl   = document.createElement('div');
        dayEl.className = 'calendar-day mx-auto';
        dayEl.textContent = day;

        const dayDate     = new Date(year, month, day);
        const isAvailable = diasDisponiblesEdit.includes(dateStr);
        const isPast      = dayDate < today;

        if (isPast) {
            dayEl.classList.add('disabled');
            dayEl.style.opacity = '0.3';
        } else if (!isAvailable && dateStr !== citaActual.fecha) {
            // La fecha actual de la cita siempre es seleccionable
            dayEl.classList.add('disabled');
        } else {
            if (selected.fecha === dateStr) dayEl.classList.add('selected');
            dayEl.addEventListener('click', () => selectDateEdit(dateStr, dayEl));
        }

        grid.appendChild(dayEl);
    }
}

async function selectDateEdit(dateStr, element) {
    document.querySelectorAll('#calendar-grid-edit .calendar-day').forEach(el => el.classList.remove('selected'));
    element.classList.add('selected');
    selected.fecha = dateStr;
    document.getElementById('input-fecha').value = dateStr;

    // Reset hora al cambiar fecha
    if (dateStr !== citaActual.fecha) {
        selected.hora = null;
        document.getElementById('input-hora').value = '';
    } else {
        selected.hora = citaActual.hora;
        document.getElementById('input-hora').value = citaActual.hora;
    }

    const dateObj   = new Date(dateStr + 'T00:00:00');
    const formatted = dateObj.toLocaleDateString('es-ES', { weekday:'long', day:'numeric', month:'long' });
    document.getElementById('fecha-seleccionada-info').textContent = `Fecha: ${formatted}`;

    await cargarHorasDisponiblesEdit(dateStr);
    renderTimeSlotsEdit();
}

async function cargarHorasDisponiblesEdit(dateStr) {
    if (!selected.medico_id) return;
    const url = `/citas/api/horas/${selected.medico_id}/${dateStr}/`;
    try {
        const resp = await fetch(url);
        const data = await resp.json();
        // Incluir la hora actual de la cita aunque esté ocupada (es de esta cita)
        horasDisponiblesEdit = data.horas || [];
        if (dateStr === citaActual.fecha && !horasDisponiblesEdit.includes(citaActual.hora)) {
            horasDisponiblesEdit.unshift(citaActual.hora);
        }
    } catch (e) {
        horasDisponiblesEdit = [];
        console.error('Error cargando horas:', e);
    }
}

function prevMonthEdit() {
    currentCalendarDateEdit.setMonth(currentCalendarDateEdit.getMonth() - 1);
    renderCalendarEdit();
}

function nextMonthEdit() {
    currentCalendarDateEdit.setMonth(currentCalendarDateEdit.getMonth() + 1);
    renderCalendarEdit();
}

// ==================== HORARIOS ====================
async function renderTimeSlotsEdit() {
    const container = document.getElementById('time-slots-grid-edit');
    container.innerHTML = '';

    // Si no cargó aún, intentar cargar
    if (horasDisponiblesEdit.length === 0 && selected.fecha) {
        await cargarHorasDisponiblesEdit(selected.fecha);
    }

    if (horasDisponiblesEdit.length === 0) {
        container.innerHTML = `
            <div class="w-100 text-center py-3" style="color:var(--mc-text-muted);">
                <i class="fas fa-clock fa-2x mb-2" style="opacity:.3;display:block;"></i>
                No hay horas disponibles para esta fecha.
            </div>`;
        return;
    }

    horasDisponiblesEdit.forEach(time => {
        const btn = document.createElement('button');
        btn.type      = 'button';
        btn.className = 'time-slot btn flex-fill';
        btn.style.minWidth = '72px';
        btn.textContent = time;

        const esHoraPropia  = (selected.fecha === citaActual.fecha && time === citaActual.hora);
        const conflicto     = citasExistentes.some(c => c.fecha === selected.fecha && c.hora === time);
        const ocupado       = conflicto && !esHoraPropia;

        if (ocupado) {
            btn.disabled      = true;
            btn.style.opacity = '0.4';
            btn.title         = 'Ya tienes otra cita a esta hora';
        } else {
            if (selected.hora === time) btn.classList.add('selected');
            btn.addEventListener('click', () => {
                document.querySelectorAll('#time-slots-grid-edit .time-slot').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                selected.hora = time;
                document.getElementById('input-hora').value = time;
            });
        }
        container.appendChild(btn);
    });

    // Marcar la hora actual de la cita si estamos en la misma fecha
    if (selected.fecha === citaActual.fecha && citaActual.hora) {
        const btnActual = Array.from(container.querySelectorAll('.time-slot'))
            .find(b => b.textContent === citaActual.hora);
        if (btnActual && !btnActual.disabled) btnActual.classList.add('selected');
    }
}