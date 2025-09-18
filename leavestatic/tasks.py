from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from .leaveModifyingFunctions import update_leave_progress, restore_original_approvers  # import your core logic
from .models import *

@shared_task(name="leavestatic.tasks.run_leave_progress_update")
def run_leave_progress_update():
    update_leave_progress()


@shared_task(name="leavestatic.tasks.restore_original_approvers")
def reinstate_original_approvers():
    restore_original_approvers()



@shared_task(name="leavestatic.tasks.mycount")
def mycount():
    # your logic here
    print("Counting…")


@shared_task(name="leavestatic.tasks.send_leave_email")
def send_leave_email(subject, body, to, cc=None):
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.EMAIL_HOST_USER,
        to=to,
        cc=cc or []
    )
    email.send(fail_silently=False)


@shared_task(name="leavestatic.tasks.restore_cancelled_approvers")
def restore_cancelled_approvers(leave_id):
    switches = ApproverSwitch.objects.filter(leave_obj_id=leave_id, is_active=True).select_related("old_approver", "new_approver")
    for switch in switches:
        if switch.old_approver:
            switch.old_approver.is_active = True
            switch.old_approver.save(update_fields=["is_active"])
        if switch.new_approver:
            switch.new_approver.is_active = False
            switch.new_approver.save(update_fields=["is_active"])
        switch.is_active = False
        switch.save(update_fields=["is_active"])


@shared_task(name="leavestatic.tasks.assign_leave_type_to_staff")
def assign_leave_type_to_staff(leave_type_id, seniority_id, days):
    eligible_staff = Staff.objects.filter(seniority_id=seniority_id, is_active=True)
    leave_type = LeaveType.objects.get(id=leave_type_id)

    for staff in eligible_staff:
        StaffLeaveDetail.objects.create(
            staff=staff,
            leave_type=leave_type,
            days_taken=0,
            days_remaining=days,
            is_active=True
        )


@shared_task(name="leavestatic.tasks.reset_leave_details")
def reset_leave_details(staff_id, seniority_id):
    try:
        staff = Staff.objects.get(id=staff_id)
        seniority = Seniority.objects.get(id=seniority_id)

        StaffLeaveDetail.objects.filter(staff=staff).delete()

        allowed_leave_types = LeaveType.objects.filter(seniority=seniority)
        new_details = [
            StaffLeaveDetail(
                staff=staff,
                leave_type=lt,
                days_taken=0,
                days_remaining=lt.days if lt.days is not None else None
            )
            for lt in allowed_leave_types
        ]
        StaffLeaveDetail.objects.bulk_create(new_details)

    except (Staff.DoesNotExist, Seniority.DoesNotExist) as e:
        print(f"[Celery Task] Reset failed: {e}")



@shared_task(name="leavestatic.tasks.send_verification_code")
def send_verification_code(subject, message, recipient_email):
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[recipient_email],
        fail_silently=True
    )



@shared_task
def notify_new_admin(staff_email, staff_name):
    if not staff_email:
        return

    subject = "You've Been Granted Admin Access"
    message = (
        f"Dear {staff_name},\n\n"
        f"You have been added as a system administrator.\n"
        f"You now have elevated access to manage the leave system and its settings.\n\n"
        f"Please log in to view your privileges.\n\n"
        f"Regards,\nGCPS Leave Management System"
    )

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [staff_email],
        fail_silently=True
    )


# Task to delete expired LoginSession objects
@shared_task(name="leavestatic.tasks.delete_expired_loginsessions")
def delete_expired_loginsessions():
    from django.utils import timezone
    expired_sessions = LoginSession.objects.filter(date_to_expire__lt=timezone.now())
    count = expired_sessions.count()
    expired_sessions.delete()
    return f"Deleted {count} expired LoginSession objects."


# Task to assign new approval objects to active leave requests of a specific group
# For each active leave request, check if there are appovers for it
# If there are approvers, check if each approver has an active approval object
# If not, create a new approval object for that approver
@shared_task(name="leavestatic.tasks.assign_new_approvals")
def assign_new_approvals():
    all_groups = Group.objects.filter(is_active=True)
    for group in all_groups:
        # Get all active leave requests for the specified group
        active_requests = LeaveRequest.objects.filter(applicant__group_id=group.id, status=LeaveRequest.Status.PENDING, is_active=True)
        for request in active_requests:
            # Get all active approvers for this group
            approvers = Approver.objects.filter(group_to_approve_id=group.id, is_active=True)
            for approver in approvers:
                # Check if an active Approval object exists for this request and approver
                exists = Approval.objects.filter(
                    request=request,
                    approver=approver,
                    is_active=True
                ).exists()
                if not exists:
                    # Create a new Approval object for this approver and request
                    Approval.objects.create(
                        request=request,
                        approver=approver,
                        status=Approval.ApprovalStatus.Pending,
                        is_active=True
                    )
                    # Send email notification to the approver
                    if hasattr(approver, 'user') and approver.user and approver.user.email:
                        subject = f"New Leave Approval Request for {request.applicant}"
                        body = (
                            f"Dear {approver.user.get_full_name() if hasattr(approver.user, 'get_full_name') else approver.user.username},\n\n"
                            f"You have a new leave request to approve for {request.applicant}.\n"
                            f"Leave Type: {request.leave_type}\n"
                            f"Dates: {request.start_date} to {request.end_date}\n"
                            f"Please log in to the system to review and take action.\n\n"
                            f"Regards,\nGCPS Leave Management System"
                        )
                        try:
                            EmailMessage(
                                subject=subject,
                                body=body,
                                from_email=settings.EMAIL_HOST_USER,
                                to=[approver.user.email]
                            ).send(fail_silently=True)
                        except Exception as e:
                            print(f"[assign_new_approvals] Failed to send email to {approver.user.email}: {e}")
    