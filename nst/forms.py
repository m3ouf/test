from django import forms
from dateutil import parser
from django.core.exceptions import ValidationError
from .models import NASTool


class SBRDailyUsageForm(forms.Form):
    subscriber_id = forms.CharField(max_length=30, min_length=1)
    start_date = forms.DateField()
    end_date = forms.DateField()


class CyberCrimeForm(forms.Form):
    ipAddress = forms.GenericIPAddressField()
    startDate = forms.DateTimeField()
    endDate = forms.DateTimeField()


class WifiReportForm(forms.Form):
    start_date_errors = {
        'required': 'Start Date field is required.'
    }
    start_date = forms.DateField(error_messages=start_date_errors)
    end_date = forms.DateField(required=False)


class WifiVenueForm(forms.ModelForm):
    class Meta:
        model = NASTool