"""Seating-plan generation. The unit of generation is a (hall, exam_slot)
pair, because a hall can be shared by several courses at the same slot and
capacity/shuffling only make sense considered together."""

from portal.models import (
    Accommodation,
    AccommodationType,
    HallAllocation,
    SeatAssignment,
    SeatDensity,
    SeatingMode,
    Student,
)


class SeatingError(Exception):
    pass


def _seat_positions(hall, density):
    """Yields (bench_group, bench_number, seat_position) across every bench
    type in the hall, largest benches first."""
    for bench_group in hall.bench_groups.all():
        seats = bench_group.seats_per_bench if density == SeatDensity.FULL else 1
        for bench_number in range(1, bench_group.bench_count + 1):
            for pos in range(1, seats + 1):
                yield (bench_group, bench_number, pos)


def _round_robin_merge(groups):
    """groups: list of (allocation, [students]). Interleaves one student from
    each group per pass so adjacent seats differ in course."""
    iterators = [iter(students) for _, students in groups]
    allocations = [allocation for allocation, _ in groups]
    merged = []
    active = list(range(len(iterators)))
    while active:
        still_active = []
        for idx in active:
            try:
                student = next(iterators[idx])
            except StopIteration:
                continue
            merged.append((allocations[idx], student))
            still_active.append(idx)
        active = still_active
    return merged


def generate_seating_for_hall_slot(hall, exam_slot):
    """(Re)generates SeatAssignments for every HallAllocation that places
    `hall` at `exam_slot`. Returns (seats_created, warnings)."""
    allocations = list(
        HallAllocation.objects.filter(hall=hall, exam_schedule__exam_slot=exam_slot).select_related(
            "exam_schedule__course"
        )
    )
    if not allocations:
        return 0, []

    density = allocations[0].seat_density
    capacity = hall.capacity_at_density(density)

    warnings = []
    course_groups = []
    needs_accessible_type = [AccommodationType.GROUND_FLOOR, AccommodationType.SEPARATE_ROOM]

    for allocation in allocations:
        course = allocation.exam_schedule.course
        roster = Student.objects.filter(enrollments__course=course).order_by("enrolment_number")
        needs_accessible_ids = set(
            Accommodation.objects.filter(
                student__enrollments__course=course, type__in=needs_accessible_type
            ).values_list("student_id", flat=True)
        )

        if hall.is_accessible or not needs_accessible_ids:
            students = list(roster)
        else:
            students = [s for s in roster if s.pk not in needs_accessible_ids]
            skipped_count = roster.filter(pk__in=needs_accessible_ids).count()
            sibling_has_accessible_hall = HallAllocation.objects.filter(
                exam_schedule=allocation.exam_schedule, hall__is_accessible=True
            ).exists()
            if skipped_count and not sibling_has_accessible_hall:
                warnings.append(
                    f"{course}: {skipped_count} student(s) need an accessible hall but none is allocated "
                    f"for this exam — add one before publishing."
                )

        course_groups.append((allocation, students))

    total_students = sum(len(students) for _, students in course_groups)
    if total_students > capacity:
        raise SeatingError(
            f"{hall} has effective capacity {capacity} at this seating density, but "
            f"{total_students} students need seating at this slot."
        )

    use_shuffle = len(course_groups) > 1 and any(
        allocation.seating_mode == SeatingMode.SHUFFLED for allocation, _ in course_groups
    )
    ordered = _round_robin_merge(course_groups) if use_shuffle else [
        (allocation, student) for allocation, students in course_groups for student in students
    ]

    SeatAssignment.objects.filter(hall_allocation__in=allocations).delete()

    created = []
    for (allocation, student), (bench_group, bench_number, pos) in zip(ordered, _seat_positions(hall, density)):
        created.append(
            SeatAssignment(
                hall_allocation=allocation,
                student=student,
                bench_group=bench_group,
                bench_number=bench_number,
                seat_position=pos,
            )
        )
    SeatAssignment.objects.bulk_create(created)

    return len(created), warnings
