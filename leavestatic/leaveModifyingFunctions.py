from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from datetime import timedelta
from .models import Leave, Holiday, Approval

def update_leave_progress():
    today = timezone.now().date()

    # 🌴 Get all holidays
    holidays = set(Holiday.objects.filter(is_active=True).values_list("date", flat=True))

    # 🟡 Activate pending leaves whose start date is today
    pending_leaves = Leave.objects.select_related("request", "request__applicant", "request__type").filter(
        is_active=True,
        status=Leave.LeaveStatus.Pending,
        request__status="APPROVED",  # Replace with LeaveRequest.Status.Approved enum if available
        request__start_date=today
    )
    for leave in pending_leaves:
        leave.status = Leave.LeaveStatus.On_Leave
        leave.save()

    # 🟢 Progress active leaves
    active_leaves = Leave.objects.select_related("request", "request__applicant", "request__type").filter(
        is_active=True,
        status=Leave.LeaveStatus.On_Leave
    )
    for leave in active_leaves:
        request = leave.request
        staff = request.applicant

        # Filter valid leave days (excluding weekends and holidays)
        current = request.start_date
        valid_days = []
        while current <= today and current <= request.end_date:
            if current.weekday() < 5 and current not in holidays:
                valid_days.append(current)
            current += timedelta(days=1)

        used_days = len(valid_days)
        leave.days_remaining = max(leave.days_granted - used_days, 0)
        leave.save()

        # 📨 Notify threshold changes
        if leave.days_remaining % 5 == 0 or leave.days_remaining == 1:
            subject = f"Leave Update: {request.type.name}"
            message = (
                f"Dear {staff.first_name},\n\n"
                f"You have {leave.days_remaining} day(s) remaining on your current leave.\n"
                f"Leave Type: {request.type.name}\n"
                f"Resumption Date: {request.return_date}\n\n"
                f"Please prepare accordingly.\n\n"
                f"Regards,\nLeave Management System"
            )
            EmailMessage(subject, message, settings.EMAIL_HOST_USER, [staff.email]).send(fail_silently=False)

        # ✅ Mark completed if days_remaining == 0
        if leave.days_remaining == 0:
            leave.status = Leave.LeaveStatus.Completed
            leave.is_active = False
            leave.save()

            request.status = "COMPLETED"  # Replace with LeaveRequest.Status.Completed if enum used
            request.save()

            approver_emails = [
                a.approver.staff.email
                for a in Approval.objects.filter(request=request, is_active=True)
                if a.approver.staff.email
            ]

            subject = f"Leave Completed: {request.type.name}"
            message = (
                f"Dear {staff.first_name},\n\n"
                f"Your leave for {request.type.name} has been marked as completed.\n"
                f"Start Date: {request.start_date}\n"
                f"End Date: {request.end_date}\n"
                f"Resumption Date: {request.return_date}\n\n"
                f"Welcome back!\n\n"
                f"Regards,\nLeave Management System"
            )
            EmailMessage(subject, message, settings.EMAIL_HOST_USER, [staff.email], cc=approver_emails).send(fail_silently=False)