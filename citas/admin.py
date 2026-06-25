from django.contrib import admin
from .models import Especialidad, Medico, Cita, Conversation, Message

# Registrar Especialidad
@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)

# Registrar Médico
@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'especialidad')
    list_filter = ('especialidad',)
    search_fields = ['nombre']
# Registrar Cita
@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('id', 'paciente', 'medico', 'especialidad', 'fecha', 'hora', 'estado')
    list_filter = ('estado', 'fecha', 'especialidad')
    search_fields = ('paciente__username', 'medico__nombre')

# Registrar Conversation y Message (para el chat)
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'paciente', 'medico', 'created_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'timestamp', 'content')
    list_filter = ('timestamp',)

from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'cedula', 'fecha_nacimiento')
    search_fields = ('user__username', 'user__email')