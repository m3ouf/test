from django import forms
from django.core.validators import RegexValidator


class RegistrationForm(forms.Form):
    msisdn = forms.CharField(max_length=11,
                             validators=[RegexValidator(regex=r'^01[0-2,5]{1}[0-9]{8}$',
                                                        message='Please enter 11 digits that start with 010,'
                                                                ' 011, 012 or 015')])


class ActivationForm(forms.Form):
    activation_code = forms.IntegerField()
