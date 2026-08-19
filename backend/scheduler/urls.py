from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('auth/login/', views.login_view),

    path('users/', views.UserListCreateView.as_view()),
    path('users/<int:pk>/', views.UserDetailView.as_view()),

    path('faculties/', views.FacultyListCreateView.as_view()),
    path('departments/', views.DepartmentListCreateView.as_view()),
    path('departments/<int:pk>/', views.DepartmentDetailView.as_view()),
    path('cohorts/', views.LevelCohortListCreateView.as_view()),
    path('cohorts/<int:pk>/', views.LevelCohortDetailView.as_view()),

    path('groups/', views.StudentGroupListCreateView.as_view()),
    path('groups/<int:pk>/', views.StudentGroupDetailView.as_view()),

    path('venues/', views.VenueListCreateView.as_view()),
    path('venues/<int:pk>/', views.VenueDetailView.as_view()),
    path('venues/<int:pk>/review/', views.review_venue),

    path('courses/', views.CourseListCreateView.as_view()),
    path('courses/<int:pk>/', views.CourseDetailView.as_view()),
    path('courses/<int:pk>/review/', views.review_course),

    path('slots/', views.SessionSlotListCreateView.as_view()),

    path('sessions/', views.session_list),
    path('timeslots/', views.timeslot_list),

    path('constraints/', views.constraint_list),
    path('constraints/<int:pk>/', views.update_constraint),

    path('generate/', views.generate_timetable_trigger),
    path('publish/', views.publish_timetable),

    path('import/courses/', views.import_courses_csv),
    path('import/venues/', views.import_venues_csv),
]
