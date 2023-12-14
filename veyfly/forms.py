import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.forms import DateInput


class HomeSearchForm(forms.Form):
    city = forms.CharField(
        label="",
        min_length=1,
        widget=forms.TextInput(attrs={"placeholder": "Search for home city"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""  # Removes : as label suffix


class TravelPreferencesForm(forms.Form):
    nonstop_only = forms.BooleanField(required=False, label="Direct flights only")
    min_trip_length = forms.IntegerField(
        required=True, min_value=1, label="Minimum trip length"
    )
    max_trip_length = forms.IntegerField(
        required=False, min_value=1, label="Maximum trip length (optional)"
    )
    departure_date = forms.DateField(
        required=True,
        label="Departure date",
        widget=DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    latest_departure_date = forms.DateField(
        required=False,
        label="Latest departure date (optional)",
        widget=DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""  # Removes : as label suffix

    def clean_latest_departure_date(self):
        date = self.cleaned_data.get("latest_departure_date")
        if date and date < datetime.date.today():
            raise forms.ValidationError("The date cannot be in the past!")
        return date

    def clean_departure_date(self):
        date = self.cleaned_data.get("departure_date")
        if date and date < datetime.date.today():
            raise forms.ValidationError("The date cannot be in the past!")
        return date

    def clean(self):
        cleaned_data = super().clean()
        max_trip_length = cleaned_data.get("max_trip_length")
        min_trip_length = cleaned_data.get("min_trip_length")

        if max_trip_length and min_trip_length and max_trip_length <= min_trip_length:
            raise ValidationError(
                "Maximum trip length must be greater than minimum trip length."
            )
        departure_date = cleaned_data.get("departure_date")
        latest_departure_date = cleaned_data.get("latest_departure_date")

        if latest_departure_date and latest_departure_date <= departure_date:
            raise ValidationError("Latest departure date must be after departure date.")


class HomeResultsForm(forms.Form):
    city = forms.ChoiceField(widget=forms.RadioSelect, choices=())

    def __init__(self, *, choices, label=None):
        super().__init__()
        self.fields["city"].choices = choices
        if label is not None:
            self.fields["city"].label = label
