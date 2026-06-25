from django.apps import AppConfig

class CitasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'citas'

    def ready(self):
        # Esta es la forma más segura
        import citas.signals.signals  # Importamos el módulo de señales para registrar las funciones de señalización