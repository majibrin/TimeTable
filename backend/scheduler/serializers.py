from rest_framework import serializers
from .models import Course, SessionSlot

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'code', 'department', 'unit', 'level']

class SessionSlotSerializer(serializers.ModelSerializer):
    course_detail = serializers.CharField(source='course.__str__', read_only=True)

    class Meta:
        model = SessionSlot
        # Added 'lecturer' so the API and validation can handle it
        fields = ['id', 'course', 'course_detail', 'lecturer', 'venue', 'day', 'start_time', 'end_time']

    def validate(self, data):
        # 1. Extract values (Fallback to existing instance values if doing a partial update/PATCH)
        instance = self.instance
        venue = data.get('venue', getattr(instance, 'venue', None))
        lecturer = data.get('lecturer', getattr(instance, 'lecturer', None))
        day = data.get('day', getattr(instance, 'day', None))
        start_time = data.get('start_time', getattr(instance, 'start_time', None))
        end_time = data.get('end_time', getattr(instance, 'end_time', None))

        # 2. Logic Check: Time direction
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("Start time must be earlier than end time.")

        # 3. Venue Collision Check
        if venue and day and start_time and end_time:
            venue_clash = SessionSlot.objects.filter(
                day=day,
                venue=venue,
                start_time__lt=end_time,
                end_time__gt=start_time
            )
            # If updating, exclude this specific slot from its own conflict check
            if instance:
                venue_clash = venue_clash.exclude(id=instance.id)

            if venue_clash.exists():
                raise serializers.ValidationError("This venue is already occupied during this time block.")

        # 4. Lecturer Collision Check
        if lecturer and day and start_time and end_time:
            lecturer_clash = SessionSlot.objects.filter(
                day=day,
                lecturer=lecturer,
                start_time__lt=end_time,
                end_time__gt=start_time
            )
            # If updating, exclude this specific slot here too
            if instance:
                lecturer_clash = lecturer_clash.exclude(id=instance.id)

            if lecturer_clash.exists():
                raise serializers.ValidationError("This lecturer is already scheduled to teach a course during this time block.")

        return data
