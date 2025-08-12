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



def check_secure_connection(request):
    if request.is_secure():
        print("Secure connection established.")
    else:
        print("Insecure connection detected. Please use HTTPS.")
