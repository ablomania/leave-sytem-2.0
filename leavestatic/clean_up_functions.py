# Cleanup functions
from datetime import date
from datetime import timedelta
from .models import (
    Holiday,
    LeaveUpdate,
    LeaveBalanceReset,
    StaffLeaveDetail,
    ApproverEditLog,
    Approver,
    Approval,
    LeaveRequest,
    LeaveType,
    Ack,
    Resumption,
    CancelledLeave,
)

def clean_up():
    clean_holidays()
    clean_leave_updates()
    clean_leave_balances()
    clean_staff_leave_details()
    clean_approver_edit_logs()
    clean_approvers()
    clean_approval_records()
    clean_leave_requests()
    clean_leave_types()
    clean_acks()
    clean_resumptions()
    clean_cancelled_leaves()

def clean_holidays():
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    inactive_holidays = Holiday.objects.filter(is_active=False)
    for inactive_holiday in inactive_holidays:
        if inactive_holiday.date < thirty_days_ago:
            inactive_holiday.delete()

def clean_leave_updates():
    dangling_updates = LeaveUpdate.objects.filter(leaveobj=None).delete()

def clean_leave_balances():
    dangling_balances = LeaveBalanceReset.objects.filter(staff=None) | LeaveBalanceReset.objects.filter(leave_type=None)
    dangling_balances.delete()

def clean_staff_leave_details():
    dangling_details = StaffLeaveDetail.objects.filter(staff=None) | StaffLeaveDetail.objects.filter(leave_type=None)
    dangling_details.delete()

def clean_approver_edit_logs():
    dangling_logs = ApproverEditLog.objects.filter(staff=None)
    dangling_logs.delete()

def clean_approvers():
    dangling_approvers = Approver.objects.filter(staff=None) | Approver.objects.filter(group_to_approve=None) | Approver.objects.filter(level=None)
    dangling_approvers.delete()

def clean_approval_records():
    dangling_approvals = Approval.objects.filter(request=None) | Approval.objects.filter(approver=None)
    dangling_approvals.delete()


def clean_leave_requests():
    dangling_requests = LeaveRequest.objects.filter(applicant=None) | LeaveRequest.objects.filter(type=None)
    dangling_requests.delete()

def clean_leave_types():
    dangling_leave_types = LeaveType.objects.filter(seniority=None)
    dangling_leave_types.delete()

def clean_acks():
    dangling_acks = Ack.objects.filter(request=None) | Ack.objects.filter(staff=None)
    dangling_acks.delete()

def clean_resumptions():
    dangling_resumptions = Resumption.objects.filter(leave_request=None) | Resumption.objects.filter(staff=None)
    dangling_resumptions.delete()

def clean_cancelled_leaves():
    dangling_cancelled_leaves = CancelledLeave.objects.filter(leave_request=None) | CancelledLeave.objects.filter(staff=None) | CancelledLeave.objects.filter(original_leave=None)
    dangling_cancelled_leaves.delete()
