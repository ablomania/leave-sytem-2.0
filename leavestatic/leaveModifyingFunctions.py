from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from datetime import timedelta
from .models import *



def get_reset_trigger(leave_type, today):
    if leave_type.reset_period == "YEARLY":
        return today.month == 1 and today.day == 1
    elif leave_type.reset_period == "MONTHLY":
        return True
    elif leave_type.reset_period == "QUARTERLY":
        return today.month in [1, 4, 7, 10] and today.day == 1
    elif leave_type.reset_period == "SEMI ANNUALLY":
        return today.month in [1, 7] and today.day == 1
    return False


def update_leave_progress():
    today = timezone.now().date()
    holidays = set(Holiday.objects.filter(is_active=True).values_list("date", flat=True))
    pending_emails = []

    # 🗑️ Delete unapproved requests older than 2 weeks
    stale_requests = LeaveRequest.objects.filter(
        status=LeaveRequest.Status.PENDING,
        application_date__lte=today - timedelta(days=14),
        is_active=True
    )
    stale_requests.delete()

    # 🟡 Activate leaves starting today
    for leave in Leave.objects.select_related("request", "request__applicant", "request__type").filter(
        is_active=True,
        status=Leave.LeaveStatus.Pending,
        request__status=LeaveRequest.Status.APPROVED,
        request__start_date=today
    ):
        update_obj = LeaveUpdate.objects.create(leaveobj=leave)
        leave.status = Leave.LeaveStatus.On_Leave
        leave.save(update_fields=["status"])
        update_obj.status = "successful"
        update_obj.save(update_fields=["status"])

    # 🟢 Update progress on active leaves
    active_leaves = Leave.objects.select_related("request", "request__applicant", "request__type").filter(
        is_active=True,
        status=Leave.LeaveStatus.On_Leave
    )

    for leave in active_leaves:
        update_obj = LeaveUpdate.objects.create(leaveobj=leave)

        request = leave.request
        staff = request.applicant
        current = request.start_date
        valid_days = []

        while current <= today and current <= request.end_date:
            if current.weekday() < 5 and current not in holidays:
                valid_days.append(current)
            current += timedelta(days=1)

        used_days = len(valid_days)
        leave.days_remaining = max(leave.days_granted - used_days, 0)
        leave.save(update_fields=["days_remaining"])

        if leave.days_remaining % 5 == 0 or leave.days_remaining == 1:
            pending_emails.append({
                "subject": f"Leave Update: {request.type.name}",
                "to": [staff.email],
                "body": (
                    f"Dear {staff.first_name},\n\n"
                    f"You have {leave.days_remaining} day(s) remaining on your current leave.\n"
                    f"Leave Type: {request.type.name}\n"
                    f"Resumption Date: {request.return_date}\n\n"
                    f"Please prepare accordingly.\n\n"
                    f"Regards,\nLeave Management System"
                )
            })

        if leave.days_remaining == 0:
            leave.status = Leave.LeaveStatus.Completed
            leave.is_active = False
            leave.save(update_fields=["status", "is_active"])

            request.status = LeaveRequest.Status.COMPLETED
            request.save(update_fields=["status"])

            approver_emails = [
                a.approver.staff.email
                for a in Approval.objects.filter(request=request, is_active=True)
                if a.approver and a.approver.staff.email
            ]

            pending_emails.append({
                "subject": f"Leave Completed: {request.type.name}",
                "to": [staff.email],
                "cc": approver_emails,
                "body": (
                    f"Dear {staff.first_name},\n\n"
                    f"Your leave for {request.type.name} has been marked as completed.\n"
                    f"Start Date: {request.start_date}\n"
                    f"End Date: {request.end_date}\n"
                    f"Resumption Date: {request.return_date}\n\n"
                    f"Welcome back!\n\n"
                    f"Regards,\nLeave Management System"
                )
            })

        update_obj.status = "successful"
        update_obj.save(update_fields=["status"])

    # 🔄 Reset quotas if needed
    for detail in StaffLeaveDetail.objects.select_related("staff", "leave_type").filter(is_active=True):
        leave_type = detail.leave_type
        staff = detail.staff

        if not get_reset_trigger(leave_type, today):
            continue

        ongoing_leave = Leave.objects.filter(
            request__applicant=staff,
            request__type=leave_type,
            is_active=True,
            status=Leave.LeaveStatus.On_Leave
        ).select_related("request").first()

        used_days = 0
        if ongoing_leave:
            current = ongoing_leave.request.start_date
            while current <= today and current <= ongoing_leave.request.end_date:
                if current.weekday() < 5 and current not in holidays:
                    used_days += 1
                current += timedelta(days=1)

        previous_remaining = detail.days_remaining
        new_entitlement = leave_type.days or 0
        detail.days_taken = used_days
        detail.days_remaining = max(new_entitlement - used_days, 0)
        detail.save(update_fields=["days_taken", "days_remaining"])

        LeaveBalanceReset.objects.create(
            staff=staff,
            leave_type=leave_type,
            previous_remaining=previous_remaining,
            new_entitlement=new_entitlement,
            days_carried_forward=0,
            was_on_leave=bool(ongoing_leave),
            note=f"Reset on {today}. Used {used_days} day(s) already."
        )

        if ongoing_leave:
            pending_emails.append({
                "subject": f"Leave Quota Reset Notice: {leave_type.name}",
                "to": [staff.email],
                "body": (
                    f"Dear {staff.first_name},\n\n"
                    f"As part of the scheduled {leave_type.reset_period.lower()} leave quota reset, "
                    f"your available leave balance for '{leave_type.name}' has been adjusted.\n\n"
                    f"Reset Date: {today}\n"
                    f"New Quota: {new_entitlement} day(s)\n"
                    f"Days Used So Far: {used_days} day(s)\n"
                    f"Updated Balance: {detail.days_remaining} day(s) remaining\n\n"
                    f"This reset applies to all staff equally and ensures alignment with organizational policy. "
                    f"For questions, contact HR.\n\n"
                    f"Regards,\nGCPS Leave Management System"
                )
            })

    # ✉️ Final email loop
    for mail in pending_emails:
        try:
            EmailMessage(
                subject=mail["subject"],
                body=mail["body"],
                from_email=settings.EMAIL_HOST_USER,
                to=mail["to"],
                cc=mail.get("cc", [])
            ).send(fail_silently=True)
        except Exception as e:
            print(f"Email failed: {mail['subject']} → {mail['to']}\nError: {e}")


def restore_original_approvers():
    # Get all resumption-confirmed staff who have completed leave
    completed_requests = LeaveRequest.objects.filter(
        status=LeaveRequest.Status.COMPLETED,
        is_active=True
    ).select_related("applicant")

    for request in completed_requests:
        resumption = Resumption.objects.filter(
            leave_request=request,
            staff=request.applicant,
            confirmed=True,
            is_active=True
        ).first()

        if resumption:
            # Find active switch records for this leave
            switches = ApproverSwitch.objects.filter(
                leave_obj__request=request,
                is_active=True
            ).select_related("old_approver", "new_approver")

            for switch in switches:
                # Reactivate old approver
                old_approver = switch.old_approver
                old_approver.is_active = True
                old_approver.save(update_fields=["is_active"])

                # Deactivate relieving approver
                new_approver = switch.new_approver
                new_approver.is_active = False
                new_approver.save(update_fields=["is_active"])

                # Mark switch record inactive
                switch.is_active = False
                switch.save(update_fields=["is_active"])