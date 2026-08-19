from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import datetime
import json
import csv
import io
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework import generics
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import (
    Course, SessionSlot, Venue, LevelCohort, StudentGroup,
    User, Faculty, Department,
    AcademicSession, Semester, TimeSlot, ConstraintSetting
)
from .serializers import (
    CourseSerializer, SessionSlotSerializer,
    VenueSerializer, LevelCohortSerializer,
    DepartmentWithCohortsSerializer, StudentGroupSerializer
)
from .auth_serializers import LoginSerializer
from .engine import TimetableEngine


# ─── Auth Helper ─────────────────────────────────────────────────────────────

def get_authenticated_user(request):
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


def require_roles(request, roles):
    user = get_authenticated_user(request)
    if not user:
        return None, JsonResponse({"error": "Unauthorized"}, status=401)
    if user.role not in roles:
        return None, JsonResponse({"error": "Forbidden"}, status=403)
    return user, None


# ─── Auth ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def index(request):
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized Access"}, status=401)
    return Response({
        "username": user.username,
        "role": user.role,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
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
        "first_name": user.first_name,
        "last_name": user.last_name,
    })


# ─── User Management ─────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'department', 'department_name']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'password', 'department']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.select_related('department').all().order_by('role', 'username')
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer

    def dispatch(self, request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user or user.role != 'SUPER_ADMIN':
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.select_related('department').all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user or user.role != 'SUPER_ADMIN':
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)


# ─── Faculty ─────────────────────────────────────────────────────────────────

class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ['id', 'name', 'code']


class FacultyListCreateView(generics.ListCreateAPIView):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        if request.method != 'GET' and user.role not in ('SUPER_ADMIN', 'TIMETABLE_OFFICER'):
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)


# ─── Department ──────────────────────────────────────────────────────────────

class DepartmentSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source='faculty.name', read_only=True)

    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'faculty', 'faculty_name']


class DepartmentListCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.query_params.get('with_cohorts') == 'true':
            return DepartmentWithCohortsSerializer
        return DepartmentSerializer

    def get_queryset(self):
        qs = Department.objects.select_related('faculty').all()
        faculty_id = self.request.query_params.get('faculty')
        if faculty_id:
            qs = qs.filter(faculty_id=faculty_id)
        return qs

    def dispatch(self, request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        if request.method != 'GET' and user.role not in ('SUPER_ADMIN', 'TIMETABLE_OFFICER'):
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.select_related('faculty').all()
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user or user.role not in ('SUPER_ADMIN', 'TIMETABLE_OFFICER'):
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)


# ─── LevelCohort ─────────────────────────────────────────────────────────────

class LevelCohortListCreateView(generics.ListCreateAPIView):
    serializer_class = LevelCohortSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = LevelCohort.objects.select_related('department__faculty').all()
        dept = self.request.query_params.get('department')
        if dept:
            qs = qs.filter(department_id=dept)
        return qs

    def dispatch(self, request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        if request.method != 'GET' and user.role not in ('SUPER_ADMIN', 'TIMETABLE_OFFICER'):
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)


class LevelCohortDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LevelCohort.objects.select_related('department__faculty').all()
    serializer_class = LevelCohortSerializer
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user or user.role not in ('SUPER_ADMIN', 'TIMETABLE_OFFICER'):
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)


# ─── StudentGroup (Officer-maintained grouping schemes) ──────────────────────

class StudentGroupListCreateView(generics.ListCreateAPIView):
    serializer_class = StudentGroupSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = StudentGroup.objects.prefetch_related('departments').all()
        level = self.request.query_params.get('level')
        scheme = self.request.query_params.get('scheme')
        if level:
            qs = qs.filter(level=level)
        if scheme:
            qs = qs.filter(scheme=scheme)
        return qs

    def dispatch(self, request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        if request.method != 'GET' and user.role not in ('SUPER_ADMIN', 'TIMETABLE_OFFICER'):
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)


class StudentGroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StudentGroup.objects.prefetch_related('departments').all()
    serializer_class = StudentGroupSerializer
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user or user.role not in ('SUPER_ADMIN', 'TIMETABLE_OFFICER'):
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)


# ─── Venue ───────────────────────────────────────────────────────────────────

class VenueListCreateView(generics.ListCreateAPIView):
    serializer_class = VenueSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Venue.objects.select_related('faculty', 'department').all()
        department = self.request.query_params.get('department')
        status_param = self.request.query_params.get('status')
        if department:
            qs = qs.filter(department_id=department)
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def dispatch(self, request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        if request.method != 'GET' and user.role not in ('SUPER_ADMIN', 'TIMETABLE_OFFICER', 'DEPARTMENT'):
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = get_authenticated_user(self.request)
        if user.role == 'DEPARTMENT':
            serializer.save(department=user.department, status='PENDING')
        else:
            serializer.save(status='APPROVED')


class VenueDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Venue.objects.select_related('faculty', 'department').all()
    serializer_class = VenueSerializer
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        if request.method == 'GET':
            return super().dispatch(request, *args, **kwargs)
        if user.role in ('SUPER_ADMIN', 'TIMETABLE_OFFICER'):
            return super().dispatch(request, *args, **kwargs)
        if user.role == 'DEPARTMENT':
            venue = Venue.objects.filter(pk=kwargs.get('pk')).first()
            if not venue or venue.department_id != user.department_id:
                return JsonResponse({"error": "Forbidden"}, status=403)
            return super().dispatch(request, *args, **kwargs)
        return JsonResponse({"error": "Forbidden"}, status=403)


# ─── Course ──────────────────────────────────────────────────────────────────

class CourseListCreateView(generics.ListCreateAPIView):
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Course.objects.select_related('department').prefetch_related('cohorts', 'student_groups').all()
        department = self.request.query_params.get('department')
        cohort = self.request.query_params.get('cohort')
        level = self.request.query_params.get('level')
        status_param = self.request.query_params.get('status')
        if department:
            qs = qs.filter(department_id=department)
        if cohort:
            qs = qs.filter(cohorts__id=cohort)
        if level:
            qs = qs.filter(cohorts__level=level)
        if status_param:
            qs = qs.filter(status=status_param)
        return qs.distinct()

    def dispatch(self, request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        if request.method != 'GET' and user.role not in ('SUPER_ADMIN', 'TIMETABLE_OFFICER', 'DEPARTMENT'):
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = get_authenticated_user(self.request)
        if user.role == 'DEPARTMENT':
            serializer.save(department=user.department, status='PENDING')
        else:
            serializer.save(status='APPROVED')


class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.select_related('department').prefetch_related('cohorts', 'student_groups').all()
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def dispatch(self, request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        if request.method == 'GET':
            return super().dispatch(request, *args, **kwargs)
        if user.role in ('SUPER_ADMIN', 'TIMETABLE_OFFICER'):
            return super().dispatch(request, *args, **kwargs)
        if user.role == 'DEPARTMENT':
            course = Course.objects.filter(pk=kwargs.get('pk')).first()
            if not course or course.department_id != user.department_id:
                return JsonResponse({"error": "Forbidden"}, status=403)
            return super().dispatch(request, *args, **kwargs)
        return JsonResponse({"error": "Forbidden"}, status=403)


# ─── Course / Venue Review (Officer approval workflow) ───────────────────────

@csrf_exempt
def review_course(request, pk):
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    user, err = require_roles(request, ['SUPER_ADMIN', 'TIMETABLE_OFFICER'])
    if err:
        return err
    try:
        course = Course.objects.get(pk=pk)
    except Course.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    decision = data.get('decision')
    if decision not in ('APPROVED', 'REJECTED'):
        return JsonResponse({"error": "decision must be APPROVED or REJECTED"}, status=400)
    course.status = decision
    course.officer_note = data.get('note', '')
    course.save()
    return JsonResponse({"status": decision, "id": pk})


@csrf_exempt
def review_venue(request, pk):
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    user, err = require_roles(request, ['SUPER_ADMIN', 'TIMETABLE_OFFICER'])
    if err:
        return err
    try:
        venue = Venue.objects.get(pk=pk)
    except Venue.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    decision = data.get('decision')
    if decision not in ('APPROVED', 'REJECTED'):
        return JsonResponse({"error": "decision must be APPROVED or REJECTED"}, status=400)
    venue.status = decision
    venue.officer_note = data.get('note', '')
    venue.save()
    return JsonResponse({"status": decision, "id": pk})


# ─── Session Slots ───────────────────────────────────────────────────────────

class SessionSlotListCreateView(generics.ListCreateAPIView):
    serializer_class = SessionSlotSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = SessionSlot.objects.select_related(
            'course__department', 'venue', 'cohort', 'student_group'
        ).all()
        level = self.request.query_params.get('level')
        day = self.request.query_params.get('day')
        department = self.request.query_params.get('department')
        cohort = self.request.query_params.get('cohort')
        published = self.request.query_params.get('published')
        if level:
            qs = qs.filter(cohort__level=level)
        if day:
            qs = qs.filter(day__iexact=day)
        if department:
            qs = qs.filter(cohort__department_id=department)
        if cohort:
            qs = qs.filter(cohort_id=cohort)
        if published == 'true':
            qs = qs.filter(is_published=True)
        return qs


# ─── Academic Session & Semester ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def session_list(request):
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    sessions = AcademicSession.objects.prefetch_related('semesters').all()
    data = []
    for s in sessions:
        data.append({
            'id': s.id,
            'name': s.name,
            'is_active': s.is_active,
            'semesters': list(s.semesters.values('id', 'name', 'is_active'))
        })
    return Response(data)


# ─── TimeSlot ────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def timeslot_list(request):
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    slots = TimeSlot.objects.filter(is_active=True).values('id', 'hour', 'label', 'is_break')
    return Response(list(slots))


# ─── Constraint Settings ─────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def constraint_list(request):
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    constraints = ConstraintSetting.objects.all().values('id', 'name', 'constraint_type', 'weight', 'enabled', 'description')
    return Response(list(constraints))


@csrf_exempt
def update_constraint(request, pk):
    if request.method != 'PATCH':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    user, err = require_roles(request, ['SUPER_ADMIN', 'TIMETABLE_OFFICER'])
    if err:
        return err
    try:
        constraint = ConstraintSetting.objects.get(pk=pk)
        data = json.loads(request.body)
        if 'weight' in data:
            constraint.weight = int(data['weight'])
        if 'enabled' in data:
            constraint.enabled = bool(data['enabled'])
        constraint.save()
        return JsonResponse({"id": pk, "weight": constraint.weight, "enabled": constraint.enabled})
    except ConstraintSetting.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ─── CSV Import ───────────────────────────────────────────────────────────────

@csrf_exempt
def import_courses_csv(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    user, err = require_roles(request, ['SUPER_ADMIN', 'TIMETABLE_OFFICER'])
    if err:
        return err
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({"error": "No file uploaded"}, status=400)
    decoded = file.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    created = 0
    errors = []
    for i, row in enumerate(reader, start=2):
        try:
            dept_name = row.get('department', '').strip()
            cohort_levels = [l.strip() for l in row.get('cohorts', '').split(';') if l.strip()]

            dept = Department.objects.get(name__iexact=dept_name)

            course, _ = Course.objects.update_or_create(
                code=row['code'].strip(),
                defaults={
                    'title': row['title'].strip(),
                    'unit': int(row['unit']),
                    'department': dept,
                    'status': 'APPROVED',
                }
            )

            cohorts = []
            for level in cohort_levels:
                try:
                    c = LevelCohort.objects.get(department=dept, level=level)
                    cohorts.append(c)
                except LevelCohort.DoesNotExist:
                    errors.append(f"Row {i}: Cohort '{dept_name} {level}' not found")
            if cohorts:
                course.cohorts.set(cohorts)

            created += 1
        except Department.DoesNotExist:
            errors.append(f"Row {i}: Department '{dept_name}' not found")
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
    return JsonResponse({"created_or_updated": created, "errors": errors})


@csrf_exempt
def import_venues_csv(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    user, err = require_roles(request, ['SUPER_ADMIN', 'TIMETABLE_OFFICER'])
    if err:
        return err
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({"error": "No file uploaded"}, status=400)
    decoded = file.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    created = 0
    errors = []
    for i, row in enumerate(reader, start=2):
        try:
            Venue.objects.update_or_create(
                name=row['name'].strip(),
                defaults={'capacity': int(row['capacity']), 'status': 'APPROVED'}
            )
            created += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
    return JsonResponse({"created_or_updated": created, "errors": errors})


# ─── Generation ───────────────────────────────────────────────────────────────

@csrf_exempt
def generate_timetable_trigger(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    user, err = require_roles(request, ['SUPER_ADMIN', 'TIMETABLE_OFFICER'])
    if err:
        return err

    try:
        data = json.loads(request.body) if request.body else {}
    except Exception:
        data = {}

    initial_temp = float(data.get('initial_temperature', 1000.0))
    cooling_rate = float(data.get('cooling_rate', 0.95))
    min_temp = float(data.get('min_temperature', 0.01))

    constraint_map = {
        'Venue Clash': 'venue_clash',
        'Cohort Clash': 'cohort_clash',
        'Venue Capacity': 'venue_capacity',
        'Faculty Break': 'faculty_break',
        'Lecture Hours': 'lecture_hours',
        'Same Day Split': 'same_day_split',
        'Saturday Lectures': 'saturday_lectures',
        'Idle Gaps': 'idle_gaps',
    }
    constraint_weights = {}
    for cs in ConstraintSetting.objects.all():
        key = constraint_map.get(cs.name)
        if key:
            constraint_weights[key] = cs.weight if cs.enabled else 0

    active_semester = Semester.objects.filter(is_active=True).first()

    courses = Course.objects.filter(status='APPROVED').prefetch_related('cohorts', 'student_groups').all()
    venues = Venue.objects.filter(status='APPROVED').all()
    level_cohorts = LevelCohort.objects.all()

    if not venues.exists():
        return JsonResponse({"error": "No approved venues configured."}, status=400)
    if not courses.exists():
        return JsonResponse({"error": "No approved courses configured."}, status=400)

    sessions_to_optimize = []

    for course in courses:
        groups = list(course.student_groups.all())

        if groups:
            for group in groups:
                if course.unit == 3:
                    sessions_to_optimize.append({
                        'course_id': course.id, 'group_kind': 'GROUP',
                        'cohort_ids': [group.id], 'duration': 2
                    })
                    sessions_to_optimize.append({
                        'course_id': course.id, 'group_kind': 'GROUP',
                        'cohort_ids': [group.id], 'duration': 1
                    })
                else:
                    sessions_to_optimize.append({
                        'course_id': course.id, 'group_kind': 'GROUP',
                        'cohort_ids': [group.id],
                        'duration': course.unit if course.unit > 0 else 1
                    })
            continue

        cohort_ids = list(course.cohorts.values_list('id', flat=True))
        if not cohort_ids:
            continue

        if course.unit == 3:
            sessions_to_optimize.append({
                'course_id': course.id, 'group_kind': 'COHORT',
                'cohort_ids': cohort_ids, 'duration': 2
            })
            sessions_to_optimize.append({
                'course_id': course.id, 'group_kind': 'COHORT',
                'cohort_ids': cohort_ids, 'duration': 1
            })
        else:
            sessions_to_optimize.append({
                'course_id': course.id, 'group_kind': 'COHORT',
                'cohort_ids': cohort_ids,
                'duration': course.unit if course.unit > 0 else 1
            })

    if not sessions_to_optimize:
        return JsonResponse({"error": "No approved courses with cohorts or groups assigned."}, status=400)

    try:
        engine = TimetableEngine(
            initial_temp=initial_temp,
            cooling_rate=cooling_rate,
            min_temp=min_temp,
            constraint_weights=constraint_weights
        )
        optimized_state, final_energy = engine.run_optimization(
            sessions_to_optimize, venues, level_cohorts, 0
        )

        with transaction.atomic():
            SessionSlot.objects.all().delete()
            days_lookup = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
            time_hours_lookup = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17]

            for slot in optimized_state:
                target_day = days_lookup[slot['day_index']]
                target_hour = time_hours_lookup[slot['time_slot_index']]

                if slot['group_kind'] == 'GROUP':
                    SessionSlot.objects.create(
                        course_id=slot['course_id'],
                        venue_id=slot['venue_id'],
                        student_group_id=slot['cohort_ids'][0],
                        semester=active_semester,
                        day=target_day,
                        start_time=datetime.time(target_hour, 0),
                        duration=slot['duration'],
                        is_published=False
                    )
                else:
                    for cohort_id in slot['cohort_ids']:
                        SessionSlot.objects.create(
                            course_id=slot['course_id'],
                            venue_id=slot['venue_id'],
                            cohort_id=cohort_id,
                            semester=active_semester,
                            day=target_day,
                            start_time=datetime.time(target_hour, 0),
                            duration=slot['duration'],
                            is_published=False
                        )

        return JsonResponse({
            "status": "Optimization completed successfully.",
            "hard_conflicts": int(final_energy // 1000),
            "final_energy_score": final_energy,
            "sessions_generated": len(optimized_state)
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": f"Generation failed: {str(e)}"}, status=500)


# ─── Publish ─────────────────────────────────────────────────────────────────

@csrf_exempt
def publish_timetable(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    user, err = require_roles(request, ['SUPER_ADMIN', 'TIMETABLE_OFFICER'])
    if err:
        return err
    count = SessionSlot.objects.filter(is_published=False).update(is_published=True)
    return JsonResponse({"status": "Published", "slots_published": count})
