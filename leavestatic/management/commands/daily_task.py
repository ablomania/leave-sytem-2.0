from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json
import leavestatic.tasks

class Command(BaseCommand):
    help = 'Schedules a daily task if it does not exist.'

    def handle(self, *args, **kwargs):
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='0', hour='8', day_of_week='*', day_of_month='*', month_of_year='*',
        )

        task_name = 'run_leave_progress_update'
        if not PeriodicTask.objects.filter(name=task_name).exists():
            PeriodicTask.objects.create(
                crontab=schedule,
                name=task_name,
                task='leavestatic.tasks.run_leave_progress_update',
                args=json.dumps([]),
                enabled=True,
            )
            self.stdout.write(self.style.SUCCESS(f'Task "{task_name}" created'))
        else:
            self.stdout.write(self.style.WARNING(f'Task "{task_name}" already exists'))

        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='2', hour='8', day_of_week='*', day_of_month='*', month_of_year='*',
        )

        task_name = 'restore_original_approvers'
        if not PeriodicTask.objects.filter(name=task_name).exists():
            PeriodicTask.objects.create(
                crontab=schedule,
                name=task_name,
                task='leavestatic.tasks.restore_original_approvers',
                args=json.dumps([]),
                enabled=True,
            )
            self.stdout.write(self.style.SUCCESS(f'Task "{task_name}" created'))
        else:
            self.stdout.write(self.style.WARNING(f'Task "{task_name}" already exists'))    