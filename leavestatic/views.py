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
from .leaveModifyingFunctions import *
from django.utils.safestring import mark_safe
import json
from collections import defaultdict
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


# from datetime import date
# for ll in LeaveRequest.objects.all():
#     ll.start_date = date.today()
#     ll.save()

# first = current = date(date.today().year, 1, 1)
# day = first.isoweekday()
# print("the date is ", day)
# my_count = 0
# from dateutil.relativedelta import relativedelta

# year = (date.today() + relativedelta(years=1)).year
# while current.year < year:
#     if current.isoweekday() <= 5:  # Monday to Friday are 1-5
#         my_count += 1
#     current += datetime.timedelta(days=1)
# print("the year is ", year)
# print("the count is ", my_count)
# print("current is: ", current)

# days = [True, True, False]
# days_count = sum(1 for day in days if day)
# print("the days count is ", days_count)

def index(request):
    template = loader.get_template('index.html')

    context = {
        "index": True,
    }
    return HttpResponse(template.render(context, request))


def get_client_ip_address(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # The 'X-Forwarded-For' header can contain a comma-separated list of IPs.
        # The first IP in the list is typically the original client's IP.
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def login_user(request, next_page=None):
    next_page = next_page or '0'
    form = LoginForm(request.POST or None)
    incorrect = False

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['username']
        password = form.cleaned_data['password']
        staff = Staff.objects.filter(email=email).first()

        if not staff:
            form.add_error(None, "Invalid username or password")
            incorrect = True
            print("Staff not found for email:", email)
        else:
            user = authenticate(request, username=staff.username, password=password)
            if user:
                login(request, user)

                # Remove old login sessions in bulk
                LoginSession.objects.filter(user=user).delete()

                # Ensure unique slug
                slug = random_string(50)
                while LoginSession.objects.filter(slug=slug).exists():
                    slug = random_string(50)

                LoginSession.objects.create(
                    user=user,
                    slug=slug,
                )

                # Check if user is an active admin
                if hasattr(user, 'admin_profile') and user.admin_profile.is_active:
                    redirect_path = reverse('setup')
                elif next_page.isdigit() and int(next_page) > 0:
                    redirect_path = reverse('relieve_ack', args=[next_page])
                elif next_page != '0':
                    redirect_path = reverse(next_page)
                else:
                    redirect_path = reverse('dashboard')

                response = redirect(redirect_path)
                response = set_session_cookie(response, slug)
                return response
            else:
                print("Authentication failed for user:", email)
                form.add_error(None, "Invalid username or password")
                incorrect = True

    context = {'form': form, 'login': True, 'next_page': next_page, 'index': True, "incorrect": incorrect}
    template = loader.get_template('login.html')
    response = HttpResponse(template.render(context, request))
    return response


def trigger_leave_update(request):
    """Manually run leave update logic and display feedback without a template."""

    try:
        update_leave_progress()
        restore_original_approvers()
        message = f"✅ Leave progress updated successfully at {timezone.now().strftime('%H:%M %p')}."
        color = "#0077c0"
    except Exception as e:
        message = f"❌ Failed to update leave progress: {str(e)}"
        color = "#d14343"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Leave Update Result</title>
        <style>
            body {{
                font-family: 'Segoe UI', sans-serif;
                background-color: #f4f8fb;
                padding: 50px;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }}
            .result-box {{
                background-color: #fff;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                text-align: center;
                max-width: 600px;
            }}
            .result-box h1 {{
                color: {color};
                font-size: 20px;
                margin-bottom: 10px;
            }}
            .back-link {{
                margin-top: 25px;
                display: inline-block;
                background-color: {color};
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 6px;
                transition: background-color 0.3s ease;
            }}
            .back-link:hover {{
                background-color: #005fa3;
            }}
        </style>
    </head>
    <body>
        <div class="result-box">
            <h1>{message}</h1>
        </div>
    </body>
    </html>
    """

    return HttpResponse(html)


def dashboard(request):
    session_slug = get_user_from_session_cookie(request)

    if not session_slug:
        return redirect(reverse("login", args=["dashboard"]))

    user = Staff.objects.get(id=get_user_id_from_login_session(session_slug))
    is_approver = check_for_approver(user.id)
    
    self_ack = Ack.objects.filter(staff_id=user.id, type=Ack.Type.SELF, status=Ack.Status.Ready, is_active=True).first()
    all_relief_acks = Ack.objects.filter(staff_id=user.id, type=Ack.Type.RELIEF, status=Ack.Status.Pending, is_active=True)   
    r_ack = all_relief_acks.first()
    leaves_count = LeaveRequest.objects.filter(applicant_id=user.id).count()
    on_leave = Leave.objects.filter(request__applicant_id=user.id, status=Leave.LeaveStatus.On_Leave).first()
    resume_obj = Resumption.objects.filter(staff_id=user.id, is_active=True, confirmed=False).first()

    context = {
        "user_name": f"{user.last_name}, {user.first_name} {user.other_names}",
        'is_approver': is_approver, "self_ack": self_ack,
        "r_ack": r_ack, "leaves_count": leaves_count,
        "on_leave": on_leave, "resume_obj": resume_obj,
        "loc": "dashboard", "all_relief_acks": all_relief_acks.count(),
    }

    response = render(request, "dashboard.html", context)
    response = set_session_cookie(response, session_slug)

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
        'index': True,
    }

    if request.method == 'POST':
        form_data = request.POST
        step = int(form_data['step'])
        username = form_data['usernameOriginal']

        if step == 1:
            email = form_data['email']
            if Staff.objects.filter(email=email).exists():
                user = Staff.objects.get(email=email)
                username = user.username
            else:
                return HttpResponse("Account not found")

            context.update({'email': email, 'step': step, 'username': username})
            random_number = str(random.randint(12345, 999999))

            # ✉️ Send verification via Celery
            subject = "GCPS Leave System Verification Code"
            message = f"{random_number} is your verification code. Don't share your code with anyone."
            send_verification_code.delay(subject, message, email)

            step += 1
            context.update({'random_number': random_number, 'step': step, 'username': username})

        elif step == 2:
            code = form_data['verification_code']
            random_number = form_data['random_number']
            if code == random_number:
                step += 1
            else:
                return HttpResponse("Code is incorrect")
            context.update({'step': step, 'username': username})

        elif step == 3:
            password = form_data['password2']
            user = Staff.objects.get(username=username)
            user.set_password(password)
            user.save()
            return HttpResponseRedirect(reverse('login', args=['0',]))

    return HttpResponse(template.render(context, request))


# Add / Edit setup views
# --- STAFF ADD/EDIT ---

def staff_add(request, group_id=None):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_staff"]))
    
    message = request.COOKIES.get('message', None)
    all_groups = Group.objects.order_by('name')
    all_genders = Gender.objects.all().order_by("name")
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    group = get_object_or_404(Group, id=group_id) if group_id else None
    context = {
        "all_groups": all_groups,
        "all_genders": all_genders,
        "seniority": seniority,
        "group": group,
        'message': message,
        "index": True,
    }
    template = loader.get_template("setup/staff/staff_add.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response

def staff_add_group(request, group_id):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_staff"]))
    
    message = request.COOKIES.get('message', None)
    all_groups = Group.objects.order_by('name')
    group = Group.objects.get(id=group_id)
    all_genders = Gender.objects.all().order_by("name")
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    context = {
        "all_groups": all_groups,
        "all_genders": all_genders,
        "seniority": seniority,
        'message': message,
        "group": group,
        "index": True,
    }
    template = loader.get_template("setup/staff/staff_add_group.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response


def staff_edit(request, staff_id):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_staff"]))
    
    message = request.COOKIES.get('message', None)
    staff = get_object_or_404(Staff, id=staff_id)
    all_groups = Group.objects.order_by('name')
    all_genders = Gender.objects.all().order_by("name")
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    group = staff.group if hasattr(staff, "group") else None
    context = {
        "staff": staff,
        "all_groups": all_groups,
        "all_genders": all_genders,
        "seniority": seniority,
        "group": group,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/staff/staff_edit.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response

# --- APPROVER ADD/EDIT ---

def approver_add(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_approvers"]))
    
    message = request.COOKIES.get('message', None)
    all_staff = Staff.objects.filter(is_superuser=False).order_by("last_name", "first_name")
    all_groups = Group.objects.order_by('name')
    all_levels = Level.objects.filter(is_active=True).order_by("name")
    groups_list = {group: None for group in all_groups}
    context = {
        "all_staff": all_staff,
        "all_groups": all_groups,
        "all_levels": all_levels,
        "groups_list": groups_list,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/approvers/setup_approver_add.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response



def approver_edit(request, staff_id):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_approvers"]))
    
    message = request.COOKIES.get('message', None)
    staff = get_object_or_404(Staff, id=staff_id)
    all_staff = Staff.objects.filter(is_superuser=False).order_by("last_name", "first_name")
    all_groups = Group.objects.order_by('name')
    all_levels = Level.objects.filter(is_active=True).order_by("name")
    # All Approver objects for this staff
    approver_objs = Approver.objects.filter(staff=staff)
    context = {
        "staff": staff,
        "all_staff": all_staff,
        "all_groups": all_groups,
        "all_levels": all_levels,
        "approver_objs": approver_objs,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/approvers/setup_approver_edit.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response

# --- CATEGORY (SENIORITY) ADD/EDIT ---

def category_add(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_categories"]))
    
    message = request.COOKIES.get('message', None)
    context = {
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/categories/setup_categories_add.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response



def category_edit(request, cat_id):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_categories"]))
    
    message = request.COOKIES.get('message', None)
    category = get_object_or_404(Seniority, id=cat_id)
    context = {
        "sen": category,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/categories/setup_categories_edit.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response

# --- GENDER ADD/EDIT ---

def gender_add(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_genders"]))
    
    message = request.COOKIES.get('message', None)
    context = {
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/gender/gender_add.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response



def gender_edit(request, gender_id):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_genders"]))
    
    message = request.COOKIES.get('message', None)
    gender = get_object_or_404(Gender, id=gender_id)
    context = {
        "gender": gender,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/gender/gender_edit.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response

# --- HOLIDAY ADD/EDIT ---

def holiday_add(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_holidays"]))
    message = request.COOKIES.get('message', None)
    context = {
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/holidays/holidays_add.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response



def holiday_edit(request, hol_id):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_holidays"]))
    
    message = request.COOKIES.get('message', None)
    holiday = get_object_or_404(Holiday, id=hol_id)
    context = {
        "holiday": holiday,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/holidays/holidays_edit.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response

# --- GROUP ADD/EDIT ---

def group_add(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_groups"]))
    
    message = request.COOKIES.get('message', None)
    context = {
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/groups/group_add.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response



def group_edit(request, group_id):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_groups"]))
    
    message = request.COOKIES.get('message', None)
    group = get_object_or_404(Group, id=group_id)
    context = {
        "group": group,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/groups/group_edit.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response

# --- LEVEL ADD/EDIT ---

def level_add(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_levels"]))
    
    message = request.COOKIES.get('message', None)
    context = {
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/levels/level_add.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response



def level_edit(request, level_id):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_levels"]))
    
    message = request.COOKIES.get('message', None)
    level = get_object_or_404(Level, id=level_id)
    context = {
        "lvl": level,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/levels/level_edit.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response

# --- LEAVE TYPE ADD/EDIT ---

def leavetype_add(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_leave_types"]))
    
    message = request.COOKIES.get('message', None)
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    context = {
        "seniority": seniority,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/leave/leavetype_add.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response



def leavetype_edit(request, leave_id):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_leave_types"]))
    
    message = request.COOKIES.get('message', None)
    leave = get_object_or_404(LeaveType, id=leave_id)
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    context = {
        "leave": leave,
        "seniority": seniority,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/leave/leavetype_edit.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response


def setup_groups(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_groups"]))

    message = request.COOKIES.get('message', None)
    groups = Group.objects.filter(is_active=True).order_by('name')
    all_groups = Group.objects.order_by('name')
    staff_dict = {id: Staff.objects.filter(group_id=id).count() for id in all_groups.values_list("id", flat=True)}
    active_groups = groups
    groups_list = defaultdict(list)
    for group in groups:
        users = Staff.objects.filter(group=group)
        groups_list[group] = users

    context = {
        "groups": groups,
        "all_groups": all_groups,
        "staff_dict": staff_dict,
        "active_groups": active_groups,
        "message": message,
        "groups_list": groups_list,
        "index": True,
    }
    template = loader.get_template("setup/groups/setup_groups.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response



def setup_staff(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_staff"]))
    
    message = request.COOKIES.get('message', None)
    food = request.COOKIES.get("food", "default_value")
    print("the food is:", food)
    all_staff = Staff.objects.filter(is_superuser=False).order_by("last_name", "first_name")
    active_groups = Group.objects.filter(is_active=True).order_by("name")
    all_groups = Group.objects.order_by('name')
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    all_genders = Gender.objects.all().order_by("name")
    groups_list = {group: Staff.objects.filter(group=group) for group in active_groups}

    context = {
        "all_staff": all_staff,
        "active_groups": active_groups,
        "all_groups": all_groups,
        "seniority": seniority,
        "all_genders": all_genders,
        "groups_list": groups_list,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/staff/setup_staff.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response



def setup_approvers(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_approvers"]))

    message = request.COOKIES.get('message', None)
    # Fetch all staff, groups, and levels
    all_staff = Staff.objects.filter(is_superuser=False).order_by("last_name", "first_name")
    all_groups = Group.objects.order_by('name')
    all_levels = Level.objects.filter(is_active=True).order_by("name")
    # Build approvers_list as in setup()
    approvers_list = {}
    staff_qs = Staff.objects.filter(approver__isnull=False).distinct()
    for staff in staff_qs:
        staff_approvers = Approver.objects.filter(staff=staff).select_related('group_to_approve', 'level')
        if staff_approvers:
            approvers_list[staff] = staff_approvers

    context = {
        "all_staff": all_staff,
        "all_groups": all_groups,
        "all_levels": all_levels,
        "approvers_list": approvers_list,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/approvers/setup_approvers.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response


def setup_leave_types(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_leave_types"]))

    message = request.COOKIES.get('message', None)
    # Fetch all active seniority categories, leave types, and levels
    categories = Seniority.objects.filter(is_active=True).order_by("name")
    all_leave = LeaveType.objects.all().order_by('name', 'seniority__name')
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    all_levels = Level.objects.filter(is_active=True).order_by("name")

    context = {
        "all_leave": all_leave,
        "seniority": seniority,
        "all_levels": all_levels,
        "message": message,
        "index": True,
        "categories": categories,
    }
    template = loader.get_template("setup/leave/setup_leave.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response


def setup_holidays(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_holidays"]))

    message = request.COOKIES.get('message', None)
    # Fetch all active fixed and variable holidays
    f_holidays = Holiday.objects.filter(type='Fixed', is_active=True).order_by("name")
    v_holidays = Holiday.objects.filter(type='Variable', is_active=True).order_by("name")
    all_holidays = Holiday.objects.all().order_by("name")

    context = {
        "f_holidays": f_holidays,
        "v_holidays": v_holidays,
        "all_holidays": all_holidays,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/holidays/setup_holidays.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response


def setup_genders(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_genders"]))

    message = request.COOKIES.get('message', None)
    all_genders = Gender.objects.all().order_by("name")

    context = {
        "all_genders": all_genders,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/gender/setup_gender.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response


def setup_categories(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_categories"]))

    message = request.COOKIES.get('message', None)
    # Fetch all active and inactive seniority categories
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    i_seniority = Seniority.objects.filter(is_active=False).order_by("name")
    a_seniority = seniority

    context = {
        "seniority": seniority,
        "i_seniority": i_seniority,
        "a_seniority": a_seniority,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/categories/setup_categories.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response


def setup_levels(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_levels"]))

    message = request.COOKIES.get('message', None)
    # Fetch all active and inactive levels
    all_levels = Level.objects.filter(is_active=True).order_by("name")
    i_levels = Level.objects.filter(is_active=False).order_by("name")

    context = {
        "all_levels": all_levels,
        "i_levels": i_levels,
        "message": message,
        "index": True,
    }
    template = loader.get_template("setup/levels/setup_levels.html")
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response


def submit_inputs(request):
    if request.method == "POST":
        form_data = request.POST
        meta = form_data.get('form_meta')
        page = None
        message = None

        if meta == "add_group":
            add_group(form_data)
            message = f"Group {form_data['group_name']} was added successfully."
            if form_data.get('again') == "false":
                page = "setup_groups"
            elif form_data.get('again') == "group":
                page = "group_add"
        elif meta == "edit_group":
            edit_group(form_data)
            message = f"Group {form_data['name']} was updated successfully."
            page = "setup_groups"
        elif meta == "del_group":
            del_group(dict(form_data))
            message = f"Group deleted successfully."
            page = "setup_groups"
        elif meta == "restore_group":
            restore_group(dict(form_data))
            message = f"Group restored successfully."
            page = "setup_groups"

        elif meta == "add_staff":
            add_staff(form_data, request)
            message = f"Staff {form_data['first_name']} {form_data['last_name']} was added successfully."
            if form_data.get('again') == "false":
                page = "setup_staff"  
            elif form_data.get('again') == "staff":
                page = "staff_add"
            elif form_data.get('again') == "staff_group":
                page = "staff_add_group"
        elif meta == "edit_staff":
            edit_staff(form_data)
            message = f"Staff {form_data['first_name']} {form_data['last_name']} was updated successfully."
            page = "setup_staff"
        elif meta == "rem_staff":
            rem_staff(form_data)
            message = f"Staff removed successfully."
            page = "setup_staff"
        elif meta == "del_staff_form":
            del_staff(dict(form_data))
            message = f"Staff deleted successfully."
            page = "setup_staff"
        elif meta == "restore_staff":
            restore_staff(dict(form_data))
            message = f"Staff restored successfully."
            page = "setup_staff"

        elif meta == "add_approver":
            add_approver(form_data)
            message = f"Approver added successfully."
            if form_data.get('again') == "false":
                page = "setup_approvers"
            elif form_data.get('again') == "approver":
                page = "approver_add"
        elif meta == "edit_app":
            edit_approver(dict(form_data))
            message = f"Approver updated successfully."
            page = "setup_approvers"
        elif meta == "del_approver":
            del_approver(form_data)
            message = f"Approver deleted successfully."
            page = "setup_approvers"
        elif meta == "restore_approver":
            res_approver(form_data)
            message = f"Approver restored successfully."
            page = "setup_approvers"

        elif meta == "add_lvt":
            add_leave_type(form_data)
            message = f"Leave type {form_data['name']} was added successfully."
            page = "setup_leave_types"
        elif meta == "edit_lvt":
            edit_leave(form_data)
            message = f"Leave type {form_data['name']} was updated successfully."
            page = "setup_leave_types"
        elif meta == "del_lvt":
            del_leave(dict(form_data))
            message = f"Leave type deleted successfully."
            page = "setup_leave_types"
        elif meta == "res_lvt":
            res_leave(form_data)
            message = f"Leave type restored successfully."
            page = "setup_leave_types"
        elif meta == "del_multi_lvt":
            del_multi_lvt(dict(form_data))
            message = f"Leave types deleted successfully."
            page = "setup_leave_types"

        elif meta == "add_hol":
            add_holiday(form_data)
            message = f"Holiday {form_data['name']} was added successfully."
            page = "setup_holidays"
        elif meta == "edit_hol":
            edit_holiday(form_data)
            message = f"Holiday {form_data['name']} was updated successfully."
            page = "setup_holidays"
        elif meta == "del_hol":
            del_holiday(form_data)
            message = f"Holiday deleted successfully."
            page = "setup_holidays"
        elif meta == "res_hol":
            res_holiday(form_data)
            message = f"Holiday restored successfully."
            page = "setup_holidays"

        elif meta == "add_gender":
            add_gender(form_data)
            message = f"Gender {form_data['name']} was added successfully."
            page = "setup_genders"
        elif meta == "edit_gender":
            edit_gender(form_data)
            message = f"Gender {form_data['name']} was updated successfully."
            page = "setup_genders"
        elif meta == "del_gender":
            del_gender(form_data)
            message = f"Gender deleted successfully."
            page = "setup_genders"
        elif meta == "res_gender":
            res_gender(form_data)
            message = f"Gender restored successfully."
            page = "setup_genders"

        elif meta == "add_cat":
            add_sen(form_data)
            message = f"Category {form_data['name']} was added successfully."
            page = "setup_categories"
        elif meta == "edit_cat":
            edit_sen(form_data)
            message = f"Category {form_data['name']} was updated successfully."
            page = "setup_categories"
        elif meta == "del_sen":
            del_sen(form_data)
            message = f"Category deleted successfully."
            page = "setup_categories"
        elif meta == "res_sen":
            res_sen(form_data)
            message = f"Category restored successfully."
            page = "setup_categories"

        elif meta == "add_level":
            add_lvl(form_data)
            message = f"Level {form_data['name']} was added successfully."
            page = "setup_levels"
        elif meta == "edit_level":
            edit_lvl(form_data)
            message = f"Level {form_data['name']} was updated successfully."
            page = "setup_levels"
        elif meta == "del_level":
            del_lvl(form_data)
            message = f"Level deleted successfully."
            page = "setup_levels"
        elif meta == "res_level":
            res_lvl(form_data)
            message = f"Level restored successfully."
            page = "setup_levels"

        elif meta == "del_multi_staff":
            del_multi_staff(dict(form_data))
            message = f"Staff deleted successfully."
            page = "setup_staff"
        elif meta == "change_group":
            multi_change_group(dict(form_data))
            message = f"Group changed successfully."
            page = "setup_groups"
        elif meta == "change_group_group":
            multi_change_group_group(dict(form_data))
            message = f"Group changed successfully."
            page = "setup_groups"
        elif meta == "change_category":
            multi_change_category(dict(form_data))
            message = f"Category changed successfully."
            page = "setup_leave_types"

        response = HttpResponseRedirect(reverse(page if page else "setup"))
        response.set_cookie('message', message, max_age=1, secure=False, httponly=True)
        return response



def group_detail(request, group_id):
    # Maintain session consistency (mirrors setup view behavior)
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup_groups"]))

    message = request.COOKIES.get('message', None)
    group = get_object_or_404(Group, id=group_id)
    groups = Group.objects.filter(is_active=True).exclude(id=group_id).order_by('name')

    # Build staff queryset for this group (both active and inactive; template filters itself)
    staff_qs = (
        Staff.objects.filter(group=group)
        .order_by("last_name", "first_name")
    )

    # groups_list maps a Group object to its staff list (as in the congested setup view)
    groups_list = {group: staff_qs}

    # staff_dict maps group.id -> total staff count (template compares key to group.id)
    staff_dict = {group.id: staff_qs.count()}

    # Optional: attach a 'leader' attribute expected by the template.
    # If you have a defined leader model field elsewhere, replace this heuristic.
    leader = (
        Staff.objects.filter(group=group, is_active=True)
        .select_related("seniority")
        .order_by("seniority__rank", "last_name", "first_name")
        .first()
    )
    setattr(group, "leader", leader)

    template = loader.get_template("setup/groups/gpd/group_detail.html")
    context = {
        "group": group,
        "groups_list": groups_list,
        "staff_dict": staff_dict,
        "message": message,
        'index': True,
        'groups': groups,
    }
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response



def setup(request):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["setup"]))
    
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
        'a_seniority': a_seniority, "i_levels" : i_levels,
        'index': True, "general": True,
    }
    response = HttpResponse(template.render(context, request))
    response = set_session_cookie(response, session_slug)
    return response



def sys_admin(request):
    template = loader.get_template("system_admin.html")

    context = {
        "first_time": True,
    }
    return HttpResponse(template.render(context, request))



def leave_request(request):
    """Handles leave request submission with session validation and message feedback."""

    session_slug = get_user_from_session_cookie(request)

    if not session_slug:
        return redirect(reverse("login", args=["leave_request"]))

    user = Staff.objects.filter(id=get_user_id_from_login_session(session_slug)).first()
    if not user:
        return redirect(reverse("login", args=["staff_on_leave"]))
    
    is_approver = check_for_approver(user.id)
    allowed_leave_types = LeaveType.objects.filter(seniority_id=user.seniority_id, is_active=True)
    staff_leave_data = {
        ld.leave_type_id: {
            "taken": ld.days_taken or 0,
            "remaining": ld.days_remaining or 0,
            "leave_type": ld.leave_type.name or "N/A"
        } for ld in StaffLeaveDetail.objects.filter(staff_id=user.id)
    }

    holiday_data = {ah.id: ah.date.strftime('%Y-%m-%d') for ah in Holiday.objects.filter(is_active=True)}


    leave_type_dict = {lt.id: lt.name for lt in allowed_leave_types}
    allowed_leave_type_dict = {
        lt.id: {
            "name": lt.name or "N/A",
            "days": lt.days or "N/A",
            "paidLeave": str(lt.paid_leave),
            "i_date": str(lt.includes_date_of_occurence),
            "i_institution": str(lt.includes_institution),
            "i_course": str(lt.includes_course),
            "i_note": str(lt.includes_med_note),
            "i_letter": str(lt.includes_letter)
        } for lt in allowed_leave_types
    }

    relieving_officers = Staff.objects.filter(
        is_active=True, group_id=user.group.id
    ).exclude(id=user.id).order_by("first_name", "last_name")

    approvers_set = set(Approver.objects.filter(is_active=True).values_list('staff_id', flat=True))
    all_approvers = Staff.objects.filter(id__in=approvers_set).exclude(id=user.id)
    active_leave_staff_ids = Leave.objects.filter(
        is_active=True,
        status=Leave.LeaveStatus.On_Leave
    ).values_list('request__applicant_id', flat=True)
    relieving_officers = relieving_officers.exclude(id__in=active_leave_staff_ids).exclude(id__in=approvers_set)

    

    message = ""

    if request.method == "POST":
        form_data = request.POST
        result = leaveRequestHandler(form_data, user, request)

        # You can refine how result is structured if needed
        if result:
            message = "Leave request submitted successfully."
        else:
            message = result.get("error", "There was an issue submitting your request.")

    context = {
        "user_name": f"{user.last_name}, {user.first_name} {user.other_names}",
        "user_id": user.id,
        "user": user,
        "all_approvers": all_approvers,
        "allowed_leave_types": allowed_leave_types,
        "leave_type_dict": leave_type_dict,
        "allowed_leave_types_dict": allowed_leave_type_dict,
        "staff_leave_data": staff_leave_data,
        "officers": relieving_officers,
        "is_approver": is_approver,
        'loc': 'request',
        'message': message,
        "holiday_json": json.dumps(list(holiday_data.values()))  # just the date list
    }

    response = render(request, "leave_form.html", context)
    response.set_cookie('message', message, max_age=1, secure=False, httponly=True)
    response = set_session_cookie(response, session_slug)

    return response



def confirm_leave_view(request, id):
    # Validate session
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=[id]))
    
    user = Staff.objects.get(id=get_user_id_from_login_session(session_slug))
    is_approver = check_for_approver(user.id)

    # Fetch LeaveRequest and ensure applicant matches session
    ack_obj = get_object_or_404(
    Ack.objects.select_related("request__applicant", "request__type"),
        id=id,
        type=Ack.Type.SELF,
        is_active=True
    )
    leave_request = ack_obj.request

    # Handle submission
    if request.method == "POST":
        decision = request.POST.get("leave_response")
        reason = request.POST.get("decline_reason", "").strip()

        if decision == "ACCEPTED":
            Ack.objects.update_or_create(
                id=ack_obj.id,
                request=leave_request,
                staff=leave_request.applicant,
                type=Ack.Type.SELF,
                defaults={
                    "status": Ack.Status.Approved,
                    "is_active": True
                }
            )
            createLeave(leave_request.applicant, leave_request, ack_obj.id)
            
        elif decision == "DECLINED":
            Ack.objects.update_or_create(
                request=leave_request,
                staff=leave_request.applicant,
                type=Ack.Type.SELF,
                defaults={
                    "status": Ack.Status.Denied,
                    "reason": reason,
                    "is_active": True
                }
            )

        response = redirect(reverse("dashboard"))
        response = set_session_cookie(response, session_slug)
        return response

    # Render confirmation form
    context = {
        "leave_request": leave_request,
        "is_approver": is_approver,
        "date": timezone.now().date(),
        "id": id
    }
    response = render(request, "self_ack.html", context)
    response = set_session_cookie(response, session_slug)
    return response



def cancelLeave(request, id):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["cancel_leave"]))

    user = Staff.objects.filter(id=get_user_id_from_login_session(session_slug)).first()
    if not user:
        return redirect(reverse("login", args=["staff_on_leave"]))
    
    is_approver = check_for_approver(user.id)
    leave = get_object_or_404(
        Leave.objects.select_related("request", "request__type", "request__applicant"),
        id=id,
        request__applicant=user,
        is_active=True,
        status=Leave.LeaveStatus.On_Leave
    )
    

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        handle_leave_cancellation(leave, user, reason)
        messages.success(request, "Your leave cancellation has been logged and your balance updated.")
        return redirect(reverse("dashboard"))

    context = {
        "leave_request": leave.request,
        "leave": leave,
        "is_approver": is_approver
    }

    return render(request, "cancel_leave.html", context)


def leaveComplete(request, id):
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["dashboard"]))

    user = Staff.objects.filter(id=get_user_id_from_login_session(session_slug)).first()
    if not user:
        return redirect(reverse("login", args=["staff_on_leave"]))
    
    is_approver = check_for_approver(user.id)
    message = ""
    resume_obj = Resumption.objects.filter(
        staff=user,
        id=id,
        is_active=True
    ).first()
    leave_request = get_object_or_404(
        LeaveRequest.objects.select_related("applicant"),
        id=resume_obj.leave_request_id,
        applicant=user,
        is_active=True,
        status=LeaveRequest.Status.COMPLETED
    )

    if request.method == "POST":
        notes = request.POST.get("notes", "").strip()
        confirmed = request.POST.get("confirm") == "on"

        # Save resumption record
        resume_obj.notes = notes
        resume_obj.confirmed = confirmed
        resume_obj.date_submitted = timezone.now()
        resume_obj.save()
        # Send confirmation email
        subject = f"Resumption Confirmed: {leave_request.type.name.split()[0]} Leave"
        to = [user.email]
        body = (
            f"Dear {user.first_name},\n\n"
            f"This is to confirm that you have successfully submitted your Resumption of Duty form following your {leave_request.type.name.split()[0]} leave.\n"
            f"Start Date: {leave_request.start_date}\n"
            f"End Date: {leave_request.end_date}\n"
            f"Resumption Date: {leave_request.return_date}\n\n"
            f"Your return has been recorded in the system. Welcome back!\n\n"
            f"Regards,\nLeave Management System"
        )
        send_leave_email.delay(subject, body, [user.email])
        message = "Resumption form submitted successfully."
        messages.success(request, "Resumption form submitted successfully.")
        return redirect(reverse("dashboard"))

    context = {
        "leave_request": leave_request,
        "is_approver": is_approver,
        "resumption_date": leave_request.return_date,
        "message": message
    }

    response = render(request, "leave_complete_form.html", context)
    response.set_cookie('message', message, max_age=1, secure=False, httponly=True)
    response = set_session_cookie(response, session_slug)
    return response



def relieve_ack(request, id):
    # 1. Validate session
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["dashboard"]))

    # 2. Fetch Ack and related staff in one query
    ack = get_object_or_404(Ack.objects.select_related("staff"), id=id)
    user = ack.staff

    is_approver = check_for_approver(user.id)
   
    # 6. Handle POST submission
    if request.method == "POST":
        form_data = request.POST
        if form_data['form_meta'] == "approve": approve_ack(form_data, ack.request)
        elif form_data['form_meta'] == "deny": deny_ack(form_data, ack.request)
        response = HttpResponseRedirect(reverse("dashboard"))
        response = set_session_cookie(response, session_slug)
        return response

    # 7. Render template
    context = {
        "date": timezone.now().date(),
        "ack": ack,
        "id": id,
        "is_approver": is_approver
    }
    response = render(request, "relieve_ack.html", context)
    response = set_session_cookie(response, session_slug)
    return response



def leave_history(request):
    """Displays a user's leave history with approval and acknowledgment progress."""
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["leave_history"]))

    user = Staff.objects.filter(id=get_user_id_from_login_session(session_slug)).first()
    if not user:
        return redirect(reverse("login", args=["staff_on_leave"]))
    
    is_approver = check_for_approver(user.id)

    # Prefetch related approvals, acknowledgments, and leave objects
    leave_requests = (
        LeaveRequest.objects
        .filter(applicant=user)
        .select_related("type")
        .prefetch_related(
            Prefetch("approval_set", queryset=Approval.objects.select_related("approver__staff")),
            Prefetch("ack_set", queryset=Ack.objects.select_related("staff")),
            Prefetch("leave_set", queryset=Leave.objects.all()),
            Prefetch("resumption_set", queryset=Resumption.objects.all()),
        )
        .order_by("-application_date")
    )

    # Group leave by year
    grouped_leave_dict = {}
    for lr in leave_requests:
        year = lr.application_date.year
        grouped_leave_dict.setdefault(year, []).append(lr)

    # Sort and paginate year keys (each page displays one year)
    years_sorted = sorted(grouped_leave_dict.keys(), reverse=True)
    paginator = Paginator(years_sorted, 1)
    page_number = request.GET.get("page") or "1"

    try:
        year_page = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        return redirect(f"{reverse('leave_history')}?page=1")

    # Safely extract the current year
    current_year = year_page.object_list[0] if year_page.object_list else None
    grouped_leave = {current_year: grouped_leave_dict[current_year]} if current_year else {}

    # Cancelled leaves
    terminated_leaves = (
        CancelledLeave.objects
        .filter(staff=user, is_active=True)
        .select_related("leave_request__type", "original_leave")
        .order_by("-date_cancelled")
    )

    context = {
        "grouped_leave": grouped_leave,
        "terminated_leaves": terminated_leaves,
        "is_approver": is_approver,
        "year_page": year_page,
        "loc": "history"
    }

    response = render(request, "leave_history.html", context)
    response = set_session_cookie(response, session_slug)
    return response




def user_logout(request):
    """Handles secure user logout with session validation."""

    session_slug = get_user_from_session_cookie(request)

    if not session_slug:
        return redirect(reverse("login"))

    logout(request)
    LoginSession.objects.filter(slug=session_slug).update(
        date_to_expire=timezone.now(),
        last_activity=timezone.now()
    )
    response = HttpResponseRedirect(reverse("login", args=["0"]))
    response.delete_cookie("session_id")

    return response






def users_on_leave(request):
    """Lists all users currently on leave, grouped by their department (group)."""

    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["staff_on_leave"]))

    user = Staff.objects.filter(id=get_user_id_from_login_session(session_slug)).first()
    if not user:
        return redirect(reverse("login", args=["staff_on_leave"]))
    
    is_approver = check_for_approver(user.id)
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
        "is_approver": is_approver,
        "dept_group": dict(dept_group),
        'loc': 'on_leave'
    }

    response = render(request, "on_leave.html", context)
    response = set_session_cookie(response, session_slug)
    return response





def profile(request):
    """Displays and manages a staff profile with leave stats and approver status."""

    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["profile"]))

    user = Staff.objects.filter(id=get_user_id_from_login_session(session_slug)).first()
    if not user:
        return redirect(reverse("login", args=["profile"]))
    
    is_approver = check_for_approver(user.id)
    # Fetch all leave details for this staff
    leave_details = StaffLeaveDetail.objects.filter(staff=user, is_active=True).select_related("leave_type")

    # Check if user is an approver
    is_approver = Approver.objects.filter(staff=user, is_active=True).exists()

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
        "is_approver": is_approver,
        'loc': 'profile'
    }

    response = render(request, "profile.html", context)
    response = set_session_cookie(response, session_slug)
    return response







def leave_requests(request):
    # 1. Session check
    session_slug = get_user_from_session_cookie(request)
    if not session_slug:
        return redirect(reverse("login", args=["leave_requests"]))

    # 2. Load user
    try:
        user = Staff.objects.get(id=get_user_id_from_login_session(session_slug))
    except Staff.DoesNotExist:
        return redirect(reverse("login", args=["leave_requests"]))

    # 3. Ensure approver
    is_approver = check_for_approver(user.id)
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
    relieving_acks = Ack.objects.filter(
        type=Ack.Type.RELIEF,
        is_active=True
    )

    # 5. Split by status
    pending_approvals  = approvals.filter(status=Approval.ApprovalStatus.Pending)
    approved_approvals = approvals.filter(status=Approval.ApprovalStatus.Approved)
    denied_approvals   = approvals.filter(status=Approval.ApprovalStatus.Denied)

    if request.method == "POST":
        form_data = request.POST
        if form_data['form_meta'] == "approve": approve_leave(form_data)
        elif form_data["form_meta"] == "deny": deny_leave(form_data)
        return redirect(reverse("leave_requests"))
    # 6. Render
    context = {
        "is_approver": is_approver,
        "approval_groups": approvers,
        "pending_approvals": pending_approvals,
        "approved_approvals": approved_approvals,
        "denied_approvals": denied_approvals,
        "loc": "approvals", "relieving_acks": relieving_acks
    }
    response = render(request, "leave_requests.html", context)

    # 7. Mirror session key into a cookie
    response = set_session_cookie(response, session_slug)
    return response
