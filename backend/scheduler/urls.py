from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('courses/', views.CourseListCreateView.as_view(), name='course-list-create'),
    path('slots/', views.SessionSlotListCreateView.as_view(), name='sessionslot-list-create'),
    path('generate/', views.generate_timetable_trigger, name='generate-timetable'),
]



