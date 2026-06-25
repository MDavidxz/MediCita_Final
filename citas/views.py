from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, datetime, time, date
from functools import wraps
import json
from .validators_perfil import validar_info_personal

from .models import (
    Especialidad, Medico, Cita, Conversation, Message,
    Profile, NotaCita, HorarioMedico, DiaBlockeado
)


# ==================== DECORADOR MÉDICO ====================
def medico_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_staff:
            return redirect('citas:home')
        return view_func(request, *args, **kwargs)
    return wrapper


# ==================== HELPER: generar slots de 30 min ====================
def _generar_slots(hora_inicio, hora_fin):
    """Devuelve lista de strings 'HH:MM' cada 30 minutos entre inicio y fin."""
    slots  = []
    actual = datetime.combine(date.today(), hora_inicio)
    fin    = datetime.combine(date.today(), hora_fin)
    while actual < fin:
        slots.append(actual.strftime('%H:%M'))
        actual += timedelta(minutes=30)
    return slots


# ==================== HOME MÉDICO (rediseñado) ====================
@medico_required
def home_medico(request):
    try:
        medico = request.user.medico_perfil
    except Medico.DoesNotExist:
        return redirect('citas:home')

    if not medico.perfil_completado:
        return redirect('citas:completar_perfil_medico')

    hoy = timezone.now().date()

    citas_hoy = (
        Cita.objects
        .filter(medico=medico, fecha=hoy)
        .exclude(estado='cancelada')
        .order_by('hora')
        .select_related('paciente', 'paciente__profile', 'especialidad')
    )

    proximas_citas = (
        Cita.objects
        .filter(medico=medico, fecha__gt=hoy)
        .exclude(estado='cancelada')
        .order_by('fecha', 'hora')
        .select_related('paciente', 'especialidad')[:6]
    )

    mensajes_nuevos = Message.objects.filter(
        conversation__medico=request.user,
        leido=False
    ).exclude(sender=request.user).count()

    total_pacientes = (
        Cita.objects.filter(medico=medico)
        .values('paciente').distinct().count()
    )

    citas_atendidas = Cita.objects.filter(medico=medico, estado='atendida').count()
    citas_pendientes = Cita.objects.filter(
        medico=medico, estado__in=['confirmada', 'pendiente']
    ).count()

    # Notas ya existentes para las citas de hoy
    notas_dict = {
        n.cita_id: n
        for n in NotaCita.objects.filter(cita__medico=medico, cita__fecha=hoy)
    }
    for c in citas_hoy:
        c.nota_existente = notas_dict.get(c.id)

    context = {
        'medico':               medico,
        'citas_hoy':            citas_hoy,
        'proximas_citas':       proximas_citas,
        'mensajes_nuevos':      mensajes_nuevos,
        'total_pacientes':      total_pacientes,
        'citas_atendidas':      citas_atendidas,
        'citas_pendientes':     citas_pendientes,
        'hoy':                  hoy,
        'hide_django_messages': True,
    }
    return render(request, 'citas/home_medico.html', context)


# ==================== AGENDA MÉDICO ====================
@medico_required
def agenda_medico(request):
    try:
        medico = request.user.medico_perfil
    except Medico.DoesNotExist:
        return redirect('citas:home')
 
    if not medico.perfil_completado:
        return redirect('citas:completar_perfil_medico')
 
    filtro = request.GET.get('filtro', 'hoy')
 
    # ── Fecha/hora local correcta (Bolivia = UTC-4) ──
    ahora = timezone.localtime(timezone.now())
    hoy   = ahora.date()
 
    citas_qs = (
        Cita.objects
        .filter(medico=medico)
        .order_by('fecha', 'hora')
        .select_related('paciente', 'paciente__profile', 'especialidad')
    )
 
    if filtro == 'hoy':
        citas_qs = citas_qs.filter(fecha=hoy)
    elif filtro == 'semana':
        citas_qs = citas_qs.filter(fecha__gte=hoy, fecha__lte=hoy + timedelta(days=7))
    elif filtro == 'mes':
        citas_qs = citas_qs.filter(fecha__gte=hoy, fecha__lte=hoy + timedelta(days=30))
    # 'todas' → sin filtro de fecha, incluye pasadas
 
    # Notas existentes
    ids_citas  = [c.id for c in citas_qs]
    notas_dict = {n.cita_id: n for n in NotaCita.objects.filter(cita_id__in=ids_citas)}
    for c in citas_qs:
        c.nota_existente = notas_dict.get(c.id)
 
    # ── Separar en "por atender" y "ya atendidas / canceladas" ──
    # Por atender: pendiente, confirmada, en_consulta — y si es hoy, solo las que aún no pasaron
    hora_actual = ahora.time()
 
    por_atender  = []
    ya_atendidas = []
 
    for c in citas_qs:
        estado_terminado = c.estado in ('atendida', 'cancelada')
 
        if estado_terminado:
            ya_atendidas.append(c)
        else:
            # Si la cita es de hoy y la hora ya pasó → mover a ya_atendidas visualmente
            if filtro == 'hoy' and c.fecha == hoy:
                hora_cita = c.hora  # es un objeto time de Django
                if isinstance(hora_cita, str):
                    try:
                        hora_cita = datetime.strptime(hora_cita, '%H:%M').time()
                    except ValueError:
                        hora_cita = None
                if hora_cita and hora_cita < hora_actual and c.estado == 'confirmada':
                    # Hora ya pasó y sigue confirmada sin atender — mostrar aparte
                    ya_atendidas.append(c)
                else:
                    por_atender.append(c)
            else:
                por_atender.append(c)
 
    context = {
        'medico':               medico,
        'por_atender':          por_atender,
        'ya_atendidas':         ya_atendidas,
        'filtro':               filtro,
        'hoy':                  hoy,
        'hide_django_messages': True,
    }
    return render(request, 'citas/agenda_medico.html', context)
 
 
# ==================== API: horas disponibles de un día ====================
@login_required
def api_horas_disponibles(request, medico_id, fecha_str):
    medico = get_object_or_404(Medico, id=medico_id)
 
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'horas': []})
 
    # Bloqueado?
    if DiaBlockeado.objects.filter(medico=medico, fecha=fecha).exists():
        return JsonResponse({'horas': []})
 
    dia_semana = fecha.weekday()
    try:
        horario = HorarioMedico.objects.get(medico=medico, dia_semana=dia_semana, activo=True)
    except HorarioMedico.DoesNotExist:
        return JsonResponse({'horas': []})
 
    slots = []
    if horario.hora_inicio_manana and horario.hora_fin_manana:
        slots += _generar_slots(horario.hora_inicio_manana, horario.hora_fin_manana)
    if horario.hora_inicio_tarde and horario.hora_fin_tarde:
        slots += _generar_slots(horario.hora_inicio_tarde, horario.hora_fin_tarde)
 
    # Quitar horas ya ocupadas (citas activas ese día)
    ocupadas = set(
        Cita.objects.filter(medico=medico, fecha=fecha)
        .exclude(estado='cancelada')
        .values_list('hora', flat=True)
    )
    slots = [s for s in slots if s not in ocupadas]
 
    # ── Si la fecha es hoy, quitar slots cuya hora ya pasó ──
    ahora     = timezone.localtime(timezone.now())
    hoy_local = ahora.date()
    if fecha == hoy_local:
        hora_actual = ahora.time()
        slots_filtrados = []
        for s in slots:
            try:
                hora_slot = datetime.strptime(s, '%H:%M').time()
                if hora_slot > hora_actual:
                    slots_filtrados.append(s)
            except ValueError:
                slots_filtrados.append(s)
        slots = slots_filtrados
 
    return JsonResponse({'horas': slots})



# ==================== DETALLE DE CITA (MÉDICO) ====================
@medico_required
def detalle_cita_medico(request, cita_id):
    try:
        medico = request.user.medico_perfil
    except Medico.DoesNotExist:
        return redirect('citas:home')

    cita = get_object_or_404(
        Cita.objects.select_related(
            'paciente', 'paciente__profile', 'especialidad', 'medico'
        ),
        id=cita_id, medico=medico
    )

    nota = getattr(cita, 'nota', None)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        # ── Cambiar estado ──
        if accion == 'en_consulta' and cita.estado == 'confirmada':
            cita.estado = 'en_consulta'
            cita.save()
            messages.success(request, 'Cita marcada como En Consulta.')
            return redirect('citas:detalle_cita_medico', cita_id=cita.id)

        elif accion == 'cancelar':
            cita.estado = 'cancelada'
            cita.save()
            messages.success(request, 'Cita cancelada.')
            return redirect('citas:agenda_medico')

        # ── Guardar nota y marcar atendida ──
        elif accion == 'atender':
            diagnostico          = request.POST.get('diagnostico', '').strip()
            tratamiento          = request.POST.get('tratamiento', '').strip()
            receta               = request.POST.get('receta', '').strip()
            requiere_seguimiento = request.POST.get('requiere_seguimiento') == 'on'
            fecha_seguimiento    = request.POST.get('fecha_seguimiento') or None

            if not diagnostico:
                messages.error(request, 'El diagnóstico es obligatorio.')
                return redirect('citas:detalle_cita_medico', cita_id=cita.id)

            nota, _ = NotaCita.objects.get_or_create(cita=cita)
            nota.diagnostico          = diagnostico
            nota.tratamiento          = tratamiento
            nota.receta               = receta
            nota.requiere_seguimiento = requiere_seguimiento
            nota.fecha_seguimiento    = fecha_seguimiento if requiere_seguimiento else None
            nota.save()

            cita.estado = 'atendida'
            cita.save()
            messages.success(request, f'Cita de {cita.paciente.get_full_name() or cita.paciente.username} marcada como Atendida.')
            return redirect('citas:detalle_cita_medico', cita_id=cita.id)

        # ── Guardar nota sin cambiar estado (editar nota existente) ──
        elif accion == 'guardar_nota':
            diagnostico          = request.POST.get('diagnostico', '').strip()
            tratamiento          = request.POST.get('tratamiento', '').strip()
            receta               = request.POST.get('receta', '').strip()
            requiere_seguimiento = request.POST.get('requiere_seguimiento') == 'on'
            fecha_seguimiento    = request.POST.get('fecha_seguimiento') or None

            nota, _ = NotaCita.objects.get_or_create(cita=cita)
            nota.diagnostico          = diagnostico
            nota.tratamiento          = tratamiento
            nota.receta               = receta
            nota.requiere_seguimiento = requiere_seguimiento
            nota.fecha_seguimiento    = fecha_seguimiento if requiere_seguimiento else None
            nota.save()
            messages.success(request, 'Nota clínica guardada correctamente.')
            return redirect('citas:detalle_cita_medico', cita_id=cita.id)

    context = {
        'cita':                 cita,
        'nota':                 nota,
        'medico':               medico,
        'hide_django_messages': False,
    }
    return render(request, 'citas/detalle_cita_medico.html', context)


# ==================== DISPONIBILIDAD MÉDICO ====================
@medico_required
def disponibilidad_medico(request):
    try:
        medico = request.user.medico_perfil
    except Medico.DoesNotExist:
        return redirect('citas:home')

    if not medico.perfil_completado:
        return redirect('citas:completar_perfil_medico')

    if request.method == 'POST':
        accion = request.POST.get('accion')

        # ── Cambiar estado de un día (disponible/bloqueado/libre) ──
        if accion == 'estado_dia':
            fecha_str = request.POST.get('fecha', '').strip()
            estado    = request.POST.get('estado', 'libre')
            if fecha_str:
                try:
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    if estado == 'bloqueado':
                        DiaBlockeado.objects.get_or_create(medico=medico, fecha=fecha_obj)
                        # Si existía como disponible (horario), no borrar el horario
                    elif estado == 'disponible':
                        # Quitar bloqueo si existía
                        DiaBlockeado.objects.filter(medico=medico, fecha=fecha_obj).delete()
                    elif estado == 'libre':
                        # Quitar todo
                        DiaBlockeado.objects.filter(medico=medico, fecha=fecha_obj).delete()
                        HorarioMedico.objects.filter(
                            medico=medico, dia_semana=fecha_obj.weekday()
                        ).update(activo=False)
                except ValueError:
                    pass
            return JsonResponse({'ok': True})

        # ── Guardar horario de un día específico ──
        elif accion == 'guardar_horario_dia':
            fecha_str = request.POST.get('fecha', '').strip()
            if fecha_str:
                try:
                    fecha_obj  = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    dia_semana = fecha_obj.weekday()

                    inicio_m = request.POST.get('hora_inicio_manana') or None
                    fin_m    = request.POST.get('hora_fin_manana')    or None
                    inicio_t = request.POST.get('hora_inicio_tarde')  or None
                    fin_t    = request.POST.get('hora_fin_tarde')     or None

                    horario, _ = HorarioMedico.objects.get_or_create(
                        medico=medico, dia_semana=dia_semana
                    )
                    horario.activo             = True
                    horario.hora_inicio_manana = inicio_m
                    horario.hora_fin_manana    = fin_m
                    horario.hora_inicio_tarde  = inicio_t
                    horario.hora_fin_tarde     = fin_t
                    horario.save()

                    # Quitar bloqueo si existía
                    DiaBlockeado.objects.filter(medico=medico, fecha=fecha_obj).delete()

                except ValueError:
                    pass
            return JsonResponse({'ok': True})

    # GET — preparar datos para el template
    hoy = timezone.now().date()

    # Días bloqueados (próximos 3 meses)
    fin = hoy + timedelta(days=90)
    bloqueados_set = set(
        DiaBlockeado.objects.filter(medico=medico, fecha__gte=hoy, fecha__lte=fin)
        .values_list('fecha', flat=True)
    )

    # Días con horario activo (por día de semana)
    horarios_activos = {
        h.dia_semana: h
        for h in HorarioMedico.objects.filter(medico=medico, activo=True)
    }

    # Construir dias_estado_json y horarios_json para el template
    dias_estado_json = []
    horarios_json    = []

    for offset in range(90):
        d = hoy + timedelta(days=offset)
        if d.weekday() == 6:  # domingo
            continue
        dateStr = d.strftime('%Y-%m-%d')

        if d in bloqueados_set:
            dias_estado_json.append({'fecha': dateStr, 'estado': 'bloqueado'})
        elif d.weekday() in horarios_activos:
            dias_estado_json.append({'fecha': dateStr, 'estado': 'disponible'})
            h = horarios_activos[d.weekday()]
            horarios_json.append({
                'fecha':   dateStr,
                'inicio_m': h.hora_inicio_manana.strftime('%H:%M') if h.hora_inicio_manana else '07:00',
                'fin_m':    h.hora_fin_manana.strftime('%H:%M')    if h.hora_fin_manana    else '12:00',
                'inicio_t': h.hora_inicio_tarde.strftime('%H:%M')  if h.hora_inicio_tarde  else '',
                'fin_t':    h.hora_fin_tarde.strftime('%H:%M')     if h.hora_fin_tarde     else '',
            })

    context = {
        'medico':           medico,
        'dias_estado_json': dias_estado_json,
        'horarios_json':    horarios_json,
        'hoy':              hoy,
        'hide_django_messages': False,
    }
    return render(request, 'citas/disponibilidad_medico.html', context)


# ==================== API: días disponibles del mes ====================
@login_required
def api_disponibilidad_mes(request, medico_id, year, month):
    medico = get_object_or_404(Medico, id=medico_id)

    horarios_activos = set(
        HorarioMedico.objects.filter(medico=medico, activo=True)
        .values_list('dia_semana', flat=True)
    )
    dias_bloqueados = set(
        DiaBlockeado.objects.filter(medico=medico, fecha__year=year, fecha__month=month)
        .values_list('fecha', flat=True)
    )

    import calendar
    _, days_in_month = calendar.monthrange(year, month)
    today = date.today()

    disponibles = []
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        if d < today:
            continue
        # weekday(): 0=Lunes … 5=Sábado, 6=Domingo
        if d.weekday() == 6:           # domingo siempre cerrado
            continue
        if d.weekday() not in horarios_activos:
            continue
        if d in dias_bloqueados:
            continue
        disponibles.append(d.strftime('%Y-%m-%d'))

    return JsonResponse({'disponibles': disponibles})


# ==================== API: horas disponibles de un día ====================
@login_required
def api_horas_disponibles(request, medico_id, fecha_str):
    medico = get_object_or_404(Medico, id=medico_id)

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'horas': []})

    # Bloqueado?
    if DiaBlockeado.objects.filter(medico=medico, fecha=fecha).exists():
        return JsonResponse({'horas': []})

    dia_semana = fecha.weekday()   # 0=Lunes … 5=Sábado
    try:
        horario = HorarioMedico.objects.get(medico=medico, dia_semana=dia_semana, activo=True)
    except HorarioMedico.DoesNotExist:
        return JsonResponse({'horas': []})

    slots = []
    if horario.hora_inicio_manana and horario.hora_fin_manana:
        slots += _generar_slots(horario.hora_inicio_manana, horario.hora_fin_manana)
    if horario.hora_inicio_tarde and horario.hora_fin_tarde:
        slots += _generar_slots(horario.hora_inicio_tarde, horario.hora_fin_tarde)

    # Quitar horas ya ocupadas (citas activas ese día)
    ocupadas = set(
        Cita.objects.filter(medico=medico, fecha=fecha)
        .exclude(estado='cancelada')
        .values_list('hora', flat=True)
    )
    slots = [s for s in slots if s not in ocupadas]

    return JsonResponse({'horas': slots})


# ==================== AGENDAR CITA ====================
@login_required
def agendar_cita(request):
    if request.method == "POST":
        try:
            data            = json.loads(request.body)
            especialidad_id = data.get('especialidad_id')
            medico_id       = data.get('medico_id')
            fecha           = data.get('fecha')
            hora            = data.get('hora')

            if not all([especialidad_id, medico_id, fecha, hora]):
                return JsonResponse({"success": False, "error": "Faltan datos obligatorios"}, status=400)

            especialidad = Especialidad.objects.get(id=especialidad_id)
            medico       = Medico.objects.get(id=medico_id)

            choque = Cita.objects.filter(
                paciente=request.user, fecha=fecha, hora=hora
            ).exclude(estado='cancelada').exists()

            if choque:
                return JsonResponse({"success": False, "error": "Ya tienes una cita agendada en esa fecha y hora."}, status=400)

            cita = Cita.objects.create(
                paciente=request.user, medico=medico,
                especialidad=especialidad, fecha=fecha, hora=hora, estado='confirmada'
            )

            if medico.usuario:
                Conversation.objects.get_or_create(paciente=request.user, medico=medico.usuario)

            return JsonResponse({
                "success": True,
                "codigo":  f"MED-{cita.id:05d}",
                "doctor":  medico.nombre,
                "fecha":   fecha,
                "hora":    hora,
            })

        except Especialidad.DoesNotExist:
            return JsonResponse({"success": False, "error": "Especialidad no existe."}, status=400)
        except Medico.DoesNotExist:
            return JsonResponse({"success": False, "error": "Médico no existe."}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    medicos_qs = (
        Medico.objects.filter(perfil_completado=True)
        .select_related('especialidad', 'usuario', 'usuario__profile')
    )
    medicos = []
    for m in medicos_qs:
        foto = ''
        if m.foto:
            foto = m.foto
        elif m.usuario:
            try:
                if m.usuario.profile.photo:
                    foto = m.usuario.profile.photo.url
            except Profile.DoesNotExist:
                pass
        medicos.append({
            'id': m.id, 'nombre': m.nombre,
            'especialidad_id': m.especialidad_id,
            'especialidad': m.especialidad.nombre,
            'licencia': m.licencia, 'descripcion': m.descripcion, 'foto': foto,
        })

    especialidades   = list(Especialidad.objects.values('id', 'nombre', 'icono'))
    citas_existentes = list(
        Cita.objects.filter(paciente=request.user).exclude(estado='cancelada').values('fecha', 'hora')
    )
    for c in citas_existentes:
        c['fecha'] = c['fecha'].strftime('%Y-%m-%d')

    proximas_citas = Cita.objects.filter(
        paciente=request.user, estado__in=['pendiente', 'confirmada']
    ).order_by('fecha', 'hora')[:3]

    context = {
        'especialidades': especialidades, 'medicos': medicos,
        'citas_existentes': citas_existentes, 'proximas_citas': proximas_citas,
        'hide_django_messages': True,
    }
    return render(request, 'citas/agendar_cita.html', context)


# ==================== HOME PACIENTE ====================
@login_required
def home(request):
    user = request.user
    proxima_cita = Cita.objects.filter(
        paciente=user, estado__in=['pendiente', 'confirmada']
    ).order_by('fecha', 'hora').first()

    if user.is_staff:
        mensajes_nuevos = Message.objects.filter(
            conversation__medico=user, leido=False
        ).exclude(sender=user).count()
    else:
        mensajes_nuevos = Message.objects.filter(
            conversation__paciente=user, leido=False
        ).exclude(sender=user).count()

    historial_count = Cita.objects.filter(paciente=user, estado='confirmada').count()

    context = {
        'proxima_cita': proxima_cita,
        'mensajes_nuevos': mensajes_nuevos,
        'historial_count': historial_count,
        'hide_django_messages': True,
    }
    return render(request, 'citas/home.html', context)


# ==================== MIS CITAS ====================
@login_required
def mis_citas(request):
    citas = Cita.objects.filter(paciente=request.user).order_by('-fecha', '-hora')
    return render(request, 'citas/mis_citas.html', {'citas': citas})


# ── PEGAR ESTAS DOS FUNCIONES en views.py ──────────────────────────────────
# 1) Reemplaza la función editar_cita existente
# 2) Agrega ver_cita como función nueva
# ───────────────────────────────────────────────────────────────────────────

# ESTADOS QUE BLOQUEAN EDICIÓN
ESTADOS_BLOQUEADOS = ('atendida', 'en_consulta', 'cancelada')


@login_required
def editar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, paciente=request.user)

    # ── Si el estado no permite edición, redirigir a vista de solo lectura ──
    if cita.estado in ESTADOS_BLOQUEADOS:
        return redirect('citas:ver_cita', cita_id=cita.id)

    if request.method == 'POST':
        # Doble verificación en POST (por si alguien llega por URL directa)
        if cita.estado in ESTADOS_BLOQUEADOS:
            messages.error(request, 'Esta cita no puede modificarse.')
            return redirect('citas:mis_citas')

        especialidad_id = request.POST.get('especialidad_id')
        medico_id       = request.POST.get('medico_id')
        fecha           = request.POST.get('fecha')
        hora            = request.POST.get('hora')

        errores   = []
        fecha_obj = None
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            errores.append('La fecha ingresada no es válida.')

        medico = Medico.objects.filter(id=medico_id).first()
        if not medico:
            errores.append('El médico seleccionado no existe.')
        elif str(medico.especialidad_id) != str(especialidad_id):
            errores.append('El médico no pertenece a la especialidad seleccionada.')

        if fecha_obj and hora:
            choque = Cita.objects.filter(
                paciente=request.user, fecha=fecha_obj, hora=hora
            ).exclude(id=cita.id).exclude(estado='cancelada').exists()
            if choque:
                errores.append('Ya tienes otra cita activa en esa misma fecha y hora.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            cita.especialidad_id = especialidad_id
            cita.medico          = medico
            cita.fecha           = fecha_obj
            cita.hora            = hora
            cita.save()
            if medico.usuario:
                Conversation.objects.get_or_create(paciente=request.user, medico=medico.usuario)
            messages.success(request, 'Cita actualizada correctamente.')
            return redirect('citas:mis_citas')

    especialidades = list(Especialidad.objects.values('id', 'nombre', 'icono'))
    medicos_qs = (
        Medico.objects.filter(perfil_completado=True)
        .select_related('especialidad', 'usuario', 'usuario__profile')
    )
    medicos = []
    for m in medicos_qs:
        foto = ''
        if m.foto:
            foto = m.foto
        elif m.usuario:
            try:
                if m.usuario.profile.photo:
                    foto = m.usuario.profile.photo.url
            except Profile.DoesNotExist:
                pass
        medicos.append({
            'id': m.id, 'nombre': m.nombre,
            'especialidad_id': m.especialidad_id,
            'especialidad': m.especialidad.nombre,
            'licencia': m.licencia, 'descripcion': m.descripcion, 'foto': foto,
        })

    citas_existentes = list(
        Cita.objects.filter(paciente=request.user)
        .exclude(estado='cancelada').exclude(id=cita.id).values('fecha', 'hora')
    )
    for c in citas_existentes:
        c['fecha'] = c['fecha'].strftime('%Y-%m-%d')

    context = {
        'cita': cita, 'especialidades': especialidades,
        'medicos': medicos, 'citas_existentes': citas_existentes,
    }
    return render(request, 'citas/editar_cita.html', context)


@login_required
def ver_cita(request, cita_id):
    """Vista de solo lectura para el paciente — citas atendidas, en consulta o canceladas."""
    cita = get_object_or_404(
        Cita.objects.select_related('medico', 'especialidad', 'paciente'),
        id=cita_id,
        paciente=request.user
    )

    # Si por alguna razón llega aquí una cita editable, redirigir a editar
    if cita.estado in ('pendiente', 'confirmada'):
        return redirect('citas:editar_cita', cita_id=cita.id)

    nota = getattr(cita, 'nota', None)

    context = {
        'cita': cita,
        'nota': nota,
    }
    return render(request, 'citas/ver_cita.html', context)


# ==================== CANCELAR / ELIMINAR ====================
@login_required
def cancelar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, paciente=request.user)
    cita.estado = 'cancelada'
    cita.save()
    messages.success(request, 'Cita cancelada correctamente.')
    return redirect('citas:mis_citas')


@login_required
def eliminar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, paciente=request.user)
    cita.delete()
    messages.success(request, 'Cita eliminada correctamente.')
    return redirect('citas:mis_citas')


# ==================== CHAT ====================
@login_required
def chat_view(request):
    from datetime import timedelta
    user    = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.last_seen = timezone.now()
    profile.save(update_fields=['last_seen'])

    conversations = (
        Conversation.objects.filter(paciente=user) |
        Conversation.objects.filter(medico=user)
    ).distinct().order_by('-last_message_at')

    if user.is_staff:
        conversations = conversations.filter(messages__isnull=False).distinct()

    selected_conversation = None
    chat_messages = []
    other_user    = None
    selected_medico = None
    medicos = None

    conversation_id = request.GET.get('conversation')
    medico_id       = request.GET.get('medico')

    if conversation_id:
        try:
            selected_conversation = conversations.get(id=conversation_id)
            chat_messages = selected_conversation.messages.all().order_by('timestamp')
            other_user = selected_conversation.medico if selected_conversation.paciente == user else selected_conversation.paciente
            selected_conversation.messages.filter(leido=False).exclude(sender=user).update(leido=True)
        except Conversation.DoesNotExist:
            pass

    elif medico_id and not user.is_staff:
        try:
            selected_medico = User.objects.get(id=medico_id, is_staff=True)
            selected_conversation, _ = Conversation.objects.get_or_create(paciente=user, medico=selected_medico)
            chat_messages = selected_conversation.messages.all().order_by('timestamp')
            other_user    = selected_medico
            selected_conversation.messages.filter(leido=False).exclude(sender=user).update(leido=True)
        except User.DoesNotExist:
            pass

    if not user.is_staff:
        medicos = User.objects.filter(is_staff=True).exclude(id=user.id)

    if request.method == 'POST' and selected_conversation:
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(conversation=selected_conversation, sender=user, content=content)
            selected_conversation.save()
            if user.is_staff:
                return redirect(f"{request.path}?conversation={selected_conversation.id}")
            else:
                rid = selected_medico.id if selected_medico else selected_conversation.medico.id
                return redirect(f"{request.path}?medico={rid}")

    context = {
        'conversations': conversations, 'selected_conversation': selected_conversation,
        'messages': chat_messages, 'other_user': other_user,
        'user_is_staff': user.is_staff, 'medicos': medicos,
        'selected_medico': selected_medico, 'hide_django_messages': True,
    }
    return render(request, 'citas/chat.html', context)


# ==================== POLLING ====================
@login_required
def chat_poll(request, conversation_id):
    try:
        conv = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        return JsonResponse({"messages": [], "other_online": False})

    if conv.paciente != request.user and conv.medico != request.user:
        return JsonResponse({"messages": [], "other_online": False}, status=403)

    last_id = int(request.GET.get('last_id', 0))
    nuevos  = conv.messages.filter(id__gt=last_id).order_by('timestamp')
    nuevos.exclude(sender=request.user).update(leido=True)

    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.last_seen = timezone.now()
    profile.save(update_fields=['last_seen'])

    other_user   = conv.medico if conv.paciente == request.user else conv.paciente
    other_online = False
    try:
        if other_user.profile.last_seen:
            other_online = (timezone.now() - other_user.profile.last_seen) < timedelta(seconds=60)
    except Profile.DoesNotExist:
        pass

    data = [{"id": m.id, "content": m.content,
             "sender": "me" if m.sender == request.user else "other",
             "time": m.timestamp.strftime("%H:%M")} for m in nuevos]

    return JsonResponse({"messages": data, "other_online": other_online})


@login_required
def notificaciones_poll(request):
    user = request.user
    if user.is_staff:
        count = Message.objects.filter(conversation__medico=user, leido=False).exclude(sender=user).count()
    else:
        count = Message.objects.filter(conversation__paciente=user, leido=False).exclude(sender=user).count()
    return JsonResponse({"count": count})


# ==================== ASIGNAR / QUITAR DOCTOR ====================
@login_required
def asignar_doctor(request, user_id):
    if not request.user.is_superuser:
        return redirect('citas:home')
    usuario = get_object_or_404(User, id=user_id)
    usuario.is_staff = True
    usuario.save()

    especialidad_default = Especialidad.objects.first()
    if especialidad_default:
        medico, creado = Medico.objects.get_or_create(
            usuario=usuario,
            defaults={
                'nombre':            usuario.get_full_name() or usuario.username,
                'especialidad':      especialidad_default,
                'perfil_completado': False,
            }
        )
        if not creado and not medico.nombre:
            medico.nombre = usuario.get_full_name() or usuario.username
            medico.save(update_fields=['nombre'])

    messages.success(request, f'{usuario.get_full_name() or usuario.username} ahora es Doctor.')
    return redirect('citas:perfil')


@login_required
def quitar_doctor(request, user_id):
    if not request.user.is_superuser:
        return redirect('citas:home')
    usuario = get_object_or_404(User, id=user_id)
    usuario.is_staff = False
    usuario.save()
    try:
        m = usuario.medico_perfil
        m.usuario = None
        m.perfil_completado = False
        m.save(update_fields=['usuario', 'perfil_completado'])
    except Medico.DoesNotExist:
        pass
    messages.success(request, f'Rol de Doctor eliminado a {usuario.get_full_name() or usuario.username}.')
    return redirect('citas:perfil')


# ==================== PERFIL ====================
@login_required
def perfil(request):
    from django.contrib.auth import update_session_auth_hash
    profile, _ = Profile.objects.get_or_create(user=request.user)
 
    # Guardamos los valores "sucios" para repoblar el form si hay error,
    # y los errores por campo para mostrarlos en el template.
    errores_info = {}
    valores_info = {}
 
    if request.method == 'POST':
        tab = request.POST.get('tab', 'info')
 
        if 'photo' in request.FILES:
            profile.photo = request.FILES['photo']
            profile.save()
            messages.success(request, 'Foto actualizada.')
            return redirect('citas:perfil')
 
        if tab == 'info':
            limpio, errores_info = validar_info_personal(request.POST)
            valores_info = limpio  # para repoblar el formulario tal como el usuario lo escribió
 
            if errores_info:
                # Mostramos cada error como mensaje individual (aparecen arriba)
                for campo, msg in errores_info.items():
                    messages.error(request, msg)
                # No guardamos nada — re-renderizamos el mismo formulario con los errores
                context = _contexto_perfil(request, profile, errores_info, valores_info)
                return render(request, 'citas/perfil.html', context)
 
            # ── Todo válido: ahora sí guardamos ──
            request.user.first_name = limpio['first_name']
            request.user.last_name  = limpio['last_name']
            request.user.save()
 
            profile.phone               = limpio['phone']
            profile.cedula              = limpio['cedula']
            profile.fecha_nacimiento    = limpio['fecha_nacimiento']
            profile.genero              = limpio['genero']
            profile.direccion           = limpio['direccion']
            profile.ciudad              = limpio['ciudad']
            profile.pais                = limpio['pais']
            profile.codigo_postal       = limpio['codigo_postal']
            profile.contacto_emergencia = limpio['contacto_emergencia']
            profile.numero_emergencia   = limpio['numero_emergencia']
            profile.save()
            messages.success(request, 'Información actualizada.')
            return redirect('citas:perfil')
 
        elif tab == 'email':
            new_email = request.POST.get('new_email', '').strip().lower()  # ← .lower() aplicado
            if new_email and new_email != request.user.email:
                if User.objects.filter(email=new_email).exists():
                    messages.error(request, 'Ese correo ya está en uso.')
                else:
                    request.user.email = new_email
                    request.user.save()
                    messages.success(request, 'Correo actualizado.')
            else:
                messages.error(request, 'Ingresa un correo válido y diferente al actual.')
            return redirect('citas:perfil')
 
        elif tab == 'password':
            current = request.POST.get('current_password', '')
            new_p1  = request.POST.get('new_password1', '')
            new_p2  = request.POST.get('new_password2', '')
            if not request.user.check_password(current):
                messages.error(request, 'La contraseña actual es incorrecta.')
            elif new_p1 != new_p2:
                messages.error(request, 'Las contraseñas nuevas no coinciden.')
            elif not (8 <= len(new_p1) <= 64):
                messages.error(request, 'La contraseña debe tener entre 8 y 64 caracteres.')
            else:
                request.user.set_password(new_p1)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Contraseña cambiada.')
            return redirect('citas:perfil')
 
        elif tab == 'profesional':
            if request.user.is_staff and not request.user.is_superuser:
                try:
                    medico = request.user.medico_perfil
                except Medico.DoesNotExist:
                    medico = None
                if medico:
                    especialidad_id = request.POST.get('especialidad_id')
                    licencia        = request.POST.get('licencia', '').strip()
                    descripcion     = request.POST.get('descripcion', '').strip()
                    if not especialidad_id:
                        messages.error(request, 'Selecciona una especialidad.')
                    elif not licencia:
                        messages.error(request, 'El número de licencia es obligatorio.')
                    else:
                        medico.especialidad_id   = especialidad_id
                        medico.licencia          = licencia
                        medico.descripcion       = descripcion
                        medico.nombre            = request.user.get_full_name() or request.user.username
                        medico.perfil_completado = True
                        medico.save()
                        messages.success(request, 'Datos profesionales actualizados.')
                else:
                    messages.error(request, 'No se encontró tu perfil médico.')
            return redirect('citas:perfil')
 
        return redirect('citas:perfil')
 
    context = _contexto_perfil(request, profile, errores_info, valores_info)
    return render(request, 'citas/perfil.html', context)
 
 
def _contexto_perfil(request, profile, errores_info=None, valores_info=None):
    """Construye el context dict del template de perfil (evita repetir código)."""
    from datetime import date
    todos_usuarios = User.objects.all().order_by('date_joined') if request.user.is_superuser else None
    medico_perfil  = None
    especialidades = None
    if request.user.is_staff and not request.user.is_superuser:
        especialidades = Especialidad.objects.all()
        try:
            medico_perfil = request.user.medico_perfil
        except Medico.DoesNotExist:
            pass
 
    hoy = date.today()
    fecha_max_nacimiento = hoy.replace(year=hoy.year - 18)   # el más joven permitido (18 años)
    fecha_min_nacimiento = hoy.replace(year=hoy.year - 100)  # el más viejo permitido (100 años)
 
    return {
        'user': request.user, 'profile': profile,
        'todos_usuarios': todos_usuarios,
        'medico_perfil': medico_perfil, 'especialidades': especialidades,
        'errores_info': errores_info or {},
        'valores_info': valores_info or {},
        'fecha_min_nacimiento': fecha_min_nacimiento,
        'fecha_max_nacimiento': fecha_max_nacimiento,
    }


# ==================== COMPLETAR PERFIL MÉDICO ====================
@login_required
def completar_perfil_medico(request):
    if not request.user.is_staff:
        return redirect('citas:home')
    try:
        medico = request.user.medico_perfil
    except Medico.DoesNotExist:
        return redirect('citas:home')

    if medico.perfil_completado:
        return redirect('citas:home_medico')

    especialidades = Especialidad.objects.all()

    if request.method == 'POST':
        especialidad_id = request.POST.get('especialidad_id')
        licencia        = request.POST.get('licencia', '').strip()
        descripcion     = request.POST.get('descripcion', '').strip()
        errores = []
        if not especialidad_id:
            errores.append('Selecciona una especialidad.')
        if not licencia:
            errores.append('El número de licencia es obligatorio.')
        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            medico.especialidad      = get_object_or_404(Especialidad, id=especialidad_id)
            medico.licencia          = licencia
            medico.descripcion       = descripcion
            medico.nombre            = request.user.get_full_name() or request.user.username
            medico.perfil_completado = True
            medico.save()
            messages.success(request, '¡Perfil completado! Bienvenido al portal médico.')
            return redirect('citas:home_medico')

    context = {'especialidades': especialidades, 'medico': medico}
    return render(request, 'citas/completar_perfil_medico.html', context)