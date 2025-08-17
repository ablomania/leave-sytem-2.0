from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SystemAdmin, Approver
from .tasks import notify_new_admin

@receiver(post_save, sender=SystemAdmin)
def send_admin_email(sender, instance, created, **kwargs):
    if created and instance.is_active:
        staff = instance.staff
        if staff.email:
            notify_new_admin.delay(staff.email, staff.get_full_name())


# # Signal to run assign_new_approvals from tasks.py each time a new approver is created
# @receiver(post_save, sender=Approver)
# def trigger_assign_new_approvals(sender, instance, created, **kwargs):
#     if created and instance.is_active and instance.group_to_approve_id:
#         from .tasks import assign_new_approvals
#         assign_new_approvals.delay(instance.group_to_approve_id)
