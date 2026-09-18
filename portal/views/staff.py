from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from portal.decorators import role_required
from portal.forms import HallForm, UploadFileForm, bench_group_formset_factory
from portal.models import Course, Faculty, Hall, Student
from portal.services import importers


def _handle_upload(request, entity_key, validate_fn, commit_fn, title, help_text):
    session_key = f"import_preview_{entity_key}"
    result = None
    ready_to_commit = False

    if request.method == "POST" and request.POST.get("confirm") == "1":
        valid_rows = request.session.get(session_key)
        if valid_rows is None:
            messages.error(request, "That preview expired — please re-upload the file.")
        else:
            count = commit_fn(valid_rows)
            del request.session[session_key]
            messages.success(request, f"Imported {count} record(s).")
        return redirect(request.path)

    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            rows = importers.read_xlsx_rows(form.cleaned_data["file"])
            result = validate_fn(rows)
            if not result.has_errors:
                request.session[session_key] = result.valid_rows
                ready_to_commit = True
    else:
        form = UploadFileForm()

    return render(
        request,
        "portal/staff/upload.html",
        {"form": form, "result": result, "ready_to_commit": ready_to_commit, "title": title, "help_text": help_text},
    )


@role_required("Staff")
def upload_courses(request):
    return _handle_upload(
        request,
        "courses",
        importers.validate_courses,
        importers.commit_courses,
        "Upload Courses",
        "Columns required: code, name, program (BTECH/MTECH/PHD), branch (CSE/ECE/MST), year",
    )


@role_required("Staff")
def upload_students(request):
    return _handle_upload(
        request,
        "students",
        importers.validate_students,
        importers.commit_students,
        "Upload Students",
        "Columns required: enrolment_number, name, program (BTECH/MTECH/PHD), branch (CSE/ECE/MST), year",
    )


@role_required("Staff")
def upload_faculty(request):
    return _handle_upload(
        request,
        "faculty",
        importers.validate_faculty,
        importers.commit_faculty,
        "Upload Faculty / Research Scholars",
        "Columns required: name, email, kind (FACULTY/SCHOLAR), branch (CSE/ECE/MST)",
    )


@role_required("Staff")
def upload_course_enrollment(request):
    return _handle_upload(
        request,
        "enrollment",
        importers.validate_course_enrollment,
        importers.commit_course_enrollment,
        "Upload Course-wise Student List",
        "Columns required: course_code, enrolment_number. Upload courses and students first — "
        "one row per student per course.",
    )


@role_required("Staff")
def courses_list(request):
    return render(request, "portal/staff/courses_list.html", {"courses": Course.objects.all()})


@role_required("Staff")
def students_list(request):
    return render(request, "portal/staff/students_list.html", {"students": Student.objects.all()})


@role_required("Staff")
def faculty_list(request):
    return render(request, "portal/staff/faculty_list.html", {"faculty": Faculty.objects.all()})


@role_required("Staff")
def halls_list(request):
    return render(request, "portal/staff/halls_list.html", {"halls": Hall.objects.all()})


@role_required("Staff")
def hall_add(request):
    unsaved_hall = Hall()
    FormSetClass = bench_group_formset_factory(existing_count=0)
    form = HallForm(request.POST or None)
    formset = FormSetClass(request.POST or None, instance=unsaved_hall)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            hall = form.save()
            formset.instance = hall
            formset.save()
        messages.success(request, "Hall saved.")
        return redirect("halls_list")
    return render(request, "portal/staff/hall_form.html", {"form": form, "formset": formset, "title": "Add Hall"})


@role_required("Staff")
def hall_edit(request, pk):
    hall = get_object_or_404(Hall, pk=pk)
    FormSetClass = bench_group_formset_factory(existing_count=hall.bench_groups.count())
    form = HallForm(request.POST or None, instance=hall)
    formset = FormSetClass(request.POST or None, instance=hall)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        messages.success(request, "Hall updated.")
        return redirect("halls_list")
    return render(request, "portal/staff/hall_form.html", {"form": form, "formset": formset, "title": f"Edit {hall.name}"})
