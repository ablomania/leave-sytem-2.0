from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('leave_request', views.leave_request, name='leave_request'),
    path('login/<str:next_page>', views.login_user, name='login'),
    path('dashboard', views.dashboard, name="dashboard"),
    path('password_reset', views.password_reset, name='password_reset'),
    path('resumption_of_duty_form/<int:id>', views.leaveComplete, name='leaveComplete'),
    path('leave_requests', views.leave_requests, name='leave_requests'),
    path('profile', views.profile, name='profile'),
    path('leave_history', views.leave_history, name="leave_history"),
    path('logout', views.user_logout, name='logout1'),
    path('staff_on_leave', views.users_on_leave, name='staff_on_leave'),
    path('relief_ack/<int:id>', views.relieve_ack, name='relieve_ack'),
    path('confirm_leave/<int:id>', views.confirm_leave_view, name="confirm_leave_view"),
    path('cancel_leave/<int:id>', views.cancelLeave, name="cancel_leave"),
    path('update_leave', views.trigger_leave_update, name="update_leave"),
    path('system_setup', views.setup, name='setup'),
    path('submit_inputs', views.submit_inputs, name='submit_inputs'),
    # Approvers
    path('setup/approvers/add', views.approver_add, name='setup_approver_add'),
    path('setup/approvers/edit/<int:staff_id>', views.approver_edit, name='setup_approver_edit'),
    path('setup/approvers', views.setup_approvers, name='setup_approvers'),
    # Categories
    path('setup/categories/add', views.category_add, name='setup_category_add'),
    path('setup/categories/edit/<int:cat_id>', views.category_edit, name='setup_category_edit'),
    path('setup/categories', views.setup_categories, name='setup_categories'),
    # Staff
    path('setup/staff', views.setup_staff, name="setup_staff"),
    path('setup/staff/add', views.staff_add, name="staff_add"),
    path('setup/staff/edit/<str:staff_id>', views.staff_edit, name="staff_edit"),
    path('setup/staff/add_to_group/<int:group_id>', views.staff_add_group, name="staff_add_group"),
    # Groups
    path('setup/groups', views.setup_groups, name="setup_groups"),
    path('setup/groups/add', views.group_add, name="group_add"),
    path('setup/groups/edit/<int:group_id>', views.group_edit, name="group_edit"),
    path('setup/groups/detail/<int:group_id>', views.group_detail, name="group_detail"),
    # Gender
    path('setup/gender', views.setup_genders, name="setup_genders"),
    path('setup/gender/add', views.gender_add, name="gender_add"),
    path('setup/gender/edit/<int:gender_id>', views.gender_edit, name="gender_edit"),
    # Levels
    path('setup/levels', views.setup_levels, name="setup_levels"),
    path('setup/levels/add', views.level_add, name="level_add"),
    path('setup/levels/edit/<int:level_id>', views.level_edit, name="level_edit"),
    # Leave Types
    path('setup/leave_types', views.setup_leave_types, name="setup_leave_types"),
    path('setup/leave_types/add', views.leavetype_add, name="leavetype_add"),
    path('setup/leave_types/edit/<int:leave_id>', views.leavetype_edit, name="leave_type_edit"),
    # Holidays
    path('setup/holidays', views.setup_holidays, name="setup_holidays"),
    path('setup/holidays/add', views.holiday_add, name="holiday_add"),
    path('setup/holidays/edit/<int:hol_id>', views.holiday_edit, name="holiday_edit"),
]