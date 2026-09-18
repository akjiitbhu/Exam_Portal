from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.contrib.auth.models import User


class Program(models.TextChoices):
    BTECH = "BTECH", "B.Tech"
    MTECH = "MTECH", "M.Tech"
    PHD = "PHD", "PhD"


class Branch(models.TextChoices):
    CSE = "CSE", "Computer Science & Engineering"
    ECE = "ECE", "Electronics & Communication Engineering"
    MST = "MST", "Mathematics & Scientific Computing"


class ExamKind(models.TextChoices):
    MID = "MID", "Mid-Term"
    END = "END", "End-Term"


class FacultyKind(models.TextChoices):
    FACULTY = "FACULTY", "Faculty"
    SCHOLAR = "SCHOLAR", "Research Scholar"


class SeatingMode(models.TextChoices):
    ROLL_ORDER = "ROLL_ORDER", "Roll number order"
    SHUFFLED = "SHUFFLED", "Shuffled across courses"


class SeatDensity(models.TextChoices):
    FULL = "FULL", "Full bench capacity"
    SINGLE = "SINGLE", "One seat per bench (spread out)"


class AccommodationType(models.TextChoices):
    EXTRA_TIME = "EXTRA_TIME", "Extra time"
    SCRIBE = "SCRIBE", "Scribe"
    GROUND_FLOOR = "GROUND_FLOOR", "Ground floor hall"
    SEPARATE_ROOM = "SEPARATE_ROOM", "Separate room"


class DutyRole(models.TextChoices):
    INVIGILATOR = "INVIGILATOR", "Invigilator"
    RESERVE = "RESERVE", "Reserve"


class DutyStatus(models.TextChoices):
    ASSIGNED = "ASSIGNED", "Assigned"
    ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
    DROPPED = "DROPPED", "Dropped"
    REASSIGNED = "REASSIGNED", "Reassigned"


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    program = models.CharField(max_length=10, choices=Program.choices)
    branch = models.CharField(max_length=10, choices=Branch.choices)
    year = models.PositiveSmallIntegerField(help_text="Year of study this course belongs to")

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class Student(models.Model):
    enrolment_number = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=255)
    program = models.CharField(max_length=10, choices=Program.choices)
    branch = models.CharField(max_length=10, choices=Branch.choices)
    year = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["enrolment_number"]

    def __str__(self):
        return f"{self.enrolment_number} — {self.name}"


class CourseEnrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")

    class Meta:
        unique_together = ("course", "student")

    def __str__(self):
        return f"{self.student.enrolment_number} in {self.course.code}"


class Faculty(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    kind = models.CharField(max_length=10, choices=FacultyKind.choices)
    branch = models.CharField(max_length=10, choices=Branch.choices)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Faculty"

    def __str__(self):
        return f"{self.name} ({self.get_kind_display()})"


class Hall(models.Model):
    name = models.CharField(max_length=100, unique=True)
    building = models.CharField(max_length=100, blank=True)
    floor = models.CharField(max_length=50, blank=True)
    is_accessible = models.BooleanField(default=False, help_text="Ground floor / accessible for PwD students")

    class Meta:
        ordering = ["name"]

    @property
    def max_capacity(self):
        return sum(bg.bench_count * bg.seats_per_bench for bg in self.bench_groups.all())

    def capacity_at_density(self, density):
        if density == SeatDensity.FULL:
            return self.max_capacity
        return sum(bg.bench_count for bg in self.bench_groups.all())

    def __str__(self):
        return self.name


class BenchGroup(models.Model):
    """A hall can have more than one type of bench (e.g. some seat 3
    students, some seat 2, some only 1) — each such type is one BenchGroup."""

    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name="bench_groups")
    label = models.CharField(max_length=50, help_text="e.g. \"3-seater bench\"")
    bench_count = models.PositiveSmallIntegerField()
    seats_per_bench = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["-seats_per_bench", "id"]

    def __str__(self):
        return f"{self.label} ({self.bench_count} × {self.seats_per_bench})"


class ExamTerm(models.Model):
    label = models.CharField(max_length=100)
    kind = models.CharField(max_length=5, choices=ExamKind.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    students_per_invigilator = models.PositiveSmallIntegerField(default=30)
    reserves_per_hall = models.PositiveSmallIntegerField(default=1)
    min_gap_minutes = models.PositiveIntegerField(
        default=0, help_text="Minimum gap required between two exams for the same student"
    )

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.label


class Holiday(models.Model):
    exam_term = models.ForeignKey(ExamTerm, on_delete=models.CASCADE, related_name="holidays")
    date = models.DateField()
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("exam_term", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.date} — {self.description}"


class ExamSlot(models.Model):
    exam_term = models.ForeignKey(ExamTerm, on_delete=models.CASCADE, related_name="slots")
    date = models.DateField()
    session_number = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="Which session of the day this is (a day may have up to 4 sessions)",
    )
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ("exam_term", "date", "session_number")
        ordering = ["date", "session_number"]

    def __str__(self):
        return f"{self.date} Session {self.session_number}"


class ExamSchedule(models.Model):
    exam_term = models.ForeignKey(ExamTerm, on_delete=models.CASCADE, related_name="schedules")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="exam_schedules")
    exam_slot = models.ForeignKey(ExamSlot, on_delete=models.CASCADE, related_name="exam_schedules")
    duration_minutes = models.PositiveIntegerField(default=180)

    class Meta:
        unique_together = ("exam_term", "course")
        ordering = ["exam_slot__date", "exam_slot__start_time"]

    def __str__(self):
        return f"{self.course.code} on {self.exam_slot}"


class HallAllocation(models.Model):
    exam_schedule = models.ForeignKey(ExamSchedule, on_delete=models.CASCADE, related_name="hall_allocations")
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name="hall_allocations")
    seat_density = models.CharField(max_length=10, choices=SeatDensity.choices, default=SeatDensity.SINGLE)
    seating_mode = models.CharField(max_length=10, choices=SeatingMode.choices, default=SeatingMode.ROLL_ORDER)

    class Meta:
        unique_together = ("exam_schedule", "hall")

    def __str__(self):
        return f"{self.exam_schedule} @ {self.hall}"


class SeatAssignment(models.Model):
    hall_allocation = models.ForeignKey(HallAllocation, on_delete=models.CASCADE, related_name="seat_assignments")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="seat_assignments")
    bench_group = models.ForeignKey(BenchGroup, on_delete=models.CASCADE, related_name="seat_assignments")
    bench_number = models.PositiveSmallIntegerField()
    seat_position = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ("hall_allocation", "bench_group", "bench_number", "seat_position")
        ordering = ["bench_group", "bench_number", "seat_position"]

    def __str__(self):
        return f"{self.student.enrolment_number} @ {self.bench_group.label} #{self.bench_number}.{self.seat_position}"


class Accommodation(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="accommodations")
    type = models.CharField(max_length=20, choices=AccommodationType.choices)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["student__enrolment_number"]

    def __str__(self):
        return f"{self.student.enrolment_number} — {self.get_type_display()}"


class Duty(models.Model):
    exam_schedule = models.ForeignKey(ExamSchedule, on_delete=models.CASCADE, related_name="duties")
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name="duties")
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="duties")
    role = models.CharField(max_length=15, choices=DutyRole.choices)
    status = models.CharField(max_length=15, choices=DutyStatus.choices, default=DutyStatus.ASSIGNED)

    class Meta:
        unique_together = ("exam_schedule", "hall", "faculty")

    def __str__(self):
        return f"{self.faculty.name} — {self.exam_schedule} ({self.get_role_display()})"


class ScheduleVersion(models.Model):
    exam_term = models.ForeignKey(ExamTerm, on_delete=models.CASCADE, related_name="versions")
    label = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    snapshot = models.JSONField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.exam_term} — v{self.pk} ({self.created_at:%Y-%m-%d %H:%M})"
