from django.contrib import admin
from . import models

admin.site.register(models.Course)
admin.site.register(models.Student)
admin.site.register(models.CourseEnrollment)
admin.site.register(models.Faculty)
admin.site.register(models.Hall)
admin.site.register(models.BenchGroup)
admin.site.register(models.ExamTerm)
admin.site.register(models.Holiday)
admin.site.register(models.ExamSlot)
admin.site.register(models.ExamSchedule)
admin.site.register(models.HallAllocation)
admin.site.register(models.SeatAssignment)
admin.site.register(models.Accommodation)
admin.site.register(models.Duty)
admin.site.register(models.ScheduleVersion)
