from django import forms


class HomeForm(forms.Form):
    city_or_airport = forms.CharField(label="Home city or airport", min_length=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""  # Removes : as label suffix
