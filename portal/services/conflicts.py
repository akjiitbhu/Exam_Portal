"""Conflict detection for exam scheduling: student double-booking (with a
configurable minimum gap), hall double-booking / capacity overflow, and
faculty duty double-booking."""

from datetime import datetime, timedelta

from portal.models import Duty, ExamSchedule, HallAllocation, Student


def _as_datetime(date_, time_):
    return datetime.combine(date_, time_)


def slots_conflict(slot_a, slot_b, min_gap_minutes=0):
    """True if two ExamSlots overlap, or fall within min_gap_minutes of each
    other on the same day."""
    if slot_a.pk == slot_b.pk:
        return True
    if slot_a.date != slot_b.date:
        return False

    a_start, a_end = _as_datetime(slot_a.date, slot_a.start_time), _as_datetime(slot_a.date, slot_a.end_time)
    b_start, b_end = _as_datetime(slot_b.date, slot_b.start_time), _as_datetime(slot_b.date, slot_b.end_time)

    if a_start < b_end and b_start < a_end:
        return True

    gap = (b_start - a_end) if b_start >= a_end else (a_start - b_end)
    return gap < timedelta(minutes=min_gap_minutes)


def find_student_conflicts(course, exam_slot, exclude_schedule=None):
    """Students enrolled in `course` who already have another exam in the same
    term that overlaps, or is too close to, `exam_slot`."""
    exam_term = exam_slot.exam_term
    min_gap = exam_term.min_gap_minutes

    students_in_course = Student.objects.filter(enrollments__course=course)

    other_schedules = (
        ExamSchedule.objects.filter(exam_term=exam_term, course__enrollments__student__in=students_in_course)
        .exclude(course=course)
        .select_related("exam_slot", "course")
        .distinct()
    )
    if exclude_schedule:
        other_schedules = other_schedules.exclude(pk=exclude_schedule.pk)

    conflicts = []
    students_in_course_ids = set(students_in_course.values_list("pk", flat=True))

    for schedule in other_schedules:
        if not slots_conflict(exam_slot, schedule.exam_slot, min_gap):
            continue
        clashing_students = Student.objects.filter(
            pk__in=students_in_course_ids, enrollments__course=schedule.course
        )
        for student in clashing_students:
            conflicts.append({"student": student, "other_course": schedule.course, "other_slot": schedule.exam_slot})

    return conflicts


def find_hall_conflicts(hall, exam_slot, seat_density, extra_student_count, exclude_allocation=None):
    """Returns a list of human-readable conflict strings for allocating
    `hall` to a new exam at `exam_slot` seating `extra_student_count`
    students at `seat_density`."""
    problems = []

    same_slot_allocations = HallAllocation.objects.filter(hall=hall, exam_schedule__exam_slot=exam_slot)
    if exclude_allocation:
        same_slot_allocations = same_slot_allocations.exclude(pk=exclude_allocation.pk)

    existing_students = sum(a.exam_schedule.course.enrollments.count() for a in same_slot_allocations)
    capacity = hall.capacity_at_density(seat_density)
    if existing_students + extra_student_count > capacity:
        problems.append(
            f"{hall} has effective capacity {capacity} at this seating density, but would need to seat "
            f"{existing_students + extra_student_count} students at this slot."
        )

    other_slot_allocations = HallAllocation.objects.filter(hall=hall).exclude(exam_schedule__exam_slot=exam_slot)
    if exclude_allocation:
        other_slot_allocations = other_slot_allocations.exclude(pk=exclude_allocation.pk)
    for allocation in other_slot_allocations.select_related("exam_schedule__exam_slot"):
        if slots_conflict(exam_slot, allocation.exam_schedule.exam_slot):
            problems.append(
                f"{hall} is already allocated to {allocation.exam_schedule} at an overlapping time."
            )

    return problems


def find_faculty_conflict(faculty, exam_slot, exclude_duty=None):
    """Returns the conflicting Duty, if `faculty` is already on duty at an
    overlapping slot, else None."""
    duties = Duty.objects.filter(faculty=faculty).exclude(status="DROPPED").select_related("exam_schedule__exam_slot")
    if exclude_duty:
        duties = duties.exclude(pk=exclude_duty.pk)
    for duty in duties:
        if slots_conflict(exam_slot, duty.exam_schedule.exam_slot):
            return duty
    return None
