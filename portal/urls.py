from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from portal.views import auth as auth_views_local
from portal.views import coordinator as coord
from portal.views import staff

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="dashboard")),
    path("login/", auth_views.LoginView.as_view(template_name="portal/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", auth_views_local.dashboard, name="dashboard"),
    # Staff portal
    path("staff/courses/", staff.courses_list, name="courses_list"),
    path("staff/courses/upload/", staff.upload_courses, name="upload_courses"),
    path("staff/students/", staff.students_list, name="students_list"),
    path("staff/students/upload/", staff.upload_students, name="upload_students"),
    path("staff/faculty/", staff.faculty_list, name="faculty_list"),
    path("staff/faculty/upload/", staff.upload_faculty, name="upload_faculty"),
    path("staff/enrollment/upload/", staff.upload_course_enrollment, name="upload_course_enrollment"),
    path("staff/halls/", staff.halls_list, name="halls_list"),
    path("staff/halls/add/", staff.hall_add, name="hall_add"),
    path("staff/halls/<int:pk>/edit/", staff.hall_edit, name="hall_edit"),
    # Coordinator portal
    path("coordinator/terms/", coord.exam_terms_list, name="exam_terms_list"),
    path("coordinator/terms/add/", coord.exam_term_add, name="exam_term_add"),
    path("coordinator/terms/<int:term_id>/", coord.exam_term_detail, name="exam_term_detail"),
    path("coordinator/terms/<int:term_id>/holidays/add/", coord.holiday_add, name="holiday_add"),
    path("coordinator/terms/<int:term_id>/slots/add/", coord.slot_add, name="slot_add"),
    path("coordinator/terms/<int:term_id>/schedules/add/", coord.schedule_add, name="schedule_add"),
    path("coordinator/terms/<int:term_id>/publish/", coord.publish, name="publish"),
    path("coordinator/terms/<int:term_id>/versions/", coord.versions_list, name="versions_list"),
    path("coordinator/terms/<int:term_id>/export/master.xlsx", coord.export_master_schedule, name="export_master_schedule"),
    path("coordinator/terms/<int:term_id>/export/duties.xlsx", coord.export_duty_roster, name="export_duty_roster"),
    path("coordinator/schedules/<int:pk>/", coord.schedule_detail, name="schedule_detail"),
    path("coordinator/schedules/<int:schedule_id>/halls/add/", coord.hall_allocation_add, name="hall_allocation_add"),
    path("coordinator/halls/<int:hall_id>/slots/<int:slot_id>/", coord.hall_slot_detail, name="hall_slot_detail"),
    path("coordinator/halls/<int:hall_id>/slots/<int:slot_id>/seating/generate/", coord.generate_seating, name="generate_seating"),
    path("coordinator/halls/<int:hall_id>/slots/<int:slot_id>/duties/generate/", coord.generate_duties, name="generate_duties"),
    path("coordinator/halls/<int:hall_id>/slots/<int:slot_id>/export/seating.pdf", coord.export_seating_pdf, name="export_seating_pdf"),
    path("coordinator/halls/<int:hall_id>/slots/<int:slot_id>/export/attendance.pdf", coord.export_attendance_pdf, name="export_attendance_pdf"),
    path("coordinator/duties/<int:duty_id>/drop/", coord.duty_drop, name="duty_drop"),
    path("coordinator/accommodations/", coord.accommodations_list, name="accommodations_list"),
    path("coordinator/versions/<int:version_id>/restore/", coord.version_restore, name="version_restore"),
]
