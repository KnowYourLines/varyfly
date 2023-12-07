from django import forms


class HomeForm(forms.Form):
    city_or_airport = forms.CharField(label="Home city or airport", min_length=1)
    direct = forms.BooleanField(required=False, label="Direct only")
    one_way = forms.BooleanField(required=False, label="One way")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""  # Removes : as label suffix
