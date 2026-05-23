from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from .models import Course, SessionSlot
from .serializers import CourseSerializer, SessionSlotSerializer



@api_view(['GET'])
def index(request):
  return Response({"Username" : request.user.username, "role": request.user.role})



class CourseListCreateView(generics.ListCreateAPIView):
  queryset = Course.objects.all()
  serializer_class = CourseSerializer


class SessionSlotListCreateView(generics.ListCreateAPIView):
  def get_queryset(self):
    queryset = SessionSlot.objects.all()
    level = self.request.query_params.get('level')
    
    day = self.request.query_params.get('day')

    if level:
      queryset = queryset.filter(course__level=level)
    if day:
      queryset = queryset.filter(day__iexact=day)
    return queryset

  serializer_class = SessionSlotSerializer
