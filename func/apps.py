from django.apps import AppConfig


class FuncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'func'
    def ready(self):
        import func.signals
