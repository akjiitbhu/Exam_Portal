from django import forms
from django.forms import inlineformset_factory

from portal.models import Accommodation, BenchGroup, ExamSchedule, ExamSlot, ExamTerm, Hall, HallAllocation, Holiday


class UploadFileForm(forms.Form):
    file = forms.FileField(label="Select .xlsx file")


class HallForm(forms.ModelForm):
    class Meta:
        model = Hall
        fields = ["name", "building", "floor", "is_accessible"]


class BenchGroupForm(forms.ModelForm):
    class Meta:
        model = BenchGroup
        fields = ["label", "bench_count", "seats_per_bench"]
        labels = {"seats_per_bench": "Students per bench"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

    def clean(self):
        cleaned = super().clean()
        filled = [cleaned.get("label"), cleaned.get("bench_count"), cleaned.get("seats_per_bench")]
        if any(filled) and not all(filled):
            raise forms.ValidationError("Fill in label, bench count and students/bench, or leave this bench type blank.")
        return cleaned


def bench_group_formset_factory(existing_count):
    extra = max(1, 3 - existing_count)
    return inlineformset_factory(
        Hall, BenchGroup, form=BenchGroupForm, extra=extra, can_delete=True
    )


class ExamTermForm(forms.ModelForm):
    class Meta:
        model = ExamTerm
        fields = ["label", "kind", "start_date", "end_date", "students_per_invigilator", "reserves_per_hall", "min_gap_minutes"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class HolidayForm(forms.ModelForm):
    class Meta:
        model = Holiday
        fields = ["date", "description"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class ExamSlotForm(forms.ModelForm):
    class Meta:
        model = ExamSlot
        fields = ["date", "session_number", "start_time", "end_time"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }


class ExamScheduleForm(forms.ModelForm):
    class Meta:
        model = ExamSchedule
        fields = ["course", "exam_slot", "duration_minutes"]

    def __init__(self, *args, exam_term=None, **kwargs):
        super().__init__(*args, **kwargs)
        if exam_term is not None:
            self.fields["exam_slot"].queryset = ExamSlot.objects.filter(exam_term=exam_term)


class HallAllocationForm(forms.ModelForm):
    class Meta:
        model = HallAllocation
        fields = ["hall", "seat_density", "seating_mode"]


class AccommodationForm(forms.ModelForm):
    class Meta:
        model = Accommodation
        fields = ["student", "type", "notes"]
