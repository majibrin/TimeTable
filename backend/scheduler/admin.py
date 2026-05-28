from django.contrib import admin
from .models import User, Faculty, Venue, Department, Course, SessionSlot, LevelCohort
# Register your models here.


admin.site.register(User)
admin.site.register(Faculty)
admin.site.register(Venue)
admin.site.register(Department)
admin.site.register(Course)
admin.site.register(SessionSlot)
admin.site.register(LevelCohort)
