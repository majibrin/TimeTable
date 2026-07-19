from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.index),
    path('auth/login/', views.login_view),

    # Users (Super Admin)
    path('users/', views.UserListCreateView.as_view()),
    path('users/<int:pk>/', views.UserDetailView.as_view()),
    path('lecturers/', views.lecturer_list),

    # Faculty / Department / Cohort
    path('faculties/', views.FacultyListCreateView.as_view()),
    path('departments/', views.DepartmentListCreateView.as_view()),
    path('departments/<int:pk>/', views.DepartmentDetailView.as_view()),
    path('cohorts/', views.LevelCohortListCreateView.as_view()),
    path('cohorts/<int:pk>/', views.LevelCohortDetailView.as_view()),

    # Venues
    path('venues/', views.VenueListCreateView.as_view()),
    path('venues/<int:pk>/', views.VenueDetailView.as_view()),

    # Courses
    path('courses/', views.CourseListCreateView.as_view()),
    path('courses/<int:pk>/', views.CourseDetailView.as_view()),

    # Slots
    path('slots/', views.SessionSlotListCreateView.as_view()),

    # Generation & Publishing
    path('generate/', views.generate_timetable_trigger),
    path('publish/', views.publish_timetable),

    # CSV Import
    path('import/courses/', views.import_courses_csv),
    path('import/venues/', views.import_venues_csv),

    # Adjustment Requests
    path('requests/', views.AdjustmentRequestListCreateView.as_view()),
    path('requests/<int:pk>/', views.AdjustmentRequestDetailView.as_view()),
    path('requests/<int:pk>/review/', views.review_adjustment_request),
]
