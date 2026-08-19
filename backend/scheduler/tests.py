import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from scheduler.models import (
    Faculty, Department, LevelCohort, Course, Venue, StudentGroup,
    AcademicSession, Semester, SessionSlot,
    ConstraintSetting,
)
from scheduler.engine import TimetableEngine

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────
# Shared fixture helper
# ─────────────────────────────────────────────────────────────────────────

class BaseAPITestCase(TestCase):
    """Common setup used across most test classes: faculty/department/
    cohort/venue scaffolding plus one user per role, with helper to
    obtain an authenticated APIClient for a given user."""

    def setUp(self):
        self.client = APIClient()

        self.faculty = Faculty.objects.create(name="Faculty of Science", code="SCI")
        self.department = Department.objects.create(
            name="Computer Science", code="CSC", faculty=self.faculty
        )
        self.other_department = Department.objects.create(
            name="Biology", code="BIO", faculty=self.faculty
        )
        self.cohort_100 = LevelCohort.objects.create(
            department=self.department, level="100L", student_count=80
        )
        self.venue = Venue.objects.create(
            name="LT1", capacity=150, faculty=self.faculty, status="APPROVED"
        )

        self.super_admin = User.objects.create_user(
            username="admin1", password="StrongPass123", role=User.RoleChoices.SUPER_ADMIN
        )
        self.officer = User.objects.create_user(
            username="officer1", password="StrongPass123", role=User.RoleChoices.TIMETABLE_OFFICER
        )
        self.department_user = User.objects.create_user(
            username="dept1", password="StrongPass123",
            role=User.RoleChoices.DEPARTMENT, department=self.department
        )
        self.other_department_user = User.objects.create_user(
            username="dept2", password="StrongPass123",
            role=User.RoleChoices.DEPARTMENT, department=self.other_department
        )
        self.student = User.objects.create_user(
            username="stud1", password="StrongPass123",
            role=User.RoleChoices.STUDENT, department=self.department
        )

    def auth_client(self, user):
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return client


# ─────────────────────────────────────────────────────────────────────────
# 4.7.1 Authentication Testing
# ─────────────────────────────────────────────────────────────────────────

class AuthenticationTests(BaseAPITestCase):

    def test_login_with_valid_credentials_returns_token_and_role(self):
        response = self.client.post("/auth/login/", {
            "username": "officer1", "password": "StrongPass123"
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["role"], "TIMETABLE_OFFICER")

    def test_login_with_invalid_password_is_rejected(self):
        response = self.client.post("/auth/login/", {
            "username": "officer1", "password": "WrongPassword"
        }, format="json")
        self.assertEqual(response.status_code, 401)

    def test_login_with_nonexistent_user_is_rejected(self):
        response = self.client.post("/auth/login/", {
            "username": "ghost", "password": "whatever"
        }, format="json")
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_request_to_protected_endpoint_is_rejected(self):
        response = self.client.get("/users/")
        self.assertEqual(response.status_code, 403)

    def test_authenticated_index_returns_user_profile(self):
        client = self.auth_client(self.officer)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "officer1")
        self.assertEqual(response.data["role"], "TIMETABLE_OFFICER")


# ─────────────────────────────────────────────────────────────────────────
# 4.7.2 User Management Testing
# ─────────────────────────────────────────────────────────────────────────

class UserManagementTests(BaseAPITestCase):

    def test_super_admin_can_create_user(self):
        client = self.auth_client(self.super_admin)
        response = client.post("/users/", {
            "username": "newstud", "email": "newstud@example.com",
            "first_name": "New", "last_name": "Student",
            "role": "STUDENT", "password": "SomePass123",
            "department": self.department.id
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="newstud").exists())

    def test_super_admin_can_create_department_account(self):
        client = self.auth_client(self.super_admin)
        response = client.post("/users/", {
            "username": "newdept", "email": "newdept@example.com",
            "first_name": "New", "last_name": "Dept",
            "role": "DEPARTMENT", "password": "SomePass123",
            "department": self.department.id
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(username="newdept").role, "DEPARTMENT")

    def test_duplicate_username_is_rejected(self):
        client = self.auth_client(self.super_admin)
        response = client.post("/users/", {
            "username": "officer1",
            "email": "dupe@example.com",
            "first_name": "Dup", "last_name": "Licate",
            "role": "STUDENT", "password": "SomePass123",
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_required_field_is_rejected(self):
        client = self.auth_client(self.super_admin)
        response = client.post("/users/", {
            "email": "nouser@example.com",
            "role": "STUDENT", "password": "SomePass123",
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_non_admin_cannot_create_user(self):
        client = self.auth_client(self.officer)
        response = client.post("/users/", {
            "username": "sneaky", "email": "sneaky@example.com",
            "first_name": "S", "last_name": "N",
            "role": "STUDENT", "password": "SomePass123",
        }, format="json")
        self.assertEqual(response.status_code, 403)

    def test_super_admin_can_deactivate_user(self):
        client = self.auth_client(self.super_admin)
        response = client.patch(f"/users/{self.student.id}/", {
            "is_active": False
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)


# ─────────────────────────────────────────────────────────────────────────
# 4.7.3 Course and Venue Management Testing
# ─────────────────────────────────────────────────────────────────────────

class CourseVenueManagementTests(BaseAPITestCase):

    def test_officer_can_create_course_with_cohort(self):
        client = self.auth_client(self.officer)
        response = client.post("/courses/", {
            "title": "Data Structures", "code": "CSC201", "unit": 3,
            "department": self.department.id,
            "cohorts": [self.cohort_100.id],
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Course.objects.filter(code="CSC201").exists())

    def test_officer_created_course_is_auto_approved(self):
        client = self.auth_client(self.officer)
        client.post("/courses/", {
            "title": "Data Structures", "code": "CSC202", "unit": 3,
            "department": self.department.id,
            "cohorts": [self.cohort_100.id],
        }, format="json")
        course = Course.objects.get(code="CSC202")
        self.assertEqual(course.status, "APPROVED")

    def test_department_created_course_is_pending_and_owned(self):
        client = self.auth_client(self.department_user)
        response = client.post("/courses/", {
            "title": "Algorithms", "code": "CSC203", "unit": 3,
            "cohorts": [self.cohort_100.id],
        }, format="json")
        self.assertEqual(response.status_code, 201)
        course = Course.objects.get(code="CSC203")
        self.assertEqual(course.status, "PENDING")
        self.assertEqual(course.department_id, self.department.id)

    def test_officer_can_update_course(self):
        course = Course.objects.create(title="Old", code="CSC100", unit=2, department=self.department, status="APPROVED")
        course.cohorts.add(self.cohort_100)
        client = self.auth_client(self.officer)
        response = client.patch(f"/courses/{course.id}/", {"title": "Updated Title"}, format="json")
        self.assertEqual(response.status_code, 200)
        course.refresh_from_db()
        self.assertEqual(course.title, "Updated Title")

    def test_department_can_edit_own_course(self):
        course = Course.objects.create(title="Old", code="CSC104", unit=2, department=self.department, status="PENDING")
        client = self.auth_client(self.department_user)
        response = client.patch(f"/courses/{course.id}/", {"title": "Fixed Title"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_department_cannot_edit_other_departments_course(self):
        course = Course.objects.create(title="Other", code="BIO101", unit=2, department=self.other_department, status="PENDING")
        client = self.auth_client(self.department_user)
        response = client.patch(f"/courses/{course.id}/", {"title": "Hacked"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_department_can_view_other_departments_courses(self):
        Course.objects.create(title="Other", code="BIO102", unit=2, department=self.other_department, status="APPROVED")
        client = self.auth_client(self.department_user)
        response = client.get("/courses/")
        self.assertEqual(response.status_code, 200)
        codes = [c["code"] for c in response.data]
        self.assertIn("BIO102", codes)

    def test_officer_can_delete_course(self):
        course = Course.objects.create(title="ToDelete", code="CSC999", unit=1, department=self.department, status="APPROVED")
        client = self.auth_client(self.officer)
        response = client.delete(f"/courses/{course.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Course.objects.filter(id=course.id).exists())

    def test_officer_can_create_venue(self):
        client = self.auth_client(self.officer)
        response = client.post("/venues/", {"name": "LT2", "capacity": 200}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Venue.objects.filter(name="LT2").exists())

    def test_department_created_venue_is_pending(self):
        client = self.auth_client(self.department_user)
        response = client.post("/venues/", {"name": "LT-DEPT", "capacity": 60}, format="json")
        self.assertEqual(response.status_code, 201)
        venue = Venue.objects.get(name="LT-DEPT")
        self.assertEqual(venue.status, "PENDING")
        self.assertEqual(venue.department_id, self.department.id)

    def test_student_cannot_create_course(self):
        client = self.auth_client(self.student)
        response = client.post("/courses/", {
            "title": "Hack", "code": "HAX101", "unit": 1,
            "department": self.department.id, "cohorts": [self.cohort_100.id],
        }, format="json")
        self.assertEqual(response.status_code, 403)

    def test_csv_import_creates_courses_and_reports_errors(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        csv_content = (
            "code,title,unit,department,cohorts\n"
            f"CSC301,Algorithms,3,{self.department.name},100L\n"
            "CSC999,BadRow,2,Nonexistent Department,100L\n"
        )
        upload = SimpleUploadedFile("courses.csv", csv_content.encode("utf-8"), content_type="text/csv")
        client = self.auth_client(self.officer)
        response = client.post("/import/courses/", {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Course.objects.filter(code="CSC301").exists())
        self.assertGreaterEqual(len(response.json()["errors"]), 1)


# ─────────────────────────────────────────────────────────────────────────
# 4.7.4 Course / Venue Approval Workflow Testing
# ─────────────────────────────────────────────────────────────────────────

class ApprovalWorkflowTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.pending_course = Course.objects.create(
            title="Pending Course", code="CSC301", unit=2,
            department=self.department, status="PENDING"
        )
        self.pending_venue = Venue.objects.create(
            name="Pending Venue", capacity=50, department=self.department, status="PENDING"
        )

    def test_officer_can_approve_course(self):
        client = self.auth_client(self.officer)
        response = client.post(f"/courses/{self.pending_course.id}/review/", {
            "decision": "APPROVED"
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.pending_course.refresh_from_db()
        self.assertEqual(self.pending_course.status, "APPROVED")

    def test_officer_can_reject_course_with_note(self):
        client = self.auth_client(self.officer)
        response = client.post(f"/courses/{self.pending_course.id}/review/", {
            "decision": "REJECTED", "note": "Duplicate course code"
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.pending_course.refresh_from_db()
        self.assertEqual(self.pending_course.status, "REJECTED")
        self.assertEqual(self.pending_course.officer_note, "Duplicate course code")

    def test_officer_can_approve_venue(self):
        client = self.auth_client(self.officer)
        response = client.post(f"/venues/{self.pending_venue.id}/review/", {
            "decision": "APPROVED"
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.pending_venue.refresh_from_db()
        self.assertEqual(self.pending_venue.status, "APPROVED")

    def test_department_cannot_review_course(self):
        client = self.auth_client(self.department_user)
        response = client.post(f"/courses/{self.pending_course.id}/review/", {
            "decision": "APPROVED"
        }, format="json")
        self.assertEqual(response.status_code, 403)

    def test_department_can_filter_own_pending_submissions(self):
        client = self.auth_client(self.department_user)
        response = client.get(f"/courses/?department={self.department.id}&status=PENDING")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["code"], "CSC301")


# ─────────────────────────────────────────────────────────────────────────
# 4.7.5 Timetable Generation Testing
# ─────────────────────────────────────────────────────────────────────────

class TimetableGenerationTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.session = AcademicSession.objects.create(name="2025/2026", is_active=True)
        self.semester = Semester.objects.create(
            session=self.session, name="FIRST", is_active=True
        )
        self.course = Course.objects.create(
            title="Intro to Programming", code="CSC101", unit=2,
            department=self.department, status="APPROVED"
        )
        self.course.cohorts.add(self.cohort_100)

    def test_generation_requires_officer_or_admin_role(self):
        client = self.auth_client(self.student)
        response = client.post("/generate/", {}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_generation_fails_with_no_venues(self):
        Venue.objects.all().delete()
        client = self.auth_client(self.officer)
        response = client.post("/generate/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_generation_ignores_pending_courses(self):
        Course.objects.create(
            title="Pending", code="CSC199", unit=2,
            department=self.department, status="PENDING"
        ).cohorts.add(self.cohort_100)
        client = self.auth_client(self.officer)
        client.post("/generate/", {
            "initial_temperature": 100.0, "cooling_rate": 0.8, "min_temperature": 1.0
        }, format="json")
        codes_used = set(SessionSlot.objects.values_list("course__code", flat=True))
        self.assertNotIn("CSC199", codes_used)

    def test_generation_produces_session_slots(self):
        client = self.auth_client(self.officer)
        response = client.post("/generate/", {
            "initial_temperature": 100.0,
            "cooling_rate": 0.8,
            "min_temperature": 1.0,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("final_energy_score", response.json())
        self.assertGreater(SessionSlot.objects.count(), 0)

    def test_generated_slots_are_linked_to_active_semester(self):
        client = self.auth_client(self.officer)
        client.post("/generate/", {
            "initial_temperature": 100.0, "cooling_rate": 0.8, "min_temperature": 1.0
        }, format="json")
        slot = SessionSlot.objects.first()
        self.assertEqual(slot.semester, self.semester)


# ─────────────────────────────────────────────────────────────────────────
# 4.7.6 Constraint Validation Testing (direct engine unit tests)
# ─────────────────────────────────────────────────────────────────────────

class ConstraintValidationTests(TestCase):
    """Exercises TimetableEngine.calculate_energy directly with crafted
    states to confirm each hard constraint contributes its penalty weight."""

    def setUp(self):
        self.engine = TimetableEngine()
        self.venue_caps = {1: 100}
        self.cohort_caps = {1: 50}

    def _base_session(self, **overrides):
        base = {
            'course_id': 1, 'cohort_ids': [1],
            'venue_id': 1, 'day_index': 0, 'time_slot_index': 0, 'duration': 1,
        }
        base.update(overrides)
        return base

    def test_venue_clash_is_penalized(self):
        state = [
            self._base_session(course_id=1),
            self._base_session(course_id=2),
        ]
        energy = self.engine.calculate_energy(state, self.venue_caps, self.cohort_caps)
        self.assertGreaterEqual(energy, self.engine.w['venue_clash'])

    def test_cohort_clash_is_penalized(self):
        state = [
            self._base_session(course_id=1, venue_id=1),
            self._base_session(course_id=2, venue_id=2),
        ]
        self.venue_caps[2] = 100
        energy = self.engine.calculate_energy(state, self.venue_caps, self.cohort_caps)
        self.assertGreaterEqual(energy, self.engine.w['cohort_clash'])

    def test_no_conflicts_yields_zero_energy(self):
        state = [
            self._base_session(course_id=1, day_index=0, time_slot_index=0),
            self._base_session(course_id=2, venue_id=2,
                                cohort_ids=[2], day_index=1, time_slot_index=0),
        ]
        self.venue_caps[2] = 100
        self.cohort_caps[2] = 40
        energy = self.engine.calculate_energy(state, self.venue_caps, self.cohort_caps)
        self.assertEqual(energy, 0)

    def test_venue_capacity_violation_is_penalized(self):
        state = [self._base_session(cohort_ids=[1])]
        small_venue_caps = {1: 10}
        energy = self.engine.calculate_energy(state, small_venue_caps, self.cohort_caps)
        self.assertGreaterEqual(energy, self.engine.w['venue_capacity'])

    def test_saturday_lecture_incurs_soft_penalty_only(self):
        state = [self._base_session(day_index=5)]
        energy = self.engine.calculate_energy(state, self.venue_caps, self.cohort_caps)
        self.assertEqual(energy, self.engine.w['saturday_lectures'])

    def test_initial_state_never_selects_break_slot(self):
        sessions_data = [
            {'course_id': 1, 'cohort_ids': [1], 'duration': 1}
        ]
        for _ in range(50):
            state = self.engine._generate_initial_state(sessions_data, [1])
            self.assertNotEqual(state[0]['time_slot_index'], 5)


# ─────────────────────────────────────────────────────────────────────────
# 4.7.7 Timetable Publishing Testing
# ─────────────────────────────────────────────────────────────────────────

class TimetablePublishingTests(BaseAPITestCase):

    def setUp(self):
        super().setUp()
        self.course = Course.objects.create(
            title="Intro to Programming", code="CSC101", unit=2,
            department=self.department, status="APPROVED"
        )
        self.slot = SessionSlot.objects.create(
            course=self.course, venue=self.venue,
            cohort=self.cohort_100, day="MON",
            start_time=datetime.time(9, 0), duration=1, is_published=False
        )

    def test_unpublished_slot_not_visible_to_student_filter(self):
        client = self.auth_client(self.student)
        response = client.get("/slots/?published=true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_publish_marks_slots_published(self):
        client = self.auth_client(self.officer)
        response = client.post("/publish/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.slot.refresh_from_db()
        self.assertTrue(self.slot.is_published)

    def test_published_slot_visible_after_publish(self):
        client = self.auth_client(self.officer)
        client.post("/publish/", {}, format="json")
        student_client = self.auth_client(self.student)
        response = student_client.get(f"/slots/?published=true&cohort={self.cohort_100.id}")
        self.assertEqual(len(response.data), 1)

    def test_non_officer_cannot_publish(self):
        client = self.auth_client(self.student)
        response = client.post("/publish/", {}, format="json")
        self.assertEqual(response.status_code, 403)


# ─────────────────────────────────────────────────────────────────────────
# 4.7.8 Student Grouping Testing
# ─────────────────────────────────────────────────────────────────────────

class StudentGroupTests(BaseAPITestCase):

    def test_officer_can_create_student_group(self):
        client = self.auth_client(self.officer)
        response = client.post("/groups/", {
            "level": "100L", "scheme": "GENERAL", "name": "A",
            "departments": [self.department.id]
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(StudentGroup.objects.filter(level="100L", name="A").exists())

    def test_department_cannot_create_student_group(self):
        client = self.auth_client(self.department_user)
        response = client.post("/groups/", {
            "level": "100L", "scheme": "GENERAL", "name": "B",
            "departments": [self.department.id]
        }, format="json")
        self.assertEqual(response.status_code, 403)

    def test_course_with_groups_generates_one_slot_per_group(self):
        session = AcademicSession.objects.create(name="2025/2026", is_active=True)
        Semester.objects.create(session=session, name="FIRST", is_active=True)

        group_a = StudentGroup.objects.create(level="200L", scheme="COURSE_SPECIFIC", name="A")
        group_a.departments.add(self.department)
        group_b = StudentGroup.objects.create(level="200L", scheme="COURSE_SPECIFIC", name="B")
        group_b.departments.add(self.other_department)

        venue2 = Venue.objects.create(name="LT-GROUP2", capacity=100, faculty=self.faculty, status="APPROVED")

        course = Course.objects.create(
            title="Chemistry I", code="CHM210", unit=2,
            department=self.department, status="APPROVED"
        )
        course.student_groups.set([group_a, group_b])

        client = self.auth_client(self.officer)
        response = client.post("/generate/", {
            "initial_temperature": 100.0, "cooling_rate": 0.8, "min_temperature": 1.0
        }, format="json")
        self.assertEqual(response.status_code, 200)

        slots = SessionSlot.objects.filter(course=course)
        self.assertEqual(slots.count(), 2)
        group_ids_used = set(slots.values_list("student_group_id", flat=True))
        self.assertEqual(group_ids_used, {group_a.id, group_b.id})

    def test_course_without_groups_still_uses_cohort_fallback(self):
        session = AcademicSession.objects.create(name="2025/2026", is_active=True)
        Semester.objects.create(session=session, name="FIRST", is_active=True)

        course = Course.objects.create(
            title="Intro", code="CSC101F", unit=2,
            department=self.department, status="APPROVED"
        )
        course.cohorts.add(self.cohort_100)

        client = self.auth_client(self.officer)
        response = client.post("/generate/", {
            "initial_temperature": 100.0, "cooling_rate": 0.8, "min_temperature": 1.0
        }, format="json")
        self.assertEqual(response.status_code, 200)

        slot = SessionSlot.objects.get(course=course)
        self.assertEqual(slot.cohort_id, self.cohort_100.id)
        self.assertIsNone(slot.student_group_id)
