from django import forms


class HomeSearchForm(forms.Form):
    city_or_airport = forms.CharField(label="Home city or airport", min_length=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""  # Removes : as label suffix


class HomeResultsForm(forms.Form):
    airports = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple, choices=()
    )

    def __init__(self, choices, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["airports"].choices = choices
