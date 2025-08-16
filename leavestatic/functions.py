import string, random
from .models import *




def random_string(length=255):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def get_all_leave_requests():
    group_names = Group.objects.values_list('department_name', flat=True)
    all_leave_dict = {}
    for group in group_names:
        all_leave = Leave.objects.filter(request__applicant__position__group_id=group.id)
        all_leave_dict[group] = all_leave or None
    return all_leave_dict
print(get_all_leave_requests)



def change_session(slug):
    session = (
        LoginSession.objects
        .filter(slug=slug, date_to_expire__date__gte=timezone.localdate(), status='ACTIVE')
        .select_related('user')
        .first()
    )
    return session.user.slug if session else None


def get_login_session(slug):
    session = (
        LoginSession.objects
        .filter(slug=slug)
        .select_related('user')
        .first()
    )
    if session:
        session.date_to_expire = session.date_to_expire + timezone.timedelta(days=1)
        session.save()
        return True
    else: return False

def set_session_cookie(response, slug):
    response.set_cookie('session_slug', slug, max_age=86400, secure=False, httponly=True)
    # response.set_cookie('session_id', session_key, max_age=86400, secure=True, httponly=True)  # Use this for production
    return response

def get_user_from_session_cookie(request):
    session_slug = request.COOKIES.get('session_slug')
    loginSession = get_login_session(session_slug)
    if loginSession:
        return session_slug
    return None


def get_user_id_from_login_session(session_slug):
    loginSession_obj = LoginSession.objects.filter(slug=session_slug).first()
    if loginSession_obj:
        return loginSession_obj.user_id
    return None
    

def check_for_approver(user_id):
    approver = Approver.objects.filter(staff_id=user_id, is_active=True)
    return True if approver.count() > 0 else False
    
    
