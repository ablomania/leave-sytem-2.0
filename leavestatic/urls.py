from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('leave_request/<str:slug>', views.leave_request, name='leave_request'),
    path('login/<str:next_page>', views.login_user, name='login'),
    path('dashboard/<str:slug>', views.dashboard, name="dashboard"),
    path('password_reset', views.password_reset, name='password_reset'),
    path('resumption_of_duty_form/<int:id>/<str:slug>', views.leaveComplete, name='leaveComplete'),
    path('leave_requests/<str:slug>', views.leave_requests, name='leave_requests'),
    path('profile/<str:slug>', views.profile, name='profile'),
    path('leave_history/<str:slug>', views.leave_history, name="leave_history"),
    path('logout/<str:slug>', views.user_logout, name='logout1'),
    path('staff_on_leave/<str:slug>', views.users_on_leave, name='staff_on_leave'),
    path('relief_ack/<int:id>/<str:slug>', views.relieve_ack, name='relieve_ack'),
    path('confirm_leave/<int:id>/<str:slug>', views.confirm_leave_view, name="confirm_leave_view"),
    path('cancel_leave/<int:id>/<str:slug>', views.cancelLeave, name="cancel_leave"),
    path('update_leave', views.trigger_leave_update, name="update_leave"),
    path('system_setup/<str:slug>', views.setup, name='setup'),
]