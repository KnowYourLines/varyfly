from django import forms


class HomeSearchForm(forms.Form):
    city = forms.CharField(
        label="",
        min_length=1,
        widget=forms.TextInput(attrs={"placeholder": "Search for home city"}),
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


class CitiesForm(forms.Form):
    cities = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=())

    def __init__(self, *, choices, label=None):
        super().__init__()
        self.fields["cities"].choices = choices
        if label is not None:
            self.fields["cities"].label = label
