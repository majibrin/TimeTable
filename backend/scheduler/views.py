import datetime
from django.db import transaction
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import generics, status
from .models import Course, SessionSlot, Venue, LevelCohort, User
from .serializers import CourseSerializer, SessionSlotSerializer
from .engine import TimetableEngine

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def index(request):
    """
    Returns base metadata about the currently authenticated user session.
    """
    return Response({
        "username": request.user.username,
        "role": request.user.role
    })

class CourseListCreateView(generics.ListCreateAPIView):
    """
    Handles retrieval and generation of academic course records.
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

class SessionSlotListCreateView(generics.ListCreateAPIView):
    """
    Handles listing and creation of timetable slots with robust hierarchy filtering.
    """
    serializer_class = SessionSlotSerializer

    def get_queryset(self):
        queryset = SessionSlot.objects.all()
        level = self.request.query_params.get('level')
        day = self.request.query_params.get('day')

        # Relational fix: looks up level via the updated LevelCohort relationship path
        if level:
            queryset = queryset.filter(course__cohort__level=level)
        if day:
            queryset = queryset.filter(day__iexact=day)

        return queryset

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_timetable_trigger(request):
    """
    Administrative API endpoint to execute the Simulated Annealing scheduling engine.
    """
    # Restrict execution entirely to Admin/Faculty Officers
    if request.user.role != 'ADMIN':
        return Response(
            {"error": "Unauthorized Access. Only Faculty Officers can execute scheduling generations."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Ingest baseline optimization control numbers from the client dashboard payload
    initial_temp = float(request.data.get('initial_temperature', 1000.0))
    cooling_rate = float(request.data.get('cooling_rate', 0.95))
    min_temp = float(request.data.get('min_temperature', 0.01))

    # Fetch active assets into memory for the layout tracking
    courses = Course.objects.all()
    venues = Venue.objects.all()
    lecturers = User.objects.filter(role='LECTURER')
    level_cohorts = LevelCohort.objects.all()

    if not venues.exists():
        return Response(
            {"error": "Cannot execute scheduling optimization without any configured target venues."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # Build the in-memory array representation of items to optimize
    sessions_to_optimize = []
    default_lecturer = lecturers.first()

    for course in courses:
        # Course Credit Splitting Logic (SRS Section 4.C)
        if course.unit == 3:
            # Component A: Continuous 2-Hour block (DOUBLE)
            sessions_to_optimize.append({
                'course_id': course.id,
                'cohort_id': course.cohort.id,
                'lecturer_id': default_lecturer.id if default_lecturer else None,
                'duration': 2
            })
            # Component B: Isolated 1-Hour block (SINGLE)
            sessions_to_optimize.append({
                'course_id': course.id,
                'cohort_id': course.cohort.id,
                'lecturer_id': default_lecturer.id if default_lecturer else None,
                'duration': 1
            })
        else:
            # 1 or 2 Unit courses map directly to their unit size
            sessions_to_optimize.append({
                'course_id': course.id,
                'cohort_id': course.cohort.id,
                'lecturer_id': default_lecturer.id if default_lecturer else None,
                'duration': course.unit if course.unit > 0 else 1
            })

    try:
        # Initialize and fire the engine optimization loop
        engine = TimetableEngine(initial_temp=initial_temp, cooling_rate=cooling_rate, min_temp=min_temp)
        optimized_state, final_energy = engine.run_optimization(
            sessions_to_optimize, venues, level_cohorts, lecturers.count()
        )

        # Atomic transaction block to clear old schedule items and commit new generation matrix safely
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

        return Response({
            "status": "Optimization completed successfully.",
            "hard_conflicts": hard_conflicts,
            "final_energy_score": final_energy
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Heuristic optimization execution failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
