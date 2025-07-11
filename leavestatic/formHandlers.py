from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from .models import LeaveRequest, Leave, Ack, Approval, Approver, Staff
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils import timezone


def createLeave(user, leave_request):
    new_leave = Leave(
        name = leave_request.type.name.split()[0],
        days_granted = leave_request.days_requested,
        days_remaining = leave_request.days_requested,
        request_id = leave_request.id,
        status = Leave.LeaveStatus.Pending
    )
    new_leave.save()


def update_ack_status(form_data, status):
    try:
        ack_id = int(form_data.get("ack_id"))
        updated = Ack.objects.filter(id=ack_id).update(status=status)
        return updated > 0  # True if update succeeded
    except (ValueError, TypeError):
        return False  # Invalid ack_id

def approve_ack(form_data, request):
    return update_ack_status(form_data, Ack.Status.Approved)

def deny_ack(form_data, request):
    return update_ack_status(form_data, Ack.Status.Denied)



def approve_leave(form_data):
    try:
        approval_id = int(form_data.get('approval_id'))
        approval = Approval.objects.select_related('request__applicant', 'approver__staff').get(id=approval_id)
        approval.status = Approval.ApprovalStatus.Approved
        approval.save(update_fields=["status"])

        # Notify next pending approver
        next_approval = (
            Approval.objects
            .filter(request=approval.request, status=Approval.ApprovalStatus.Pending)
            .select_related("approver__staff", "request__applicant")
            .order_by("approver__level__level")
            .first()
        )

        if next_approval:
            send_mail(
                subject='Leave Application Pending Approval',
                message=(
                    f"Dear {next_approval.approver.staff.first_name},\n\n"
                    f"A leave application from {next_approval.request.applicant.get_full_name()} is pending your approval.\n"
                    f"Submitted on: {next_approval.request.application_date}\n\n"
                    f"Please review it at your earliest convenience.\n\n"
                    f"Thank you."
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[next_approval.approver.staff.email],
                fail_silently=False
            )
        else:
            staff = Staff.objects.get(id=approval.request.applicant_id)
            send_mail(
                subject=f'Confirmation of Approved Leave Assignment To: {staff.get_full_name}, {staff.other_names}',
                message=(
                    f"Date: {timezone.now()} \n\n"
                    f"Dear {staff.first_name},\n\n"
                    f"We are pleased to inform you that your leave application for {approval.reason.type.name.split()[0]} Leave — scheduled from \n\t{approval.request.start_date} to {approval.request.end_date}\n — has been officially approved following review by all relevant parties.\n\n"
                    f"Kindly acknowledge your acceptance of this approved leave and confirm your availability for the specified period. If, for any reason, you are unable to proceed with the leave as approved, please notify the administration immediately."
                    f"\n\n\033[1mAdditional Notes:\033[0m!\n"
                    f"•\tEnsure all work handovers and transitional arrangements are completed prior to departure.\n"
                    f"•\tRelieving officers assigned will be notified accordingly.\n"
                    f"•\tFor any updates or further assistance, feel free to reach out to the HR department.\n"
                    f"\nSincerely, GCPS Leave System"
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[staff.email],
                fail_silently=False
            )

        return True
    except (ValueError, TypeError, Approval.DoesNotExist):
        return False


def deny_leave(form_data):
    try:
        approval_id = int(form_data.get('approval_id'))
        updated = Approval.objects.filter(id=approval_id).update(status=Approval.ApprovalStatus.Denied)
        return updated > 0
    except (ValueError, TypeError):
        return False


def leaveRequestHandler(form_data, user, request, slug):
    # Create LeaveRequest
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
        med_note=form_data.get("med_note") or None,
        letter=form_data.get("letter") or None
    )

    # Create Ack for relieving officer
    relieving_officer_id = int(form_data["relieving_officer"])
    Ack.objects.create(request=leave_request, staff_id=relieving_officer_id)

    # Create approvals
    approvers = Approver.objects.select_related("staff", "level").filter(
        group_to_approve_id=user.group_id,
        is_active=True
    ).exclude(staff_id=user.id)

    Approval.objects.bulk_create([
        Approval(approver=approver, request=leave_request)
        for approver in approvers
    ])

    # Email: Applicant
    send_mail(
        subject='Acknowledgment of Leave Application',
        message=(
            f"Dear {user.first_name},\n\n"
            f"This email acknowledges receipt of your leave application submitted on {leave_request.application_date}.\n"
            f"Your request is under review. We’ll notify you once a decision is made.\n\n"
            f"Regards,\nLeave Management System"
        ),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        fail_silently=True
    )

    # Email: Relieving Officer
    relieving_officer = Staff.objects.get(id=relieving_officer_id)
    leave_type_name = leave_request.type.name.split()[0]
    send_mail(
        subject=f"Relief Assignment During {user.first_name} {user.last_name}’s Leave",
        message=(
            f"Dear {relieving_officer.first_name},\n\n"
            f"You are assigned to relieve {user.get_full_name()} during their {leave_type_name.lower()} leave "
            f"from {leave_request.start_date} to {leave_request.end_date}.\n\n"
            f"Please acknowledge here:\n"
            f"{request.build_absolute_uri(reverse('relieve_ack', args=[leave_request.id, slug]))}\n\n"
            f"Thank you."
        ),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[relieving_officer.email],
        fail_silently=True
    )

    # Email: First Approver
    first_approver = approvers.order_by("level__level").first()
    if first_approver:
        send_mail(
            subject='Leave Application Pending Approval',
            message=(
                f"Dear {first_approver.staff.first_name},\n\n"
                f"A leave application from {user.get_full_name()} is pending your approval.\n"
                f"Submitted on: {leave_request.application_date}\n\n"
                f"Please review it at your earliest convenience.\n\n"
                f"Thank you."
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[first_approver.staff.email],
            fail_silently=True
        )
