import datetime
from rest_framework import serializers
from .models import Course, SessionSlot

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'code', 'unit', 'cohort']

class SessionSlotSerializer(serializers.ModelSerializer):
    course_detail = serializers.CharField(source='course.__str__', read_only=True)
    venue_name = serializers.CharField(source='venue.__str__', read_only=True)
    lecturer_name = serializers.CharField(source='lecturer.__str__', read_only=True)

    class Meta:
        model = SessionSlot
        fields = ['id', 'course', 'course_detail', 'lecturer', 'lecturer_name', 'venue', 'venue_name', 'day', 'start_time', 'duration', 'is_published']

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
                raise serializers.ValidationError("Lectures must fall strictly within standard working hours (08:00 AM - 06:00 PM).")

            if start_time < datetime.time(14, 0) and calculated_end_time > datetime.time(13, 0):
                raise serializers.ValidationError("Scheduling conflicts with the mandatory system-wide institutional break (01:00 PM - 02:00 PM).")

            if venue and day:
                venue_clash = SessionSlot.objects.filter(day=day, venue=venue)
                if instance:
                    venue_clash = venue_clash.exclude(id=instance.id)
                for slot in venue_clash:
                    if slot.start_time:
                        slot_start = datetime.datetime.combine(datetime.date.today(), slot.start_time)
                        slot_end = (slot_start + datetime.timedelta(hours=slot.duration)).time()
                        if start_time < slot_end and calculated_end_time > slot.start_time:
                            raise serializers.ValidationError("The selected venue is already occupied during this specific duration block.")

            if lecturer and day:
                lecturer_clash = SessionSlot.objects.filter(day=day, lecturer=lecturer)
                if instance:
                    lecturer_clash = lecturer_clash.exclude(id=instance.id)
                for slot in lecturer_clash:
                    if slot.start_time:
                        slot_start = datetime.datetime.combine(datetime.date.today(), slot.start_time)
                        slot_end = (slot_start + datetime.timedelta(hours=slot.duration)).time()
                        if start_time < slot_end and calculated_end_time > slot.start_time:
                            raise serializers.ValidationError("This lecturer is already scheduled to teach another course during this duration block.")

        return data
