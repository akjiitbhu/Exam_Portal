from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from portal.decorators import role_required
from portal.forms import AccommodationForm, ExamScheduleForm, ExamSlotForm, ExamTermForm, HallAllocationForm, HolidayForm
from portal.models import Accommodation, Duty, ExamSchedule, ExamSlot, ExamTerm, Hall, HallAllocation, ScheduleVersion, SeatAssignment
from portal.services import conflicts as conflicts_service
from portal.services import duties as duties_service
from portal.services import exports as exports_service
from portal.services import history as history_service
from portal.services import seating as seating_service
from portal.services.seating import SeatingError


@role_required("Coordinator")
def exam_terms_list(request):
    return render(request, "portal/coordinator/terms_list.html", {"terms": ExamTerm.objects.all()})


@role_required("Coordinator")
def exam_term_add(request):
    form = ExamTermForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        term = form.save()
        messages.success(request, "Exam term created.")
        return redirect("exam_term_detail", term_id=term.pk)
    return render(request, "portal/coordinator/term_form.html", {"form": form, "title": "New Exam Term"})


@role_required("Coordinator")
def exam_term_detail(request, term_id):
    exam_term = get_object_or_404(ExamTerm, pk=term_id)
    schedules = exam_term.schedules.select_related("course", "exam_slot").prefetch_related("hall_allocations__hall")
    return render(
        request,
        "portal/coordinator/term_detail.html",
        {
            "exam_term": exam_term,
            "schedules": schedules,
            "holidays": exam_term.holidays.all(),
            "slots": exam_term.slots.all(),
        },
    )


@role_required("Coordinator")
def holiday_add(request, term_id):
    exam_term = get_object_or_404(ExamTerm, pk=term_id)
    form = HolidayForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        holiday = form.save(commit=False)
        holiday.exam_term = exam_term
        holiday.save()
        messages.success(request, "Holiday added.")
        return redirect("exam_term_detail", term_id=exam_term.pk)
    return render(request, "portal/coordinator/holiday_form.html", {"form": form, "exam_term": exam_term})


@role_required("Coordinator")
def slot_add(request, term_id):
    exam_term = get_object_or_404(ExamTerm, pk=term_id)
    form = ExamSlotForm(request.POST or None)
    holiday_warning = None
    if request.method == "POST" and form.is_valid():
        date = form.cleaned_data["date"]
        clash = exam_term.holidays.filter(date=date).first()
        if clash and request.POST.get("force") != "1":
            holiday_warning = clash
        else:
            slot = form.save(commit=False)
            slot.exam_term = exam_term
            slot.save()
            messages.success(request, "Exam slot added.")
            return redirect("exam_term_detail", term_id=exam_term.pk)
    return render(
        request,
        "portal/coordinator/slot_form.html",
        {"form": form, "exam_term": exam_term, "holiday_warning": holiday_warning},
    )


@role_required("Coordinator")
def schedule_add(request, term_id):
    exam_term = get_object_or_404(ExamTerm, pk=term_id)
    form = ExamScheduleForm(request.POST or None, exam_term=exam_term)
    conflicts = []
    if request.method == "POST" and form.is_valid():
        course = form.cleaned_data["course"]
        exam_slot = form.cleaned_data["exam_slot"]
        conflicts = conflicts_service.find_student_conflicts(course, exam_slot)
        if not conflicts or request.POST.get("force") == "1":
            schedule = form.save(commit=False)
            schedule.exam_term = exam_term
            schedule.save()
            messages.success(request, "Exam scheduled.")
            return redirect("schedule_detail", pk=schedule.pk)
    return render(
        request,
        "portal/coordinator/schedule_form.html",
        {"form": form, "exam_term": exam_term, "conflicts": conflicts},
    )


@role_required("Coordinator")
def schedule_detail(request, pk):
    schedule = get_object_or_404(
        ExamSchedule.objects.select_related("course", "exam_slot", "exam_term"), pk=pk
    )
    allocations = schedule.hall_allocations.select_related("hall")
    return render(request, "portal/coordinator/schedule_detail.html", {"schedule": schedule, "allocations": allocations})


@role_required("Coordinator")
def hall_allocation_add(request, schedule_id):
    schedule = get_object_or_404(ExamSchedule.objects.select_related("course", "exam_slot"), pk=schedule_id)
    form = HallAllocationForm(request.POST or None)
    problems = []
    if request.method == "POST" and form.is_valid():
        hall = form.cleaned_data["hall"]
        seat_density = form.cleaned_data["seat_density"]
        student_count = schedule.course.enrollments.count()
        problems = conflicts_service.find_hall_conflicts(hall, schedule.exam_slot, seat_density, student_count)
        if not problems or request.POST.get("force") == "1":
            allocation = form.save(commit=False)
            allocation.exam_schedule = schedule
            allocation.save()
            messages.success(request, "Hall allocated.")
            return redirect("schedule_detail", pk=schedule.pk)
    return render(
        request,
        "portal/coordinator/hall_allocation_form.html",
        {"form": form, "schedule": schedule, "problems": problems},
    )


@role_required("Coordinator")
def hall_slot_detail(request, hall_id, slot_id):
    hall = get_object_or_404(Hall, pk=hall_id)
    exam_slot = get_object_or_404(ExamSlot.objects.select_related("exam_term"), pk=slot_id)
    allocations = list(
        HallAllocation.objects.filter(hall=hall, exam_schedule__exam_slot=exam_slot).select_related(
            "exam_schedule__course"
        )
    )
    schedule_ids = [a.exam_schedule_id for a in allocations]
    seat_assignments = (
        SeatAssignment.objects.filter(hall_allocation__in=allocations)
        .select_related("student", "bench_group", "hall_allocation__exam_schedule__course")
        .order_by("bench_group", "bench_number", "seat_position")
    )
    duty_list = Duty.objects.filter(hall=hall, exam_schedule_id__in=schedule_ids).select_related("faculty")

    grid_lookup = {}
    for sa in seat_assignments:
        grid_lookup.setdefault((sa.bench_group_id, sa.bench_number), []).append(sa)
    seat_grid = [
        {
            "bench_group": bench_group,
            "benches": [
                grid_lookup.get((bench_group.id, bench_number), [])
                for bench_number in range(1, bench_group.bench_count + 1)
            ],
        }
        for bench_group in hall.bench_groups.all()
    ]

    return render(
        request,
        "portal/coordinator/hall_slot_detail.html",
        {
            "hall": hall,
            "exam_slot": exam_slot,
            "allocations": allocations,
            "seat_assignments": seat_assignments,
            "seat_grid": seat_grid,
            "duty_list": duty_list,
        },
    )


@role_required("Coordinator")
def generate_seating(request, hall_id, slot_id):
    hall = get_object_or_404(Hall, pk=hall_id)
    exam_slot = get_object_or_404(ExamSlot, pk=slot_id)
    try:
        count, warnings = seating_service.generate_seating_for_hall_slot(hall, exam_slot)
        messages.success(request, f"Generated {count} seat assignment(s).")
        for warning in warnings:
            messages.warning(request, warning)
    except SeatingError as exc:
        messages.error(request, str(exc))
    return redirect("hall_slot_detail", hall_id=hall.pk, slot_id=exam_slot.pk)


@role_required("Coordinator")
def generate_duties(request, hall_id, slot_id):
    hall = get_object_or_404(Hall, pk=hall_id)
    exam_slot = get_object_or_404(ExamSlot, pk=slot_id)
    assigned, shortage = duties_service.allocate_duties_for_hall_slot(hall, exam_slot)
    messages.success(request, f"Assigned {len(assigned)} duty/duties.")
    if shortage:
        messages.warning(request, f"Short by {shortage} — not enough available faculty/scholars for this slot.")
    return redirect("hall_slot_detail", hall_id=hall.pk, slot_id=exam_slot.pk)


@role_required("Coordinator")
def duty_drop(request, duty_id):
    duty = get_object_or_404(Duty.objects.select_related("faculty", "hall", "exam_schedule__exam_slot"), pk=duty_id)
    hall_id, slot_id = duty.hall_id, duty.exam_schedule.exam_slot_id
    promoted = duties_service.promote_reserve(duty)
    if promoted:
        messages.success(request, f"{duty.faculty.name} marked dropped; {promoted.faculty.name} promoted from reserve.")
    else:
        messages.warning(request, f"{duty.faculty.name} marked dropped; no reserve was available to promote.")
    return redirect("hall_slot_detail", hall_id=hall_id, slot_id=slot_id)


@role_required("Coordinator")
def accommodations_list(request):
    form = AccommodationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Accommodation recorded.")
        return redirect("accommodations_list")
    return render(
        request,
        "portal/coordinator/accommodations.html",
        {"form": form, "accommodations": Accommodation.objects.select_related("student").all()},
    )


@role_required("Coordinator")
def publish(request, term_id):
    exam_term = get_object_or_404(ExamTerm, pk=term_id)
    if request.method == "POST":
        history_service.snapshot_exam_term(exam_term, label=request.POST.get("label", ""), user=request.user)
        messages.success(request, "Published a new version of this exam term.")
    return redirect("versions_list", term_id=exam_term.pk)


@role_required("Coordinator")
def versions_list(request, term_id):
    exam_term = get_object_or_404(ExamTerm, pk=term_id)
    return render(
        request, "portal/coordinator/versions.html", {"exam_term": exam_term, "versions": exam_term.versions.all()}
    )


@role_required("Coordinator")
def version_restore(request, version_id):
    version = get_object_or_404(ScheduleVersion, pk=version_id)
    if request.method == "POST":
        history_service.restore_version(version)
        messages.success(request, f"Restored the version published on {version.created_at:%d %b %Y %H:%M}.")
    return redirect("versions_list", term_id=version.exam_term_id)


@role_required("Coordinator")
def export_master_schedule(request, term_id):
    exam_term = get_object_or_404(ExamTerm, pk=term_id)
    buffer = exports_service.export_master_schedule_pdf(exam_term)
    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="master_schedule_{exam_term.pk}.pdf"'
    return response


@role_required("Coordinator")
def export_duty_roster(request, term_id):
    exam_term = get_object_or_404(ExamTerm, pk=term_id)
    buffer = exports_service.export_duty_roster_pdf(exam_term)
    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="duty_roster_{exam_term.pk}.pdf"'
    return response


@role_required("Coordinator")
def export_seating_pdf(request, hall_id, slot_id):
    hall = get_object_or_404(Hall, pk=hall_id)
    exam_slot = get_object_or_404(ExamSlot, pk=slot_id)
    buffer = exports_service.export_seating_chart_pdf(hall, exam_slot)
    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="seating_{hall.pk}_{exam_slot.pk}.pdf"'
    return response


@role_required("Coordinator")
def export_attendance_pdf(request, hall_id, slot_id):
    hall = get_object_or_404(Hall, pk=hall_id)
    exam_slot = get_object_or_404(ExamSlot, pk=slot_id)
    buffer = exports_service.export_attendance_sheet_pdf(hall, exam_slot)
    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="attendance_{hall.pk}_{exam_slot.pk}.pdf"'
    return response
