from django import forms
from django.core.exceptions import ValidationError


class CreateOrChangeForm(forms.Form):
    userName = forms.CharField(max_length=128)
    serviceName = forms.CharField(max_length=128, required=False)
    transactionId = forms.CharField(max_length=128, required=False)
    isOptionPack = forms.BooleanField(required=False)
    WanIp = forms.IPAddressField(required=False)
    WanMask = forms.IPAddressField(required=False)
    lanip = forms.IPAddressField(required=False)
    lanMask = forms.IPAddressField(required=False)
    zone = forms.CharField(required=False, max_length=64)
    route = forms.CharField(required=False, max_length=64)
    isVrf = forms.BooleanField(required=False)
    vrfName = forms.CharField(max_length=128, required=False)
    wanPeIp = forms.CharField(max_length=128, required=False)


    def clean(self):
        cleaned_data = super(CreateOrChangeForm, self).clean()
        if self.errors:
            return cleaned_data
        if not self.cleaned_data['isOptionPack'] and not self.cleaned_data["userName"]:
            self._errors["userName"] =  self.error_class(["arguments ['userName'] are required but not provided"])

        if self.cleaned_data.get('isOptionPack', False):
            required_params = set(['wanIp', 'wanMask', 'lanIp', 'lanMask','zone','wanPeIp'])
            provided_params = set() # I hate myself for doing this without dict comprehension but you can blame python2.6 :(
            for param in required_params:
                if self.cleaned_data[param]:
                    provided_params.add(param)
            if bool(required_params - provided_params):
                error_msg = "param [{0}] are required but not provided".format(",".join(required_params - provided_params))
                self._errors["optionPackErrors"] = self.error_class([error_msg])

        return cleaned_data
