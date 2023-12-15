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
    trip_length = forms.ChoiceField(
        required=True,
        label="Trip length: ",
        choices=[(num, f"{num} {'days' if num > 1 else 'day'}") for num in range(1, 16)]
        + [("One way", "One way")],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""  # Removes : as label suffix


class HomeResultsForm(forms.Form):
    city = forms.ChoiceField(widget=forms.RadioSelect, choices=())

    def __init__(self, *, choices, label=None):
        super().__init__()
        self.fields["city"].choices = choices
        if label is not None:
            self.fields["city"].label = label
