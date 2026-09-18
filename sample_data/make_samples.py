import os
import openpyxl

BASE = os.path.dirname(__file__)


def save(name, headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(os.path.join(BASE, name))


save(
    "courses.xlsx",
    ["code", "name", "program", "branch", "year"],
    [
        ["CSE301", "Data Structures", "BTECH", "CSE", 2],
        ["CSE302", "Computer Networks", "BTECH", "CSE", 3],
        ["ECE301", "Digital Signal Processing", "BTECH", "ECE", 3],
    ],
)

save(
    "courses_bad.xlsx",
    ["code", "name", "program", "branch", "year"],
    [
        ["CSE301", "Data Structures", "BTECH", "CSE", 2],
        ["CSE301", "Duplicate Code", "BTECH", "CSE", 2],
        ["CSE999", "Unknown Program Course", "XTECH", "CSE", 2],
    ],
)

save(
    "students.xlsx",
    ["enrolment_number", "name", "program", "branch", "year"],
    [
        [f"2023CSE{i:03d}", f"Student {i}", "BTECH", "CSE", 2] for i in range(1, 41)
    ]
    + [
        [f"2022ECE{i:03d}", f"ECE Student {i}", "BTECH", "ECE", 3] for i in range(1, 21)
    ],
)

save(
    "faculty.xlsx",
    ["name", "email", "kind", "branch"],
    [
        ["Dr. A Sharma", "a.sharma@jnu.ac.in", "FACULTY", "CSE"],
        ["Dr. B Gupta", "b.gupta@jnu.ac.in", "FACULTY", "CSE"],
        ["Dr. C Rao", "c.rao@jnu.ac.in", "FACULTY", "ECE"],
        ["R Kumar (Scholar)", "r.kumar@jnu.ac.in", "SCHOLAR", "CSE"],
        ["S Verma (Scholar)", "s.verma@jnu.ac.in", "SCHOLAR", "ECE"],
    ],
)

enrollment_rows = [["CSE301", f"2023CSE{i:03d}"] for i in range(1, 41)]
save("enrollment_cse301.xlsx", ["course_code", "enrolment_number"], enrollment_rows)

enrollment_rows2 = [["ECE301", f"2022ECE{i:03d}"] for i in range(1, 21)]
save("enrollment_ece301.xlsx", ["course_code", "enrolment_number"], enrollment_rows2)

print("Sample files written to", BASE)
