from django.apps import apps as django_apps

def create_default_specialties_and_doctors(sender, **kwargs):
    # Solo ejecutamos para la app 'citas'
    if sender.name != 'citas':
        return

    Especialidad = django_apps.get_model('citas', 'Especialidad')
    Medico = django_apps.get_model('citas', 'Medico')

    # Crear especialidades si no existen
    especialidades = [
        "Cardiología",
        "Pediatría",
        "Dermatología",
        "Traumatología",
        "Ginecología",
        "Medicina General"
    ]

    for nombre in especialidades:
        Especialidad.objects.get_or_create(nombre=nombre)

    # Crear médicos por defecto
    medicos = [
        {"nombre": "Dr. Alejandro Ruiz", "especialidad": "Cardiología", "hospital": "Hospital Vida Nueva", "anos_experiencia": 8},
        {"nombre": "Dra. María Fernanda López", "especialidad": "Cardiología", "hospital": "Clínica Central", "anos_experiencia": 6},
        {"nombre": "Dr. Diego Salazar", "especialidad": "Pediatría", "hospital": "Hospital San Rafael", "anos_experiencia": 10},
        {"nombre": "Dra. Lucía Fernández", "especialidad": "Dermatología", "hospital": "Clínica Central", "anos_experiencia": 5},
    ]

    for m in medicos:
        try:
            especialidad = Especialidad.objects.get(nombre=m["especialidad"])
            Medico.objects.get_or_create(
                nombre=m["nombre"],
                defaults={
                    "especialidad": especialidad,
                    "hospital": m["hospital"],
                    "anos_experiencia": m["anos_experiencia"]
                }
            )
        except Especialidad.DoesNotExist:
            pass