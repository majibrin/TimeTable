import datetime
from rest_framework import serializers
from .models import Course, SessionSlot, Venue, Department, LevelCohort


class CourseSerializer(serializers.ModelSerializer):
    cohorts = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=LevelCohort.objects.all()
    )
    cohorts_detail = serializers.SerializerMethodField()
    lecturer_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'code', 'unit',
            'department', 'department_name',
            'cohorts', 'cohorts_detail',
            'lecturer', 'lecturer_name'
        ]

    def get_cohorts_detail(self, obj):
        return [
            {'id': c.id, 'label': f"{c.department.name} — {c.level}"}
            for c in obj.cohorts.select_related('department').all()
        ]

    def get_lecturer_name(self, obj):
        if obj.lecturer:
            return f"{obj.lecturer.first_name} {obj.lecturer.last_name}".strip() or obj.lecturer.username
        return "Unassigned"


class VenueSerializer(serializers.ModelSerializer):
    faculty_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()

    class Meta:
        model = Venue
        fields = ['id', 'name', 'capacity', 'faculty', 'faculty_name', 'department', 'department_name']

    def get_faculty_name(self, obj):
        return obj.faculty.name if obj.faculty else None

    def get_department_name(self, obj):
        return obj.department.name if obj.department else None


class LevelCohortSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_code = serializers.CharField(source='department.code', read_only=True)
    faculty_name = serializers.CharField(source='department.faculty.name', read_only=True)

    class Meta:
        model = LevelCohort
        fields = ['id', 'department', 'department_name', 'department_code', 'faculty_name', 'level', 'student_count']


class DepartmentWithCohortsSerializer(serializers.ModelSerializer):
    cohorts = serializers.SerializerMethodField()
    faculty_name = serializers.CharField(source='faculty.name', read_only=True)

    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'faculty', 'faculty_name', 'cohorts']

    def get_cohorts(self, obj):
        cohorts = LevelCohort.objects.filter(department=obj).order_by('level')
        return [{'id': c.id, 'level': c.level, 'student_count': c.student_count} for c in cohorts]


class SessionSlotSerializer(serializers.ModelSerializer):
    course_detail = serializers.SerializerMethodField()
    venue_name = serializers.SerializerMethodField()
    lecturer_name = serializers.SerializerMethodField()
    cohort_detail = serializers.SerializerMethodField()

    class Meta:
        model = SessionSlot
        fields = [
            'id', 'course', 'course_detail',
            'lecturer', 'lecturer_name',
            'venue', 'venue_name',
            'cohort', 'cohort_detail',
            'day', 'start_time', 'duration', 'is_published'
        ]

    def get_course_detail(self, obj):
        return str(obj.course) if obj.course else None

    def get_venue_name(self, obj):
        return obj.venue.name if obj.venue else "TBD"

    def get_lecturer_name(self, obj):
        if obj.lecturer:
            return f"{obj.lecturer.first_name} {obj.lecturer.last_name}".strip() or obj.lecturer.username
        return "Unassigned"

    def get_cohort_detail(self, obj):
        if obj.cohort:
            return f"{obj.cohort.department.code} {obj.cohort.level}"
        return None

    def validate(self, data):
        instance = self.instance
        venue = data.get('venue', getattr(instance, 'venue', None))
        lecturer = data.get('lecturer', getattr(instance, 'lecturer', None))
        day = data.get('day', getattr(instance, 'day', None))
        start_time = data.get('start_time', getattr(instance, 'start_time', None))
        duration = data.get('duration', getattr(instance, 'duration', 1))

        if start_time:
            start_dt = datetime.datetime.combine(datetime.date.today(), start_time)
            end_dt = start_dt + datetime.timedelta(hours=duration)
            calculated_end_time = end_dt.time()

            if start_time < datetime.time(8, 0) or calculated_end_time > datetime.time(18, 0):
                raise serializers.ValidationError("Lectures must fall within 08:00 AM - 06:00 PM.")

            if start_time < datetime.time(14, 0) and calculated_end_time > datetime.time(13, 0):
                raise serializers.ValidationError("Conflicts with the 1:00 PM - 2:00 PM break.")

            if venue and day:
                venue_clash = SessionSlot.objects.filter(day=day, venue=venue)
                if instance:
                    venue_clash = venue_clash.exclude(id=instance.id)
                for slot in venue_clash:
                    if slot.start_time:
                        slot_start = datetime.datetime.combine(datetime.date.today(), slot.start_time)
                        slot_end = (slot_start + datetime.timedelta(hours=slot.duration)).time()
                        if start_time < slot_end and calculated_end_time > slot.start_time:
                            raise serializers.ValidationError("Venue already occupied during this time.")

            if lecturer and day:
                lecturer_clash = SessionSlot.objects.filter(day=day, lecturer=lecturer)
                if instance:
                    lecturer_clash = lecturer_clash.exclude(id=instance.id)
                for slot in lecturer_clash:
                    if slot.start_time:
                        slot_start = datetime.datetime.combine(datetime.date.today(), slot.start_time)
                        slot_end = (slot_start + datetime.timedelta(hours=slot.duration)).time()
                        if start_time < slot_end and calculated_end_time > slot.start_time:
                            raise serializers.ValidationError("Lecturer already scheduled during this time.")

        return data
