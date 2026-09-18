"""Notice-board-ready PDF exports (reportlab — no GTK dependency, unlike
WeasyPrint, so it installs cleanly on Windows). The master schedule and duty
roster carry the School of Engineering letterhead (JNU crest + address,
reproduced from the university's official letterhead template); seating
charts and attendance sheets stay plain since they're per-hall working
documents, not official notices."""

from io import BytesIO
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from portal.models import Duty, ExamSchedule, HallAllocation, SeatAssignment

LOGO_PATH = Path(settings.BASE_DIR) / "portal" / "static" / "portal" / "img" / "jnu_logo.png"


def _draw_letterhead(canvas, doc):
    canvas.saveState()
    width, height = doc.pagesize
    margin = doc.leftMargin
    top = height - 28

    if LOGO_PATH.exists():
        logo_size = 46
        canvas.drawImage(
            str(LOGO_PATH), margin, top - logo_size + 6, width=logo_size, height=logo_size,
            mask="auto", preserveAspectRatio=True,
        )

    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawCentredString(width / 2, top, "Jawaharlal Nehru University")
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawCentredString(width / 2, top - 15, "School of Engineering")
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(width / 2, top - 29, "New Delhi - 110067")

    canvas.setLineWidth(1)
    canvas.line(margin, top - 40, width - margin, top - 40)

    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(
        width / 2, doc.bottomMargin - 22,
        "New Mehrauli Road, New Campus, Jawaharlal Nehru University, New Delhi - 110067",
    )
    canvas.drawCentredString(width / 2, doc.bottomMargin - 32, "Tel.: 26739285, 26739283, 26742023")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - margin, doc.bottomMargin - 32, f"Page {doc.page}")
    canvas.restoreState()


def _table_style():
    return TableStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    )


def export_seating_chart_pdf(hall, exam_slot) -> BytesIO:
    allocations = HallAllocation.objects.filter(hall=hall, exam_schedule__exam_slot=exam_slot)
    seat_assignments = SeatAssignment.objects.filter(hall_allocation__in=allocations).select_related(
        "student", "bench_group", "hall_allocation__exam_schedule__course"
    )
    grid = {}
    for sa in seat_assignments:
        grid.setdefault((sa.bench_group_id, sa.bench_number), []).append(sa)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"Seating Chart — {hall} — {exam_slot}", styles["Title"]), Spacer(1, 12)]

    for bench_group in hall.bench_groups.all():
        elements.append(Paragraph(f"{bench_group.label} ({bench_group.bench_count} benches)", styles["Heading3"]))
        row_cells = []
        for bench_number in range(1, bench_group.bench_count + 1):
            seats = sorted(grid.get((bench_group.id, bench_number), []), key=lambda s: s.seat_position)
            if seats:
                text = "\n".join(
                    f"{s.student.enrolment_number} ({s.hall_allocation.exam_schedule.course.code})" for s in seats
                )
            else:
                text = "-"
            row_cells.append(text)
        if not row_cells:
            continue
        table_rows = [row_cells[i : i + 6] for i in range(0, len(row_cells), 6)]
        table = Table(table_rows, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 10))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def export_attendance_sheet_pdf(hall, exam_slot) -> BytesIO:
    allocations = HallAllocation.objects.filter(hall=hall, exam_schedule__exam_slot=exam_slot).select_related(
        "exam_schedule__course"
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"Attendance Sheet — {hall} — {exam_slot}", styles["Title"]), Spacer(1, 12)]

    for allocation in allocations:
        elements.append(Paragraph(str(allocation.exam_schedule.course), styles["Heading3"]))
        seat_assignments = (
            SeatAssignment.objects.filter(hall_allocation=allocation)
            .select_related("student", "bench_group")
            .order_by("bench_group", "bench_number", "seat_position")
        )
        data = [["Seat", "Enrolment No.", "Name", "Signature"]]
        for sa in seat_assignments:
            seat_label = f"{sa.bench_group.label} #{sa.bench_number}.{sa.seat_position}"
            data.append([seat_label, sa.student.enrolment_number, sa.student.name, ""])
        table = Table(data, colWidths=[110, 90, 180, 100])
        table.setStyle(
            TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("FONTSIZE", (0, 0), (-1, -1), 8)])
        )
        elements.append(table)
        elements.append(Spacer(1, 16))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def export_master_schedule_pdf(exam_term) -> BytesIO:
    """Grouped session-wise: one table per session number, listing every
    date that session occurs on."""
    schedules = (
        ExamSchedule.objects.filter(exam_term=exam_term)
        .select_related("course", "exam_slot")
        .prefetch_related("hall_allocations__hall")
        .order_by("exam_slot__session_number", "exam_slot__date")
    )

    by_session = {}
    for schedule in schedules:
        by_session.setdefault(schedule.exam_slot.session_number, []).append(schedule)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), topMargin=100, bottomMargin=60, leftMargin=36, rightMargin=36
    )
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"Master Examination Schedule — {exam_term.label}", styles["Title"]), Spacer(1, 12)]

    for session_number in sorted(by_session):
        elements.append(Paragraph(f"Session {session_number}", styles["Heading2"]))
        data = [["Date", "Time", "Course Code", "Course Name", "Program", "Branch", "Year", "Halls"]]
        for schedule in by_session[session_number]:
            slot = schedule.exam_slot
            halls = ", ".join(a.hall.name for a in schedule.hall_allocations.all()) or "—"
            data.append(
                [
                    slot.date.strftime("%d %b %Y"),
                    f"{slot.start_time.strftime('%H:%M')}–{slot.end_time.strftime('%H:%M')}",
                    schedule.course.code,
                    schedule.course.name,
                    schedule.course.get_program_display(),
                    schedule.course.get_branch_display(),
                    schedule.course.year,
                    halls,
                ]
            )
        table = Table(data, repeatRows=1)
        table.setStyle(_table_style())
        elements.append(table)
        elements.append(Spacer(1, 16))

    if not by_session:
        elements.append(Paragraph("No exams scheduled yet.", styles["Normal"]))

    doc.build(elements, onFirstPage=_draw_letterhead, onLaterPages=_draw_letterhead)
    buffer.seek(0)
    return buffer


def export_duty_roster_pdf(exam_term) -> BytesIO:
    """Grouped date-wise: one table per exam date, listing every session and
    hall that day."""
    duties = (
        Duty.objects.filter(exam_schedule__exam_term=exam_term)
        .select_related("exam_schedule__exam_slot", "hall", "faculty")
        .order_by("exam_schedule__exam_slot__date", "exam_schedule__exam_slot__session_number", "hall__name")
    )

    by_date = {}
    for duty in duties:
        by_date.setdefault(duty.exam_schedule.exam_slot.date, []).append(duty)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=100, bottomMargin=60, leftMargin=36, rightMargin=36)
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"Invigilation Duty Roster — {exam_term.label}", styles["Title"]), Spacer(1, 12)]

    for date in sorted(by_date):
        elements.append(Paragraph(date.strftime("%d %B %Y"), styles["Heading2"]))
        data = [["Session", "Hall", "Faculty / Scholar", "Kind", "Role", "Status"]]
        for duty in by_date[date]:
            slot = duty.exam_schedule.exam_slot
            data.append(
                [
                    f"Session {slot.session_number}",
                    duty.hall.name,
                    duty.faculty.name,
                    duty.faculty.get_kind_display(),
                    duty.get_role_display(),
                    duty.get_status_display(),
                ]
            )
        table = Table(data, repeatRows=1)
        table.setStyle(_table_style())
        elements.append(table)
        elements.append(Spacer(1, 16))

    if not by_date:
        elements.append(Paragraph("No duties assigned yet.", styles["Normal"]))

    doc.build(elements, onFirstPage=_draw_letterhead, onLaterPages=_draw_letterhead)
    buffer.seek(0)
    return buffer
