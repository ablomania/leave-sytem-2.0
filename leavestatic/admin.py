from django.contrib import admin
from .models import *
from django_celery_beat.models import PeriodicTask, CrontabSchedule

# Register your models here.
admin.site.register(Staff)
# admin.site.register(Position)
admin.site.register(Leave)
admin.site.register(LeaveType) 
admin.site.register(Approval)
admin.site.register(Ack)
admin.site.register(LeaveRequest)
admin.site.register(Group)
admin.site.register(Email)
admin.site.register(LoginSession)
admin.site.register(SystemAdmin)
admin.site.register(Gender)
admin.site.register(Level)
admin.site.register(StaffLeaveDetail)
admin.site.register(Approver)
admin.site.register(Seniority)
admin.site.register(Holiday)
admin.site.register(CancelledLeave)
admin.site.register(Resumption)
admin.site.register(LeaveUpdate)
admin.site.register(ApproverSwitch)


