# JNU School of Engineering — Exam Portal

A local Django app for the Examination Coordinator and Examination Staff to
manage Mid-Term / End-Term exam schedules, seating plans, and invigilation
duty rosters for B.Tech (CSE/ECE), M.Tech (CSE/ECE/MST) and PhD.

## Setup (Windows)

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python manage.py migrate
venv\Scripts\python manage.py create_default_users
venv\Scripts\python manage.py runserver
```

Then open http://127.0.0.1:8000 in a browser.

Two accounts are created by `create_default_users` (password `changeme123`
by default — pass `--password yourpassword` to set a different one):

- `coordinator` — Exam Terms, holidays, slots, scheduling, hall allocation,
  seating & duty generation, accommodations, publish/version history, exports.
- `staff` — upload/manage courses, students, faculty & research scholars,
  halls, and course-wise enrollment lists.

**Change both passwords after first login** (via `/admin/` or
`manage.py changepassword <username>`) before using this for real data.

## Typical workflow

1. **Staff**: upload courses, students, and faculty/research scholars as
   `.xlsx` files (see column requirements on each upload page), add exam
   halls — each hall can have several bench types (e.g. some benches seat 3
   students, some 2, some 1; leave a bench-type row blank if it doesn't
   apply) — then upload a course-wise enrollment list to map students to
   courses.
2. **Coordinator**: create an Exam Term (Mid-Term/End-Term), mark holidays,
   add exam slots (date + session number — a day can have up to 4 sessions
   — + time), schedule each course into a slot (conflicts with a student's
   other exams are flagged before saving), allocate one or more halls per
   exam at either full bench capacity or one seat per bench for spacing
   (hall-capacity conflicts are flagged too), then generate seating and
   invigilation duties for each hall+slot. Publish a version snapshot once
   the schedule is finalized — you can restore any earlier published
   version later.

## Exports

- **Seating chart / attendance sheet** (per hall+slot) — plain PDF working
  documents.
- **Master schedule** (grouped by session) and **duty roster** (grouped by
  date) — PDF, carrying the School of Engineering letterhead (crest +
  address, reproduced from the university's official letterhead template)
  for printing/circulation as an official notice.

## Sample data

`sample_data/make_samples.py` generates example `.xlsx` files (including one
intentionally invalid file) for exercising the upload flows:

```bash
venv\Scripts\python sample_data\make_samples.py
```

## Notes

- Data lives in `db.sqlite3` in the project root — back it up before making
  risky changes (there's also in-app version history for the exam schedule
  itself, reachable from an Exam Term's page).
- PDF exports use `reportlab` (not WeasyPrint) specifically because it has
  no GTK dependency and installs cleanly on Windows.
