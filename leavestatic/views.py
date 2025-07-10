from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from .forms import LoginForm
# , StaffForm, LeaveDetailsForm
from .models import *
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
import datetime, random
from django.shortcuts import redirect
from django.utils import timezone
import threading
from django.db.models import Prefetch, Q
import time
from django.shortcuts import get_object_or_404, redirect, render
# Create your views here.
import string
from .admin_setup_functions import *
from .functions import *
from .formHandlers import *
from django.utils.safestring import mark_safe
import json
from collections import defaultdict



# # for leave_request in Leave_Request.objects.all():
# #     if leave_request.leave_end_date < datetime.date.today() and leave_request.status != Leave_Request.Status.COMPLETED:
# #         if leave_request.status != Leave_Request.Status.APPROVED:
# #             print(f"Leave request {leave_request.id} has an end date in the past and is not completed. Updating status to REJECTED.")
# #             leave_request.status = Leave_Request.Status.REJECTED
# #         else: leave_request.status = Leave_Request.Status.COMPLETED
# #         leave_request.save()
# #         print(f"Updated leave request {leave_request.id} to REJECTED due to end date being in the past.")

# # # for leave_details in Leave_Details.objects.all():
# # #     if 


def index(request):
    template = loader.get_template('index.html')

    context = {

    }
    return HttpResponse(template.render(context, request))


def login_user(request, next_page):
    next_page = next_page if next_page else '0'  # Default to '0' if empty
    template = loader.get_template('login.html')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # Fetch staff object efficiently
            staff = Staff.objects.filter(email=email).first()
            if not staff:
                return redirect(reverse('login', args=['0',]))

            user = authenticate(request, username=staff.username, password=password)
            if user:
                login(request, user)
                
                temp_session = LoginSession.objects.filter(user=user)
                if len(temp_session) > 0:
                    # Delete previous sessions for the user
                    print("Deleting previous sessions for user:", user.username)
                    for session in temp_session:
                        session.delete()
                slug=random_string(50)
                other_sessions = LoginSession.objects.filter(slug=slug)
                while len(other_sessions) > 0:
                    slug = random_string(50)
                    other_sessions = LoginSession.objects.filter(slug=slug)
                new_session = LoginSession(
                    user=user,
                    session_key=request.session.session_key,
                    status='ACTIVE',
                    slug=slug,
                )
                new_session.save()

                request.session.modified = True  # Ensure session persistence
                
                print("Session user_slug:", request.session.get('user_slug'))
                if next_page.isdigit() and int(next_page) > 0:
                    response = HttpResponseRedirect(reverse('relieve_ack', args=[next_page, slug]))
                elif next_page != '0':
                    response = HttpResponseRedirect(reverse(next_page, args=[slug,]))
                else:
                    response = HttpResponseRedirect(reverse('dashboard', args=[slug]))
                request.session.update({
                    'user_slug': user.slug,
                    'user_email': user.email
                })
                response.set_cookie('session_id', request.session.session_key, max_age=86400, secure=True, httponly=True)
                return response
            else:
                form.add_error(None, "Invalid username or password")

    else:
        form = LoginForm()
    context = {'form': form, 'login': True, 'next_page': next_page}
    response = HttpResponse(template.render(context, request))
    response.set_cookie('session_id', request.session.session_key, max_age=86400, secure=True, httponly=True)
    return response


for staff in Staff.objects.filter(slug__isnull=True):
    base_slug = slugify(f"{staff.first_name}-{staff.phone_number}")
    slug = base_slug
    counter = 1
    while Staff.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    staff.slug = slug
    staff.save()
    print()


def dashboard(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)

    if not user_slug:
        return redirect(reverse("login", args=["leave_list"]))

    user = Staff.objects.get(slug=user_slug)
    is_approver = True if Approver.objects.filter(staff_id=user.id, is_active=True).count() > 0 else False
    print("pp ",is_approver)
    
    self_ack = Ack.objects.filter(staff_id=user.id, type=Ack.Type.SELF, status=Ack.Status.Pending).first()
    r_ack = Ack.objects.filter(staff_id=user.id, type=Ack.Type.RELIEF, status=Ack.Status.Pending).first()
    leaves_count = LeaveRequest.objects.filter(applicant_id=user.id).count()

    context = {
        "user_name": f"{user.last_name}, {user.first_name} {user.other_names}",
        'slug': slug,
        'is_approver': is_approver, "self_ack": self_ack,
        "r_ack": r_ack, "leaves_count": leaves_count,
    }

    response = render(request, "dashboard.html", context)
    response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)

    return response


def password_reset(request):
    template = loader.get_template("password_reset.html")
    step = 1
    random_number = None
    email = user = ''
    email_input = ''
    username = ''
    context = {
        'step': step, 'random_number': random_number, 'email': email, 
    }
    if request.method == 'POST':
        form_data = request.POST
        step = int(form_data['step'])
        username = form_data['usernameOriginal']
        if step == 1:
            email = form_data['email']
            if(len(Staff.objects.filter(email=email)) > 0):
                user = Staff.objects.get(email=email)
                username = user.username
            else: return HttpResponse("Account not found")
            context.update({'email': email, 'step':step, 'username':username})
            random_number = random.randrange(12345, 999999)
            subject="GCPS Leave System Verification Code"
            message=f"{random_number} is your verification code. Don't share your code with anyone."
            receiver = email
            # new_email = Email(
            #     subject = subject,
            #     message = message,
            #     receiver = receiver
            # )
            # new_email.save()
            send_mail(subject=subject, message=message, from_email=settings.EMAIL_HOST_USER, recipient_list=[receiver])
            step = step + 1
            context.update({ 'random_number':random_number, 'step':step, 'username': username })
        elif step == 2:
            code = form_data['verification_code']
            random_number = form_data['random_number']
            if code == random_number:
                step = step + 1
            else: return HttpResponse("Code is incorrect")
            context.update({'step':step, 'username': username})
        elif step == 3:
            password = form_data['password2']
            user = Staff.objects.get(username=username)
            user.set_password(password)
            user.save()
            return HttpResponseRedirect(reverse('login', args=['0',])) 
               
    return HttpResponse(template.render(context, request))




def sys_admin_login(request):
    template = loader.get_template("login.html")
    if request.method == "POST":
        form = LoginForm(request.POST)
    else: form = LoginForm()
    context = {
        'is_sys_admin' : True, "form" : form,
    }
    return HttpResponse(template.render(context, request))



def setup(request):
    template = loader.get_template("setup.html")
    groups = Group.objects.filter(is_active=True)
    levels = Level.objects.all()
    all_leave = LeaveType.objects.all().order_by('name','seniority__name')
    f_holidays = Holiday.objects.filter(type='Fixed', is_active=True).order_by("name")
    v_holidays = Holiday.objects.filter(type='Variable', is_active=True).order_by("name")
    all_holidays = Holiday.objects.all().order_by("name")
    all_groups = Group.objects.order_by('name')
    all_approvers = Approver.objects.all()
    all_types = Seniority.objects.all().order_by("name")
    all_genders = Gender.objects.all().order_by("name")
    all_levels = Level.objects.filter(is_active=True).order_by("name")
    i_levels = Level.objects.filter(is_active=False).order_by("name")
    active_groups = Group.objects.filter(is_active=True).order_by("name")
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    a_seniority = seniority.filter(is_active=True).order_by("name")
    i_seniority = Seniority.objects.filter(is_active=False).order_by("name")
    groups_list = {}
    staff_dict = {}
    group_ids = all_groups.values_list("id",flat=True)
    for id in group_ids:
        temp = Staff.objects.filter(group_id=id)
        staff_dict[id] = temp.count()

    # Maintain uniqueness by staff in all_approvers
    approvers_list = {}
    # Get all unique staff who are approvers
    staff_qs = Staff.objects.filter(approver__isnull=False).distinct()
    for staff in staff_qs:
        # Get all Approver records for this staff (each is a group/level pair)
        staff_approvers = Approver.objects.filter(staff=staff).select_related('group_to_approve', 'level')
        if staff_approvers:
            approvers_list[staff] = staff_approvers

    all_staff = Staff.objects.filter(is_superuser=False).order_by("last_name", "first_name")
    for group in groups:
        users = Staff.objects.filter(group=group)
        groups_list[group] = users

    if request.method == "POST":
        form_data = request.POST
        if form_data['form_meta'] == "add_group": add_group(form_data)
        elif form_data['form_meta'] == "edit_group": edit_group(form_data)
        elif form_data['form_meta'] == "del_group": del_group(dict(form_data))
        elif form_data['form_meta'] == "add_staff": add_staff(form_data, request)
        elif form_data['form_meta'] == "rem_staff": rem_staff(form_data)
        elif form_data['form_meta'] == "edit_staff": edit_staff(form_data)
        elif form_data['form_meta'] == "del_staff_form": del_staff(dict(form_data))
        elif form_data['form_meta'] == "restore_group": restore_group(dict(form_data))
        elif form_data['form_meta'] == "restore_staff": restore_staff(dict(form_data))
        elif form_data['form_meta'] == "add_approver": add_approver(form_data)
        elif form_data['form_meta'] == "edit_app": edit_approver(dict(form_data))
        elif form_data['form_meta'] == "del_approver": del_approver(form_data)
        elif form_data['form_meta'] == "restore_approver": res_approver(form_data)
        elif form_data['form_meta'] == "add_lvt": add_leave_type(form_data)
        elif form_data['form_meta'] == "edit_lvt": edit_leave(form_data)
        elif form_data['form_meta'] == "del_lvt": del_leave(dict(form_data))
        elif form_data['form_meta'] == "res_lvt": res_leave(form_data)
        elif form_data['form_meta'] == "add_hol": add_holiday(form_data)
        elif form_data['form_meta'] == "edit_hol": edit_holiday(form_data)
        
        elif form_data['form_meta'] == "del_gender": del_gender(form_data)
        elif form_data['form_meta'] == "res_gender": res_gender(form_data)
        elif form_data['form_meta'] == "edit_gender": edit_gender(form_data)
        elif form_data['form_meta'] == "add_gender": add_gender(form_data)
        
        elif form_data['form_meta'] == "add_cat": add_sen(form_data)
        elif form_data['form_meta'] == "edit_cat": edit_sen(form_data)
        elif form_data['form_meta'] == "res_sen": res_sen(form_data)
        elif form_data['form_meta'] == "del_sen": del_sen(form_data)
        
        elif form_data['form_meta'] == "del_level": del_lvl(form_data)
        elif form_data['form_meta'] == "res_level": res_lvl(form_data)
        elif form_data['form_meta'] == "add_level": add_lvl(form_data)
        elif form_data['form_meta'] == "edit_level": edit_lvl(form_data)
        print(form_data)
        return redirect(setup)

    context = {
        'first_time': False, 'groups_list': groups_list,
        'approvers_list': approvers_list, 'all_staff': all_staff,
        'all_leave': all_leave, 'f_holidays': f_holidays,
        'v_holidays': v_holidays, 'all_holidays': all_holidays,
        "all_groups": all_groups,
        'all_approvers': all_approvers, 'all_types': all_types,
        'all_genders': all_genders, 'all_levels': all_levels,
        'seniority': seniority, 'staff_dict': staff_dict,
        'active_groups': active_groups, 'i_seniority': i_seniority,
        'a_seniority': a_seniority, "i_levels" : i_levels
    }
    return HttpResponse(template.render(context, request))

def sys_admin(request):
    template = loader.get_template("system_admin.html")

    context = {
        "first_time": True,
    }
    return HttpResponse(template.render(context, request))


# def sec_check(request, slug):
#     template = loader.get_template("red.html")

#     context = {

#     }
#     return HttpResponse(template.render(context, request))


# def add_department(request, slug):
#     """Handles department creation efficiently using session validation."""

#     user_slug = request.session.get("user_slug") or change_session(slug)

#     if not user_slug:
#         return redirect(reverse("login", args=["add_department"]))
    
#     # Update session messages
#     request.session.update({
#         "prev_page": "add_department",
#         "message": "Department created successfully",
#         "button": "Add another department",
#         "next_page": "all_staff",
#         "next_btn": "Back to All Staff"
#     })

#     # Update LoginSession efficiently
#     LoginSession.objects.filter(slug=user_slug).update(
#         prev_page="add_department",
#         button="Add another department",
#         next_page="all_staff",
#         next_btn="Back to All Staff",
#         message="Department created successfully"
#     )

#     user = get_object_or_404(Staff.objects.select_related("department"), slug=user_slug)

#     all_staff = Staff.objects.filter(is_superuser=False).exclude(type__in=["RECTOR", "HOHR", "STAFF"]).order_by("last_name", "first_name")

#     if request.method == "POST":
#         form_data = request.POST
#         dept_head = get_object_or_404(Staff, slug=form_data["dept_head"])

#         new_department = Department.objects.create(
#             department_name=form_data["dept_name"],
#             department_head=dept_head,
#             department_head_email=dept_head.email,
#             department_head_phone=dept_head.phone_number,
#             department_image=request.FILES.get("dept_icon", "not")
#         )

#         return HttpResponseRedirect(reverse("all_staff", args=[slug]))

#     context = {
#         "all_staff": all_staff,
#     }

#     response = render(request, "add_department.html", context)
#     response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)

#     return response



def leave_request(request, slug):
    """Handles leave request submission with session validation."""

    user_slug = request.session.get("user_slug") or change_session(slug)

    if not user_slug:
        return redirect(reverse("login", args=["leave_request"]))

    request.session.update({
        "prev_page": f"leave_request",
        "message": "Leave Request successful. Pending approval. For more information, please contact your administrator.",
        "button": "Request For Another Leave",
        "next_page": f"leave_list",
        "next_btn": "Back to Dashboard",
    })

    # Update LoginSession efficiently
    LoginSession.objects.filter(slug=user_slug).update(
        prev_page="leave_request",
        button="Request For Another Leave",
        next_page=f"leave_list",
        next_btn="Back to Dashboard",
        message="Leave Request successful. Pending approval. For more information, please contact your administrator.",
    )

    user = Staff.objects.get(slug=user_slug)
    allowed_leave_types = LeaveType.objects.filter(seniority_id=user.seniority_id, is_active=True)
    leave_type_dict = {}
    staffLeaveDetails = StaffLeaveDetail.objects.filter(staff_id=user.id)
    allowed_leave_type_dict = {
        lt.id: 
        {"name": str(lt.name) or "N/A", "days": lt.days or "N/A", "paidLeave": str(lt.paid_leave) or "N/A", "i_date": str(lt.includes_date_of_occurence),
        "i_institution": str(lt.includes_institution), "i_course": str(lt.includes_course), "i_note": str(lt.includes_med_note),
        "i_letter": str(lt.includes_letter) } 
        for lt in allowed_leave_types
    }
    staff_leave_data = {
        ld.leave_type_id:
        {"taken": ld.days_taken or 0, "remaining": ld.days_remaining or 0, "leave_type": ld.leave_type.name or "N/A"}
        for ld in staffLeaveDetails
    }
    relieving_officers = Staff.objects.filter(is_active=True, group_id=user.group.id).exclude(id=user.id).order_by("first_name", "last_name")

    for leave_type in allowed_leave_types:
        leave_type_dict[leave_type.id] = leave_type.name
    
    if request.method == "POST":
        form_data = request.POST
        result = leaveRequestHandler(form_data, user, request, slug)

    # if request.method == "POST":
    #     form_data = request.POST
    #     relieving_officer = get_object_or_404(Staff, slug=form_data["relieving_officer"])

    #     leave_request = Leave_Request.objects.create(
    #         applicant=user,
    #         leave_days_requested=form_data["days_requested"],
    #         leave_start_date=form_data["start_date"],
    #         leave_end_date=form_data["end_date"],
    #         resumption_date=form_data["resumption_date"],
    #         reason=form_data.get("reason", None),            
    #         type=form_data["leave_type"],
    #         relieving_officer=relieving_officer,
    #         med_note=request.FILES["med_note"] if form_data["med_note"] != "" else None,
    #         letter=request.FILES["letter"] if form_data["letter"] != "" else None,
    #         disembarkation_date=form_data["disembarkation"] if form_data["disembarkation"] != "" else None,
    #         due_date=form_data["due-date"] if form_data["due-date"] != "" else None,
    #         institution=form_data["institution"] if form_data["institution"] != "" else None,
    #         course=form_data["course"] if form_data["course"] != "" else None,
    #     )
    #     approval_mapping = {
    #         "HOD": [("department_head_approval", "APPROVED"), ("department_head_approval_date", timezone.now())],
    #         "HOHR": [
    #             ("department_head_approval", "APPROVED"), ("department_head_approval_date", timezone.now()),
    #             ("HOHR_approval", "APPROVED"), ("HOHR_approval_date", timezone.now())
    #         ],
    #         "RECTOR": [("final_approval", "APPROVED"), ("final_approval_date", timezone.now())]
    #     }

    #     if user.type in approval_mapping:
    #         for field, value in approval_mapping[user.type]:
    #             setattr(leave_request, field, value)

    #     leave_request.save()


    #     # Email Notification
    #     subject = f"Notification of Relief Assignment During {user.first_name} {user.last_name}’s Leave"
    #     message = (
    #         f"Dear {relieving_officer.first_name},\n\n"
    #         f"I hope this email finds you well.\n\n"
    #         f"As part of our operational planning, I would like to formally notify you that "
    #         f"you will be temporarily relieving {user.first_name} {user.last_name}, {user.other_names} "
    #         f"during their {leave_request.type.lower()} leave from {leave_request.leave_start_date} to {leave_request.leave_end_date}.\n\n"
    #         f"Your responsibilities will include {user.first_name}’s duties during this period. "
    #         f"Please let me know if you require any additional support or resources to ensure a smooth transition. "
    #         f"Your cooperation and professionalism are greatly appreciated.\n\n"
    #         f"Kindly confirm your understanding of this arrangement at your earliest convenience. "
    #         f"Should you have any questions, please feel free to reach out.\n\n"
    #         f"Thank you for your dedication and support.\n\n"
    #         f"Click on this link to acknowledge this email:\n\n"
    #         f"{request.build_absolute_uri(reverse('relieve_ack', args=[leave_request.id, slug]))}"
    #     )
        
    #     Email.objects.create(subject=subject, message=message, receiver=relieving_officer.email)

    #     response = HttpResponseRedirect(reverse("success_page", args=[slug]))
    #     response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
    #     return response

    # Prepare response context
    context = {
        "user_name": f"{user.last_name}, {user.first_name} {user.other_names}",
        "user_id": user.id, "user": user,
        "allowed_leave_types": allowed_leave_types,
        'leave_type_dict': leave_type_dict,
        'allowed_leave_types_dict': allowed_leave_type_dict,
        'staff_leave_data': staff_leave_data, "officers": relieving_officers,
    }

    response = render(request, "leave_form.html", context)
    response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)

    return response





def relieve_ack(request, id, slug):
    # 1. Validate session
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=[id]))

    # 2. Fetch Ack and related staff in one query
    ack = get_object_or_404(Ack.objects.select_related("staff"), id=id)
    user = ack.staff

    # 3. Ensure the session user matches the Ack's staff
    if user_slug != user.slug:
        return redirect(reverse("login", args=[id]))

    # 4. Determine next page based on user type
    next_page = "leave_list" if getattr(user, "type", "STAFF") == "STAFF" else "admin_dashboard"

    # 5. Update session and LoginSession
    session_updates = {
        "prev_page": "not",
        "message": "Your response has been received and will be reviewed. For more information, please contact your administrator.",
        "button": "not",
        "next_page": next_page,
        "next_btn": "Back to Dashboard",
    }
    request.session.update(session_updates)

    LoginSession.objects.filter(slug=user_slug).update(**session_updates)

    # 6. Handle POST submission
    if request.method == "POST":
        form_data = request.POST
        if form_data['form_meta'] == "approve": approve_ack(form_data, request)
        elif form_data['form_meta'] == "deny": deny_ack(form_data, request)
        response = HttpResponseRedirect(reverse("dashboard", args=[slug]))
        response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
        return response

    # 7. Render template
    context = {
        "date": timezone.now().date(),
        "ack": ack,
        "id": id,
        "slug": slug,
    }
    response = render(request, "relieve_ack.html", context)
    response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
    return response




def leave_history(request, slug):
    """Displays a user's leave history with approval and acknowledgment progress."""

    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["leave_history"]))

    user = get_object_or_404(Staff, slug=user_slug)

    # Prefetch related approvals and acknowledgments
    leave_requests = (
        LeaveRequest.objects
        .filter(applicant=user)
        .select_related("type")
        .prefetch_related(
            Prefetch("approval_set", queryset=Approval.objects.select_related("approver__staff")),
            Prefetch("ack_set", queryset=Ack.objects.select_related("staff"))
        )
        .order_by("-application_date")
    )

    # Group by year
    grouped_leave = {}
    for lr in leave_requests:
        year = lr.application_date.year
        grouped_leave.setdefault(year, []).append(lr)

    context = {
        "leave_requests": leave_requests,
        "grouped_leave": grouped_leave,
        "slug": slug,
    }

    response = render(request, "leave_history.html", context)
    response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
    return response




def user_logout(request, slug):
    """Handles secure user logout with session validation."""

    user_slug = request.session.get("user_slug") or change_session(slug)

    if not user_slug:
        return redirect(reverse("login"))

    logout(request)
    LoginSession.objects.filter(slug=user_slug).update(
                status='INACTIVE',
                date_to_expire=timezone.now(),
                last_activity=timezone.now()
            )
    response = HttpResponseRedirect(reverse("login", args=["0",]))
    response.delete_cookie("session_id")

    return response




# def signup_user(request, slug):
#     """Handles user signup efficiently using session validation."""

#     user_slug = request.session.get("user_slug") or change_session(slug)
    
#     if not user_slug: 
#         return redirect(reverse("login", args=["signup"]))

#     request.session.update({
#         "prev_page": f"/signup/{slug}",
#         "next_page": f"/leaveapplications/{slug}",
#         "next_btn": "Back to Dashboard",
#         "button": "Add another User",
#     })
    
#     current_user = get_object_or_404(Staff.objects.select_related("department"), slug=user_slug)

#     # Allow only authorized roles
#     allowed_roles = {"HOD", "HOHR", "RECTOR"}
#     if current_user.type not in allowed_roles:
#         return HttpResponse("Sorry, you are not allowed to view this page", status=403)

#     # Fetch emails efficiently
#     emails = list(Staff.objects.all().values_list("email", flat=True))
#     print(len(Staff.objects.all()))
#     print("ee  ", emails)
#     all_departments = Department.objects.all()

#     if request.method == "POST":
#         form_data = request.POST
#         user = Staff(
#             first_name = form_data['first_name'],
#             last_name = form_data['last_name'],
#             other_names = form_data['other_names'],
#             phone_number = form_data['phone_number'],
#             email = form_data['email'],
#             department_id = int(form_data['department']),
#             type = form_data['type'],
#             position = form_data['position'],
#             sex = form_data['sex'],
#         )
#         user.username = f"{user.first_name}{user.last_name[0]}{user.other_names[0]}{Staff.objects.count()}"
#         user.save()

#         subject = "Account Created Successfully"
#         message = (
#             f"Dear {user.first_name},\n"
#             f"Your account was created successfully.\n"
#             f"Your email is {user.email}\n\n"
#             f"Click on the link below to set your password:\n\n"
#             f"{request.build_absolute_uri(reverse('password_reset'))}\n\n"
#             "Best regards, \nGCPS Leave System"
#         )
#         Email.objects.create(subject=subject, message=message, receiver=user.email)

#         # Handle HOD role department assignment
#         if user.type == "HOD":
#             Department.objects.filter(id=user.department_id).update(
#                 department_head_id=user.id,
#                 department_head_email=user.email,
#                 acting_department_head_phone=user.phone_number,
#             )

#         if request.POST.get("leave_details"):
#             leave_details = Leave_Details.objects.create(
#                 days_entitled=36, days_eligible=36, days_taken=0, days_remaining=36, staff=user
#             )
#             LoginSession.objects.filter(slug=slug).update(
#                 prev_page="signup",
#                 button="Add another User",
#                 next_page=f"admin_dashboard",
#                 next_btn="Back to Dashboard",
#                 message= request.session.get("message", None)
#             )

#             response = HttpResponseRedirect(reverse("success_page", args=[slug,]))
#             response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
#             return response

#         request.session["message"] = (
#             f"User created successfully.\n\tName:\t{user.first_name} {user.last_name}, {user.other_names}\n"
#             f"\tEmail:\t{user.email}\n\tDepartment:\t{user.department.department_name}\n"
#             f"\tPosition:\t{user.position}"
#         )
#         LoginSession.objects.filter(slug=slug).update(
#             prev_page="signup",
#             button="Add another User",
#             next_page="leave_list",
#             next_btn="Back to Dashboard",
#             message= request.session.get("message", None)
#             )
#         response = HttpResponseRedirect(reverse("leave_details_view", args=[user.slug, slug]))
#         response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
#         return response

#     return render(request, "signup.html", {"emails": emails, "all_departments": all_departments, "current_user": current_user, "user_type": current_user.type, 'slug': slug})




# def success_page(request, slug):
#     """Handles the success page efficiently using session validation with change_session()."""

#     user_slug = request.session.get("user_slug") or change_session(slug)

#     if not user_slug:
#         return redirect(reverse("login", args=["success_page"]))

#     current_session = get_object_or_404(LoginSession.objects.select_related("user"), slug=slug)
#     prev_page = current_session.prev_page
#     page_ref = {
#         'leave_request': f'/leave_request/{slug}'
#     }
#     # Retrieve session values with default fallbacks
#     context = {
#         "prev_page": request.session.get("prev_page", current_session.prev_page or "login/0"),
#         "message": request.session.get("message", current_session.message or ""),
#         "button": request.session.get("button", current_session.button or ""),
#         "next_page": request.session.get("next_page", current_session.next_page or ""),
#         "next_btn": request.session.get("next_btn", current_session.next_btn or ""),
#     }

#     response = render(request, "success_page.html", context)
#     response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)

#     return response



def staff_ack(request, slug):
    """Handles staff leave request acknowledgements with session validation."""

    user_slug = request.session.get("user_slug") or change_session(slug)

    if not user_slug:
        return redirect(reverse("login", args=["leave_details_view"]))

    user = get_object_or_404(Staff.objects.select_related("department"), slug=user_slug)
    
    # Prepare session messages
    request.session.update({
        "prev_page": "not",
        "message": "Leave Request acknowledgement successful. For more information, please contact your administrator",
        "button": "not",
        "next_page": f"/leaveapplications/{slug}",
        "next_btn": "Back to Dashboard",
    })
    LoginSession.objects.filter(slug=slug).update(
        prev_page="not",
        button="not",
        next_page=f"leave_list",
        next_btn="Back to Dashboard",
        message="Leave Request acknowledgement successful. For more information, please contact your administrator"
            )
    # Retrieve leave request efficiently
    leave_request = Leave_Request.objects.filter(applicant=user, status="APPROVED").first()

    if not leave_request:
        return HttpResponseRedirect(reverse("success_page", args=[slug,]))

    department_head = get_object_or_404(Staff, department=user.department, type="HOD")
    HOHR = get_object_or_404(Staff, type="HOHR")

    if request.method == "POST":
        form_data = request.POST
        leave_request.applicant_approval = form_data.get("staff_ack")
        leave_request.applicant_approval_date = timezone.now()
        leave_request.save()

        if leave_request.applicant_approval == "REJECTED":
            leave_request.status = "CANCELLED"
            notify_staff_rejection(leave_request, department_head)

        elif leave_request.applicant_approval == "APPROVED":
            leave_request.status = "APPROVED"
            notify_staff_approval(leave_request, department_head)

        response = HttpResponseRedirect(reverse("success_page", args=[slug,]))
        response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
        return response

    # Prepare response context
    context = {
        "leave_request": leave_request,
        "department_head_name": f"{department_head.first_name} {department_head.last_name} {department_head.other_names}",
        "HOHR_name": f"{HOHR.first_name} {HOHR.last_name} {HOHR.other_names}",
    }

    response = render(request, "staff_ack.html", context)
    response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
    return response

# def notify_staff_rejection(leave_request, department_head):
#     """Send notifications upon leave request rejection."""
#     subject = "Notification of Leave Request Cancellation"
#     message = (
#         f"Dear {department_head.first_name},\n\n"
#         f"I hope this email finds you well.\n\n"
#         f"The leave application submitted on {leave_request.application_date} "
#         f"by {leave_request.applicant.first_name} {leave_request.applicant.last_name} has been cancelled.\n\n"
#         f"If further clarification is required, please reach out.\n\n"
#         f"Yours sincerely,\nGCPS Leave System"
#     )
#     Email.objects.create(subject=subject, message=message, receiver=department_head.email)

#     subject = "Acknowledgment of Leave Request Terms Denial"
#     message = (
#         f"Dear {leave_request.applicant.first_name},\n\n"
#         f"We acknowledge your response regarding the approved leave request.\n\n"
#         f"If additional clarifications are required, kindly notify your Administrator.\n\n"
#         f"Yours sincerely,\nGCPS Leave System"
#     )
#     Email.objects.create(subject=subject, message=message, receiver=leave_request.applicant.email)

# def notify_staff_approval(leave_request, department_head):
#     """Send notifications upon leave request approval."""
#     subject = "Leave Request Acknowledgement"
#     message = (
#         f"Dear {department_head.first_name},\n\n"
#         f"The leave application submitted by {leave_request.applicant.first_name} {leave_request.applicant.last_name} "
#         f"on {leave_request.application_date:%B %d, %Y} has been approved.\n\n"
#         f"If further clarification is required, please reach out.\n\n"
#         f"Yours sincerely,\nGCPS Leave System"
#     )
#     Email.objects.create(subject=subject, message=message, receiver=department_head.email)

#     subject = "Confirmation of Leave Request Terms Acceptance"
#     message = (
#         f"Dear {leave_request.applicant.first_name},\n\n"
#         f"Your leave request submitted on {leave_request.application_date} has been approved.\n\n"
#         f"If you require any further clarification, please contact our support team.\n\n"
#         f"Yours sincerely,\nGCPS Leave System"
#     )
#     Email.objects.create(subject=subject, message=message, receiver=leave_request.applicant.email)



# def leave_details_view(request, staff_slug, slug):
#     """Handles staff leave details efficiently using session validation."""
    
#     user_slug = request.session.get("user_slug") or change_session(slug)
    
#     if not user_slug:
#         return redirect(reverse("login", args=["leave_details_view"]))

#     request.session.update({"prev_page": "signup"})

#     user = get_object_or_404(Staff.objects.select_related("department"), slug=user_slug)
#     staff = get_object_or_404(Staff.objects.select_related("department"), slug=staff_slug)

#     if request.method == "POST":
#         form = LeaveDetailsForm(request.POST)

#         if form.is_valid():
#             new_leave_details = Leave_Details.objects.create(
#                 staff=staff,
#                 days_entitled=form.cleaned_data["days_entitled"],
#                 days_eligible=form.cleaned_data["days_eligible"],
#                 days_taken=form.cleaned_data["days_taken"],
#                 days_remaining=form.cleaned_data["days_entitled"] - form.cleaned_data["days_taken"]
#             )

#             # Update session messages
#             request.session.update({
#                 "prev_page": f"/signup/{slug}",
#                 "button": "Add another User",
#                 "message": (
#                     f"User created successfully.\n\tName:\t{staff.first_name} {staff.last_name}, {staff.other_names}\n"
#                     f"\tEmail:\t{staff.email}\n\tDepartment:\t{staff.department.department_name}\n"
#                     f"\tPosition:\t{staff.position}\n\nLeave Details\n\tDays Entitled:\t{new_leave_details.days_entitled}\n"
#                     f"\tDays Eligible:\t{new_leave_details.days_eligible}\n\tDays Taken:\t{new_leave_details.days_taken}\n"
#                     f"\tDays Remaining:\t{new_leave_details.days_remaining}"
#                 ),
#                 "next_page": f"/leaveapplications/{slug}",
#                 "next_btn": "Back to Dashboard"
#             })

#             # Update LoginSession efficiently
#             LoginSession.objects.filter(slug=staff_slug).update(
#                 prev_page=f"signup",
#                 button="Add another User",
#                 next_page=f"leave_list",
#                 next_btn="Back to Dashboard",
#                 message=request.session.get("message", None)
#             )

#             response = HttpResponseRedirect(reverse("success_page", args=[slug,]))
#             response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
#             return response

#     else:
#         form = LeaveDetailsForm()

#     context = {
#         "form": form,
#         "user_name": f"{staff.last_name}, {staff.first_name} {staff.other_names}",
#         "staff_slug": staff_slug, 'slug': slug,
#     }

#     response = render(request, "leave_details_form.html", context)
#     response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)

#     return response



# def is_not_integer(s):
#     try:
#         int(s)  # Try converting the string to an integer
#         return False  # If successful, it's a valid integer
#     except ValueError:
#         return True  # If an error occurs, it's not an integer





def users_on_leave(request, slug):
    """Lists all users currently on leave, grouped by their department (group)."""

    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["staff_on_leave"]))

    user = get_object_or_404(Staff, slug=user_slug)
    today = timezone.now().date()

    # Fetch all active leave objects with related request and applicant
    active_leaves = Leave.objects.select_related(
        "request__applicant__group", "request__type"
    ).filter(
        is_active=True,
        request__is_active=True,
        request__return_date__gte=today,
        request__status=LeaveRequest.Status.APPROVED
    ).exclude(request__status=LeaveRequest.Status.COMPLETED)

    # Group leaves by department
    dept_group = defaultdict(list)
    for leave in active_leaves:
        group = leave.request.applicant.group
        dept_group[group].append(leave)

    context = {
        "slug": slug,
        "dept_group": dict(dept_group),
    }

    response = render(request, "on_leave.html", context)
    response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
    return response





# def all_staff(request, slug):
#     """Handles the staff list view efficiently using session validation."""

#     user_slug = request.session.get("user_slug") or change_session(slug)
    
#     if not user_slug:  # Redirect if no session is found
#         return redirect(reverse("login", args=["all_staff"]))

#     user = get_object_or_404(Staff.objects.select_related("department"), slug=user_slug)

#     grouped_staff = {}  # Dictionary to hold department-wise staff mapping
#     department_name = user.department.department_name if user.department else ""
    
#     if user.type == "HOD":
#         departments = (Department.objects.filter(department_head=user) | Department.objects.filter(acting_department_head=user)).order_by("department_name")
#         members = {}
#         for department in departments:
#             temp = Staff.objects.filter(department_id=department.id).order_by('last_name')
#             members[department] = temp
#         context = {
#             "user_type": user.type,
#             "members": members,
#             "department_name": department_name,
#             "slug2": user.slug,
#         }
    
#     elif user.type in {"HOHR", "RECTOR"}:
#         departments = Department.objects.all()
#         unassigned_staff_exists = Staff.objects.filter(department=None).exists()

#         for department in departments:
#             staff = Staff.objects.filter(department=department, is_superuser=False).order_by("last_name")
#             grouped_staff[department] = staff
        
#         context = {
#             "user_type": user.type,
#             "department_name": department_name,
#             "slug": slug,
#             "group": grouped_staff,
#             "ustaff": unassigned_staff_exists,
#             "slug2": slug,
#         }

#     response = render(request, "all_staff.html", context)
#     response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)

#     return response





# def department_details(request, department_id, slug):
#     """Handles department details efficiently using session validation."""
#     user_slug = request.session.get("user_slug") or change_session(slug)
#     if not user_slug:
#         print("goin back") 
#         return redirect(reverse("login", args=["department_details"]))

#     user = get_object_or_404(Staff.objects.select_related("department"), slug=user_slug)

#     # Only allow HOHR and RECTOR roles
#     if user.type not in {"HOHR", "RECTOR"}:
#         return HttpResponse("Please sign in", status=403)

#     department = get_object_or_404(Department, id=int(department_id))

#     # Retrieve related staff and departments efficiently
#     all_staff = Staff.objects.order_by("department_id")
#     members = Staff.objects.filter(department=department)
#     all_departments = Department.objects.exclude(id=department_id).order_by("department_name")

#     # Handle POST request
#     if request.method == "POST":
#         form_data = request.POST

#         if "department_head" in form_data:
#             # Update department details
#             former_head = Staff.objects.get(id=department.department_head_id)
#             former_head.type = "STAFF"
#             former_head.position = "Unknown"
#             former_head.save()
#             department.department_name = form_data.get("department_name", department.department_name)
#             department.department_head_id = int(form_data.get("department_head", department.department_head_id))
#             department.department_image = form_data.get("department_image") if "department_image" in form_data != '' else department.department_image
            
#             staff = Staff.objects.get(id=department.department_head_id)
#             staff.department_id = department.id if staff.department_id != department.id and staff.type == "STAFF" else staff.department_id
#             staff.type = "HOD"
#             staff.position = f"Head of {department.department_name}"
#             department.department_head_email = staff.email
#             department.save()
#             staff.save()

#         elif "delete-option" in form_data:
#             delete_option = form_data["delete-option"]

#             if delete_option == "reassign":
#                 for index, member in enumerate(members, start=1):
#                     new_department_id = int(form_data.get(f"member_name{index}", member.department_id))
#                     member.department_id = new_department_id
#                     member.save()
#                 department.delete()

#             elif delete_option == "set_to_none":
#                 members.update(department=None)
#                 department.delete()

#             elif delete_option == "delete_all":
#                 members.delete()
#                 department.delete()

#             else:
#                 department.delete()

#             request.session.update({
#                 "prev_page": "not",
#                 "button": "not",
#                 "next_page": f"all_staff",
#                 "next_btn": "View All Staff",
#                 "message": "Department deleted successfully."
#             })
#            # Update LoginSession efficiently
#             LoginSession.objects.filter(slug=slug).update(
#                 prev_page="not",
#                 button="not",
#                 next_page=f"all_staff",
#                 next_btn="View All Staff",
#                 message="Department deleted successfully.",
#                 last_activity=timezone.now(),
#                 date_to_expire=timezone.now() + timezone.timedelta(days=1)
#             )

#             return HttpResponseRedirect(reverse("success_page", args=[slug,]))

#     # Render response
#     context = {
#         "department": department,
#         "all_staff": all_staff,
#         "members": members,
#         "all_departments": all_departments,
#         "slug": slug
#     }
    
#     response = render(request, "department_details.html", context)
#     response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)

#     return response



# def staff_delete(request, slug):
#     """Handles staff deletion securely with optimized session validation."""

#     user_slug = request.session.get("user_slug") or change_session(slug)

#     if not user_slug:
#         return redirect(reverse("login", args=["staff_delete"]))

#     request.session.update({
#         "prev_page": "admin_dashboard",
#         "message": "Staff deleted successfully.",
#         "button": "Back to dashboard",
#         "next_page": "all_staff",
#         "next_btn": "Back to all staff",
#     })

#     # Update LoginSession efficiently
#     LoginSession.objects.filter(slug=user_slug).update(
#         prev_page="admin_dashboard",
#         button="Back to dashboard",
#         next_page="all_staff",
#         next_btn="Back to all staff",
#         message="Staff deleted successfully.",
#         last_activity=timezone.now(),
#         date_to_expire=timezone.now() + timezone.timedelta(days=1),
#     )

#     if request.method == "POST":
#         staff_id = request.POST.get("staff_id")
#         staff = get_object_or_404(Staff, id=staff_id)
#         staff.delete()

#         response = HttpResponseRedirect(reverse("all_staff", args=[slug,]))
#         response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)

#     return response





# def staff_password_reset(request, slug):
#     """Handles staff password reset requests securely with session validation."""

#     user_slug = request.session.get("user_slug") or change_session(slug)

#     if not user_slug:
#         return redirect(reverse("login", args=["staff_password_reset"]))

#     if request.method == "POST":
#         staff_id = request.POST.get("staff_id")
#         staff = get_object_or_404(Staff, id=staff_id)

#         message = (
#             f"Dear {staff.first_name}, \n\n"
#             f"Your administrator has initiated a password reset for your account. \n\n"
#             f"Please use the following link to reset your password: \n\n"
#             f"{request.build_absolute_uri(reverse('password_reset'))}"
#             f"\n\nIf you did not request this change, please contact your administrator immediately.\n\n"
#             f"Best regards,\nGCPS Leave System"
#         )

#         Email.objects.create(
#             subject="Password Reset Request",
#             message=message,
#             receiver=staff.email
#         )

#         response = HttpResponseRedirect(reverse("all_staff", args=[slug]))
#         response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)

#         return response



def profile(request, slug):
    """Displays and manages a staff profile with leave stats and approver status."""

    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["profile"]))

    user = get_object_or_404(Staff, slug=user_slug)

    # Fetch all leave details for this staff
    leave_details = StaffLeaveDetail.objects.filter(staff=user, is_active=True).select_related("leave_type")

    # Check if user is an approver
    is_approver = Approver.objects.filter(staff=user, is_active=True).exists()

    # Update session metadata
    request.session.update({
        "prev_page": "profile",
        "message": "Profile updated successfully",
        "button": "Back to Profile",
        "next_page": "leaveapplications" if user.is_staff else "admin_dashboard",
        "next_btn": "Back to Dashboard",
    })

    # Update login session
    LoginSession.objects.filter(slug=user_slug).update(
        prev_page="profile",
        button="Back to Profile",
        next_page="leave_list" if user.is_staff else "admin_dashboard",
        next_btn="Back to Dashboard",
        message="Profile updated successfully",
        last_activity=timezone.now(),
        date_to_expire=timezone.now() + timezone.timedelta(days=1),
    )

    # Handle profile update
    if request.method == "POST":
        form_data = request.POST
        user.email = form_data.get("email", user.email)
        user.phone_number = form_data.get("phone", user.phone_number)
        user.first_name = form_data.get("f_name", user.first_name)
        user.last_name = form_data.get("l_name", user.last_name)
        user.other_names = form_data.get("o_name", user.other_names)
        user.save()

    context = {
        "user": user,
        "leave_details": leave_details,
        "is_approver": is_approver,
        "slug": slug,
    }

    response = render(request, "profile.html", context)
    response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
    return response



# def staff_details(request, staff_slug, slug):
#     """Handles staff details with optimized session validation and form processing."""
#     user_slug = request.session.get("user_slug") or change_session(slug)
#     if not user_slug:
#         return redirect(reverse("login", args=["0",]))

#     user = get_object_or_404(Staff.objects.select_related("department"), slug=user_slug)
#     staff = get_object_or_404(Staff.objects.select_related("department"), slug=staff_slug)
#     leave_details = get_object_or_404(Leave_Details, staff=staff)
#     leave_requests = Leave_Request.objects.filter(applicant=staff).order_by("-application_date")

#     request.session.update({
#         "prev_page": "all_staff",
#         "message": "Details updated successfully",
#         "button": "Back to All Staff",
#         "next_page": "admin_dashboard",
#         "next_btn": "Back to Dashboard",
#     })

#     LoginSession.objects.filter(slug=user_slug).update(
#         prev_page="all_staff",
#         button="Back to All Staff",
#         next_page="admin_dashboard",
#         next_btn="Back to Dashboard",
#         message="Details updated successfully",
#         last_activity=timezone.now(),
#         date_to_expire=timezone.now() + timezone.timedelta(days=1),
#     )

#     # Determine accessible departments
#     departments = Department.objects.all() if user.type in {"HOHR", "RECTOR"} else Department.objects.filter(id=user.department.id)

#     if request.method == "POST":
#         form_data = request.POST
#         staff.first_name = form_data.get("first_name", staff.first_name)
#         staff.last_name = form_data.get("last_name", staff.last_name)
#         staff.other_names = form_data.get("other_names", staff.other_names)
#         staff.phone_number = form_data.get("phone", staff.phone_number)
#         staff.department_id = form_data.get("department", staff.department_id)
#         staff.position = form_data.get("position", staff.position)
#         staff.leave_status = form_data.get("leave_status", staff.leave_status)
#         staff.email = form_data.get("email", staff.email)
#         staff.type = form_data.get("staff_type", staff.type)
#         staff.save()
#         leave_details.days_entitled = int(form_data.get("days_entitled", leave_details.days_entitled))
#         leave_details.days_eligible = int(form_data.get("days_eligible", leave_details.days_eligible))
#         leave_details.save()
#         print("bob is gone")
#         response = HttpResponseRedirect(reverse("success_page", args=[slug,]))
#         return response

#     context = {
#         "slug": slug,
#         "staff": staff,
#         "departments": departments,
#         "leave_details": leave_details,
#         "leave_requests": leave_requests,
#         "days_entitled": range(1, 101),
#         "user_type": user.type,
#     }

#     response = render(request, "staff_details.html", context)
#     response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)

#     return response





# def leave_details(request, leave_id, slug):
#     """Handles leave request details with optimized session validation."""

#     user_slug = request.session.get("user_slug") or change_session(slug)

#     if not user_slug:
#         return redirect(reverse("login", args=["leave_list"]))

#     user = get_object_or_404(Staff.objects.select_related("department"), slug=user_slug)
#     leave_request = get_object_or_404(Leave_Request, id=leave_id)
#     user_leave_details = get_object_or_404(Leave_Details, staff=user)

#     context = {
#         "user_name": f"{user.last_name}, {user.first_name} {user.other_names}",
#         "leave_request": leave_request,
#         "user_leave_details": user_leave_details,
#     }

#     response = render(request, "leave_details.html", context)
#     response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)

#     return response





def leave_requests(request, slug):
    # 1. Session check
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["leave_requests"]))

    # 2. Load user
    try:
        user = Staff.objects.get(slug=user_slug)
    except Staff.DoesNotExist:
        return redirect(reverse("login", args=["leave_requests"]))

    # 3. Ensure approver
    approvers = (
        Approver.objects
        .filter(staff=user, is_active=True)
        .select_related("group_to_approve")
    )
    if not approvers.exists():
        return redirect(reverse("login", args=["0"]))

    # 4. Fetch all relevant approvals in one go
    approvals = (
        Approval.objects
        .filter(
            approver__in=approvers,
            is_active=True
        )
        .exclude(request__applicant=user)
        .select_related(
            "request__applicant",
            "request__type",
            "approver__group_to_approve"
        )
    )

    # 5. Split by status
    pending_approvals  = approvals.filter(status=Approval.ApprovalStatus.Pending)
    approved_approvals = approvals.filter(status=Approval.ApprovalStatus.Approved)
    denied_approvals   = approvals.filter(status=Approval.ApprovalStatus.Denied)

    if request.method == "POST":
        form_data = request.POST
        if form_data['form_meta'] == "approve": approve_leave(form_data)
        elif form_data["form_meta"] == "deny": deny_leave(form_data)
        return redirect(reverse("leave_requests", args=[slug,]))
    # 6. Render
    context = {
        "slug": slug,
        "approval_groups": approvers,
        "pending_approvals": pending_approvals,
        "approved_approvals": approved_approvals,
        "denied_approvals": denied_approvals,
    }
    response = render(request, "leave_requests.html", context)

    # 7. Mirror session key into a cookie
    response.set_cookie(
        "session_id",
        request.session.session_key,
        max_age=86400,
        secure=True,
        httponly=True
    )
    return response




# def send_email(leave_request_id, user_slug, reason):
#     print("Sending email notifications for leave request ID:", leave_request_id)
#     leave_request = Leave_Request.objects.get(id=leave_request_id)
#     applicant = Staff.objects.get(id=leave_request.applicant_id)
#     department_head = Department.objects.get(id=applicant.department_id).department_head
#     leave_details = Leave_Details.objects.get(staff_id=applicant.id)
#     department = Department.objects.get(id=applicant.department_id)
#     department_head_email = department.department_head_email
#     user = Staff.objects.get(slug=user_slug)
#     subject = ''
#     message = ''
#     receiver = ''
#     relieving_officer = leave_request.relieving_officer.first_name + ' ' + leave_request.relieving_officer.last_name + ', ' + leave_request.relieving_officer.other_names
#     number_map = {
#         0: "zero",
#         1: "one",
#         2: "two",
#         3: "three",
#         4: "four",
#         5: "five",
#         6: "six",
#         7: "seven",
#         8: "eight",
#         9: "nine",
#         10: "ten",
#         11: "eleven",
#         12: "twelve",
#         13: "thirteen",
#         14: "fourteen",
#         15: "fifteen",
#         16: "sixteen",
#         17: "seventeen",
#         18: "eighteen",
#         19: "nineteen",
#         20: "twenty",
#     }

#     # Adding multiples of ten
#     tens = ["thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
#     for i, word in enumerate(tens, start=3):
#         number_map[i * 10] = word

#     # Adding numbers between 21 and 99
#     for tens in range(2, 10):
#         for ones in range(1, 10):
#             number_map[tens * 10 + ones] = number_map[tens * 10] + "-" + number_map[ones]

#     # Finally, adding 100
#     number_map[100] = "one hundred"
    
#     if(leave_request.department_head_approval == 'PENDING' and user.type == 'HOD' or user.type == 'STAFF'):
#         print("HOD approval pending email notification")
#         # Send email to applicant
#         subject = 'Acknowledgment of Leave Application'
#         message = f'Dear {applicant.first_name},\n\nI trust this email finds you well.\n\nThis email serves as formal acknowledgment of the receipt of your leave application, submitted on {leave_request.application_date}. We appreciate your diligence in adhering to the college\'s leave request procedures. Kindly note that your application is currently under review, and a formal response regarding its approval status will be communicated to you in due course.\n\nShould any additional information be required, we will reach out to you. In the meantime, please do not hesitate to your administrator if you have any queries or require further clarification.\n\nYours sincerely,\nLeave Management System'
#         receiver = applicant.email
#         send_mail( subject, message, settings.EMAIL_HOST_USER, [receiver], fail_silently=False)
#         # Send email to department head
#         subject = 'Leave Application Pending Approval'
#         message = f"Dear {department_head.first_name},\n\nI hope this email finds you well.\n\nPlease be informed that a leave application has been submitted by {leave_request.applicant.first_name} {leave_request.applicant.last_name}, {leave_request.applicant.other_names} on {leave_request.application_date}. As per college protocol, the request is currently pending your approval. Kindly review the application at your earliest convenience and provide your decision accordingly.\n\nShould you require any additional details regarding this request, please do not hesitate to reach out.\n\nThank you for your time and consideration.\n\nYours sincerely,\nGCPS Leave System"
#         receiver = department_head_email
#     if(leave_request.department_head_approval == 'REJECTED' and user.type == 'HOD'):
#         print("HOD rejection email notification to applicant")
#         # Send email to applicant
#         subject = 'Notification of Leave Request Decision'
#         message = f"Dear {applicant.first_name},\n\nI hope this email finds you well.\n\nFollowing the review of your leave application submitted on {leave_request.application_date}, I regret to inform you that your request has not been approved by {department_head.first_name} {department_head.last_name}, {department_head.other_names} due to \n\"{reason.lower()}\".\n\nWe understand that this may be disappointing, and we appreciate your cooperation in adhering to the college\'s policies and operational requirements. Should you wish to discuss this further or explore alternative arrangements, please feel free to reach out.\n\nThank you for your understanding.\n\nYours sincerely,\nGCPS Leave System"
#         receiver = applicant.email
#     if(leave_request.department_head_approval == 'APPROVED' and leave_request.HOHR_approval == 'PENDING' and user.type == 'HOHR'):
#         print("Admin head approval pending email notification")
#         # Send email to admin head
#         subject = 'Leave Application Pending Approval'
#         message = f"Dear {user.first_name},\n\nI hope this email finds you well.\n\nPlease be informed that the leave application submitted by {leave_request.applicant.first_name} {leave_request.applicant.last_name}, {leave_request.applicant.other_names} on {leave_request.application_date} has been reviewed and approved by {department_head.first_name} {department_head.last_name}, {department_head.other_names} - Head of {department.department_name}. As part of our approval process, the request now requires further review, and your approval is one of the remaining steps.\n\nKindly review the application at your earliest convenience and provide your decision accordingly. If you require any additional details regarding this request, please do not hesitate to reach out.\n\nThank you for your time and consideration.\n\nYours sincerely,\nGCPS Leave System"
#         receiver = Staff.objects.get(type='HOHR').email
#     if(leave_request.HOHR_approval == 'REJECTED' and user.type == 'HOHR'):
#         print("Admin rejection email notification to applicant")
#         # Send email to applicant
#         subject = 'Notification of Leave Request Decision'
#         message = f"Dear {applicant.first_name},\n\nI hope you are doing well.\n\nFollowing the review of your leave application submitted on {leave_request.application_date}, I regret to inform you that the request has not been approved by {user.first_name} {user.last_name}, {user.other_names}. This decision has been made in consideration of '{reason.lower()}', in alignment with college policies and operational requirements.\n\nWe understand that this may not be the outcome you were hoping for, and we appreciate your cooperation and understanding. Should you wish to discuss this further or explore alternative arrangements, please feel free to reach out to your administrator.\n\nThank you for your time and dedication.\n\nYours sincerely,\nGCPS Leave System"
#         receiver = applicant.email
#     if(leave_request.HOHR_approval == 'APPROVED' and leave_request.final_approval == 'PENDING' and user.type == 'RECTOR'):
#         print("Final approval pending email notification to super admin")
#         # Send email to final approver
#         admin = Staff.objects.get(type='HOHR')
#         admin_name = admin.first_name + ' ' + admin.last_name + ', ' + admin.other_names
#         subject = 'Leave Application Pending Final Approval'
#         message = f"Dear {user.first_name},\n\nI hope this email finds you well.\n\nPlease be informed that the leave application submitted by {leave_request.applicant.first_name} {leave_request.applicant.last_name}, {leave_request.applicant.last_name} on {leave_request.application_date} has been reviewed and approved by {admin_name}. As part of our approval process, the request now requires your final review and decision.\n\nKindly review the application at your earliest convenience and provide your response accordingly. Should you require any additional details regarding this request, please do not hesitate to reach out.\n\nThank you for your time and consideration.\n\nYours sincerely,\nGCPS Leave System"
#         receiver = Staff.objects.get(type='RECTOR').email
#     if(leave_request.final_approval == 'APPROVED' and user.type == 'RECTOR'):
#         print("Final approval email notification to applicant")
#         # Send email to releiving officer
#         subject = f"Confirmation of Acting Head of Department Appointment"
#         message = (
#             f"Dear {applicant.first_name},\n\n"
#             f"\nThis communication serves to formally confirm your appointment as the Acting {applicant.position} for {applicant.department.department_name}. Your acceptance to serve as the relieving officer has been recorded, and your leadership during this period is highly valued."
#             f"\nAppointment Details:"
#             f"\n- Acceptance Date: {leave_request.relieving_officer_approval_date}"
#             f"\n- Leave Start Date: {leave_request.leave_start_date}"
#             f"\n- Leave Duration: {leave_request.leave_days_approved}"
#             f"\n- Resumption Date: {leave_request.resumption_date}"
#             f"\nDuring this time, you will oversee departmental operations, ensuring continuity and efficiency. Your cooperation and dedication are appreciated, and the team is encouraged to support you in fulfilling this role effectively."
#             f"\nShould you require any assistance, please do not hesitate to reach out. Thank you for stepping into this responsibility."
#             f"\nBest regards,"
#             f"\nGCPS Leave System"
#             )
#         #send email to all members
#         receiver = leave_request.relieving_officer.email
#         send_mail(subject=subject, message=message, recipient_list=[receiver])
#         subject = "Notification of Acting Head of Department Appointment"
#         message = (
#             f"Dear Team,\n"
#             f"This is to formally inform you that {leave_request.relieving_officer.last_name}, {leave_request.relieving_officer.first_name} {leave_request.relieving_officer.other_names} has assumed the role of {applicant.position} for {applicant.department.department_name}, following their acceptance as the relieving officer."
#             f"Appointment Details:"
#             f"- Acceptance Date: {leave_request.relieving_officer_approval_date}"
#             f"- Leave Start Date: {leave_request.leave_start_date}"
#             f"- Leave Duration: {leave_request.leave_days_approved}"
#             f"- Resumption Date: {leave_request.resumption_date}"
#             f"During this period, {leave_request.relieving_officer.last_name}, {leave_request.relieving_officer.first_name} {leave_request.relieving_officer.other_names} assume all responsibilities of {applicant.last_name} {applicant.first_name}, {applicant.other_names} and ensure continuity in operations. Your support and collaboration are essential in facilitating a smooth transition and maintaining efficiency within the department."
#             f"Please extend your full cooperation and assistance to {leave_request.relieving_officer.last_name}, {leave_request.relieving_officer.first_name} {leave_request.relieving_officer.other_names} as they undertake these responsibilities."
#             f"Best regards,"
#             f"GCPS Leave System"
#         )
#         receiver = Staff.objects.values_list("email", flat=True)
#         send_mail(subject, message, list(receiver))
#         subject = f'Approval of {leave_request.leave_days_approved} days {leave_request.type.lower()} Leave'
#         message = f"Dear {applicant.first_name},\n\nApproval has been given for you to take {number_map[{leave_request.leave_days_approved}]} ({leave_request.leave_days_approved}) days {leave_request.type} Leave as follows: .\n\t•  Start date : {leave_request.leave_start_date}\n\t•  End date : {leave_request.leave_end_date}\n\nYou are required to resume work on {leave_request.resumption_date}.\nYou have {leave_details.days_remaining} annual leave days remaining.\nYour relieving officer will be {leave_request.relieving_officer}\nKindly complete a Resumption of Duty from Annual Leave Form upon your return from leave.\nBest Wishes during your Leave. \n\n\nLeave Management System"
#         receiver = applicant.email
#     if(leave_request.final_approval == 'REJECTED' and user.type == 'RECTOR'):
#         print("Super admin rejection email notification to applicant")
#         # Send email to applicant
#         subject = 'Notification of Leave Request Decision'
#         message = f"Dear {applicant.first_name},\n\nI hope this email finds you well.\n\nFollowing the review of your leave application submitted on {leave_request.application_date}, I regret to inform you that the request has not been approved by {user.first_name} {user.last_name}, {user.other_names}. This decision has been made in consideration of '{reason.lower()}', in alignment with college policies and operational requirements.\n\nWe understand that this may not be the outcome you were hoping for, and we appreciate your cooperation and understanding. Should you wish to discuss this further or explore alternative arrangements, please feel free to reach out to your administrator.\n\nThank you for your time and dedication.\n\nYours sincerely,\nGCPS Leave System"
#         receiver = applicant.email
#     new_email = Email(
#         subject = subject,
#         message = message,
#         receiver = receiver
#     )
#     new_email.save()
#     print("Email sent to:", receiver)
#     return
    


# def leave_approval(request, applicant_slug, leave_id, slug):
#     """Handles leave request approvals securely with session validation."""

#     user_slug = request.session.get("user_slug") or change_session(slug)

#     if not user_slug:
#         return redirect(reverse("login", args=["admin_dashboard"]))

#     request.session.update({
#         "prev_page": "leave_requests",
#         "message": "Leave Request approved successfully",
#         "button": "Review other requests",
#         "next_page": "admin_dashboard",
#         "next_btn": "Back to Dashboard",
#     })

#     LoginSession.objects.filter(slug=user_slug).update(
#         prev_page="leave_requests",
#         message="Leave Request approved successfully",
#         button="Review other requests",
#         next_page="admin_dashboard",
#         next_btn="Back to Dashboard",
#         last_activity=timezone.now(),
#         date_to_expire=timezone.now() + timezone.timedelta(days=1),
#     )

#     leave_request = get_object_or_404(
#         Leave_Request.objects.select_related("applicant", "relieving_officer"), id=leave_id
#     )
#     user = get_object_or_404(Staff.objects.select_related("department"), slug=user_slug)
#     applicant = get_object_or_404(Staff.objects.select_related("department"), slug=applicant_slug)
#     leave_details = get_object_or_404(Leave_Details, staff=applicant)
#     department = get_object_or_404(Department, id=applicant.department_id)
#     HOHR = get_object_or_404(Staff, type="HOHR")

#     if user.type not in {"HOHR", "RECTOR", "HOD"}:
#         return HttpResponse("You are not authorized to view this page.", status=403)

#     days_remaining = int(leave_details.days_remaining)
#     days = list(range(1, days_remaining + 1))

#     # File access handling
#     medical_note_link = leave_request.med_note.url if leave_request.type == "SICK" and leave_request.med_note else None
#     admission_letter_link = leave_request.letter.url if leave_request.type in {
#         "STUDY_LEAVE_WITH_PAY", "STUDY_LEAVE_WITHOUT_PAY"
#     } and leave_request.letter else None

#     if request.method == "POST":
#         form_data = request.POST

#         approval_mapping = {
#             "HOD": ("department_head_approval", "department_head_approval_date"),
#             "HOHR": ("HOHR_approval", "HOHR_approval_date"),
#             "RECTOR": ("final_approval", "final_approval_date"),
#         }

#         approval_field, approval_date_field = approval_mapping.get(user.type, (None, None))
#         if approval_field and getattr(leave_request, approval_field) == "PENDING":
#             setattr(leave_request, approval_field, form_data["approval"])
#             if form_data["approval"] == "APPROVED":
#                 setattr(leave_request, approval_date_field, timezone.now())

#         leave_request.leave_days_approved = form_data.get("days_requested", leave_request.leave_days_requested)
#         leave_request.leave_start_date = form_data["start_date"]
#         leave_request.leave_end_date = form_data["end_date"]
#         leave_request.save()

#         print(form_data)
#         send_email(leave_id, user.slug, form_data["reason"] if "reason" in form_data else "")

#         if all(getattr(leave_request, field) == "APPROVED" for field in [
#             "department_head_approval", "HOHR_approval", "final_approval"
#         ]):
#             leave_details.days_taken += int(leave_request.leave_days_approved)
#             leave_details.save()
#             leave_request.status = Leave_Request.Status.APPROVED
#             leave_request.save()
#             department.acting_department_head = leave_request.relieving_officer if applicant.type == "HOD" else department.acting_department_head
#             department.save()

#         response = HttpResponseRedirect(reverse("leave_requests", args=['slug',]))
#         response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
#         return response

#     context = {
#         "applicant_name": f"{applicant.last_name}, {applicant.first_name} {applicant.other_names}",
#         "leave_request": leave_request,
#         "leave_details": leave_details,
#         "department_name": department.department_name,
#         "department_head_name": f"{department.department_head.last_name}, {department.department_head.first_name} {department.department_head.other_names}",
#         "days_remaining": days_remaining - int(leave_request.leave_days_requested),
#         "HOHR_name": f"{HOHR.last_name}, {HOHR.first_name} {HOHR.other_names}",
#         "applicant_slug": applicant_slug,
#         "user_type": user.type,
#         "days": days,
#         "medical_note_link": medical_note_link,
#         "admission_letter_link": admission_letter_link,
#     }

#     return render(request, "leave_approval.html", context)




#     # if(leave_request.department_head_approval == True and leave_request.HOHR_approval == True and leave_request.final_approval == True):
#     #     # Send email to applicant
#     #     subject = 'Leave Request Approved'
#     #     message = f"Dear {applicant.first_name},\n\nYour leave request has been approved.\n\nBest regards,\nLeave Management System"
#     # elif(leave_request.department_head_approval == False and leave_request.HOHR_approval == False and leave_request.final_approval == False):
#     #     # Send email to applicant
#     #     subject = 'Leave Request Rejected'
#     #     message = f"Dear {applicant.first_name},\n\nYour leave request has been rejected.\n\nBest regards,\nLeave Management System"
#     # else:
#     #     # Send email to department head
#     #     subject = 'Leave Request Pending Approval'
#     #     message = f"Dear {department_head.first_name},\n\nA leave request is pending your approval.\n\nBest regards,\nLeave Management System"


    