from .models import *
from django.urls import reverse
from django.contrib.auth import get_user_model
from .tasks import *

#Staff
def add_staff(form_data, request):
    def get_instance(model, key):
        return model.objects.get(id=int(form_data[key]))

    try:
        # 🚀 Create Staff object without username
        new_staff = Staff(
            first_name=form_data['first_name'],
            last_name=form_data['last_name'],
            other_names=form_data.get('other_names', ''),
            gender=get_instance(Gender, 'gender_add'),
            phone_number=form_data['phone_number'],
            email=form_data['email'],
            group=get_instance(Group, 'group'),
            seniority=get_instance(Seniority, 'seniority')
        )
        new_staff.save()

        # 🧮 Generate username
        new_staff.username = f"{new_staff.first_name}{new_staff.phone_number}{new_staff.id}"
        new_staff.save(update_fields=["username"])

        # 📊 Create leave detail records
        allowed_leave_types = LeaveType.objects.filter(seniority=new_staff.seniority)
        leave_details = [
            StaffLeaveDetail(
                staff=new_staff,
                leave_type=leave_type,
                days_taken=0,
                days_remaining=leave_type.days if leave_type.days is not None else None
            )
            for leave_type in allowed_leave_types
        ]
        StaffLeaveDetail.objects.bulk_create(leave_details)

        # ✉️ Compose email message
        subject = "Account Created Successfully"
        message = (
            f"Dear {new_staff.first_name},\n"
            f"Your account was created successfully.\n"
            f"Your email is {new_staff.email}\n\n"
            f"Click on the link below to set your password:\n\n"
            f"{request.build_absolute_uri(reverse('password_reset'))}\n\n"
            f"Best regards,\nGCPS Leave System"
        )

        # 📮 Send email asynchronously
        send_leave_email.delay(subject, message, [new_staff.email])

        print("staff saved")

    except (KeyError, ValueError, Gender.DoesNotExist, Group.DoesNotExist, Seniority.DoesNotExist) as e:
        raise ValueError(f"Error adding staff: {e}")

    


def edit_staff(form_data):
    try:
        staff = Staff.objects.get(id=int(form_data['staff_id']))
        original_seniority_id = staff.seniority_id
        original_group_id = staff.group_id
        original_leave_types = list(
            StaffLeaveDetail.objects.filter(staff=staff)
            .select_related("leave_type")
            .values_list("leave_type__name", flat=True)
        )

        # Update core fields
        for field in ['first_name', 'last_name', 'other_names', 'phone_number', 'email']:
            setattr(staff, field, form_data[field])

        staff.gender = Gender.objects.get(id=int(form_data['gender']))
        staff.group = Group.objects.get(id=int(form_data['group']))
        new_seniority = Seniority.objects.get(id=int(form_data['seniority']))
        staff.seniority = new_seniority
        staff.save()

        # 🎯 Leave entitlements reset + audit if seniority changed
        if original_seniority_id != new_seniority.id:
            StaffLeaveDetail.objects.filter(staff=staff).delete()
            allowed_leave_types = LeaveType.objects.filter(seniority=new_seniority)

            # Log old vs. new entitlements
            new_leave_names = list(allowed_leave_types.values_list("name", flat=True))
            LeaveTypeAuditLog.objects.create(
                staff=staff,
                old_leave_types=" | ".join(original_leave_types),
                new_leave_types=" | ".join(new_leave_names),
                changed_by="System",
                notes=f"Seniority changed from ID {original_seniority_id} to {new_seniority.id}"
            )

            StaffLeaveDetail.objects.bulk_create([
                StaffLeaveDetail(
                    staff=staff,
                    leave_type=lt,
                    days_taken=0,
                    days_remaining=lt.days if lt.days is not None else None
                )
                for lt in allowed_leave_types
            ])

        # ✉️ Email staff confirmation
        subject = "Staff Profile Updated"
        message = (
            f"Dear {staff.first_name},\n\n"
            f"Your staff profile has been successfully updated in the GCPS Leave System.\n"
            f"Please review your leave entitlements and confirm any changes with HR.\n\n"
            f"Best regards,\nLeave Management System"
        )
        send_leave_email.delay(subject, message, [staff.email])

        # 📣 Notify approvers if group changed
        if original_group_id != staff.group_id:
            approvers = Approver.objects.filter(group_to_approve_id=staff.group_id).select_related("staff")
            notify_msg = (
                f"Staff member {staff.get_full_name()} has been reassigned to your approval group.\n"
                f"Please review their profile and update approval settings if needed."
            )
            for approver in approvers:
                send_leave_email.delay(
                    subject="Staff Group Reassignment",
                    body=notify_msg,
                    to=[approver.staff.email]
                )

    except (Staff.DoesNotExist, Gender.DoesNotExist, Seniority.DoesNotExist, Group.DoesNotExist) as e:
        print(f"Update failed: {e}")



def del_staff(form_data):
    staff_ids = form_data.get('staff_ids')
    if not staff_ids:
        return

    # Normalize input to a list of integers
    if isinstance(staff_ids, str):
        staff_ids = [staff_ids]
    elif isinstance(staff_ids, (list, tuple)):
        staff_ids = list(staff_ids)
    else:
        staff_ids = list(staff_ids)

    staff_ids = [int(sid) for sid in staff_ids if str(sid).isdigit()]
    if not staff_ids:
        return

    # Deactivate staff
    Staff.objects.filter(id__in=staff_ids).update(is_active=False)

    # Deactivate related leave details
    StaffLeaveDetail.objects.filter(staff_id__in=staff_ids).update(is_active=False)



def restore_staff(form_data):
    staff_ids = form_data.get('staff_id')
    if not staff_ids:
        return

    # Normalize input to a list of integers
    if isinstance(staff_ids, str):
        staff_ids = [staff_ids]
    elif isinstance(staff_ids, (list, tuple)):
        staff_ids = list(staff_ids)
    else:
        staff_ids = list(staff_ids)

    staff_ids = [int(sid) for sid in staff_ids if str(sid).isdigit()]
    if not staff_ids:
        return

    # Reactivate staff
    Staff.objects.filter(id__in=staff_ids).update(is_active=True)

    # Reactivate related leave details
    StaffLeaveDetail.objects.filter(staff_id__in=staff_ids).update(is_active=True)



#Groups
def add_group(form_data):
    name = form_data['group_name']
    if not Group.objects.filter(name=name).exists():
        Group.objects.create(name=name)


def rem_staff(form_data):
    group_ids = form_data.getlist('group_ids')
    Staff.objects.filter(group_id__in=group_ids).update(group=None)



def restore_group(form_data):
    group_ids = form_data.get('group_ids')
    if not group_ids:
        return

    # Accept both a single ID or a list of IDs
    if isinstance(group_ids, str):
        group_ids = [group_ids]
    elif isinstance(group_ids, (list, tuple)):
        group_ids = list(group_ids)
    else:
        group_ids = list(group_ids)

    # Convert all IDs to integers
    group_ids = [int(gid) for gid in group_ids if str(gid).isdigit()]

    # Bulk update for efficiency
    Group.objects.filter(id__in=group_ids).update(is_active=True)
    return


def edit_group(form_data):
    group_id = form_data['group_id']
    name = form_data['name']
    
    try:
        group = Group.objects.get(id=group_id)
        group.name = name
        group.save()
    except Group.DoesNotExist:
        pass  # Or handle error, e.g., log or return a message


def del_group(form_data):
    group_ids = form_data.get('group_ids')
    if not group_ids:
        return

    # Accept both a single ID or a list of IDs
    if isinstance(group_ids, str):
        group_ids = [group_ids]
    elif isinstance(group_ids, (list, tuple)):
        group_ids = list(group_ids)
    else:
        group_ids = list(group_ids)

    # Convert all IDs to integers
    group_ids = [int(gid) for gid in group_ids if str(gid).isdigit()]

    # Bulk update for efficiency
    Group.objects.filter(id__in=group_ids).update(is_active=False)
    return


#Approvers
def add_approver(form_data):
    try:
        approver_id = int(form_data['approver_name'])
        approver_group_id = int(form_data['approver_group'])
        approver_level_id = int(form_data['approver_level'])

        # Update special approver flag on Staff
        is_special = form_data.get("is_special_approver") == "True"
        Staff.objects.filter(id=approver_id).update(is_special_approver=is_special)

        # Check for existing assignment
        exists = Approver.objects.filter(
            staff_id=approver_id,
            group_to_approve_id=approver_group_id,
            level_id=approver_level_id
        ).exists()

        if not exists:
            # 🧩 Create new approver record
            new_approver = Approver.objects.create(
                staff_id=approver_id,
                group_to_approve_id=approver_group_id,
                level_id=approver_level_id
            )

            # 🔎 Fetch matching pending requests
            senior_staff_ids = Approver.objects.filter(
                level__level__gte=new_approver.level.level,
                is_active=True
            ).values_list("staff_id", flat=True)

            pending_requests = LeaveRequest.objects.filter(
                applicant__group_id=approver_group_id,
                status=LeaveRequest.Status.PENDING,
                is_active=True
            ).exclude(applicant_id__in=senior_staff_ids)

            # 🚦 Add approvals for those requests
            Approval.objects.bulk_create([
                Approval(
                    approver=new_approver,
                    request=request,
                    status=Approval.ApprovalStatus.Pending,
                    is_active=True
                ) for request in pending_requests
            ])

            # ✉️ Notify approver via email
            approver = new_approver
            subject = "New Approver Assignment"
            message = (
                f"Dear {approver.staff.first_name},\n\n"
                f"You have been assigned as an approver for group '{approver.group_to_approve.name}' "
                f"at level '{approver.level.name}'.\n\n"
                f"There are {pending_requests.count()} pending leave requests awaiting your review.\n"
                f"Please log in to the system to view and take action.\n\n"
                f"Regards,\nLeave Management System"
            )
            send_leave_email.delay(subject, message, [approver.staff.email])

    except (KeyError, ValueError, Staff.DoesNotExist) as e:
        print(f"Error adding approver: {e}")



#Edit Approver
def edit_approver(form_data):
    """
    Updates approver assignments for a staff member.
    Ensures one active approver per group, updates levels, and disables obsolete records.
    """
    try:
        staff_id_val = form_data.get('staff_id') or form_data.get('approver_staff')
        staff_id = int(staff_id_val[0]) if isinstance(staff_id_val, (list, tuple)) else int(staff_id_val)

        # Handle special approver flag
        is_special = form_data.get("is_special_approver") == "on"
        Staff.objects.filter(id=staff_id).update(is_special_approver=is_special)

        # Extract group and level IDs
        if hasattr(form_data, 'getlist'):
            group_ids = form_data.getlist('groups')
            level_ids = form_data.getlist('levels')
        else:
            group_ids = form_data.get('groups')
            level_ids = form_data.get('levels')
            group_ids = [group_ids] if isinstance(group_ids, str) else group_ids
            level_ids = [level_ids] if isinstance(level_ids, str) else level_ids

        # Clean and pair inputs
        group_ids = [int(gid) for gid in group_ids if gid]
        level_ids = [int(lid) for lid in level_ids if lid]
        input_pairs = list(zip(group_ids, level_ids))

        # Fetch existing approvers
        existing_approvers = Approver.objects.filter(staff_id=staff_id)
        existing_by_group = {a.group_to_approve_id: a for a in existing_approvers}

        assigned_pairs = []

        # Process input pairs
        for group_id, level_id in input_pairs:
            if group_id not in existing_by_group:
                # Create new approver
                Approver.objects.create(
                    staff_id=staff_id,
                    group_to_approve_id=group_id,
                    level_id=level_id,
                    is_active=True
                )
            else:
                approver = existing_by_group[group_id]
                approver.level_id = level_id
                approver.is_active = True
                approver.save()

            group_name = Group.objects.get(id=group_id).name
            level_name = Level.objects.get(id=level_id).name
            assigned_pairs.append(f"• {group_name} (Level: {level_name})")

        # Mark any leftover approvers as inactive
        for group_id, approver in existing_by_group.items():
            if group_id not in group_ids:
                approver.is_active = False
                approver.save()

        # Email notification
        User = get_user_model()
        approver_user = User.objects.get(id=staff_id)

        subject = "Approver Assignment Updated"
        message = (
            f"Dear {approver_user.first_name},\n\n"
            f"Your approver assignments have been updated:\n\n" +
            ("\n".join(assigned_pairs) if assigned_pairs else "No active assignments.") +
            ("\n\nAdditionally, you have been designated as a fallback Special Approver."
             if is_special else "") +
            "\n\nPlease log in to review your responsibilities.\n\nRegards,\nGCPS Leave System"
        )

        send_leave_email.delay(subject, message, [approver_user.email])

    except Exception as e:
        print(f"Error editing approver: {e}")

    


def del_approver(form_data):
    """
    Deactivates Approver objects and related Approval records for a given staff member(s),
    and sends a notification email to each affected approver asynchronously.
    """
    staff_id = form_data.get('staff_id')
    if not staff_id:
        return

    # Normalize to list of integers
    if isinstance(staff_id, (list, tuple)):
        staff_ids = [int(sid) for sid in staff_id if str(sid).isdigit()]
    else:
        staff_ids = [int(staff_id)] if str(staff_id).isdigit() else []

    if staff_ids:
        approver_qs = Approver.objects.filter(staff_id__in=staff_ids, is_active=True)
        approver_ids = list(approver_qs.values_list("id", flat=True))

        # Deactivate approvers
        approver_qs.update(is_active=False)

        # Deactivate approval records
        if approver_ids:
            Approval.objects.filter(approver_id__in=approver_ids).update(is_active=False)

        # 📩 Notify users asynchronously
        User = get_user_model()
        for sid in staff_ids:
            try:
                user = User.objects.get(id=sid)
                subject = "Approver Assignment Removed"
                message = (
                    f"Dear {user.first_name},\n\n"
                    "You have been removed as an approver in the leave management system.\n"
                    "If this change was unexpected, please contact your HR administrator.\n\n"
                    "Regards,\nGCPS Leave System"
                )
                send_leave_email.delay(subject, message, [user.email])
            except User.DoesNotExist:
                print(f"User with ID {sid} not found.")
            except Exception as e:
                print(f"Error queuing notification for user {sid}: {e}")



def res_approver(form_data):
    """
    Restores Approver objects by setting is_active=True and sends email notification via Celery.
    Expects:
        - approver_id: single ID or list of IDs
    """
    approver_id = form_data.get('approver_id')
    if not approver_id:
        return

    if isinstance(approver_id, (list, tuple)):
        ids = [int(aid) for aid in approver_id if str(aid).isdigit()]
    else:
        ids = [int(approver_id)] if str(approver_id).isdigit() else []

    if ids:
        Approver.objects.filter(id__in=ids).update(is_active=True)

        User = get_user_model()
        for approver in Approver.objects.filter(id__in=ids).select_related('staff'):
            try:
                user = User.objects.get(id=approver.staff_id)
                subject = "Approver Role Restored"
                message = (
                    f"Dear {user.first_name},\n\n"
                    "Your approver role has been reactivated in the system.\n"
                    "You may now resume approval duties for your assigned groups.\n\n"
                    "Regards,\nGCPS Leave System"
                )
                send_leave_email.delay(subject, message, [user.email])  # 🔄 asynchronous
            except User.DoesNotExist:
                print(f"User with staff_id {approver.staff_id} not found.")
            except Exception as e:
                print(f"Error notifying user {approver.staff_id}: {e}")




#Leave type
def add_leave_type(form_data):
    name = form_data['name']
    code = form_data['code']
    days = int(form_data['days'])
    seniority_id = int(form_data['seniority'])
    reset_period = form_data['reset_period']
    allow_multiple_applications = form_data['allow_multiple_applications'] == "True"
    paid_leave = form_data['paid_leave'] == "True"
    eligibility = form_data.get('eligibilty', "")

    i_date = 'i_date' in form_data
    i_institution = 'i_institution' in form_data
    i_course = 'i_course' in form_data
    i_note = 'i_note' in form_data
    i_letter = 'i_letter' in form_data

    # Create LeaveType instance
    new_lvt = LeaveType.objects.create(
        name=name,
        code=code,
        days=days,
        seniority_id=seniority_id,
        reset_period=reset_period,
        allow_multiple_applications=allow_multiple_applications,
        paid_leave=paid_leave,
        eligibility=eligibility,
        includes_date_of_occurence=i_date,
        includes_institution=i_institution,
        includes_course=i_course,
        includes_med_note=i_note,
        includes_letter=i_letter,
        is_active=True
    )

    # 🏃‍♀️ Launch background task
    assign_leave_type_to_staff.delay(new_lvt.id, seniority_id, days)

    return


def edit_leave(form_data):
    print("Editing leave type with form data:", form_data)
    leave_id = int(form_data.get("leave_id"))
    try:
        leave = LeaveType.objects.get(id=leave_id)
    except LeaveType.DoesNotExist:
        return  # Optionally log or raise an error here

    leave.includes_date_of_occurence = True if form_data.get("i_date") == "True" else False
    leave.includes_institution = True if form_data.get("i_institution") == "True" else False
    leave.includes_course = True if form_data.get("i_course") == "True" else False
    leave.includes_med_note = True if form_data.get("i_note") == "True" else False
    leave.includes_letter = True if form_data.get("i_letter") == "True" else False

    leave.name = form_data.get("name")
    leave.code = form_data.get("code")
    leave.days = int(form_data.get("days", 0))
    leave.seniority_id = int(form_data.get("seniority"))
    leave.reset_period = form_data.get("reset_period")
    leave.eligibility = form_data.get("eligibility", "")

    leave.save()



def del_leave(form_data):
    """
    Deactivates selected leave types and cascades deactivation to related StaffLeaveDetail records.
    Expects:
        - leave_type: a list of LeaveType IDs to deactivate
    """
    leave_ids = form_data.get('leave_type', [])
    for id in leave_ids:
        try:
            leave_type = LeaveType.objects.get(id=id)
            leave_type.is_active = False
            leave_type.save()

            # Deactivate related leave detail records
            StaffLeaveDetail.objects.filter(leave_type=leave_type).update(is_active=False)

        except LeaveType.DoesNotExist:
            print(f"LeaveType with ID {id} does not exist.")

    return



def res_leave(form_data):
    """
    Reactivates a LeaveType and updates related StaffLeaveDetail records to is_active=True.
    Expects:
        - leave_id: ID of the LeaveType to reactivate
    """
    leave_id = form_data.get('leave_id')
    if not leave_id:
        return

    try:
        leave_type = LeaveType.objects.get(id=leave_id)
        leave_type.is_active = True
        leave_type.save()

        # Reactivate all associated leave detail records
        StaffLeaveDetail.objects.filter(leave_type=leave_type).update(is_active=True)

    except LeaveType.DoesNotExist:
        print(f"LeaveType with ID {leave_id} does not exist.")

    return


#Holidays
def add_holiday(form_data):
    """
    Creates a new Holiday record from submitted form data.
    Expects:
        - name: str
        - date: date string (YYYY-MM-DD)
        - type: 'Fixed' or 'Variable'
        - recur: 'true' or 'false' as string
    """
    try:
        name = form_data.get("name", "").strip()
        date = form_data.get("date")
        holiday_type = form_data.get("type", "Fixed")
        recur_raw = form_data.get("recur", "false")

        if not name or not date:
            print("Holiday name and date are required.")
            return

        recurs_annually = True if recur_raw.lower() == "true" else False

        Holiday.objects.create(
            name=name,
            date=date,
            type=holiday_type,
            recurs_annually=recurs_annually,
            is_active=True
        )
    except Exception as e:
        print(f"Error creating holiday: {e}")



def edit_holiday(form_data):
    """
    Updates an existing Holiday object with new values from a submitted form.
    """
    try:
        holiday_id = int(form_data['hol_id'])
        name = form_data.get('name', '').strip()
        date = form_data.get('date')
        holiday_type = form_data.get('type', 'Fixed')
        recur_raw = form_data.get('recur', 'false')

        recurs_annually = recur_raw == "True"

        holiday = Holiday.objects.get(id=holiday_id)
        holiday.name = name
        holiday.date = date
        holiday.type = holiday_type
        holiday.recurs_annually = recurs_annually
        holiday.save()

    except (Holiday.DoesNotExist, ValueError, KeyError) as e:
        print(f"Error editing holiday: {e}")

    

def del_holiday(form_data):
    """
    Deactivates a Holiday object based on a single submitted ID.
    Expects form_data to include:
        - 'holiday': ID of the holiday to deactivate
    """
    hol_id = form_data.get("holiday")
    if not hol_id or not str(hol_id).isdigit():
        return

    try:
        holiday = Holiday.objects.get(id=int(hol_id))
        holiday.is_active = False
        holiday.save()
    except Holiday.DoesNotExist:
        print(f"Holiday with ID {hol_id} does not exist.")

    return



def res_holiday(form_data):
    """
    Reactivates a Holiday object based on a single submitted ID.
    Expects form_data to include:
        - 'holiday': ID of the holiday to deactivate
    """
    hol_id = form_data.get("holiday")
    if not hol_id or not str(hol_id).isdigit():
        return

    try:
        holiday = Holiday.objects.get(id=int(hol_id))
        holiday.is_active = True
        holiday.save()
    except Holiday.DoesNotExist:
        print(f"Holiday with ID {hol_id} does not exist.")

    


#Genders
def del_gender(form_data):
    try:
        gender = Gender.objects.get(id=int(form_data.get('gender_id')))
        gender.is_active = False
        gender.save()
    except (Gender.DoesNotExist, TypeError, ValueError) as e:
        # Handle the error or log it
        raise ValueError(f"Failed to deactivate gender: {e}")


def add_gender(form_data):
    try:
        name = form_data.get('name')
        pronoun = form_data.get('pronoun')

        if not name or not pronoun:
            raise ValueError("Both 'name' and 'pronoun' are required.")

        new_gender = Gender(name=name.strip(), pronoun=pronoun.strip())
        new_gender.save()
        return new_gender
    except Exception as e:
        raise ValueError(f"Failed to add gender: {e}")



def edit_gender(form_data):
    try:
        gender = Gender.objects.get(id=int(form_data.get('gender_id')))
        gender.name = form_data.get('name', gender.name)
        gender.pronoun = form_data.get('pronoun', gender.pronoun)
        gender.save()
    except (Gender.DoesNotExist, TypeError, ValueError) as e:
        raise ValueError(f"Failed to update gender: {e}")



def res_gender(form_data):
    try:
        gender = Gender.objects.get(id=int(form_data.get('gender_id')))
        gender.is_active = True
        gender.save()
    except (Gender.DoesNotExist, TypeError, ValueError) as e:
        # Handle the error or log it
        raise ValueError(f"Failed to activate gender: {e}")
    


#Categories
def del_sen(form_data):
    """
    Deactivates a Seniority record and all related LeaveType and StaffLeaveDetail records.
    Expects:
        - 'sen_id': ID of the seniority to deactivate
    """
    try:
        sen_id = int(form_data.get('sen_id'))
        seniority = Seniority.objects.get(id=sen_id)
        seniority.is_active = False
        seniority.save()

        # Deactivate related leave types
        related_leave_types = LeaveType.objects.filter(seniority_id=sen_id)
        related_leave_types.update(is_active=False)

        # Deactivate staff leave details linked to those leave types
        StaffLeaveDetail.objects.filter(leave_type__in=related_leave_types).update(is_active=False)

    except (Seniority.DoesNotExist, TypeError, ValueError) as e:
        raise ValueError(f"Failed to deactivate seniority and related records: {e}")
    

def add_sen(form_data):
    try:
        name = form_data.get('name')
        rank = int(form_data.get('rank'))

        if not name or not rank:
            raise ValueError("Both 'name' and 'rank' are required.")

        new_sen = Seniority(name=name.strip(), rank=rank)
        new_sen.save()
    except Exception as e:
        raise ValueError(f"Failed to add category: {e}")



def edit_sen(form_data):
    try:
        sen = Seniority.objects.get(id=int(form_data.get('cat_id')))
        sen.name = form_data.get('name', sen.name)
        sen.rank = form_data.get('rank', sen.rank)
        sen.save()
    except (Gender.DoesNotExist, TypeError, ValueError) as e:
        raise ValueError(f"Failed to update category: {e}")



def res_sen(form_data):
    """
    Reactivates a Seniority and cascades reactivation to related LeaveType and StaffLeaveDetail records.
    Expects:
        - 'sen_id': ID of the seniority to reactivate
    """
    try:
        sen_id = int(form_data.get('sen_id'))
        seniority = Seniority.objects.get(id=sen_id)
        seniority.is_active = True
        seniority.save()

        # Reactivate related leave types
        related_leave_types = LeaveType.objects.filter(seniority_id=sen_id)
        related_leave_types.update(is_active=True)

        # Reactivate related staff leave details
        StaffLeaveDetail.objects.filter(leave_type__in=related_leave_types).update(is_active=True)

    except (Seniority.DoesNotExist, TypeError, ValueError) as e:
        raise ValueError(f"Failed to activate seniority: {e}")


    

# Levels
def del_lvl(form_data):
    """
    Deactivates a Level and updates related Approvers to the next lower level.
    """
    try:
        lvl_id = int(form_data.get('level_id'))
        current_level = Level.objects.get(id=lvl_id)

        # Deactivate the level
        current_level.is_active = False
        current_level.save()

        # Find the next lower active level
        lower_level = (
            Level.objects
            .filter(level__lt=current_level.level, is_active=True)
            .order_by("-level")
            .first()
        )

        if lower_level:
            # Update all approvers from the deleted level to the new one
            Approver.objects.filter(level_id=lvl_id).update(level=lower_level)
        else:
            print(f"No lower active level found. Approvers remain linked to inactive level {current_level.name}.")

    except (Level.DoesNotExist, TypeError, ValueError) as e:
        raise ValueError(f"Failed to deactivate level and update approvers: {e}")
    

def add_lvl(form_data):
    try:
        name = form_data.get('name')
        level = int(form_data.get('level'))

        if not name or not level:
            raise ValueError("Both 'name' and 'level' are required.")

        new_lvl = Level(name=name.strip(), level=level)
        new_lvl.save()
    except Exception as e:
        raise ValueError(f"Failed to add category: {e}")



def edit_lvl(form_data):
    try:
        lvl = Level.objects.get(id=int(form_data.get('level_id')))
        lvl.name = form_data.get('name', lvl.name)
        lvl.level = form_data.get('level', lvl.level)
        lvl.save()
    except (Level.DoesNotExist, TypeError, ValueError) as e:
        raise ValueError(f"Failed to update level: {e}")



def res_lvl(form_data):
    try:
        lvl = Level.objects.get(id=int(form_data.get('level_id')))
        lvl.is_active = True
        lvl.save()
    except (Level.DoesNotExist, TypeError, ValueError) as e:
        # Handle the error or log it
        raise ValueError(f"Failed to activate level: {e}")
    

def del_multi_staff(form_data):
    """
    Deactivates multiple Staff records based on a list of IDs.
    Expects:
        - 'staff_ids': list of Staff IDs to deactivate
    """
    staff_ids = form_data.get('staff_ids', [])
    if not staff_ids:
        return

    # Normalize input to a list of integers
    if isinstance(staff_ids, str):
        staff_ids = [int(sid) for sid in staff_ids.split(',') if sid.isdigit()]
    elif isinstance(staff_ids, (list, tuple)):
        staff_ids = [int(sid) for sid in staff_ids if str(sid).isdigit()]
    else:
        staff_ids = []

    if not staff_ids:
        return

    # Deactivate staff and related leave details
    Staff.objects.filter(id__in=staff_ids).update(is_active=False)
    StaffLeaveDetail.objects.filter(staff_id__in=staff_ids).update(is_active=False)


def multi_change_group(form_data):
    """
    Changes the group of multiple Staff records based on a list of IDs.
    Expects:
        - 'staff_ids': list of Staff IDs to update
        - 'new_group_id': ID of the new group to assign
    """
    staff_ids = form_data.get('staff_ids', [])
    print(f"Received staff_ids: {staff_ids}")
    new_group_id = int(form_data['group_id'][0])
    if not staff_ids or not new_group_id:
        return
    # Normalize input to a list of integers
    if isinstance(staff_ids, str):
        staff_ids = [int(sid) for sid in staff_ids.split(',') if sid.isdigit()]
    elif isinstance(staff_ids, (list, tuple)):
        staff_ids = [int(sid) for sid in staff_ids if str(sid).isdigit()]
    else:
        staff_ids = []
    if not staff_ids:
        return
    # Update group for all specified staff
    Staff.objects.filter(id__in=staff_ids).update(group_id=new_group_id)
    # Notify each staff member of the group change
    User = get_user_model()
    for staff_id in staff_ids:
        try:
            user = User.objects.get(id=staff_id)
            subject = "Group Change Notification"
            message = (
                f"Dear {user.first_name},\n\n"
                "Your group has been changed. Please log in to the system to review your new group assignments.\n\n"
                "Regards,\nGCPS Leave System"
            )
            send_leave_email.delay(subject, message, [user.email])
        except User.DoesNotExist:
            print(f"User with ID {staff_id} not found.")
        except Exception as e:
            print(f"Error notifying user {staff_id}: {e}")


def multi_change_group_group(form_data):
    """
    Changes the group of multiple Staff records based on a list of IDs.
    Expects:
        - 'group_ids': list of Group IDs to fetch staff from
        - 'new_group_id': ID of the new group to assign
    """
    group_ids = form_data.get('group_ids', [])
    new_group_id = int(form_data['new_group_id'][0])
    if not group_ids or not new_group_id:
        return
    # Normalize input to a list of integers
    if isinstance(group_ids, str):
        group_ids = [int(gid) for gid in group_ids.split(',') if gid.isdigit()]
    elif isinstance(group_ids, (list, tuple)):
        group_ids = [int(gid) for gid in group_ids if str(gid).isdigit()]
    else:
        group_ids = []
    if not group_ids:
        return
    # Update group for all staff in the specified groups
    Staff.objects.filter(group_id__in=group_ids).update(group_id=new_group_id)
    # Notify each staff member of the group change
    User = get_user_model()
    for staff in Staff.objects.filter(group_id=new_group_id):
        try:
            user = User.objects.get(id=staff.id)
            subject = "Group Change Notification"
            message = (
                f"Dear {user.first_name},\n\n"
                "Your group has been changed. Please log in to the system to review your new group assignments.\n\n"
                "Regards,\nGCPS Leave System"
            )
            send_leave_email.delay(subject, message, [user.email])
        except User.DoesNotExist:
            print(f"User with ID {staff.id} not found.")
        except Exception as e:
            print(f"Error notifying user {staff.id}: {e}")



def multi_change_category(form_data):
    """
    Changes the seniority category of multiple LeaveType records based on a list of IDs.
    Expects:
        - 'leave_type_ids': list of LeaveType IDs to update
        - 'new_category_id': ID of the new seniority category to assign
    """
    leave_type_ids = form_data.get('leave_type_ids', [])
    new_category_id = int(form_data['new_category_id'][0]) if isinstance(form_data['new_category_id'], (list, tuple)) else int(form_data['new_category_id'])
    if not leave_type_ids or not new_category_id:
        return

    # Normalize input to a list of integers
    if isinstance(leave_type_ids, str):
        leave_type_ids = [int(lid) for lid in leave_type_ids.split(',') if lid.isdigit()]
    elif isinstance(leave_type_ids, (list, tuple)):
        leave_type_ids = [int(lid) for lid in leave_type_ids if str(lid).isdigit()]
    else:
        leave_type_ids = []

    if not leave_type_ids:
        return

    # Update seniority category for all specified leave types
    LeaveType.objects.filter(id__in=leave_type_ids).update(seniority_id=new_category_id)