
from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
        path('', views.index),
	path('courses/', views.CourseListCreateView.as_view(), name='course-list-craete'),
	path('slots/', views.SessionSlotListCreateView.as_view(), name='sessionslot-list-create'),

]



