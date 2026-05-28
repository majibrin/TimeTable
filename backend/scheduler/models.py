from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class RoleChoices(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin/Faculty Officer'
        LECTURER = 'LECTURER', 'Lecturer'
        STUDENT = 'STUDENT', 'Student'

    role = models.CharField(max_length=20, choices=RoleChoices.choices, default=RoleChoices.STUDENT)
    
    def __str__(self):
        return f"{self.username}({self.role})"

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

class LevelCohort(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    level = models.CharField(
        max_length=4,
        choices=[
            ("100L", "100 Level"),
            ("200L", "200 Level"),
            ("300L", "300 Level"),
            ("400L", "400 Level"),
            ("500L", "500 Level")
        ],
        default="100L"
    )
    student_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ('department', 'level')

    def __str__(self):
        return f"{self.department.code} ({self.level})"

class Course(models.Model):
    title = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    unit = models.IntegerField()
    cohort = models.ForeignKey(LevelCohort, on_delete=models.CASCADE)

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

    def __str__(self):
        return f"{self.name} (Cap: {self.capacity})"

class SessionSlot(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    venue = models.ForeignKey(Venue, on_delete=models.RESTRICT, null=True, blank=True)
    lecturer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=True, blank=True)
    day = models.CharField(
        max_length=3,
        choices=[
            ("MON", "Monday"),
            ("TUE", "Tuesday"),
            ("WED", "Wednesday"),
            ("THU", "Thursday"),
            ("FRI", "Friday"),
            ("SAT", "Saturday")
        ]
    )
    start_time = models.TimeField(null=True, blank=True)
    duration = models.IntegerField(default=1)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        venue_name = self.venue.name if self.venue else "TBD"
        return f"{self.course.code} | {venue_name} ({self.day} {self.start_time})"

