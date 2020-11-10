from django import forms
from django.core.validators import RegexValidator


class SubnetForm(forms.Form):
    network = forms.CharField(validators=[RegexValidator("(?:[0-9]{1,3}\.){3}[0-9]{1,3}\/([0-9]|[1-2][0-9]|3[0-2])$")])
    subnet = forms.IntegerField(min_value=0)
