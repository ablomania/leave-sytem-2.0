from django.apps import AppConfig


class LeavestaticConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'leavestatic'

    def ready(self):
        from django.db.migrations.recorder import MigrationRecorder
        from django.db.utils import IntegrityError, ProgrammingError
        import leavestatic.signals
        
        orig = MigrationRecorder.ensure_schema

        def patched(self):
            try:
                return orig(self)
            except (IntegrityError, ProgrammingError):
                return

        MigrationRecorder.ensure_schema = patched