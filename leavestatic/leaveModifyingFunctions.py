from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from datetime import timedelta
from .models import *
from .clean_up_functions import clean_up




def get_reset_trigger(leave_type, today):
    if leave_type.reset_period == "YEARLY":
        return today.month == 1 and today.day == 1
    elif leave_type.reset_period == "MONTHLY":
        return today.day == 1
    elif leave_type.reset_period == "QUARTERLY":
        return today.month in [1, 4, 7, 10] and today.day == 1
    elif leave_type.reset_period == "SEMI ANNUALLY":
        return today.month in [1, 7] and today.day == 1
    return False


def delete_stale_requests():
    today = timezone.now().date()
    stale_requests = LeaveRequest.objects.filter(
        status=LeaveRequest.Status.PENDING,
        application_date__lte=today - timedelta(days=28),
        is_active=True
    )
    no_errors, leave_obj_ids = True, []
    if stale_requests.count() > 0:
        for stale_request in stale_requests:
            try:
                # Delete stale Acks related to the stale requests
                stale_acks = Ack.objects.filter(request_id=stale_request.id)
                stale_acks.delete()
                # Delete stale Approvals related to the stale requests
                stale_approvals = Approval.objects.filter(request_id=stale_request.id)
                stale_approvals.delete()
            except Exception as e:
                no_errors = False
                leave_obj_ids.append(stale_request.id)
                print(f"Error deleting related records for LeaveRequest ID {stale_request.id}: {e}")
                continue
    stale_requests.delete()
    if no_errors:
        print("Stale leave requests and related records deleted successfully.")
        return True
    else:
        print(f"Stale leave requests deleted, but errors occurred for IDs: {leave_obj_ids}")
        return False


def activate_todays_leaves():
    today = timezone.now().date()
    leaves_to_activate = Leave.objects.select_related("request", "request__applicant", "request__type").filter(
        is_active=True,
        status=Leave.LeaveStatus.Pending,
        request__status=LeaveRequest.Status.APPROVED,
        request__start_date=today
    )
    for leave in leaves_to_activate:
        leave.status = Leave.LeaveStatus.On_Leave
        leave.save(update_fields=["status"])
        update_obj = LeaveUpdate.objects.create(leaveobj=leave, type="activation", status="successful")
        print(f"Activated leave ID: {leave.id} for staff: {leave.request.applicant}")
    print(f"Activated {leaves_to_activate.count()} leaves starting today.")
    return leaves_to_activate.count()


def update_leave_progress():
    today = timezone.now().date()
    holidays = set(Holiday.objects.filter(is_active=True).values_list("date", flat=True))
    pending_emails = []
    entity = Entity.objects.filter(is_active=True).first()

    # 🗑️ Delete unapproved requests older than 2 weeks
    deleted_stale_requests = delete_stale_requests()

    # 🟡 Activate leaves starting today
    activate_todays_leaves()

    # 🟢 Update progress on active leaves
    active_leaves = Leave.objects.select_related("request", "request__applicant", "request__type").filter(
        is_active=True,
        status=Leave.LeaveStatus.On_Leave
    )
    print("Updating leave progress")
    for leave in active_leaves:
        print(f"Processing leave ID: {leave.name} {leave.id}")
        has_successfully_updated_log = LeaveUpdate.objects.filter(
            leaveobj=leave,
            date_modified__date=today,
            status="successful",
            type="update"
        ).count() > 0
        if not has_successfully_updated_log:
            update_obj = LeaveUpdate.objects.create(leaveobj=leave, type="update", status="failed")

            request = leave.request
            staff = request.applicant
            current = request.start_date
            valid_days = []

            while current <= today:
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
                        f"You have {leave.days_remaining} day(s) remaining on your current {leave.name.split()[0]} leave.\n"
                        f"Leave Type: {request.type.name}\n"
                        f"Resumption Date: {request.return_date.strftime('%A, %d %B %Y')}\n\n"
                        f"Please prepare accordingly.\n\n"
                        f"Regards,\nLeave Management System"
                    )
                })

            if leave.days_remaining == 0:
                leave.status = Leave.LeaveStatus.Completed
                leave.save(update_fields=["status"])

                request.status = LeaveRequest.Status.COMPLETED
                request.save(update_fields=["status"])
                print(f"Leave completed for staff: {staff} on leave ID: {leave.id}")
                # Restore approver roles if any switches were made
                restore_original_approvers()

                # Create a resumption record
                print(f"Creating resumption record for staff: {staff}")
                resumption_record = Resumption.objects.create(
                    leave_request=request,
                    staff=staff,
                    confirmed=False,
                    is_active=True
                )
                if resumption_record: print(f"Resumption record created: {resumption_record}")
                else: print("Failed to create resumption record.")

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
                        f"Your leave for {request.type.name.split()[0]} Leave has been marked as completed.\n"
                        f"Start Date: {request.start_date.strftime('%A, %d %B %Y')}\n"
                        f"End Date: {request.end_date.strftime('%A, %d %B %Y')}\n"
                        f"Resumption Date: {request.return_date.strftime('%A, %d %B %Y')}\n\n"
                        f"You currently have 0 days of leave remaining for this leave type.\n"
                        f"Please confirm your return to duty by submitting the Resumption of Duty form.\n\n"
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

        previous_remaining = detail.days_remaining
        new_entitlement = leave_type.days or 0

        if ongoing_leave:
            # Calculate days used in the new quota period (since reset date)
            reset_date = today  # or whatever your reset date is
            current = max(ongoing_leave.request.start_date, reset_date)
            valid_days = []
            while current <= today:
                if current.weekday() < 5 and current not in holidays:
                    valid_days.append(current)
                current += timedelta(days=1)
            used_days = len(valid_days)
            detail.days_taken = used_days
            detail.days_remaining = max(new_entitlement - used_days, 0)
        else:
            detail.days_taken = 0
            detail.days_remaining = new_entitlement

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
                    f"Reset Date: {today.strftime('%A, %d %B %Y')}\n"
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

    # 🧹 Final cleanup
    clean_up()
    print("Cleanup completed.")



def restore_original_approvers():
    from .tasks import send_leave_email
    # Get all resumption-confirmed staff who have completed leave
    print("Restoring original approvers where applicable.")
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
                print(f"Restored original approver {old_approver} for staff {request.applicant}.")

                # --- EMAILS ---
                group = old_approver.group_to_approve
                level = old_approver.level
                group_name = group.name if group else "N/A"
                level_name = level.name if level else "N/A"

                # 1. Email old approver (now restored)
                if old_approver.staff.email:
                    subject_old = "Approver Role Restored"
                    message_old = (
                        f"Dear {old_approver.staff.get_full_name()},\n\n"
                        f"Your approver responsibilities for group '{group_name}' (Level: {level_name}) "
                        f"have been restored now that {request.applicant.get_full_name()} has resumed duty.\n\n"
                        f"Please log in to the system to continue your approver duties.\n\n"
                        f"Regards,\nGCPS Leave System"
                    )
                    send_leave_email.delay(subject_old, message_old, [old_approver.staff.email])

                # 2. Email new approver (now deactivated)
                if new_approver.staff.email:
                    subject_new = "Approver Role Ended"
                    message_new = (
                        f"Dear {new_approver.staff.get_full_name()},\n\n"
                        f"Your temporary approver assignment for group '{group_name}' (Level: {level_name}) "
                        f"has ended as {request.applicant.get_full_name()} has resumed duty.\n\n"
                        f"Thank you for your service during this period.\n\n"
                        f"Regards,\nGCPS Leave System"
                    )
                    send_leave_email.delay(subject_new, message_new, [new_approver.staff.email])

                # 3. Email group members
                group_member_emails = list(
                    Staff.objects.filter(
                        group=group,
                        is_active=True
                    ).exclude(id__in=[old_approver.staff.id, new_approver.staff.id]).values_list('email', flat=True)
                )
                if group_member_emails:
                    subject_group = "Approver Change Notification"
                    message_group = (
                        f"Dear Team Member,\n\n"
                        f"Please be informed that {old_approver.staff.get_full_name()} has resumed their role as your group approver "
                        f"for group '{group_name}' (Level: {level_name}).\n"
                        f"{new_approver.staff.get_full_name()} is no longer your approver for this group.\n\n"
                        f"For any leave requests or approvals, please contact your restored approver.\n\n"
                        f"Regards,\nGCPS Leave System"
                    )
                    send_leave_email.delay(subject_group, message_group, list(group_member_emails))