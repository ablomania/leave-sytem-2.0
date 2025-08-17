from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from .models import Holiday, Resumption, ApproverSwitch, LeaveRequest, CancelledLeave, StaffLeaveDetail, Leave, Ack, Approval, Approver, Staff
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils import timezone
from django.core.mail import EmailMessage
from.tasks import send_leave_email, restore_cancelled_approvers


def handle_leave_cancellation(leave, staff, reason):
    """
    Cancels an approved leave, updates balances, logs details,
    and defers email and approver restoration to Celery tasks.
    """
    leave_request = leave.request
    today = timezone.now().date()
    holidays = set(Holiday.objects.filter(is_active=True).values_list("date", flat=True))

    # Calculate used days
    elapsed_days = 0
    current = leave_request.start_date
    while current <= today and current <= leave_request.end_date:
        if current.weekday() < 5 and current not in holidays:
            elapsed_days += 1
        current += timezone.timedelta(days=1)

    # Update Leave model
    leave.days_remaining = max(leave.days_granted - elapsed_days, 0)
    leave.status = Leave.LeaveStatus.Cancelled
    leave.is_active = False
    leave.save()

    # Update quota model
    detail = StaffLeaveDetail.objects.filter(staff=staff, leave_type=leave_request.type).first()
    if detail:
        detail.days_taken += leave.days_remaining
        detail.save(update_fields=["days_taken"])

    # Log cancelled leave
    CancelledLeave.objects.create(
        staff=staff,
        leave_request=leave_request,
        original_leave=leave,
        reason=reason,
        days_used=elapsed_days,
        days_remaining_at_cancel=leave.days_remaining,
        is_active=True
    )

    # Update leave request and create resumption
    leave_request.status = LeaveRequest.Status.COMPLETED
    leave_request.save(update_fields=["status"])

    Resumption.objects.create(
        staff=staff,
        leave_request=leave_request,
        confirmed=True,
        notes=f"System-generated resumption due to cancellation on {today}.",
        is_active=True
    )

    # Deactivate pending approvals
    Approval.objects.filter(request=leave_request, status=Approval.ApprovalStatus.Pending, is_active=True).update(is_active=False)

    # 🎯 Restore approvers asynchronously
    restore_cancelled_approvers.delay(leave.id)

    # Compile CC recipients
    cc_emails = [
        a.approver.staff.email
        for a in Approval.objects.filter(request=leave_request, is_active=True)
        if a.approver.staff.email
    ]
    relief_ack = Ack.objects.filter(request=leave_request, type=Ack.Type.RELIEF, is_active=True).first()
    if relief_ack and relief_ack.staff.email:
        cc_emails.append(relief_ack.staff.email)

    # 🎯 Compose email
    subject = f"Leave Cancellation Notice: {leave_request.type.name}"
    message = (
        f"Dear {staff.first_name},\n\n"
        f"Your leave from {leave_request.start_date} to {leave_request.end_date} has been cancelled.\n"
        f"Days used (excluding holidays): {elapsed_days}\n"
        f"Days remaining at cancellation: {leave.days_remaining}\n\n"
        f"Reason provided: {reason or 'No reason specified.'}\n\n"
        f"Your leave balance has been updated accordingly.\n\n"
        f"— A system-generated resumption has been logged.\n"
        f"— Your approving responsibilities have been restored.\n"
        f"— Relieving officers have been notified.\n\n"
        f"For questions, contact HR.\n\n"
        f"Sincerely,\nGCPS Leave System"
    )

    # 🎯 Send email asynchronously
    send_leave_email.delay(subject, message, [staff.email], cc_emails)
    print("Leave cancellation processed and notifications sent.")



def delegate_approver_role(applicant, relieving_staff, leave):
    """
    Temporarily transfers the approver role from the applicant to the relieving officer.
    """
    active_approver = Approver.objects.filter(staff=applicant, is_active=True).first()
    if not active_approver or not relieving_staff:
        return

    relieving = Approver.objects.filter(staff=relieving_staff).first()
    if not relieving:
        return

    # Deactivate applicant approver role
    active_approver.is_active = False
    active_approver.save(update_fields=["is_active"])

    # Create switch record to track the delegation
    ApproverSwitch.objects.create(
        old_approver=active_approver,
        new_approver=relieving,
        leave_obj=leave,
        is_active=True
    )
    print(f"Delegated approver role from {applicant.get_full_name()} to {relieving_staff.get_full_name()} for leave {leave.id}.")



def createLeave(user, leave_request, ack_id):
    # 🚀 Create or update Leave object
    new_leave, _ = Leave.objects.update_or_create(
        id=ack_id,
        defaults={
            "name": leave_request.type.name.split()[0],
            "days_granted": leave_request.days_requested,
            "days_remaining": leave_request.days_requested,
            "request": leave_request,
            "status": Leave.LeaveStatus.Pending
        }
    )

    # ✅ Check approvals and acknowledgments
    approvals = Approval.objects.filter(request=leave_request, is_active=True)
    all_approved = approvals.exists() and all(
        a.status == Approval.ApprovalStatus.Approved for a in approvals
    )
    relieving_ack = Ack.objects.filter(
        request=leave_request,
        type=Ack.Type.RELIEF,
        status=Ack.Status.Approved
    ).first()
    self_ack = Ack.objects.filter(
        request=leave_request,
        type=Ack.Type.SELF,
        staff=user,
        status=Ack.Status.Approved
    ).exists()

    if all_approved and relieving_ack and self_ack:
        # 🔐 Approve the leave request
        leave_request.status = LeaveRequest.Status.APPROVED
        leave_request.save(update_fields=["status"])

        # 📊 Update leave balance
        details = StaffLeaveDetail.objects.filter(
            staff=user,
            leave_type=leave_request.type
        ).first()
        if details:
            details.days_remaining -= new_leave.days_granted
            details.days_taken += new_leave.days_granted
            details.save(update_fields=["days_remaining", "days_taken"])

        # 🔄 Delegate approver role if applicant is an active approver
        delegate_approver_role(user, relieving_ack.staff, new_leave)

        # ✉️ Compose approval message
        leave_type_name = leave_request.type.name.split()[0]
        start = leave_request.start_date.strftime("%A %d %B %Y")
        end = leave_request.end_date.strftime("%A %d %B %Y")
        resume = leave_request.return_date.strftime("%A %d %B %Y")
        remaining_days = details.days_remaining if details else 0

        subject = f"Leave Approval Confirmation: {leave_type_name}"
        message = (
            f"Dear {user.first_name},\n\n"
            f"Approval has been granted for you to take {leave_request.days_requested} day(s) of {leave_type_name} Leave:\n\n"
            f"• Start Date: {start}\n"
            f"• End Date: {end}\n"
            f"• Resumption Date: {resume}\n\n"
            f"You will have {remaining_days} {leave_type_name.lower()} leave day(s) remaining after this leave is completed.\n"
            f"Your relieving officer will be {relieving_ack.staff.get_full_name()}.\n\n"
            f"Kindly complete a Resumption of Duty Form upon your return.\n\n"
            f"Best wishes during your leave.\n\n"
            f"Sincerely,\nLeave Management System"
        )

        # 📩 Send email to applicant + CC approvers and relieving officer
        cc_emails = [
            a.approver.staff.email
            for a in approvals
            if a.approver and a.approver.staff.email
        ]
        if relieving_ack and relieving_ack.staff.email:
            cc_emails.append(relieving_ack.staff.email)

        send_leave_email.delay(subject, message, [user.email], cc_emails)
        print("Leave created and applicant notified.")





def update_ack_status(form_data, status):
    try:
        ack_id = int(form_data.get("ack_id"))
        updated = Ack.objects.filter(id=ack_id).update(status=status)
        return True  # True if update succeeded
    except (ValueError, TypeError):
        return False  # Invalid ack_id



def approve_ack(form_data, request_obj):
    updated = update_ack_status(form_data, Ack.Status.Approved)
    ack_id = int(form_data.get("ack_id"))
    if updated:
        finalize_leave_approval(request_obj)
        staff = request_obj.applicant
        ack_obj = Ack.objects.filter(id=ack_id).first()
        subject = f'Relieving Officer Approval — {request_obj.type.name.split()[0]} Leave'
        message = (
            f"Dear { staff.first_name },"
            f"\n\nYour assigned relieving officer, { ack_obj.staff.get_full_name }, has reviewed your leave request for { request_obj.type.name.split()[0] } Leave and has officially approved to act in your stead during your absence."
            f"\nLeave Period: { request_obj.start_date } to { request_obj.end_date }."
            f"\n\nThis approval confirms that your responsibilities will be temporarily delegated and continuity of operations will be maintained."
            f"Please ensure all necessary handover notes and access permissions are in place before your departure."
            f"\n\nBest wishes during your leave."
            f"\nSincerely, "
            f"\nGCPS Leave System"
        )
        send_leave_email.delay(subject, message, [staff.email])
    return updated



def deny_ack(form_data, request_obj):
    updated = update_ack_status(form_data, Ack.Status.Denied)
    ack_id = int(form_data.get("ack_id"))
    if updated:
        finalize_leave_approval(request_obj)
        staff = request_obj.applicant
        ack_obj = Ack.objects.filter(id=ack_id).first()

        trigger = {
            "name": f"{ ack_obj.staff.first_name } {ack_obj.staff.last_name} {ack_obj.staff.other_names}",
            "role": "Relieving Officer",
            "date": timezone.now(),
            "reason": ack_obj.reason
        }
        cancel_leave_request(request_obj, trigger)

        subject = f'Relieving Officer Disapproval — {request_obj.type.name.split()[0]} Leave'
        message = (
            f"Dear { staff.first_name },"
            f"\n\nYour assigned relieving officer, { ack_obj.staff.get_full_name }, has reviewed your leave request for {request_obj.type.name.split()[0]} Leave and has declined to act in your stead during the requested period."
            f"\n\nLeave Period: { request_obj.start_date } to { request_obj.end_date }" 
            f"\nReason for Disapproval: { ack_obj.reason if ack_obj.reason != "" else "No reason"}."
            f"\n\nThis decision may affect the approval process of your leave. Kindly consult your supervisor or HR to discuss alternative arrangements or reassignment of relieving duties."
            f"We understand this may be inconvenient and appreciate your cooperation in resolving it promptly."
            f"\n\nSincerely," 
            f"\nGCPS Leave System"
        )
        send_leave_email.delay(subject, message, [staff.email])
        return updated


def cancel_leave_request(request_obj, triggered_by):
    """
    Cancels a leave request based on the response of approvers, relieving officer
    """
    request_obj.status = LeaveRequest.Status.DENIED
    request_obj.save()
    staff = request_obj.applicant
    subject = f'Leave Request Denied {request_obj.type.name.split()[0]} Leave, { request_obj.start_date } to { request_obj.end_date }'
    message = (
        f"Dear { staff.first_name },"
        f"\n\n**Details of the decision:**"
        f"\n- **Leave Type**: {request_obj.type.name.split()[0]} Leave" 
        f"\n- **Requested Dates**: {request_obj.start_date} to {request_obj.end_date}."
        f"\n- **Decision By**: { triggered_by["name"] }."
        f"\n- **Role**: { triggered_by["role"] }."
        f"\n- **Date of Decision**: { triggered_by['date']}" 
        f"\n\n- **Reason Provided**: { triggered_by['reason'] if triggered_by['reason'] != "" else "no reason" }"
        f"\n\nYou may revise and resubmit your request if needed, or reach out to your supervisor for further clarification."
        f"\nThank you for using the GCPS Leave System."
        f"\n\nWarm regards,"
        f"\nGCPS Leave System"
    )
    send_leave_email.delay(subject, message, [staff.email])
    print(f"Leave request {request_obj.id} cancelled by {triggered_by['name']} ({triggered_by['role']}) on {triggered_by['date']}. Reason: {triggered_by['reason']}")
   
    


def finalize_leave_approval(request_obj):
    """
    Finalizes a leave request once all approvals and acknowledgments are complete.
    Sets LeaveRequest status to APPROVED and triggers any downstream logic.
    """
    # Ensure all approvals are approved
    if (Approval.objects.filter(request=request_obj, status=Approval.ApprovalStatus.Pending) | Approval.objects.filter(request=request_obj, status=Approval.ApprovalStatus.Denied)).exists():
        print("Leave request cannot be finalized: pending or denied approvals exist.")
        return False

    # Ensure all acks are approved
    if (Ack.objects.filter(request=request_obj, type=Ack.Type.RELIEF, status=Ack.Status.Pending) | Ack.objects.filter(request=request_obj, type=Ack.Type.RELIEF, status=Ack.Status.Denied)).exists():
        print("Leave request not finalized, exit 2")
        return False

    # Update request status
    request_obj.status = LeaveRequest.Status.READY
    request_obj.save(update_fields=["status"])

    ack_obj = Ack.objects.filter(request=request_obj, type=Ack.Type.SELF).first()
    ack_obj.status = Ack.Status.Ready
    ack_obj.save()

    # Optionally notify applicant here
    # ...
    print("Leave request finalized.")
    return True


def approve_leave(form_data):
    try:
        approval_id = int(form_data.get('approval_id'))
        approval = Approval.objects.select_related('request__applicant', 'approver__staff').get(id=approval_id)
        approval.status = Approval.ApprovalStatus.Approved
        approval.save(update_fields=["status"])

        request_obj = approval.request
        staff = request_obj.applicant  # ✅ define once for reuse

        # Notify next pending approver
        next_approval = (
            Approval.objects
            .filter(request=request_obj, status=Approval.ApprovalStatus.Pending)
            .select_related("approver__staff")
            .order_by("approver__level__level")
            .first()
        )

        if next_approval:
            next_approver = next_approval.approver
            subject = 'Leave Application Pending Approval'
            message = (
                f"Dear {next_approver.staff.first_name},\n\n"
                f"A leave application from {staff.get_full_name()} is pending your approval.\n"
                f"Submitted on: {request_obj.application_date}\n\n"
                f"Please review it at your earliest convenience.\n\n"
                f"Thank you."
            )
            send_leave_email.delay(subject, message, [staff.email])
            print(f"Leave request approved by {approval.approver.staff.get_full_name()} and next approver notified: {next_approver.staff.get_full_name()}.")

        else:
            # No more approvers – finalize if acks are approved
            if finalize_leave_approval(request_obj):
                subject = f'Confirmation of Approved Leave Assignment To: {staff.get_full_name()}, {staff.other_names}'
                message = (
                    f"Date: {timezone.now().strftime('%A, %d %B %Y')} \n\n"
                    f"Dear {staff.first_name},\n\n"
                    f"We are pleased to inform you that your leave application for {request_obj.type.name.split()[0]} Leave — scheduled from \n\t"
                    f"{request_obj.start_date} to {request_obj.end_date}\n — has been officially approved following review by all relevant parties.\n\n"
                    f"Kindly acknowledge your acceptance of this approved leave and confirm your availability for the specified period. "
                    f"If, for any reason, you are unable to proceed with the leave as approved, please notify the administration immediately.\n\n"
                    f"** Additional Notes: **\n"
                    f"• Ensure all work handovers and transitional arrangements are completed prior to departure.\n"
                    f"• Relieving officers assigned will be notified accordingly.\n"
                    f"• For any updates or further assistance, feel free to reach out to the HR department.\n\n"
                    f"Sincerely,\nGCPS Leave System"
                )
                send_leave_email.delay(subject, message, [staff.email])
                print("Leave request approved and applicant notified.")
            else: print(f"WAiting for finalizing actions for leave request {request_obj.id}.")
        return True
    except (ValueError, TypeError, Approval.DoesNotExist):
        return False


def deny_leave(form_data):
    try:
        approval_id = int(form_data.get('approval_id'))
        approval_obj = Approval.objects.filter(id=approval_id).first()
        approval_obj.status=Approval.ApprovalStatus.Denied
        approval_obj.save(update_fields=["status"])

        trigger = {
            "name": f"{ approval_obj.approver.staff.first_name } { approval_obj.approver.staff.last_name } { approval_obj.approver.staff.other_names }",
            "role": f"Approver, Level: {approval_obj.approver.level.name}",
            "date": timezone.now(),
            "reason": approval_obj.reason
        }
        cancel_leave_request(approval_obj.request, trigger)
        return True
    except (ValueError, TypeError):
        return False


def leaveRequestHandler(form_data, user, request):
    from django.urls import reverse
    no_approver_available = False

    # 1. Create Leave Request
    leave_request = LeaveRequest.objects.create(
        applicant=user,
        days_requested=form_data["days_requested"],
        start_date=form_data["start_date"],
        end_date=form_data["end_date"],
        reason=form_data["reason"],
        type_id=int(form_data["leave_type"]),
        return_date=form_data["resumption_date"],
        date_of_occurence=form_data.get("due-date") or None,
        institution=form_data.get("institution") or None,
        course=form_data.get("course") or None,
        med_note=request.FILES.get("med_note") or None,
        letter=request.FILES.get("letter") or None
    )

    # 2. Acknowledgment Setup
    relieving_officer_id = int(form_data["relieving_officer"])
    Ack.objects.create(request=leave_request, staff_id=relieving_officer_id)
    Ack.objects.create(request=leave_request, staff_id=user.id, type=Ack.Type.SELF)

    # 3. Fetch All Approvers in User's Group Except Self
    approvers = Approver.objects.select_related("staff", "level").filter(
        group_to_approve_id=user.group_id,
        is_active=True
    ).exclude(staff=user)
    # 4. Check if Applicant is Also an Approver
    applicant_approver = Approver.objects.filter(staff=user, is_active=True).first()
    if applicant_approver and applicant_approver.level:
        applicant_level_rank = applicant_approver.level.level
        approvers = approvers.filter(level__level__gt=applicant_level_rank)
    # 5. Create Approval Records
    created_approvals = False
    if approvers.exists():
        Approval.objects.bulk_create([
            Approval(approver=approver, request=leave_request)
            for approver in approvers
        ])
        created_approvals = True
    else:
        # 6. Fallback to Special Approver (Staff)
        fallback_staff = Staff.objects.filter(is_special_approver=True, is_active=True).first() or None
        fallback_approver = None
        if fallback_staff:
            fallback_approver = Approver.objects.filter(staff=fallback_staff, is_active=True).first()
            if fallback_approver:
                Approval.objects.create(
                    approver=fallback_approver,
                    request=leave_request,
                    status=Approval.ApprovalStatus.PENDING
                )
                created_approvals = True
            # If there are no approvers or special approvers available, pass, when an approver is created, check for pending
    if not approvers.exists() and not fallback_approver:
        no_approver_available = True

    # 7. Emails ✉️

    # Applicant Confirmation
    applicant_subject = 'Acknowledgment of Leave Application'
    applicant_msg = (
        f"Dear {user.first_name},\n\n"
        f"This email acknowledges receipt of your leave application submitted on {leave_request.application_date}.\n"
        f"Your request is under review. We’ll notify you once a decision is made.\n\n"
        f"Regards,\nLeave Management System"
    )
    send_leave_email.delay(applicant_subject, applicant_msg, [user.email])

    # Relieving Officer Assignment
    relieving_officer = Staff.objects.get(id=relieving_officer_id)
    leave_type_name = leave_request.type.name.split()[0]
    relief_subject = f"Relief Assignment During {user.first_name} {user.last_name}’s Leave"
    relief_msg = (
        f"Dear {relieving_officer.first_name},\n\n"
        f"You are assigned to relieve {user.get_full_name()} during their {leave_type_name.lower()} leave "
        f"from {leave_request.start_date} to {leave_request.end_date}.\n\n"
        f"Acknowledge here:\n"
        f"{request.build_absolute_uri(reverse('relieve_ack', args=[leave_request.id]))}\n\n"
        f"Thank you."
    )
    send_leave_email.delay(relief_subject, relief_msg, [relieving_officer.email])
    print("Leave request created successfully")
    
    # if no_approver_available == True:
    #     pass
    # else:
    #     # First Approver Notification
    #     first_approver = (
    #         approvers.order_by("level__level").first()
    #         if approvers.exists() else fallback_approver
    #     )
    #     if created_approvals and first_approver:
    #         approver_subject = 'Leave Application Pending Approval'
    #         approver_msg = (
    #             f"Dear {first_approver.staff.first_name},\n\n"
    #             f"A leave application from {user.get_full_name()} is pending your approval.\n"
    #             f"Submitted on: {leave_request.application_date}\n\n"
    #             f"Please review it at your earliest convenience.\n\n"
    #             f"Thank you."
    #         )
    #         send_leave_email.delay(approver_subject, approver_msg, [first_approver.staff.email])
    #         print("Leave request created and first approver notified.")
    return True

