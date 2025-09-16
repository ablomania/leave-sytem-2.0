from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.core.mail import send_mail
from django.conf import settings
import datetime
from django.utils import timezone

# Create your models here.

class Entity(models.Model):
    name = models.CharField(max_length=255, null=True)
    logo = models.ImageField(upload_to='images/logos', null=True)
    monday = models.BooleanField(default=False)
    tuesday = models.BooleanField(default=False)
    wednesday = models.BooleanField(default=False)
    thursday = models.BooleanField(default=False)
    friday = models.BooleanField(default=False)
    saturday = models.BooleanField(default=False)
    sunday = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    days_count = models.IntegerField(null=True)
    def save(self, *args, **kwargs):
        days = [self.monday, self.tuesday, self.wednesday, self.thursday, self.friday, self.saturday, self.sunday]
        self.days_count = sum(1 for day in days if day)
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.name}"

class Group(models.Model):
    name = models.CharField(max_length=50, null=True)
    image = models.ImageField(upload_to='images', null=True, default='images/hierarchy.png')
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.name}"

class SystemAdmin(models.Model):
    staff = models.OneToOneField("Staff", on_delete=models.CASCADE, related_name="admin_profile")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.staff.get_full_name()} (Admin)"


class Seniority(models.Model):
    name = models.CharField(max_length=255)
    rank = models.IntegerField(null=True)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.name}"

class Gender(models.Model):
    name = models.CharField(max_length=255, null=True)
    pronoun = models.CharField(max_length=255, null=True)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.name}"

class Level(models.Model):
    name = models.CharField(max_length=255, null=True)
    level = models.IntegerField(null=True)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.name}"

class Staff(AbstractUser):
    class LeaveStatus(models.TextChoices):
        ON_LEAVE = 'ON LEAVE', 'on leave'
        NOT_ON_LEAVE = 'NOT ON LEAVE', 'not on leave'
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'active'
        DISABLED = 'DISABLED', 'disabled'
    other_names = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=15, null=True)
    group = models.ForeignKey("Group", on_delete=models.CASCADE, null=True, related_name="staff_members")
    leave_status = models.CharField(max_length=13, choices=LeaveStatus.choices, default=LeaveStatus.NOT_ON_LEAVE)
    gender = models.ForeignKey('Gender', on_delete=models.CASCADE, related_name="gender_for_staff", null=True)
    is_special_approver = models.BooleanField(
        default=False,
        help_text="Can approve when no ranked approvers are available"
    )
    image = models.ImageField(upload_to='images/profiles', null=True)
    seniority = models.ForeignKey(Seniority, on_delete=models.CASCADE, related_name="seniority_of_staff", null=True)
    slug = models.SlugField(blank=True, null=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.first_name}-{self.phone_number}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} - {self.slug} - {self.id}"

# Position model REMOVED

class CancelledLeave(models.Model):
    staff = models.ForeignKey("Staff", on_delete=models.CASCADE)
    leave_request = models.ForeignKey("LeaveRequest", on_delete=models.SET_NULL, null=True)
    original_leave = models.ForeignKey("Leave", on_delete=models.SET_NULL, null=True)
    date_cancelled = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(null=True, blank=True)
    days_used = models.IntegerField(null=True)
    days_remaining_at_cancel = models.IntegerField(null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.leave_request.type.name} cancelled on {self.date_cancelled.date()}"



class Resumption(models.Model):
    staff = models.ForeignKey("Staff", on_delete=models.CASCADE)
    leave_request = models.ForeignKey("LeaveRequest", on_delete=models.CASCADE)
    date_submitted = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)
    confirmed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)


class LeaveUpdate(models.Model):
    leaveobj = models.ForeignKey("Leave", on_delete=models.CASCADE)
    date_modified = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[("failed", "Failed"), ("successful", "Successful")],
        default="failed"
    )
    type = models.CharField(
        max_length=20,
        choices=[("activation", "Activation"), ("update", "Update"), ("deactivation", "Deactivation")],
        default="update"
    )
    def __str__(self):
        return f"Update for {self.leaveobj} at {self.date_modified} → {self.status}"




class Leave(models.Model):
    class LeaveStatus(models.TextChoices):
        Pending = "Pending", "pending"
        Cancelled = "Cancelled", "cancelled"
        On_Leave = "On Leave", "on_leave"
        Completed = "Completed", "completed"
    name = models.CharField(max_length=255, null=True)
    days_granted = models.IntegerField(null=True)
    days_remaining = models.IntegerField(null=True)
    request = models.ForeignKey("LeaveRequest", on_delete=models.CASCADE, null=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=LeaveStatus.choices, default=LeaveStatus.On_Leave)
    def __str__(self):
        return f"{self.name}"


class LeaveBalanceReset(models.Model):
    staff = models.ForeignKey("Staff", on_delete=models.CASCADE)
    leave_type = models.ForeignKey("LeaveType", on_delete=models.CASCADE)
    reset_date = models.DateField(auto_now_add=True)
    previous_remaining = models.IntegerField(null=True)
    new_entitlement = models.IntegerField(null=True)
    days_carried_forward = models.IntegerField(null=True)
    was_on_leave = models.BooleanField(default=False)
    note = models.TextField(null=True, blank=True)



class LeaveType(models.Model):
    name = models.CharField(max_length=255, null=True)
    code = models.CharField(max_length=20, blank=True, null=True, help_text="Short identifier like 'AL' or 'CL'")
    days = models.PositiveIntegerField(null=True, help_text="Maximum days allowed per reset period")
    seniority = models.ForeignKey("Seniority", on_delete=models.CASCADE, null=True)

    RESET_CHOICES = [
        ("YEARLY", "Yearly"),
        ("MONTHLY", "Monthly"),
        ("QUARTERLY", "Quarterly"),
        ("SEMI ANNUALLY", "Semi Annually"),
        ("NONE", "No Reset"),
    ]
    reset_period = models.CharField(max_length=20, choices=RESET_CHOICES, default="YEARLY", help_text="How frequently the days reset")

    allow_multiple_applications = models.BooleanField(default=False, help_text="Can staff apply in batches up to the total days?")
    paid_leave = models.BooleanField(default=True, help_text="Is this leave type compensated?")
    eligibility = models.TextField(blank=True, null=True, help_text="Requirements to qualify for this leave")

    includes_date_of_occurence = models.BooleanField(default=False)
    includes_institution = models.BooleanField(default=False)
    includes_course = models.BooleanField(default=False)
    includes_med_note = models.BooleanField(default=False)
    includes_letter = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        code_str = f"[{self.code}]" if self.code else ""
        seniority_name = self.seniority.name if self.seniority else "N/A"
        return f"{code_str} {self.name} - {seniority_name} - {self.days} days"



class StaffLeaveDetail(models.Model):
    staff = models.ForeignKey("Staff", on_delete=models.CASCADE, null=True)
    days_taken = models.IntegerField(null=True)
    days_remaining = models.IntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    leave_type = models.ForeignKey("LeaveType", on_delete=models.CASCADE, null=True)
    is_active = models.BooleanField(default=True)
    def save(self, *args, **kwargs):
        if self.leave_type and self.leave_type.days is not None and self.days_taken is not None:
            self.days_remaining =  self.leave_type.days - self.days_taken
        else: self.days_remaining = None
        super().save(*args, **kwargs)

        
class Holiday(models.Model):
    class Type(models.TextChoices):
        Fixed = 'Fixed', 'fixed'
        Variable = 'Variable', 'variable'
    name = models.CharField(max_length=255, null=True)
    date = models.DateField(null=True)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.Fixed)
    recurs_annually = models.BooleanField(null=True)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.name}"


class Approver(models.Model):
    staff = models.ForeignKey("Staff", on_delete=models.CASCADE)
    group_to_approve = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="group_approvers", null=True)
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="level_for_approver_group", null=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        unique_together = ('staff', 'group_to_approve')

class Approval(models.Model):
    class ApprovalStatus(models.TextChoices):
        Pending = 'PENDING', 'Pending'
        Approved = 'APPROVED', 'Approved'
        Denied = 'DENIED', 'Denied'
    approver = models.ForeignKey("Approver", on_delete=models.CASCADE, related_name="staff_approvals", null=True)
    request = models.ForeignKey("LeaveRequest", on_delete=models.CASCADE, null=True)
    days_approved = models.IntegerField(null=True)
    status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.Pending)
    reason = models.TextField(null=True)
    is_active = models.BooleanField(default=True)

class Ack(models.Model):
    class Type(models.TextChoices):
        RELIEF = "RELIEF", "relief"
        SELF = "SELF", "self"
    class Status(models.TextChoices):
        Pending = "Pending", "pending"
        Ready = "Ready", "ready"
        Approved = "Approved", "approved"
        Denied = "Denied", "denied"
    request = models.ForeignKey("LeaveRequest", on_delete=models.CASCADE, null=True)
    date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(null=True)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.RELIEF)
    staff = models.ForeignKey("Staff", on_delete=models.CASCADE)
    status = models.CharField(max_length=13, choices=Status.choices, default=Status.Pending)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.id}"


class ApproverSwitch(models.Model):
    old_approver = models.ForeignKey("Approver", on_delete=models.CASCADE, null=True, related_name="real_approver")
    new_approver = models.ForeignKey("Approver", on_delete=models.CASCADE, null=True, related_name="auxiliary_approver")
    leave_obj = models.ForeignKey("Leave", on_delete=models.CASCADE, null=True)
    date_created = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)


class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        READY = 'READY', 'Ready'
        APPROVED = 'APPROVED', 'Approved'
        DENIED = 'DENIED', 'Denied'
        DRAFT = 'DRAFT', 'Draft'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    applicant = models.ForeignKey('Staff', on_delete=models.CASCADE, related_name='applicant', null=True)
    application_date = models.DateField(auto_now_add=True)
    days_requested = models.IntegerField(null=True)
    start_date = models.DateField(null=True)
    reason = models.TextField(null=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    type = models.ForeignKey("LeaveType", on_delete=models.CASCADE, related_name="type_of_leave")
    return_date = models.DateField(null=True)
    days_approved = models.IntegerField(null=True)
    date_of_occurence = models.DateField(null=True)
    institution = models.CharField(max_length=255, null=True)
    course = models.CharField(max_length=255, null=True)
    med_note = models.FileField(upload_to='files/med-notes', null=True)
    letter = models.FileField(upload_to='files/letters', null=True)
    is_active = models.BooleanField(default=True)
    end_date = models.DateField(null=True)
    def save(self, *args, **kwargs):
        valid_days = 0
        total_days = 0
        number_of_days = 3
        start_date = str(self.start_date)
        start_date_list = start_date.split('-')
        end_date = self.end_date
        current_date = datetime.datetime( int(start_date_list[0]), int(start_date_list[1]), int(start_date_list[2]))
        if not self.days_approved: days_requested = self.days_requested
        else: days_requested = self.days_approved
        while int(valid_days) < int(days_requested) -1:
            current_date += datetime.timedelta(days=1)
            if current_date.weekday() < 5:
                valid_days += 1
            total_days += 1
        self.end_date = current_date
        
        if (self.end_date.weekday() + 1) < 5:
            self.return_date = self.end_date + datetime.timedelta(days=1)
        else:
            if (self.end_date.weekday() + 1) < 5:
                self.return_date = self.end_date + datetime.timedelta(days=1)
            else:
                self.return_date = self.end_date + datetime.timedelta(days=3)
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.id} - {self.applicant} - {self.start_date} - {self.end_date} - {self.status} - {self.type} -- {self.id}"


class LeaveTypeAuditLog(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    old_leave_types = models.TextField()
    new_leave_types = models.TextField()
    changed_by = models.CharField(max_length=255)
    notes = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)


class ApproverEditLog(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    assignments = models.TextField()
    changed_by = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=100, default="Edit Form")



class Email(models.Model):
    subject = models.CharField(max_length=255, null=True)
    message = models.TextField(null=True)
    sender = models.CharField(max_length=255, null=True)
    receiver = models.CharField(max_length=255, null=True)
    date_created = models.DateField(auto_now_add=True, null=True)
    date_modified = models.DateField(auto_now=True, null=True)
   

class LoginSession(models.Model):
    user = models.ForeignKey('Staff', on_delete=models.CASCADE, related_name='login_session')
    session_key = models.CharField(max_length=255, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_to_expire = models.DateTimeField(default=timezone.now() + timezone.timedelta(days=1))
    last_activity = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    def __str__(self):
        return f"{self.user} - {self.session_key} - {self.status}"