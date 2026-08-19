from django.db import models
from django.contrib.auth.models import AbstractUser


LEVEL_CHOICES = [
    ("100L", "100 Level"),
    ("200L", "200 Level"),
    ("300L", "300 Level"),
    ("400L", "400 Level"),
    ("500L", "500 Level"),
]


class Faculty(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.code})"


class User(AbstractUser):
    class RoleChoices(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        TIMETABLE_OFFICER = 'TIMETABLE_OFFICER', 'Timetable Officer'
        DEPARTMENT = 'DEPARTMENT', 'Department'
        STUDENT = 'STUDENT', 'Student'

    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.STUDENT
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )

    def __str__(self):
        return f"{self.username} ({self.role})"


class SubmissionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class AcademicSession(models.Model):
    name = models.CharField(max_length=20, unique=True)  # e.g. "2025/2026"
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_active:
            AcademicSession.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class Semester(models.Model):
    class SemesterChoices(models.TextChoices):
        FIRST = 'FIRST', 'First Semester'
        SECOND = 'SECOND', 'Second Semester'

    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='semesters')
    name = models.CharField(max_length=10, choices=SemesterChoices.choices)
    is_active = models.BooleanField(default=False)

    class Meta:
        unique_together = ('session', 'name')

    def __str__(self):
        return f"{self.session.name} — {self.name}"

    def save(self, *args, **kwargs):
        if self.is_active:
            Semester.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class TimeSlot(models.Model):
    hour = models.IntegerField()  # 8, 9, 10 ... 17
    label = models.CharField(max_length=20)  # "08:00 - 09:00"
    is_break = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['hour']

    def __str__(self):
        return self.label


class LevelCohort(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    level = models.CharField(max_length=4, choices=LEVEL_CHOICES, default="100L")
    student_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ('department', 'level')

    def __str__(self):
        return f"{self.department.code} ({self.level})"


class StudentGroup(models.Model):
    """A named scheduling group for a given level, defined by the
    Timetable Officer by assigning departments to it. 'General' groups
    are broad, reusable defaults (e.g. Group A-J). 'Course-Specific'
    groups are meaningful only in the context of the course(s) they
    were defined for (e.g. CHM 210's own Group A differs from CHM 212's
    Group A, even at the same level). 'Practical' groups are used for
    lab/practical sessions."""

    class SchemeChoices(models.TextChoices):
        GENERAL = 'GENERAL', 'General Group'
        COURSE_SPECIFIC = 'COURSE_SPECIFIC', 'Course-Specific Group'
        PRACTICAL = 'PRACTICAL', 'Practical Group'

    level = models.CharField(max_length=4, choices=LEVEL_CHOICES)
    scheme = models.CharField(max_length=20, choices=SchemeChoices.choices)
    name = models.CharField(max_length=20)  # e.g. "A", "B", "1", "2"
    departments = models.ManyToManyField(Department, related_name='student_groups', blank=True)

    def __str__(self):
        return f"{self.level} {self.get_scheme_display()} — {self.name}"


class Course(models.Model):
    title = models.CharField(max_length=100)
    code = models.CharField(max_length=15, unique=True)
    unit = models.IntegerField()
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='courses',
        null=True,
        blank=True
    )
    cohorts = models.ManyToManyField(LevelCohort, related_name='courses', blank=True)
    student_groups = models.ManyToManyField(StudentGroup, related_name='courses', blank=True)
    has_practical = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.PENDING
    )
    officer_note = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.title} ({self.unit} C.U)"


class Venue(models.Model):
    name = models.CharField(max_length=50, unique=True)
    capacity = models.IntegerField()
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=10,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.PENDING
    )
    officer_note = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} (Cap: {self.capacity})"


class ConstraintSetting(models.Model):
    class TypeChoices(models.TextChoices):
        HARD = 'HARD', 'Hard Constraint'
        SOFT = 'SOFT', 'Soft Constraint'

    name = models.CharField(max_length=100, unique=True)
    constraint_type = models.CharField(max_length=4, choices=TypeChoices.choices)
    weight = models.IntegerField(default=1000)
    enabled = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.constraint_type}, w={self.weight})"


class SessionSlot(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    venue = models.ForeignKey(Venue, on_delete=models.RESTRICT, null=True, blank=True)
    cohort = models.ForeignKey(
        LevelCohort,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name='session_slots'
    )
    student_group = models.ForeignKey(
        StudentGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_slots'
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    day = models.CharField(
        max_length=3,
        choices=[
            ("MON", "Monday"), ("TUE", "Tuesday"), ("WED", "Wednesday"),
            ("THU", "Thursday"), ("FRI", "Friday"), ("SAT", "Saturday"),
        ]
    )
    start_time = models.TimeField(null=True, blank=True)
    duration = models.IntegerField(default=1)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        venue_name = self.venue.name if self.venue else "TBD"
        return f"{self.course.code} | {venue_name} ({self.day} {self.start_time})"
