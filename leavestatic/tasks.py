from celery import shared_task
from .leaveModifyingFunctions import update_leave_progress, restore_original_approvers  # import your core logic

@shared_task
def run_leave_progress_update():
    update_leave_progress()

@shared_task
def reinstate_original_approvers():
    restore_original_approvers()