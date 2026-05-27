from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField' # Isso já deve estar aí
    name = 'accounts' # Isso já deve estar aí

    # ADICIONE ESTA FUNÇÃO:
    def ready(self):
        import accounts.signals