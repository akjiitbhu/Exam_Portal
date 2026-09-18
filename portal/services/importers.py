"""Validate-then-commit .xls/.xlsx importers for courses, students, faculty and
course-wise enrollment lists. Each importer is split into a pure `validate_*`
step (never touches the DB) and a `commit_*` step that only runs once the
coordinator/staff has seen the validation preview and confirmed it."""

from dataclasses import dataclass, field
from typing import Any

import openpyxl

from portal.models import Course, CourseEnrollment, Faculty, Program, Branch, FacultyKind, Student


@dataclass
class ImportResult:
    valid_rows: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self):
        return bool(self.errors)

    @property
    def valid_count(self):
        return len(self.valid_rows)


def read_xlsx_rows(uploaded_file) -> list[dict[str, Any]]:
    """Read the first sheet of an uploaded .xlsx into a list of dicts, using the
    first row as (case-insensitive) column headers."""
    workbook = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
    sheet = workbook.worksheets[0]
    rows_iter = sheet.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        return []
    headers = [str(h).strip().lower() if h is not None else "" for h in header_row]
    rows = []
    for raw_row in rows_iter:
        if all(cell is None for cell in raw_row):
            continue
        rows.append({headers[i]: raw_row[i] for i in range(len(headers)) if i < len(raw_row)})
    return rows


def _clean_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _require_columns(rows, required):
    if not rows:
        return ["The file has no data rows."]
    missing = [col for col in required if col not in rows[0]]
    if missing:
        return [f"Missing required column(s): {', '.join(missing)}"]
    return []


def validate_courses(rows: list[dict]) -> ImportResult:
    result = ImportResult()
    missing = _require_columns(rows, ["code", "name", "program", "branch", "year"])
    if missing:
        result.errors.extend(missing)
        return result

    seen_codes = set()
    valid_programs = {c.value for c in Program}
    valid_branches = {b.value for b in Branch}

    for i, row in enumerate(rows, start=2):
        code = _clean_str(row.get("code")).upper()
        name = _clean_str(row.get("name"))
        program = _clean_str(row.get("program")).upper()
        branch = _clean_str(row.get("branch")).upper()
        year = row.get("year")

        if not code or not name:
            result.errors.append(f"Row {i}: code and name are required.")
            continue
        if code in seen_codes:
            result.errors.append(f"Row {i}: duplicate course code '{code}' in this file.")
            continue
        if program not in valid_programs:
            result.errors.append(f"Row {i}: unknown program '{row.get('program')}'.")
            continue
        if branch not in valid_branches:
            result.errors.append(f"Row {i}: unknown branch '{row.get('branch')}'.")
            continue
        try:
            year = int(year)
        except (TypeError, ValueError):
            result.errors.append(f"Row {i}: year must be a number.")
            continue

        seen_codes.add(code)
        result.valid_rows.append({"code": code, "name": name, "program": program, "branch": branch, "year": year})

    return result


def commit_courses(valid_rows: list[dict]) -> int:
    count = 0
    for row in valid_rows:
        Course.objects.update_or_create(
            code=row["code"],
            defaults={"name": row["name"], "program": row["program"], "branch": row["branch"], "year": row["year"]},
        )
        count += 1
    return count


def validate_students(rows: list[dict]) -> ImportResult:
    result = ImportResult()
    missing = _require_columns(rows, ["enrolment_number", "name", "program", "branch", "year"])
    if missing:
        result.errors.extend(missing)
        return result

    seen = set()
    valid_programs = {c.value for c in Program}
    valid_branches = {b.value for b in Branch}

    for i, row in enumerate(rows, start=2):
        enrolment_number = _clean_str(row.get("enrolment_number")).upper()
        name = _clean_str(row.get("name"))
        program = _clean_str(row.get("program")).upper()
        branch = _clean_str(row.get("branch")).upper()
        year = row.get("year")

        if not enrolment_number or not name:
            result.errors.append(f"Row {i}: enrolment_number and name are required.")
            continue
        if enrolment_number in seen:
            result.errors.append(f"Row {i}: duplicate enrolment number '{enrolment_number}' in this file.")
            continue
        if program not in valid_programs:
            result.errors.append(f"Row {i}: unknown program '{row.get('program')}'.")
            continue
        if branch not in valid_branches:
            result.errors.append(f"Row {i}: unknown branch '{row.get('branch')}'.")
            continue
        try:
            year = int(year)
        except (TypeError, ValueError):
            result.errors.append(f"Row {i}: year must be a number.")
            continue

        seen.add(enrolment_number)
        result.valid_rows.append(
            {"enrolment_number": enrolment_number, "name": name, "program": program, "branch": branch, "year": year}
        )

    return result


def commit_students(valid_rows: list[dict]) -> int:
    count = 0
    for row in valid_rows:
        Student.objects.update_or_create(
            enrolment_number=row["enrolment_number"],
            defaults={"name": row["name"], "program": row["program"], "branch": row["branch"], "year": row["year"]},
        )
        count += 1
    return count


def validate_faculty(rows: list[dict]) -> ImportResult:
    result = ImportResult()
    missing = _require_columns(rows, ["name", "email", "kind", "branch"])
    if missing:
        result.errors.extend(missing)
        return result

    seen = set()
    valid_kinds = {k.value for k in FacultyKind}
    valid_branches = {b.value for b in Branch}

    for i, row in enumerate(rows, start=2):
        name = _clean_str(row.get("name"))
        email = _clean_str(row.get("email")).lower()
        kind = _clean_str(row.get("kind")).upper()
        branch = _clean_str(row.get("branch")).upper()

        if not name or not email:
            result.errors.append(f"Row {i}: name and email are required.")
            continue
        if email in seen:
            result.errors.append(f"Row {i}: duplicate email '{email}' in this file.")
            continue
        if kind not in valid_kinds:
            result.errors.append(f"Row {i}: kind must be one of {sorted(valid_kinds)}.")
            continue
        if branch not in valid_branches:
            result.errors.append(f"Row {i}: unknown branch '{row.get('branch')}'.")
            continue

        seen.add(email)
        result.valid_rows.append({"name": name, "email": email, "kind": kind, "branch": branch})

    return result


def commit_faculty(valid_rows: list[dict]) -> int:
    count = 0
    for row in valid_rows:
        Faculty.objects.update_or_create(
            email=row["email"], defaults={"name": row["name"], "kind": row["kind"], "branch": row["branch"]}
        )
        count += 1
    return count


def validate_course_enrollment(rows: list[dict]) -> ImportResult:
    result = ImportResult()
    missing = _require_columns(rows, ["course_code", "enrolment_number"])
    if missing:
        result.errors.extend(missing)
        return result

    course_codes = set(Course.objects.values_list("code", flat=True))
    student_numbers = set(Student.objects.values_list("enrolment_number", flat=True))
    seen_pairs = set()

    for i, row in enumerate(rows, start=2):
        course_code = _clean_str(row.get("course_code")).upper()
        enrolment_number = _clean_str(row.get("enrolment_number")).upper()

        if not course_code or not enrolment_number:
            result.errors.append(f"Row {i}: course_code and enrolment_number are required.")
            continue
        if course_code not in course_codes:
            result.errors.append(f"Row {i}: unknown course code '{course_code}'. Upload courses first.")
            continue
        if enrolment_number not in student_numbers:
            result.errors.append(f"Row {i}: unknown enrolment number '{enrolment_number}'. Upload students first.")
            continue

        pair = (course_code, enrolment_number)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        result.valid_rows.append({"course_code": course_code, "enrolment_number": enrolment_number})

    return result


def commit_course_enrollment(valid_rows: list[dict]) -> int:
    count = 0
    courses = {c.code: c for c in Course.objects.all()}
    students = {s.enrolment_number: s for s in Student.objects.all()}
    for row in valid_rows:
        _, created = CourseEnrollment.objects.get_or_create(
            course=courses[row["course_code"]], student=students[row["enrolment_number"]]
        )
        if created:
            count += 1
    return count
