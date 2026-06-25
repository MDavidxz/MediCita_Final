// =============================================
// MEDICITA - WIZARD FUNCIONAL CON DJANGO
// =============================================

document.addEventListener('DOMContentLoaded', function () {
    initWizard();
});

let currentStep = 1;
let selected = {
    especialidad_id: null,
    medico_id: null,
    fecha: null,
    hora: null
};

let especialidadesData = [];
let medicosData = [];
let citasExistentesData = [];

// Calendario
let currentCalendarDate = new Date();
currentCalendarDate.setDate(1);

let diasDisponibles = [];   // fechas 'YYYY-MM-DD' del médico seleccionado
let horasDisponibles = [];  // horas del día seleccionado

function initWizard() {
    especialidadesData   = JSON.parse(document.getElementById('especialidades-data').textContent);
    medicosData          = JSON.parse(document.getElementById('medicos-data').textContent);
    citasExistentesData  = JSON.parse(document.getElementById('citas-existentes-data').textContent);
    renderEspecialidades();
}

// ==================== ESPECIALIDADES ====================
function renderEspecialidades() {
    const container = document.getElementById('especialidades-grid');
    if (!container) return;
    container.innerHTML = '';

    if (especialidadesData.length === 0) {
        container.innerHTML = '<p class="text-danger">No hay especialidades registradas.</p>';
        return;
    }

    especialidadesData.forEach(esp => {
        const col = document.createElement('div');
        col.className = 'col';
        col.innerHTML = `
            <div class="specialty-card h-100" data-id="${esp.id}">
                <i class="fas ${esp.icono || 'fa-stethoscope'}"></i>
                <h6 class="fw-semibold mb-0">${esp.nombre}</h6>
                <div class="check-icon"><i class="fas fa-check fa-sm"></i></div>
            </div>
        `;
        const card = col.querySelector('.specialty-card');
        card.addEventListener('click', () => selectEspecialidad(esp.id, card));
        container.appendChild(col);
    });
}

function selectEspecialidad(id, cardElement) {
    document.querySelectorAll('#especialidades-grid .specialty-card').forEach(c => c.classList.remove('selected'));
    cardElement.classList.add('selected');
    selected.especialidad_id = id;
    document.getElementById('btn-next-1').disabled = false;
}

// ==================== MÉDICOS ====================
function renderMedicos(especialidadId) {
    const container = document.getElementById('medicos-list');
    container.innerHTML = '';

    const filtered = medicosData.filter(m => m.especialidad_id == especialidadId);

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4" style="color:var(--mc-text-muted);">
                <i class="fas fa-user-md fa-2x mb-2" style="opacity:.3;"></i>
                <p>No hay médicos disponibles para esta especialidad.</p>
            </div>`;
        return;
    }

    filtered.forEach(med => {
        const div = document.createElement('div');
        div.className = 'doctor-card d-flex align-items-center gap-3';

        const avatarHtml = med.foto
            ? `<img src="${med.foto}" class="rounded-circle border" width="56" height="56" style="object-fit:cover;">`
            : `<div style="width:56px;height:56px;border-radius:50%;background:var(--mc-primary-soft);display:flex;align-items:center;justify-content:center;font-size:1.3rem;color:var(--mc-primary);flex-shrink:0;"><i class="fas fa-user-md"></i></div>`;

        div.innerHTML = `
            ${avatarHtml}
            <div class="flex-grow-1">
                <div class="fw-bold" style="color:var(--mc-text);">${med.nombre}</div>
                <div class="small" style="color:var(--mc-text-muted);">${med.especialidad || ''}</div>
                ${med.descripcion ? `<div class="small mt-1" style="color:var(--mc-text-muted);font-style:italic;">"${med.descripcion}"</div>` : ''}
            </div>
            <div style="font-size:.75rem;color:var(--mc-primary);font-weight:600;">
                <i class="fas fa-id-card me-1"></i>${med.licencia || ''}
            </div>
        `;
        div.addEventListener('click', () => selectMedico(med.id, div));
        container.appendChild(div);
    });
}

function selectMedico(id, element) {
    document.querySelectorAll('#medicos-list .doctor-card').forEach(el => el.classList.remove('selected'));
    element.classList.add('selected');
    selected.medico_id = id;
    document.getElementById('btn-next-2').disabled = false;
}

// ==================== CALENDARIO ====================
async function cargarDiasDisponibles(year, month) {
    if (!selected.medico_id) return;
    const url = `/citas/api/disponibilidad/${selected.medico_id}/${year}/${month}/`;
    try {
        const resp = await fetch(url);
        const data = await resp.json();
        diasDisponibles = data.disponibles || [];
    } catch (e) {
        diasDisponibles = [];
        console.error('Error cargando disponibilidad:', e);
    }
}

async function renderCalendar() {
    const grid    = document.getElementById('calendar-grid');
    const titleEl = document.getElementById('calendar-title');
    if (!grid || !titleEl) return;

    const year  = currentCalendarDate.getFullYear();
    const month = currentCalendarDate.getMonth();

    // Mostrar loading
    grid.innerHTML = '<div class="text-center py-3" style="grid-column:1/-1;color:var(--mc-text-muted);"><i class="fas fa-spinner fa-spin"></i></div>';

    await cargarDiasDisponibles(year, month + 1);

    grid.innerHTML = '';

    const monthNames = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                        'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    titleEl.textContent = `${monthNames[month]} ${year}`;

    // Cabeceras días
    ['L','M','M','J','V','S','D'].forEach(d => {
        const h = document.createElement('div');
        h.className = 'text-center fw-bold small py-1';
        h.style.color = 'var(--mc-text-muted)';
        h.textContent = d;
        grid.appendChild(h);
    });

    const firstDay    = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const startOffset = firstDay === 0 ? 6 : firstDay - 1;

    for (let i = 0; i < startOffset; i++) grid.appendChild(document.createElement('div'));

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(month + 1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
        const dayEl   = document.createElement('div');
        dayEl.className = 'calendar-day mx-auto';
        dayEl.textContent = day;

        const dayDate     = new Date(year, month, day);
        const isAvailable = diasDisponibles.includes(dateStr);
        const isPast      = dayDate < today;
        const isTaken     = citasExistentesData.some(c => c.fecha === dateStr);

        if (isPast) {
            dayEl.classList.add('disabled');
            dayEl.style.opacity = '0.3';
        } else if (!isAvailable) {
            dayEl.classList.add('disabled');
        } else if (isTaken) {
            // Tiene cita propia ese día pero puede haber otras horas
            if (selected.fecha === dateStr) dayEl.classList.add('selected');
            dayEl.addEventListener('click', () => selectDate(dateStr, dayEl));
        } else {
            if (selected.fecha === dateStr) dayEl.classList.add('selected');
            dayEl.addEventListener('click', () => selectDate(dateStr, dayEl));
        }

        grid.appendChild(dayEl);
    }
}

async function selectDate(dateStr, element) {
    document.querySelectorAll('#calendar-grid .calendar-day').forEach(el => el.classList.remove('selected'));
    element.classList.add('selected');
    selected.fecha = dateStr;
    selected.hora  = null;

    const dateObj   = new Date(dateStr + 'T00:00:00');
    const formatted = dateObj.toLocaleDateString('es-ES', { weekday:'long', day:'numeric', month:'long' });
    const resFecha  = document.getElementById('res-fecha');
    if (resFecha) resFecha.textContent = formatted;

    document.getElementById('btn-next-3').disabled = false;

    // Cargar horas disponibles para esta fecha
    await cargarHorasDisponibles(dateStr);
}

async function cargarHorasDisponibles(dateStr) {
    if (!selected.medico_id) return;
    const url = `/citas/api/horas/${selected.medico_id}/${dateStr}/`;
    try {
        const resp = await fetch(url);
        const data = await resp.json();
        horasDisponibles = data.horas || [];
    } catch (e) {
        horasDisponibles = [];
        console.error('Error cargando horas:', e);
    }
}

function prevMonth() {
    currentCalendarDate.setMonth(currentCalendarDate.getMonth() - 1);
    renderCalendar();
}

function nextMonth() {
    currentCalendarDate.setMonth(currentCalendarDate.getMonth() + 1);
    renderCalendar();
}

// ==================== HORARIOS ====================
function renderTimeSlots() {
    const container = document.getElementById('time-slots-grid');
    container.innerHTML = '';

    if (horasDisponibles.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4 w-100" style="color:var(--mc-text-muted);">
                <i class="fas fa-clock fa-2x mb-2" style="opacity:.3;display:block;"></i>
                No hay horas disponibles para esta fecha.
            </div>`;
        return;
    }

    horasDisponibles.forEach(time => {
        const btn = document.createElement('button');
        btn.className = 'time-slot btn flex-fill';
        btn.style.minWidth = '72px';
        btn.textContent = time;

        // Bloquear si el paciente ya tiene otra cita activa a esa hora ese día
        const conflicto = citasExistentesData.some(c => c.fecha === selected.fecha && c.hora === time);

        if (conflicto) {
            btn.disabled = true;
            btn.style.opacity = '0.4';
            btn.title = 'Ya tienes una cita agendada a esta hora';
        } else {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#time-slots-grid .time-slot').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                selected.hora = time;
                updateFinalSummary();
                document.getElementById('btn-confirmar').disabled = false;
            });
        }
        container.appendChild(btn);
    });
}

function updateFinalSummary() {
    const esp = especialidadesData.find(e => e.id == selected.especialidad_id);
    const med = medicosData.find(m => m.id == selected.medico_id);
    if (esp) document.getElementById('final-esp').textContent = esp.nombre;
    if (med) document.getElementById('final-med').textContent = med.nombre;
    if (selected.fecha) document.getElementById('final-fecha').textContent =
        new Date(selected.fecha + 'T00:00:00').toLocaleDateString('es-ES');
    if (selected.hora) document.getElementById('final-hora').textContent = selected.hora;
}

// ==================== NAVEGACIÓN ====================
async function goToStep(step) {
    if (step === 2 && !selected.especialidad_id) return alert('Selecciona una especialidad');
    if (step === 3 && !selected.medico_id) return alert('Selecciona un médico');
    if (step === 4 && !selected.fecha) return alert('Selecciona una fecha');

    document.querySelectorAll('.step-content').forEach(el => el.classList.add('d-none'));
    document.getElementById(`step-${step}`).classList.remove('d-none');

    document.querySelectorAll('.step').forEach((s, index) => {
        const circle  = s.querySelector('.step-circle');
        const stepNum = index + 1;
        s.classList.remove('active', 'completed');
        if (stepNum < step) {
            s.classList.add('completed');
            circle.innerHTML = '<i class="fas fa-check"></i>';
        } else if (stepNum === step) {
            s.classList.add('active');
            circle.textContent = stepNum;
        } else {
            circle.textContent = stepNum;
        }
    });

    currentStep = step;

    if (step === 2) renderMedicos(selected.especialidad_id);
    if (step === 3) await renderCalendar();
    if (step === 4) renderTimeSlots();
}

// ==================== CONFIRMAR ====================
async function confirmarCita() {
    if (!selected.especialidad_id || !selected.medico_id || !selected.fecha || !selected.hora) {
        alert('Por favor completa todos los campos');
        return;
    }

    const btn = document.getElementById('btn-confirmar');
    btn.disabled  = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Confirmando...';

    try {
        const response = await fetch('/citas/agendar/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(selected)
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('modal-codigo').textContent   = data.codigo || 'MED-00001';
            document.getElementById('modal-doctor').textContent   = data.doctor || '';
            document.getElementById('modal-datetime').textContent = `${data.fecha} ${data.hora}`;

            const modal = new bootstrap.Modal(document.getElementById('successModal'));
            modal.show();
        } else {
            alert('Error: ' + (data.error || 'No se pudo confirmar la cita'));
            btn.disabled  = false;
            btn.innerHTML = 'Confirmar Cita';
        }
    } catch (error) {
        console.error(error);
        alert('Error de conexión');
        btn.disabled  = false;
        btn.innerHTML = 'Confirmar Cita';
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        for (const cookie of document.cookie.split(';')) {
            const c = cookie.trim();
            if (c.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(c.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}