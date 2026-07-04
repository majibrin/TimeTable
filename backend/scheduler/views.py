from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import datetime
import json
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework import generics, status
from rest_framework.serializers import ModelSerializer
from django.contrib.auth import authenticate
from .models import Course, SessionSlot, Venue, LevelCohort, User
from .serializers import CourseSerializer, SessionSlotSerializer
from .auth_serializers import LoginSerializer
from .engine import TimetableEngine


def get_authenticated_user(request):
    """
    Manually parses and validates the JWT Token from the Authorization header.
    Bypasses the DRF global interceptor to prevent automatic 401 crashes.
    """
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    try:
        token_str = auth_header.split(' ')[1]
        access_token = AccessToken(token_str)
        user_id = access_token['user_id']
        return User.objects.get(id=user_id)
    except Exception:
        return None


@api_view(['GET'])
@permission_classes([AllowAny])
def index(request):
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized Access"}, status=401)
    return Response({
        "username": user.username,
        "role": getattr(user, 'role', 'ANONYMOUS')
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    user = authenticate(username=username, password=password)
    if not user:
        return Response({"error": "Invalid credentials"}, status=401)
    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "username": user.username,
        "role": user.role,
    })


class CourseListCreateView(generics.ListCreateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        if not get_authenticated_user(request):
            return JsonResponse({"error": "Unauthorized"}, status=401)
        return super().dispatch(request, *args, **kwargs)


class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        if not get_authenticated_user(request):
            return JsonResponse({"error": "Unauthorized"}, status=401)
        return super().dispatch(request, *args, **kwargs)


class VenueSerializer(ModelSerializer):
    class Meta:
        model = Venue
        fields = ['id', 'name', 'capacity']


class VenueListCreateView(generics.ListCreateAPIView):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        if not get_authenticated_user(request):
            return JsonResponse({"error": "Unauthorized"}, status=401)
        return super().dispatch(request, *args, **kwargs)


class SessionSlotListCreateView(generics.ListCreateAPIView):
    serializer_class = SessionSlotSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = SessionSlot.objects.all()
        level = self.request.query_params.get('level')
        day = self.request.query_params.get('day')

        if level:
            queryset = queryset.filter(course__cohort__level=level)
        if day:
            queryset = queryset.filter(day__iexact=day)

        return queryset


@csrf_exempt
def generate_timetable_trigger(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({"error": "Authentication credentials were not provided or are invalid."}, status=401)

    if getattr(user, 'role', '') != 'ADMIN':
        return JsonResponse({"error": "Unauthorized Access. Only Faculty Officers can execute scheduling generations."}, status=403)

    try:
        data = json.loads(request.body) if request.body else {}
    except Exception:
        data = {}

    initial_temp = float(data.get('initial_temperature', 1000.0))
    cooling_rate = float(data.get('cooling_rate', 0.95))
    min_temp = float(data.get('min_temperature', 0.01))

    courses = Course.objects.all()
    venues = Venue.objects.all()
    lecturers = User.objects.filter(role='LECTURER')
    level_cohorts = LevelCohort.objects.all()

    if not venues.exists():
        return JsonResponse({"error": "Cannot execute scheduling optimization without any configured target venues."}, status=400)

    sessions_to_optimize = []

    for course in courses:
        # Use the lecturer explicitly assigned to the course; no fallback to first()
        assigned_lecturer_id = course.lecturer_id

        if course.unit == 3:
            sessions_to_optimize.append({
                'course_id': course.id,
                'cohort_id': course.cohort.id,
                'lecturer_id': assigned_lecturer_id,
                'duration': 2
            })
            sessions_to_optimize.append({
                'course_id': course.id,
                'cohort_id': course.cohort.id,
                'lecturer_id': assigned_lecturer_id,
                'duration': 1
            })
        else:
            sessions_to_optimize.append({
                'course_id': course.id,
                'cohort_id': course.cohort.id,
                'lecturer_id': assigned_lecturer_id,
                'duration': course.unit if course.unit > 0 else 1
            })

    try:
        engine = TimetableEngine(initial_temp=initial_temp, cooling_rate=cooling_rate, min_temp=min_temp)
        optimized_state, final_energy = engine.run_optimization(
            sessions_to_optimize, venues, level_cohorts, lecturers.count()
        )

        with transaction.atomic():
            SessionSlot.objects.all().delete()

            days_lookup = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
            time_hours_lookup = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17]

            for slot in optimized_state:
                target_day = days_lookup[slot['day_index']]
                target_hour = time_hours_lookup[slot['time_slot_index']]
                start_time_obj = datetime.time(target_hour, 0)

                SessionSlot.objects.create(
                    course_id=slot['course_id'],
                    venue_id=slot['venue_id'],
                    lecturer_id=slot['lecturer_id'],
                    day=target_day,
                    start_time=start_time_obj,
                    duration=slot['duration'],
                    is_published=True
                )

        hard_conflicts = int(final_energy // 1000)

        return JsonResponse({
            "status": "Optimization completed successfully.",
            "hard_conflicts": hard_conflicts,
            "final_energy_score": final_energy
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": f"Heuristic optimization execution failed: {str(e)}"}, status=500)
