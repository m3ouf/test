from django import forms


class IpInputForm(forms.Form):
    ipAddress = forms.GenericIPAddressField()