# leave_app/schedulers.py
from django_celery_beat.schedulers import DatabaseScheduler
from django.db.utils import IntegrityError, ProgrammingError

class NoSchemaCreateScheduler(DatabaseScheduler):
    def setup_schedule(self):
        try:
            super().setup_schedule()
        except (IntegrityError, ProgrammingError):
            return
