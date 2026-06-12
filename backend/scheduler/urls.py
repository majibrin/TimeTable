from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('auth/login/', views.login_view),
    path('courses/', views.CourseListCreateView.as_view()),
    path('courses/<int:pk>/', views.CourseDetailView.as_view()),
    path('slots/', views.SessionSlotListCreateView.as_view()),
    path('generate/', views.generate_timetable_trigger),
    path('venues/', views.VenueListCreateView.as_view()),
]
