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
    path('submit_inputs/<str:slug>', views.submit_inputs, name='submit_inputs'),
    # Approvers
    path('setup/approvers/add/<str:slug>', views.approver_add, name='setup_approver_add'),
    path('setup/approvers/edit/<int:staff_id>/<str:slug>', views.approver_edit, name='setup_approver_edit'),
    path('setup/approvers/<str:slug>', views.setup_approvers, name='setup_approvers'),
    # Categories
    path('setup/categories/add/<str:slug>', views.category_add, name='setup_category_add'),
    path('setup/categories/edit/<int:cat_id>/<str:slug>', views.category_edit, name='setup_category_edit'),
    path('setup/categories/<str:slug>', views.setup_categories, name='setup_categories'),
    # Staff
    path('setup/staff/<str:slug>', views.setup_staff, name="setup_staff"),
    path('setup/staff/add/<str:slug>', views.staff_add, name="staff_add"),
    path('setup/staff/edit/<str:staff_id>/<str:slug>', views.staff_edit, name="staff_edit"),
    path('setup/staff/add_to_group/<int:group_id>/<str:slug>', views.staff_add_group, name="staff_add_group"),
    # Groups
    path('setup/groups/<str:slug>', views.setup_groups, name="setup_groups"),
    path('setup/groups/add/<str:slug>', views.group_add, name="group_add"),
    path('setup/groups/edit/<int:group_id>/<str:slug>', views.group_edit, name="group_edit"),
    path('setup/groups/detail/<int:group_id>/<str:slug>', views.group_detail, name="group_detail"),
    # Gender
    path('setup/gender/<str:slug>', views.setup_genders, name="setup_genders"),
    path('setup/gender/add/<str:slug>', views.gender_add, name="gender_add"),
    path('setup/gender/edit/<int:gender_id>/<str:slug>', views.gender_edit, name="gender_edit"),
    # Levels
    path('setup/levels/<str:slug>', views.setup_levels, name="setup_levels"),
    path('setup/levels/add/<str:slug>', views.level_add, name="level_add"),
    path('setup/levels/edit/<int:level_id>/<str:slug>', views.level_edit, name="level_edit"),
    # Leave Types
    path('setup/leave_types/<str:slug>', views.setup_leave_types, name="setup_leave_types"),
    path('setup/leave_types/add/<str:slug>', views.leavetype_add, name="leavetype_add"),
    path('setup/leave_types/edit/<int:leave_id>/<str:slug>', views.leavetype_edit, name="leave_type_edit"),
    # Holidays
    path('setup/holidays/<str:slug>', views.setup_holidays, name="setup_holidays"),
    path('setup/holidays/add/<str:slug>', views.holiday_add, name="holiday_add"),
    path('setup/holidays/edit/<int:hol_id>/<str:slug>', views.holiday_edit, name="holiday_edit"),
]