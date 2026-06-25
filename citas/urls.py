from django.urls import path
from .views import (
    home, agendar_cita, mis_citas, editar_cita, cancelar_cita, eliminar_cita,
    ver_cita,
    chat_view, chat_poll, notificaciones_poll, perfil,
    asignar_doctor, quitar_doctor,
    home_medico, agenda_medico, completar_perfil_medico,
    detalle_cita_medico, disponibilidad_medico,
    api_disponibilidad_mes, api_horas_disponibles,
)

app_name = 'citas'

urlpatterns = [
    # ── Paciente ──────────────────────────────────────────────────────────
    path('inicio/',                              home,                    name='home'),
    path('agendar/',                             agendar_cita,            name='agendar_cita'),
    path('mis-citas/',                           mis_citas,               name='mis_citas'),
    path('mis-citas/<int:cita_id>/editar/',      editar_cita,             name='editar_cita'),
    path('mis-citas/<int:cita_id>/ver/',         ver_cita,                name='ver_cita'),
    path('mis-citas/<int:cita_id>/cancelar/',    cancelar_cita,           name='cancelar_cita'),
    path('mis-citas/<int:cita_id>/eliminar/',    eliminar_cita,           name='eliminar_cita'),

    # ── Chat y notificaciones ─────────────────────────────────────────────
    path('chat/',                                chat_view,               name='chat'),
    path('chat/poll/<int:conversation_id>/',     chat_poll,               name='chat_poll'),
    path('notificaciones/poll/',                 notificaciones_poll,     name='notificaciones_poll'),

    # ── Perfil ────────────────────────────────────────────────────────────
    path('perfil/',                              perfil,                  name='perfil'),

    # ── Admin ─────────────────────────────────────────────────────────────
    path('admin/asignar-doctor/<int:user_id>/', asignar_doctor,          name='asignar_doctor'),
    path('admin/quitar-doctor/<int:user_id>/',  quitar_doctor,           name='quitar_doctor'),

    # ── Portal Médico ──────────────────────────────────────────────────────
    path('medico/inicio/',                       home_medico,             name='home_medico'),
    path('medico/agenda/',                       agenda_medico,           name='agenda_medico'),
    path('medico/completar-perfil/',             completar_perfil_medico, name='completar_perfil_medico'),
    path('medico/cita/<int:cita_id>/',           detalle_cita_medico,     name='detalle_cita_medico'),
    path('medico/disponibilidad/',               disponibilidad_medico,   name='disponibilidad_medico'),

    # ── APIs de disponibilidad ─────────────────────────────────────────────
    path('api/disponibilidad/<int:medico_id>/<int:year>/<int:month>/',
         api_disponibilidad_mes,  name='api_disponibilidad_mes'),
    path('api/horas/<int:medico_id>/<str:fecha_str>/',
         api_horas_disponibles,   name='api_horas_disponibles'),
]