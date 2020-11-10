from django import forms
from django.core.exceptions import ValidationError
from dateutil import parser
from django.utils import timezone
import datetime
import re

MIN_YEAR = datetime.datetime(year=2000, month=1, day=1)
REJECTED_CHARS_REGEX = "[!\"#$%&\'()*+,/:;<=>?[\\]^`{|}~]"


class CreateOrChangeForm(forms.Form):
    userName = forms.CharField(max_length=128)
    serviceName = forms.CharField(max_length=128)
    startDate = forms.CharField(max_length=128)
    endDate = forms.CharField(max_length=128)
    resetConsumed = forms.BooleanField(initial=True, required=False)
    carryOver = forms.FloatField(required=False)

    def clean_userName(self, *args, **kwargs):
        if re.search(REJECTED_CHARS_REGEX, self['userName'].value()) is None:
            return self.cleaned_data['userName'].encode('utf-8').strip()
        raise ValidationError("contains illegal characters")

    def clean_startDate(self, *args, **kwargs):
        try:
            start_date = parser.parse(self['startDate'].value())
            if start_date < timezone.make_aware(MIN_YEAR, timezone.get_default_timezone()):
                raise ValidationError("Start Date must be after year 2010")
            return self.cleaned_data['startDate']
        except TypeError as e:
            raise ValidationError("Enter a valid Start Date/Time")

    def clean_endDate(self, *args, **kwargs):
        try:
            end_date = parser.parse(self['endDate'].value())
            if end_date < timezone.make_aware(MIN_YEAR, timezone.get_default_timezone()):
                raise ValidationError("End Date must be after year 2010")
            return self.cleaned_data['endDate']
        except TypeError as e:
            raise ValidationError("Enter a valid End Date/Time")


class ServiceForm(forms.Form):
    userName = forms.CharField(max_length=128)
    serviceType = forms.CharField(max_length=128)
    startDate = forms.CharField(required=False, max_length=128)
    endDate = forms.CharField(required=False, max_length=128)

    def clean_userName(self, *args, **kwargs):
        if re.search(REJECTED_CHARS_REGEX, self['userName'].value()) is None:
            return self.cleaned_data['userName'].encode('utf-8').strip()
        raise ValidationError("contains illegal characters")


class InputForm(forms.Form):
    userName = forms.CharField(max_length=128)
    transactionId = forms.CharField(max_length=64)
    freeQuota = forms.BooleanField(required=False)

    def clean_userName(self, *args, **kwargs):
        if re.search(REJECTED_CHARS_REGEX, self['userName'].value()) is None:
            return self.cleaned_data['userName'].encode('utf-8').strip()
        raise ValidationError("contains illegal characters")


class DebitForm(InputForm):
    serviceName = forms.CharField(max_length=128)
    debitAmount = forms.IntegerField(min_value=0)

    def clean_serviceName(self, *args, **kwargs):
        if re.search(REJECTED_CHARS_REGEX, self['serviceName'].value()) is None:
            return self.cleaned_data['serviceName'].encode('utf-8').strip()
        raise ValidationError("contains illegal characters")


class CreditForm(InputForm):
    creditAmount = forms.IntegerField()