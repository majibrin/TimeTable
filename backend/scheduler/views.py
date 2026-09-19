from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import datetime
import json
import csv
import io
from django.db.models import Q  
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
        "department": user.department_id,
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
        "department": user.department_id,
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


class StudentRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'password', 'department']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data, role=User.RoleChoices.STUDENT)
        user.set_password(password)
        user.save()
        return user


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = StudentRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response({
        'id': user.id,
        'username': user.username,
        'role': user.role,
        'department': user.department_id,
    }, status=201)


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
        if request.method == 'GET':
            return super().dispatch(request, *args, **kwargs)
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        if user.role not in ('SUPER_ADMIN', 'TIMETABLE_OFFICER'):
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
        if request.method == 'GET':
            return super().dispatch(request, *args, **kwargs)
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        if user.role not in ('SUPER_ADMIN', 'TIMETABLE_OFFICER'):
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
        if request.method == 'GET':
            return super().dispatch(request, *args, **kwargs)
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        if user.role not in ('SUPER_ADMIN', 'TIMETABLE_OFFICER'):
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
        # Muna farawa da ciro duka session slots tare da hada dangantakarsu (select_related)
        qs = SessionSlot.objects.select_related(
            'course__department', 'venue', 'cohort', 'student_group'
        ).all()
        
        # Karban matattace (filters) na yau da kullum daga URL parameters
        day = self.request.query_params.get('day')
        published = self.request.query_params.get('published')
        
        # Karban bayanan dalibi na musamman don wannan sabon logic din
        student_dept = self.request.query_params.get('student_department')  # ID na sashen dalibi
        level = self.request.query_params.get('level')                      # Misali: '100L'
        
        # Tace bayanan idan dalibi ya bincika ta amfani da sashensa da matakinsa
        if student_dept and level:
            qs = qs.filter(
                # 1) The student's department is attached to the slot's group at this level.
                Q(student_group__departments__id=student_dept, student_group__level=level) |

                # 2) The slot belongs to a departmental cohort at this level.
                Q(cohort__department_id=student_dept, cohort__level=level, student_group__isnull=True) |

                # 3) The slot belongs to a course owned by the student's department,
                #    even when it is scheduled by a general/shared group at this level.
                Q(course__department_id=student_dept, student_group__level=level) |

                # 4) The slot belongs to a department-owned course with a cohort fallback at this level.
                Q(course__department_id=student_dept, student_group__isnull=True, cohort__level=level)
            )
        else:
            # Idan ba a bada takamaiman bayanan dalibi ba, tsarin zai yi amfani da tsofaffin matattacen
            department = self.request.query_params.get('department')
            cohort = self.request.query_params.get('cohort')
            current_level = self.request.query_params.get('level')
            
            if current_level:
                qs = qs.filter(cohort__level=current_level)
            if department:
                qs = qs.filter(cohort__department_id=department)
            if cohort:
                qs = qs.filter(cohort_id=cohort)

        # Matattacen gama-gari (Global filters)
        if day:
            qs = qs.filter(day__iexact=day)
        if published == 'true':
            qs = qs.filter(is_published=True)
            
        return qs.distinct()  # .distinct() yana hana maimaituwar layuka idan aka yi amfani da ManyToMany


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

    # Lowercase headers to tolerate alternative capitalization patterns
    if reader.fieldnames:
        reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]

    created = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        try:
            venue_name = row.get('name', '').strip()
            capacity_raw = row.get('capacity', '0').strip()
            faculty_raw = row.get('faculty', '').strip()
            dept_raw = row.get('department', '').strip()

            # Dynamic Foreign Key Database Lookups
            faculty_obj = Faculty.objects.filter(code__iexact=faculty_raw).first() or \
                          Faculty.objects.filter(name__iexact=faculty_raw).first()

            dept_obj = Department.objects.filter(code__iexact=dept_raw).first() or \
                       Department.objects.filter(name__iexact=dept_raw).first()

            if faculty_raw and not faculty_obj:
                errors.append(f"Row {i}: Faculty reference '{faculty_raw}' not found in database.")
                continue

            if dept_raw and not dept_obj:
                errors.append(f"Row {i}: Department reference '{dept_raw}' not found in database.")
                continue

            # Atomically save changes to database rows with relations intact
            Venue.objects.update_or_create(
                name=venue_name,
                defaults={
                    'capacity': int(capacity_raw or 0),
                    'faculty': faculty_obj,
                    'department': dept_obj,
                    'status': 'APPROVED'
                }
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

    courses = Course.objects.filter(status='APPROVED').prefetch_related(
        'cohorts', 'student_groups', 'student_groups__departments'
    ).all()
    venues = Venue.objects.filter(status='APPROVED').all()
    level_cohorts = LevelCohort.objects.all()

    if not venues.exists():
        return JsonResponse({"error": "No approved venues configured."}, status=400)
    if not courses.exists():
        return JsonResponse({"error": "No approved courses configured."}, status=400)

    sessions_to_optimize = []

    for course in courses:
        # 1. Dynamically extract the true level string (e.g., '100L', '400L')
        first_cohort = course.cohorts.first()
        course_level = first_cohort.level if first_cohort else '100L'
        
        # 2. Gather all department IDs offering this course (needed for 200L checks)
        offering_dept_ids = set()
        if course.department_id:
            offering_dept_ids.add(course.department_id)

        groups = list(course.student_groups.all())

        # General and practical 100L groups are reusable level-wide bundles;
        # their CSV rows intentionally have no course_code to attach by.
        has_course_specific_group = any(
            group.scheme == StudentGroup.SchemeChoices.COURSE_SPECIFIC
            for group in groups
        )
        if course_level == '100L' and not has_course_specific_group and course.department_id:
            fallback_scheme = (
                StudentGroup.SchemeChoices.PRACTICAL
                if any(term in course.title.lower() for term in ('practical', 'lab', 'laboratory'))
                else StudentGroup.SchemeChoices.GENERAL
            )
            groups = list(StudentGroup.objects.filter(
                level='100L',
                scheme=fallback_scheme,
                departments=course.department_id,
            ).distinct().prefetch_related('departments'))

        if groups:
            for group in groups:
                grp_level = group.level if group.level else course_level
                
                # Append departments attached to this specialized group container
                for d in group.departments.all():
                    offering_dept_ids.add(d.id)
                    
                if course.unit == 3:
                    sessions_to_optimize.append({
                        'course_id': course.id, 'group_kind': 'GROUP',
                        'cohort_ids': [group.id], 'duration': 2,
                        'level': grp_level, 'course_dept_id': course.department_id,
                        'offering_dept_ids': list(offering_dept_ids)
                    })
                    sessions_to_optimize.append({
                        'course_id': course.id, 'group_kind': 'GROUP',
                        'cohort_ids': [group.id], 'duration': 1,
                        'level': grp_level, 'course_dept_id': course.department_id,
                        'offering_dept_ids': list(offering_dept_ids)
                    })
                else:
                    sessions_to_optimize.append({
                        'course_id': course.id, 'group_kind': 'GROUP',
                        'cohort_ids': [group.id],
                        'duration': course.unit if course.unit > 0 else 1,
                        'level': grp_level, 'course_dept_id': course.department_id,
                        'offering_dept_ids': list(offering_dept_ids)
                    })
            continue

        cohort_ids = list(course.cohorts.values_list('id', flat=True))
        if not cohort_ids:
            continue

        if course.unit == 3:
            sessions_to_optimize.append({
                'course_id': course.id, 'group_kind': 'COHORT',
                'cohort_ids': cohort_ids, 'duration': 2,
                'level': course_level, 'course_dept_id': course.department_id,
                'offering_dept_ids': list(offering_dept_ids)
            })
            sessions_to_optimize.append({
                'course_id': course.id, 'group_kind': 'COHORT',
                'cohort_ids': cohort_ids, 'duration': 1,
                'level': course_level, 'course_dept_id': course.department_id,
                'offering_dept_ids': list(offering_dept_ids)
            })
        else:
            sessions_to_optimize.append({
                'course_id': course.id, 'group_kind': 'COHORT',
                'cohort_ids': cohort_ids,
                'duration': course.unit if course.unit > 0 else 1,
                'level': course_level, 'course_dept_id': course.department_id,
                'offering_dept_ids': list(offering_dept_ids)
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


# ─── Department / Cohort CSV Import ──────────────────────────────────────────

@csrf_exempt
def import_departments_csv(request):
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
            faculty_name = row.get('faculty', '').strip()
            faculty = Faculty.objects.get(name__iexact=faculty_name)
            Department.objects.update_or_create(
                name=row['name'].strip(),
                defaults={'code': row['code'].strip(), 'faculty': faculty}
            )
            created += 1
        except Faculty.DoesNotExist:
            errors.append(f"Row {i}: Faculty '{faculty_name}' not found")
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
    return JsonResponse({"created_or_updated": created, "errors": errors})


@csrf_exempt
def import_cohorts_csv(request):
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
            dept = Department.objects.get(name__iexact=dept_name)
            LevelCohort.objects.update_or_create(
                department=dept,
                level=row['level'].strip(),
                defaults={'student_count': int(row.get('student_count', 0) or 0)}
            )
            created += 1
        except Department.DoesNotExist:
            errors.append(f"Row {i}: Department '{dept_name}' not found")
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
    return JsonResponse({"created_or_updated": created, "errors": errors})


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def import_student_groups_csv(request):
    """
    Imports student groups from a CSV file.
    CSV Format: scheme, name, level, course_code, departments
    """
    user, err = require_roles(request, ['SUPER_ADMIN', 'TIMETABLE_OFFICER'])
    if err:
        return err

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({"error": "No file uploaded"}, status=400)

    try:
        decoded = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))

        # Standardize headers to lowercase to match lookups safely
        if reader.fieldnames:
            reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]

        created = 0
        errors = []

        with transaction.atomic():
            for i, row in enumerate(reader, start=2):
                scheme_val = row.get('scheme', '').strip().upper()
                group_name = row.get('name', '').strip()
                level_str = row.get('level', '').strip().upper()
                course_code = row.get('course_code', '').strip().upper()
                depts_raw = row.get('departments', '').strip()

                if not (scheme_val and group_name and level_str):
                    errors.append(f"Row {i}: Missing required cells (scheme, name, level).")
                    continue

                if scheme_val not in ['GENERAL', 'COURSE_SPECIFIC', 'PRACTICAL']:
                    errors.append(f"Row {i}: Invalid scheme type '{scheme_val}'.")
                    continue

                # Course-specific uniqueness mapping logic
                course_obj = None
                if scheme_val == 'COURSE_SPECIFIC':
                    if not course_code:
                        errors.append(f"Row {i}: Course-specific entries require a 'course_code'.")
                        continue
                    course_obj = Course.objects.filter(code__iexact=course_code).first()
                    if not course_obj:
                        errors.append(f"Row {i}: Course '{course_code}' not found in database.")
                        continue

                # Parse and look up Many-to-Many departments safely
                resolved_depts = []
                dept_error = False
                if depts_raw:
                    dept_items = [d.strip() for d in depts_raw.split(',') if d.strip()]
                    for item in dept_items:
                        dept = Department.objects.filter(name__iexact=item).first() or \
                               Department.objects.filter(code__iexact=item).first()
                        if dept:
                            resolved_depts.append(dept)
                        else:
                            errors.append(f"Row {i}: Department '{item}' not found.")
                            dept_error = True
                            break
                if dept_error:
                    continue

                # Resolve group instance and enforce inverse Course-M2M scope rules
                student_group = None
                if scheme_val == 'COURSE_SPECIFIC' and course_obj:
                    student_group = course_obj.student_groups.filter(
                        level=level_str, scheme=scheme_val, name=group_name
                    ).first()

                    if not student_group:
                        student_group = StudentGroup.objects.create(
                            level=level_str, scheme=scheme_val, name=group_name
                        )
                        course_obj.student_groups.add(student_group)
                        created += 1
                else:
                    student_group, is_new = StudentGroup.objects.get_or_create(
                        level=level_str, scheme=scheme_val, name=group_name
                    )
                    if is_new:
                        created += 1

                # Update the department assignments
                if resolved_depts:
                    student_group.departments.set(resolved_depts)

        return JsonResponse({"created_or_updated": created, "errors": errors})

    except Exception as e:
        return JsonResponse({"error": f"Import breakdown: {str(e)}"}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def import_faculties_csv(request):
    """
    Ingests a flat CSV dataset to batch-register university faculties.
    Expected CSV columns: name, code
    """
    user, err = require_roles(request, ['SUPER_ADMIN', 'TIMETABLE_OFFICER'])
    if err:
        return err

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({"error": "No file uploaded"}, status=400)

    try:
        decoded = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))

        if reader.fieldnames:
            reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]

        created = 0
        errors = []

        with transaction.atomic():
            for i, row in enumerate(reader, start=2):
                name_str = row.get('name', '').strip()
                code_str = row.get('code', '').strip().upper()

                if not (name_str and code_str):
                    errors.append(f"Row {i}: Missing required column data (name or code).")
                    continue

                # Enforce system integrity by evaluating codes uniquely
                Faculty.objects.update_or_create(
                    code=code_str,
                    defaults={
                        'name': name_str
                    }
                )
                created += 1

        return JsonResponse({"created_or_updated": created, "errors": errors})

    except Exception as e:
        return JsonResponse({"error": f"Faculty ingestion pipeline broke: {str(e)}"}, status=500)
