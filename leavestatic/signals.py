from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SystemAdmin
from .tasks import notify_new_admin

@receiver(post_save, sender=SystemAdmin)
def send_admin_email(sender, instance, created, **kwargs):
    if created and instance.is_active:
        staff = instance.staff
        if staff.email:
            notify_new_admin.delay(staff.email, staff.get_full_name())
