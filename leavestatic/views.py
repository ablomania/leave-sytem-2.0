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





def index(request):
    template = loader.get_template('index.html')

    context = {
        "index": True,
    }
    return HttpResponse(template.render(context, request))


def login_user(request, next_page=None):
    next_page = next_page or '0'
    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['username']
        password = form.cleaned_data['password']
        staff = Staff.objects.filter(email=email).first()

        if not staff:
            form.add_error(None, "Invalid username or password")
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
                    session_key=request.session.session_key,
                    status=LoginSession.Status.ACTIVE,
                    slug=slug,
                )

                request.session.update({
                    'user_slug': user.slug,
                    'user_email': user.email
                })

                # Check if user is an active admin
                if hasattr(user, 'admin_profile') and user.admin_profile.is_active:
                    redirect_path = reverse('setup', args=[slug])
                elif next_page.isdigit() and int(next_page) > 0:
                    redirect_path = reverse('relieve_ack', args=[next_page, slug])
                elif next_page != '0':
                    redirect_path = reverse(next_page, args=[slug])
                else:
                    redirect_path = reverse('dashboard', args=[slug])

                response = redirect(redirect_path)
                response.set_cookie('session_id', request.session.session_key, max_age=86400, secure=True, httponly=True)
                return response
            else:
                form.add_error(None, "Invalid username or password")

    context = {'form': form, 'login': True, 'next_page': next_page, 'index': True}
    template = loader.get_template('login.html')
    response = HttpResponse(template.render(context, request))
    response.set_cookie('session_id', request.session.session_key, max_age=86400, secure=True, httponly=True)
    return response


# for staff in Staff.objects.filter(slug__isnull=True):
#     base_slug = slugify(f"{staff.first_name}-{staff.phone_number}")
#     slug = base_slug
#     counter = 1
#     while Staff.objects.filter(slug=slug).exists():
#         slug = f"{base_slug}-{counter}"
#         counter += 1
#     staff.slug = slug
#     staff.save()
#     print()


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


def dashboard(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)

    if not user_slug:
        return redirect(reverse("login", args=["leave_list"]))

    user = Staff.objects.get(slug=user_slug)
    is_approver = True if Approver.objects.filter(staff_id=user.id, is_active=True).count() > 0 else False
    
    self_ack = Ack.objects.filter(staff_id=user.id, type=Ack.Type.SELF, status=Ack.Status.Pending).first()
    r_ack = Ack.objects.filter(staff_id=user.id, type=Ack.Type.RELIEF, status=Ack.Status.Pending).first()
    leaves_count = LeaveRequest.objects.filter(applicant_id=user.id).count()
    on_leave = Leave.objects.filter(request__applicant_id=user.id, status=Leave.LeaveStatus.On_Leave).first()
    resume_obj = Resumption.objects.filter(staff_id=user.id, is_active=True, confirmed=False).first()

    context = {
        "user_name": f"{user.last_name}, {user.first_name} {user.other_names}",
        'slug': slug,
        'is_approver': is_approver, "self_ack": self_ack,
        "r_ack": r_ack, "leaves_count": leaves_count,
        "on_leave": on_leave, "resume_obj": resume_obj,
        "loc": "dashboard"
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

def staff_add(request, slug, group_id=None):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_staff"]))
    all_groups = Group.objects.order_by('name')
    all_genders = Gender.objects.all().order_by("name")
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    group = get_object_or_404(Group, id=group_id) if group_id else None
    context = {
        "all_groups": all_groups,
        "all_genders": all_genders,
        "seniority": seniority,
        "group": group,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/staff/staff_add.html")
    return HttpResponse(template.render(context, request))

def staff_add_group(request, group_id, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_staff"]))
    all_groups = Group.objects.order_by('name')
    group = Group.objects.get(id=group_id)
    all_genders = Gender.objects.all().order_by("name")
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    context = {
        "all_groups": all_groups,
        "all_genders": all_genders,
        "seniority": seniority,
        "slug": slug,
        "group": group,
        "index": True,
    }
    template = loader.get_template("setup/staff/staff_add_group.html")
    return HttpResponse(template.render(context, request))

def staff_edit(request, slug, staff_id):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_staff"]))
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
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/staff/staff_edit.html")
    return HttpResponse(template.render(context, request))

# --- APPROVER ADD/EDIT ---

def approver_add(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_approvers"]))
    all_staff = Staff.objects.filter(is_superuser=False).order_by("last_name", "first_name")
    all_groups = Group.objects.order_by('name')
    all_levels = Level.objects.filter(is_active=True).order_by("name")
    groups_list = {group: None for group in all_groups}
    context = {
        "all_staff": all_staff,
        "all_groups": all_groups,
        "all_levels": all_levels,
        "groups_list": groups_list,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/approvers/setup_approver_add.html")
    return HttpResponse(template.render(context, request))

def approver_edit(request, slug, staff_id):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_approvers"]))
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
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/approvers/setup_approver_edit.html")
    return HttpResponse(template.render(context, request))

# --- CATEGORY (SENIORITY) ADD/EDIT ---

def category_add(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_categories"]))
    context = {
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/categories/setup_categories_add.html")
    return HttpResponse(template.render(context, request))

def category_edit(request, slug, cat_id):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_categories"]))
    category = get_object_or_404(Seniority, id=cat_id)
    context = {
        "sen": category,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/categories/setup_categories_edit.html")
    return HttpResponse(template.render(context, request))

# --- GENDER ADD/EDIT ---

def gender_add(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_genders"]))
    context = {
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/gender/gender_add.html")
    return HttpResponse(template.render(context, request))

def gender_edit(request, slug, gender_id):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_genders"]))
    gender = get_object_or_404(Gender, id=gender_id)
    context = {
        "gender": gender,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/gender/gender_edit.html")
    return HttpResponse(template.render(context, request))

# --- HOLIDAY ADD/EDIT ---

def holiday_add(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_holidays"]))
    context = {
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/holidays/holidays_add.html")
    return HttpResponse(template.render(context, request))

def holiday_edit(request, slug, hol_id):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_holidays"]))
    holiday = get_object_or_404(Holiday, id=hol_id)
    context = {
        "holiday": holiday,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/holidays/holidays_edit.html")
    return HttpResponse(template.render(context, request))

# --- GROUP ADD/EDIT ---

def group_add(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_groups"]))
    context = {
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/groups/group_add.html")
    return HttpResponse(template.render(context, request))

def group_edit(request, slug, group_id):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_groups"]))
    group = get_object_or_404(Group, id=group_id)
    context = {
        "group": group,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/groups/group_edit.html")
    return HttpResponse(template.render(context, request))

# --- LEVEL ADD/EDIT ---

def level_add(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_levels"]))
    context = {
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/levels/level_add.html")
    return HttpResponse(template.render(context, request))

def level_edit(request, slug, level_id):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_levels"]))
    level = get_object_or_404(Level, id=level_id)
    context = {
        "lvl": level,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/levels/level_edit.html")
    return HttpResponse(template.render(context, request))

# --- LEAVE TYPE ADD/EDIT ---

def leavetype_add(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_leave_types"]))
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    context = {
        "seniority": seniority,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/leave/leavetype_add.html")
    return HttpResponse(template.render(context, request))

def leavetype_edit(request, slug, leave_id):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_leave_types"]))
    leave = get_object_or_404(LeaveType, id=leave_id)
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    context = {
        "leave": leave,
        "seniority": seniority,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/leave/leavetype_edit.html")
    return HttpResponse(template.render(context, request))


def setup_groups(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_groups"]))

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
        "slug": slug,
        "groups_list": groups_list,
        "index": True,
    }
    template = loader.get_template("setup/groups/setup_groups.html")
    return HttpResponse(template.render(context, request))


def setup_staff(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_staff"]))

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
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/staff/setup_staff.html")
    return HttpResponse(template.render(context, request))


def setup_staff(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_staff"]))

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
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/staff/setup_staff.html")
    return HttpResponse(template.render(context, request))



def setup_approvers(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_approvers"]))

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
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/approvers/setup_approvers.html")
    return HttpResponse(template.render(context, request))


def setup_leave_types(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_leave_types"]))

    all_leave = LeaveType.objects.all().order_by('name', 'seniority__name')
    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    all_levels = Level.objects.filter(is_active=True).order_by("name")

    context = {
        "all_leave": all_leave,
        "seniority": seniority,
        "all_levels": all_levels,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/leave/setup_leave.html")
    return HttpResponse(template.render(context, request))


def setup_holidays(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_holidays"]))

    f_holidays = Holiday.objects.filter(type='Fixed', is_active=True).order_by("name")
    v_holidays = Holiday.objects.filter(type='Variable', is_active=True).order_by("name")
    all_holidays = Holiday.objects.all().order_by("name")

    context = {
        "f_holidays": f_holidays,
        "v_holidays": v_holidays,
        "all_holidays": all_holidays,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/holidays/setup_holidays.html")
    return HttpResponse(template.render(context, request))


def setup_genders(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_genders"]))

    all_genders = Gender.objects.all().order_by("name")

    context = {
        "all_genders": all_genders,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/gender/setup_gender.html")
    return HttpResponse(template.render(context, request))


def setup_categories(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_categories"]))

    seniority = Seniority.objects.filter(is_active=True).order_by("name")
    i_seniority = Seniority.objects.filter(is_active=False).order_by("name")
    a_seniority = seniority

    context = {
        "seniority": seniority,
        "i_seniority": i_seniority,
        "a_seniority": a_seniority,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/categories/setup_categories.html")
    return HttpResponse(template.render(context, request))


def setup_levels(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_levels"]))

    all_levels = Level.objects.filter(is_active=True).order_by("name")
    i_levels = Level.objects.filter(is_active=False).order_by("name")

    context = {
        "all_levels": all_levels,
        "i_levels": i_levels,
        "slug": slug,
        "index": True,
    }
    template = loader.get_template("setup/levels/setup_levels.html")
    return HttpResponse(template.render(context, request))


def submit_inputs(request, slug):
    if request.method == "POST":
        form_data = request.POST
        meta = form_data.get('form_meta')
        page = None

        if meta == "add_group":
            add_group(form_data)
            page = "setup_groups"
        elif meta == "edit_group":
            edit_group(form_data)
            page = "setup_groups"
        elif meta == "del_group":
            del_group(dict(form_data))
            page = "setup_groups"
        elif meta == "restore_group":
            restore_group(dict(form_data))
            page = "setup_groups"

        elif meta == "add_staff":
            add_staff(form_data, request)
            page = "setup_staff"
        elif meta == "edit_staff":
            edit_staff(form_data)
            page = "setup_staff"
        elif meta == "rem_staff":
            rem_staff(form_data)
            page = "setup_staff"
        elif meta == "del_staff_form":
            del_staff(dict(form_data))
            page = "setup_staff"
        elif meta == "restore_staff":
            restore_staff(dict(form_data))
            page = "setup_staff"

        elif meta == "add_approver":
            add_approver(form_data)
            page = "setup_approvers"
        elif meta == "edit_app":
            edit_approver(dict(form_data))
            page = "setup_approvers"
        elif meta == "del_approver":
            del_approver(form_data)
            page = "setup_approvers"
        elif meta == "restore_approver":
            res_approver(form_data)
            page = "setup_approvers"

        elif meta == "add_lvt":
            add_leave_type(form_data)
            page = "setup_leave_types"
        elif meta == "edit_lvt":
            edit_leave(form_data)
            page = "setup_leave_types"
        elif meta == "del_lvt":
            del_leave(dict(form_data))
            page = "setup_leave_types"
        elif meta == "res_lvt":
            res_leave(form_data)
            page = "setup_leave_types"

        elif meta == "add_hol":
            add_holiday(form_data)
            page = "setup_holidays"
        elif meta == "edit_hol":
            edit_holiday(form_data)
            page = "setup_holidays"
        elif meta == "del_hol":
            del_holiday(form_data)
            page = "setup_holidays"
        elif meta == "res_hol":
            res_holiday(form_data)
            page = "setup_holidays"

        elif meta == "add_gender":
            add_gender(form_data)
            page = "setup_genders"
        elif meta == "edit_gender":
            edit_gender(form_data)
            page = "setup_genders"
        elif meta == "del_gender":
            del_gender(form_data)
            page = "setup_genders"
        elif meta == "res_gender":
            res_gender(form_data)
            page = "setup_genders"

        elif meta == "add_cat":
            add_sen(form_data)
            page = "setup_categories"
        elif meta == "edit_cat":
            edit_sen(form_data)
            page = "setup_categories"
        elif meta == "del_sen":
            del_sen(form_data)
            page = "setup_categories"
        elif meta == "res_sen":
            res_sen(form_data)
            page = "setup_categories"

        elif meta == "add_level":
            add_lvl(form_data)
            page = "setup_levels"
        elif meta == "edit_level":
            edit_lvl(form_data)
            page = "setup_levels"
        elif meta == "del_level":
            del_lvl(form_data)
            page = "setup_levels"
        elif meta == "res_level":
            res_lvl(form_data)
            page = "setup_levels"

        print(form_data)
        return redirect(reverse(page if page else "setup", args=[slug]))



def group_detail(request, group_id, slug):
    # Maintain session consistency (mirrors setup view behavior)
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["setup_groups"]))

    group = get_object_or_404(Group, id=group_id)

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
        "slug": slug,
        'index': True,
    }
    return HttpResponse(template.render(context, request))



def setup(request, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["leave_request"]))
    
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
        'index': True, 'slug': slug, "general": True,
    }
    return HttpResponse(template.render(context, request))

def sys_admin(request):
    template = loader.get_template("system_admin.html")

    context = {
        "first_time": True,
    }
    return HttpResponse(template.render(context, request))



def leave_request(request, slug):
    """Handles leave request submission with session validation and message feedback."""

    user_slug = request.session.get("user_slug") or change_session(slug)

    if not user_slug:
        return redirect(reverse("login", args=["leave_request"]))

    # Update LoginSession context
    LoginSession.objects.filter(slug=user_slug).update(
        prev_page="leave_request",
        button="Request For Another Leave",
        next_page=f"leave_list",
        next_btn="Back to Dashboard",
        message="Leave Request successful. Pending approval. For more information, please contact your administrator."
    )

    user = Staff.objects.get(slug=user_slug)
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

    form_status_message = ""

    if request.method == "POST":
        form_data = request.POST
        result = leaveRequestHandler(form_data, user, request, slug)

        # You can refine how result is structured if needed
        if result:
            form_status_message = "✅ Leave request submitted successfully."
        else:
            form_status_message = result.get("error", "❌ There was an issue submitting your request.")

    context = {
        "user_name": f"{user.last_name}, {user.first_name} {user.other_names}",
        "user_id": user.id,
        "user": user,
        "allowed_leave_types": allowed_leave_types,
        "leave_type_dict": leave_type_dict,
        "allowed_leave_types_dict": allowed_leave_type_dict,
        "staff_leave_data": staff_leave_data,
        "officers": relieving_officers,
        "form_status_message": form_status_message,
        "slug": slug,
        'loc': 'request',
        "holiday_json": json.dumps(list(holiday_data.values()))  # just the date list
    }

    response = render(request, "leave_form.html", context)
    response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)

    return response



def confirm_leave_view(request, id, slug):
    # Validate session
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=[id]))

    # Fetch LeaveRequest and ensure applicant matches session
    ack_obj = get_object_or_404(
    Ack.objects.select_related("request__applicant", "request__type"),
        id=id,
        type=Ack.Type.SELF,
        is_active=True
    )
    leave_request = ack_obj.request



    if user_slug != leave_request.applicant.slug:
        return redirect(reverse("login", args=[id]))

    # Update session and LoginSession (optional)
    session_updates = {
        "prev_page": "not",
        "message": "Please confirm your approval of the leave assignment.",
        "button": "not",
        "next_page": "leave_list",
        "next_btn": "Back to Dashboard",
    }
    request.session.update(session_updates)
    LoginSession.objects.filter(slug=user_slug).update(**session_updates)

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

        response = redirect(reverse("dashboard", args=[slug]))
        response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
        return response

    # Render confirmation form
    context = {
        "leave_request": leave_request,
        "slug": slug,
        "date": timezone.now().date(),
        "id": id
    }
    response = render(request, "self_ack.html", context)
    response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
    return response



def cancelLeave(request, id, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["cancel_leave"]))

    staff = get_object_or_404(Staff, slug=user_slug)
    leave = get_object_or_404(
        Leave.objects.select_related("request", "request__type", "request__applicant"),
        id=id,
        request__applicant=staff,
        is_active=True,
        status=Leave.LeaveStatus.On_Leave
    )
    

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        handle_leave_cancellation(leave, staff, reason)
        messages.success(request, "Your leave cancellation has been logged and your balance updated.")
        return redirect(reverse("dashboard", args=[slug]))

    context = {
        "leave_request": leave.request,
        "leave": leave,
        "slug": slug,
    }

    return render(request, "cancel_leave.html", context)


def leaveComplete(request, id, slug):
    user_slug = request.session.get("user_slug") or change_session(slug)
    if not user_slug:
        return redirect(reverse("login", args=["leave_complete"]))

    user = get_object_or_404(Staff, slug=user_slug)
    leave_request = get_object_or_404(
        LeaveRequest.objects.select_related("applicant"),
        id=id,
        applicant=user,
        is_active=True,
        status=LeaveRequest.Status.APPROVED
    )

    if request.method == "POST":
        notes = request.POST.get("notes", "").strip()
        confirmed = request.POST.get("confirm") == "on"

        # Save resumption record
        Resumption.objects.update_or_create(
            staff=user,
            leave_request=leave_request,
            notes=notes,
            confirmed=confirmed,
            is_active=True
        )

        messages.success(request, "Resumption form submitted successfully.")
        return redirect(reverse("dashboard", args=[slug]))

    context = {
        "leave_request": leave_request,
        "slug": slug,
        "resumption_date": leave_request.return_date
    }

    return render(request, "leave_complete_form.html", context)
    


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
        if form_data['form_meta'] == "approve": approve_ack(form_data, ack.request)
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
        return redirect(f"{reverse('leave_history', args=[slug])}?page=1")

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
        "slug": slug,
        "year_page": year_page,
        "loc": "history"
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
        'loc': 'on_leave'
    }

    response = render(request, "on_leave.html", context)
    response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
    return response





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
        'loc': 'profile'
    }

    response = render(request, "profile.html", context)
    response.set_cookie("session_id", request.session.session_key, max_age=86400, secure=True, httponly=True)
    return response







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
        "loc": "approvals"
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
