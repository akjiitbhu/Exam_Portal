"""Publish-time version snapshots of an ExamTerm's schedule/seating/duties,
with the ability to restore a prior version."""

from django.db import transaction

from portal.models import (
    BenchGroup,
    Course,
    Duty,
    ExamSchedule,
    ExamSlot,
    Hall,
    HallAllocation,
    ScheduleVersion,
    SeatAssignment,
    Student,
)


def snapshot_exam_term(exam_term, label="", user=None):
    schedules = ExamSchedule.objects.filter(exam_term=exam_term)
    hall_allocations = HallAllocation.objects.filter(exam_schedule__in=schedules)
    seat_assignments = SeatAssignment.objects.filter(hall_allocation__in=hall_allocations)
    duties = Duty.objects.filter(exam_schedule__in=schedules)

    snapshot = {
        "schedules": [
            {"id": s.id, "course_id": s.course_id, "exam_slot_id": s.exam_slot_id, "duration_minutes": s.duration_minutes}
            for s in schedules
        ],
        "hall_allocations": [
            {
                "id": a.id,
                "exam_schedule_id": a.exam_schedule_id,
                "hall_id": a.hall_id,
                "seat_density": a.seat_density,
                "seating_mode": a.seating_mode,
            }
            for a in hall_allocations
        ],
        "seat_assignments": [
            {
                "hall_allocation_id": sa.hall_allocation_id,
                "student_id": sa.student_id,
                "bench_group_id": sa.bench_group_id,
                "bench_number": sa.bench_number,
                "seat_position": sa.seat_position,
            }
            for sa in seat_assignments
        ],
        "duties": [
            {
                "id": d.id,
                "exam_schedule_id": d.exam_schedule_id,
                "hall_id": d.hall_id,
                "faculty_id": d.faculty_id,
                "role": d.role,
                "status": d.status,
            }
            for d in duties
        ],
    }

    return ScheduleVersion.objects.create(exam_term=exam_term, label=label, created_by=user, snapshot=snapshot)


@transaction.atomic
def restore_version(version):
    exam_term = version.exam_term
    snapshot = version.snapshot

    ExamSchedule.objects.filter(exam_term=exam_term).delete()

    valid_slot_ids = set(ExamSlot.objects.filter(exam_term=exam_term).values_list("id", flat=True))
    valid_course_ids = set(Course.objects.values_list("id", flat=True))
    valid_hall_ids = set(Hall.objects.values_list("id", flat=True))
    valid_student_ids = set(Student.objects.values_list("id", flat=True))

    for s in snapshot.get("schedules", []):
        if s["course_id"] not in valid_course_ids or s["exam_slot_id"] not in valid_slot_ids:
            continue
        ExamSchedule.objects.create(
            id=s["id"],
            exam_term=exam_term,
            course_id=s["course_id"],
            exam_slot_id=s["exam_slot_id"],
            duration_minutes=s["duration_minutes"],
        )

    restored_schedule_ids = set(ExamSchedule.objects.filter(exam_term=exam_term).values_list("id", flat=True))

    for a in snapshot.get("hall_allocations", []):
        if a["exam_schedule_id"] not in restored_schedule_ids or a["hall_id"] not in valid_hall_ids:
            continue
        HallAllocation.objects.create(
            id=a["id"],
            exam_schedule_id=a["exam_schedule_id"],
            hall_id=a["hall_id"],
            seat_density=a["seat_density"],
            seating_mode=a["seating_mode"],
        )

    restored_allocation_ids = set(
        HallAllocation.objects.filter(exam_schedule__exam_term=exam_term).values_list("id", flat=True)
    )
    valid_bench_group_ids = set(BenchGroup.objects.values_list("id", flat=True))

    seat_assignments = []
    for sa in snapshot.get("seat_assignments", []):
        if (
            sa["hall_allocation_id"] not in restored_allocation_ids
            or sa["student_id"] not in valid_student_ids
            or sa["bench_group_id"] not in valid_bench_group_ids
        ):
            continue
        seat_assignments.append(
            SeatAssignment(
                hall_allocation_id=sa["hall_allocation_id"],
                student_id=sa["student_id"],
                bench_group_id=sa["bench_group_id"],
                bench_number=sa["bench_number"],
                seat_position=sa["seat_position"],
            )
        )
    SeatAssignment.objects.bulk_create(seat_assignments)

    for d in snapshot.get("duties", []):
        if d["exam_schedule_id"] not in restored_schedule_ids or d["hall_id"] not in valid_hall_ids:
            continue
        Duty.objects.create(
            id=d["id"],
            exam_schedule_id=d["exam_schedule_id"],
            hall_id=d["hall_id"],
            faculty_id=d["faculty_id"],
            role=d["role"],
            status=d["status"],
        )
