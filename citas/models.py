from django.db import models
from django.contrib.auth.models import User


class Especialidad(models.Model):
    nombre = models.CharField(max_length=100)
    icono = models.CharField(max_length=50, default='fa-stethoscope')

    def __str__(self):
        return self.nombre


class Medico(models.Model):
    nombre = models.CharField(max_length=100)
    especialidad = models.ForeignKey(Especialidad, on_delete=models.CASCADE)
    usuario = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='medico_perfil')
    foto = models.URLField(blank=True)
    licencia = models.CharField(max_length=50, blank=True)
    descripcion = models.TextField(blank=True)
    perfil_completado = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre


class Cita(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('en_consulta', 'En Consulta'),
        ('atendida', 'Atendida'),
        ('cancelada', 'Cancelada'),
    ]
    paciente = models.ForeignKey(User, on_delete=models.CASCADE)
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(Especialidad, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora = models.CharField(max_length=5)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='confirmada')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.paciente} - {self.medico} ({self.fecha})"


class NotaCita(models.Model):
    cita = models.OneToOneField(Cita, on_delete=models.CASCADE, related_name='nota')
    diagnostico = models.TextField(blank=True)
    tratamiento = models.TextField(blank=True)
    receta = models.TextField(blank=True)
    requiere_seguimiento = models.BooleanField(default=False)
    fecha_seguimiento = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Nota de cita #{self.cita_id}"


class HorarioMedico(models.Model):
    DIAS = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'),
        (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'),
    ]
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE, related_name='horarios')
    dia_semana = models.IntegerField(choices=DIAS)
    hora_inicio_manana = models.TimeField(null=True, blank=True)
    hora_fin_manana = models.TimeField(null=True, blank=True)
    hora_inicio_tarde = models.TimeField(null=True, blank=True)
    hora_fin_tarde = models.TimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('medico', 'dia_semana')

    def __str__(self):
        return f"{self.medico.nombre} - {self.get_dia_semana_display()}"


class DiaBlockeado(models.Model):
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE, related_name='dias_bloqueados')
    fecha = models.DateField()
    motivo = models.CharField(max_length=150, blank=True)

    class Meta:
        unique_together = ('medico', 'fecha')

    def __str__(self):
        return f"{self.medico.nombre} bloqueado el {self.fecha}"


class Conversation(models.Model):
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paciente_conversations')
    medico = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medico_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('paciente', 'medico')
        ordering = ['-last_message_at']

    def __str__(self):
        return f"Chat: {self.paciente.username} - {self.medico.username}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    cedula = models.CharField(max_length=20, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    pais = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=20, blank=True)
    genero = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    contacto_emergencia = models.CharField(max_length=150, blank=True)
    numero_emergencia = models.CharField(max_length=20, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"