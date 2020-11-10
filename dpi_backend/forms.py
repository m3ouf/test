from django import forms
from django.core.exceptions import ValidationError
import datetime
import re

MIN_YEAR = datetime.datetime(year=2000, month=1, day=1)
REJECTED_CHARS_REGEX = "[!\"#$%&\'()*+,/:;<=>?[\\]^`{|}~]"

class InputForm(forms.Form):
    subscriber_id = forms.CharField(max_length=128)
    start_date = forms.CharField(max_length=128)
    end_date = forms.CharField(max_length=128)

    def clean_subscriber_id(self, *args, **kwargs):
        if re.search(REJECTED_CHARS_REGEX, self['subscriber_id'].value()) is None:
            return self.cleaned_data['subscriber_id'].encode('utf-8').strip()
        raise ValidationError("contains illegal characters")

    def clean_start_date(self, *args, **kwargs):
        try:
            self.cleaned_data['start_date'] = self.cleaned_data['start_date'].encode('utf-8').strip() + "T00:00:00+02:00"
            return self.cleaned_data['start_date']
        except TypeError as e:
            raise ValidationError("Enter a valid Start Date/Time")

    def clean_end_date(self, *args, **kwargs):
        try:
            self.cleaned_data['end_date'] = self.cleaned_data['end_date'].encode('utf-8').strip() + "T00:00:00+02:00"
            return self.cleaned_data['end_date']
        except TypeError as e:
            raise ValidationError("Enter a valid End Date/Time")
