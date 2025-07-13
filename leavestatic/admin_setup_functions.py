from .models import *
from django.urls import reverse
#Staff
def add_staff(form_data, request):
    def get_instance(model, key):
        return model.objects.get(id=int(form_data[key]))

    try:
        # Create the staff object without username initially
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
        new_staff.save()  # Assigns ID

        # Generate username using staff ID
        new_staff.username = f"{new_staff.first_name}{new_staff.phone_number}{new_staff.id}"
        new_staff.save(update_fields=["username"])

        # Prepare leave detail records in bulk
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


        # Send email notification to user
        subject = "Account Created Successfully"
        message = (
            f"Dear {new_staff.first_name},\n"
            f"Your account was created successfully.\n"
            f"Your email is {new_staff.email}\n\n"
            f"Click on the link below to set your password:\n\n"
            f"{request.build_absolute_uri(reverse('password_reset'))}\n\n"
            "Best regards, \nGCPS Leave System"
        )
        receiver = new_staff.email
        send_mail( subject, message, settings.EMAIL_HOST_USER, [receiver], fail_silently=False)

        print("staff saved")
    except (KeyError, ValueError, Gender.DoesNotExist, Group.DoesNotExist, Seniority.DoesNotExist) as e:
        raise ValueError(f"Error adding staff: {e}")


    


def edit_staff(form_data):
    try:
        staff = Staff.objects.get(id=int(form_data['staff_id']))

        # Track original seniority before update
        original_seniority_id = staff.seniority_id

        # Update basic fields
        for field in ['first_name', 'last_name', 'other_names', 'phone_number', 'email']:
            setattr(staff, field, form_data[field])

        staff.gender = Gender.objects.get(id=int(form_data['gender']))
        staff.group = Group.objects.get(id=int(form_data['group']))
        new_seniority = Seniority.objects.get(id=int(form_data['seniority']))
        staff.seniority = new_seniority

        staff.save()

        # If seniority has changed, reset leave entitlements
        if original_seniority_id != new_seniority.id:
            # Delete old leave details
            StaffLeaveDetail.objects.filter(staff=staff).delete()

            # Create new leave details based on new seniority
            allowed_leave_types = LeaveType.objects.filter(seniority=new_seniority)
            leave_details = [
                StaffLeaveDetail(
                    staff=staff,
                    leave_type=leave_type,
                    days_taken=0,
                    days_remaining=leave_type.days if leave_type.days is not None else None
                )
                for leave_type in allowed_leave_types
            ]
            StaffLeaveDetail.objects.bulk_create(leave_details)

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

        # Prevent duplicate approvers for the same group and level
        exists = Approver.objects.filter(
            staff_id=approver_id,
            group_to_approve_id=approver_group_id,
            level_id=approver_level_id
        ).exists()

        if not exists:
            # Create the approver
            new_approver = Approver.objects.create(
                staff_id=approver_id,
                group_to_approve_id=approver_group_id,
                level_id=approver_level_id
            )

            # Fetch pending leave requests for the group and level
            pending_requests = LeaveRequest.objects.filter(
                applicant__group_id=approver_group_id,
                applicant__level_id=approver_level_id,
                status=LeaveRequest.Status.PENDING,
                is_active=True
            )

            # Create approval objects for each pending request
            for request in pending_requests:
                Approval.objects.create(
                    approver=new_approver,
                    request=request,
                    status=Approval.ApprovalStatus.Pending,
                    is_active=True
                )

            # Send email notification to the approver
            approver = Staff.objects.get(id=approver_id)
            subject = "New Approver Assignment"
            message = (
                f"Dear {approver.first_name},\n\n"
                f"You have been assigned as an approver for group '{approver.group.name}' "
                f"at level '{approver.level.name}'.\n\n"
                f"There are {pending_requests.count()} pending leave requests awaiting your review.\n"
                f"Please log in to the system to view and take action.\n\n"
                f"Regards,\nLeave Management System"
            )
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [approver.email],
                fail_silently=False
            )

    except (KeyError, ValueError, Staff.DoesNotExist) as e:
        print(f"Error adding approver: {e}")


#Edit Approver
def edit_approver(form_data):
    """
    Updates the approver assignments for a staff member.
    Expects:
        - approver_staff: staff id
        - groups: list of group ids (or a single id)
        - levels: list of level ids (or a single id)
      Only pairs up to the length of the shorter list.
    """
    try:
        # Accept both list and single value for staff_id
        staff_id_val = form_data['approver_staff']
        if isinstance(staff_id_val, (list, tuple)):
            staff_id = int(staff_id_val[0])
        else:
            staff_id = int(staff_id_val)

        # Get group_ids and level_ids as lists
        if hasattr(form_data, 'getlist'):
            group_ids = form_data.getlist('groups')
            level_ids = form_data.getlist('levels')
        else:
            group_ids = form_data.get('groups')
            level_ids = form_data.get('levels')
            if isinstance(group_ids, str):
                group_ids = [group_ids]
            if isinstance(level_ids, str):
                level_ids = [level_ids]

        # Remove empty strings
        group_ids = [gid for gid in group_ids if gid]
        level_ids = [lid for lid in level_ids if lid]

        # Remove all current approvers for this staff
        Approver.objects.filter(staff_id=staff_id).delete()

        # Only create as many pairs as the shorter list
        for group_id, level_id in zip(group_ids, level_ids):
            try:
                Approver.objects.create(
                    staff_id=staff_id,
                    group_to_approve_id=int(group_id),
                    level_id=int(level_id)
                )
            except Exception as e:
                print(f"Error creating approver for group {group_id} and level {level_id}: {e}")
    except Exception as e:
        print(f"Error editing approver: {e}")
    return
    


def del_approver(form_data):
    """
    Deactivates Approver objects and related Approval records for a given staff member(s).
    Expects:
        - staff_id: single ID or list of IDs for approvers to deactivate
    """
    staff_id = form_data.get('staff_id')
    if not staff_id:
        return

    # Normalize to a list of integers
    if isinstance(staff_id, (list, tuple)):
        staff_ids = [int(sid) for sid in staff_id if str(sid).isdigit()]
    else:
        staff_ids = [int(staff_id)] if str(staff_id).isdigit() else []

    if staff_ids:
        # Find active Approver records
        approver_qs = Approver.objects.filter(staff_id__in=staff_ids, is_active=True)

        # Collect approver IDs
        approver_ids = list(approver_qs.values_list("id", flat=True))

        # Deactivate approvers
        approver_qs.update(is_active=False)

        # Deactivate related approval records
        if approver_ids:
            Approval.objects.filter(approver_id__in=approver_ids).update(is_active=False)

    return


def res_approver(form_data):
    """
    Restores an Approver object by setting is_active=True.
    Expects:
        - approver_id: the id of the Approver object to restore
    """
    approver_id = form_data.get('approver_id')
    if not approver_id:
        return
    # Accept both a single ID or a list of IDs
    if isinstance(approver_id, (list, tuple)):
        ids = [int(aid) for aid in approver_id if str(aid).isdigit()]
    else:
        ids = [int(approver_id)] if str(approver_id).isdigit() else []

    if ids:
        Approver.objects.filter(id__in=ids).update(is_active=True)
    return


#Leave type
def add_leave_type(form_data):
    name = form_data['name']
    code = form_data['code']
    days = int(form_data['days'])
    seniority_id = int(form_data['seniority'])
    reset_period = form_data['reset_period']
    allow_multiple_applications = True if form_data['allow_multiple_applications']  == "True" else False
    paid_leave = True if form_data['paid_leave'] == "True" else False
    eligibility = form_data.get('eligibilty', "")
    
    i_date = True if 'i_date' in form_data else False
    i_institution = True if 'i_institution' in form_data else False
    i_course = True if 'i_course' in form_data else False
    i_note = True if 'i_note' in form_data else False
    i_letter = True if 'i_letter' in form_data else False

    new_lvt = LeaveType(
        name = name,
        code = code,
        days = days,
        seniority_id = seniority_id,
        reset_period = reset_period,
        allow_multiple_applications = allow_multiple_applications,
        paid_leave = paid_leave,
        eligibility = eligibility,
        includes_date_of_occurence = i_date,
        includes_institution = i_institution,
        includes_course = i_course,
        includes_med_note = i_note,
        includes_letter = i_letter,
        is_active = True
    )
    new_lvt.save()

    # Create StaffLeaveDetail for matching staff
    eligible_staff = Staff.objects.filter(seniority_id=seniority_id, is_active=True)
    for staff in eligible_staff:
        StaffLeaveDetail.objects.create(
            staff=staff,
            leave_type=new_lvt,
            days_taken=0,
            days_remaining=days,
            is_active=True
        )
    return



def edit_leave(form_data):
    leave_id = int(form_data.get("leave_id"))
    try:
        leave = LeaveType.objects.get(id=leave_id)
    except LeaveType.DoesNotExist:
        return  # Optionally log or raise an error here

    bool_fields = [
        "allow_multiple_applications",
        "paid_leave",
        "i_date",
        "i_institution",
        "i_course",
        "i_note",
        "i_letter",
    ]
    parsed_bools = {field: form_data.get(field) == "True" for field in bool_fields}

    leave.name = form_data.get("name")
    leave.code = form_data.get("code")
    leave.days = int(form_data.get("days", 0))
    leave.seniority_id = int(form_data.get("seniority"))
    leave.reset_period = form_data.get("reset_period")
    leave.eligibility = form_data.get("eligibility", "")

    # Assign all boolean fields dynamically
    for field, value in parsed_bools.items():
        setattr(leave, field, value)

    leave.save()
    return


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
    