"""Fair invigilation-duty allocation: required invigilators per hall are
derived from ExamTerm.students_per_invigilator, faculty/scholars are picked
in ascending order of their cumulative duty count for the term (so load
balances out over the exam), and a configurable number of reserves are added
per hall so a dropout can be filled with one click."""

import math

from portal.models import Duty, DutyRole, DutyStatus, Faculty, HallAllocation
from portal.services.conflicts import find_faculty_conflict


def _duty_count(faculty, exam_term):
    return (
        Duty.objects.filter(faculty=faculty, exam_schedule__exam_term=exam_term)
        .exclude(status=DutyStatus.DROPPED)
        .count()
    )


def allocate_duties_for_hall_slot(hall, exam_slot):
    """Returns (assigned_duties, shortage) where shortage is how many
    invigilator/reserve slots could not be filled for lack of available
    faculty."""
    allocations = list(
        HallAllocation.objects.filter(hall=hall, exam_schedule__exam_slot=exam_slot).select_related(
            "exam_schedule__exam_term", "exam_schedule__course"
        )
    )
    if not allocations:
        return [], 0

    exam_term = exam_slot.exam_term
    exam_schedules_here = [a.exam_schedule for a in allocations]
    total_students = sum(a.exam_schedule.course.enrollments.count() for a in allocations)
    required = max(1, math.ceil(total_students / exam_term.students_per_invigilator))
    needed = required + exam_term.reserves_per_hall
    primary_schedule = allocations[0].exam_schedule

    Duty.objects.filter(hall=hall, exam_schedule__in=exam_schedules_here).delete()

    available = [f for f in Faculty.objects.all() if find_faculty_conflict(f, exam_slot) is None]
    available.sort(key=lambda f: _duty_count(f, exam_term))

    assigned = []
    for i, faculty in enumerate(available[:needed]):
        role = DutyRole.INVIGILATOR if i < required else DutyRole.RESERVE
        duty = Duty.objects.create(
            exam_schedule=primary_schedule, hall=hall, faculty=faculty, role=role, status=DutyStatus.ASSIGNED
        )
        assigned.append(duty)

    shortage = max(0, needed - len(available))
    return assigned, shortage


def promote_reserve(dropped_duty):
    """Marks `dropped_duty` DROPPED and promotes the next available reserve
    for the same hall/exam to INVIGILATOR. Returns the promoted Duty, or
    None if no reserve was available."""
    dropped_duty.status = DutyStatus.DROPPED
    dropped_duty.save(update_fields=["status"])

    reserve = (
        Duty.objects.filter(hall=dropped_duty.hall, exam_schedule=dropped_duty.exam_schedule, role=DutyRole.RESERVE)
        .exclude(status=DutyStatus.DROPPED)
        .order_by("id")
        .first()
    )
    if not reserve:
        return None

    reserve.role = DutyRole.INVIGILATOR
    reserve.status = DutyStatus.REASSIGNED
    reserve.save(update_fields=["role", "status"])
    return reserve
