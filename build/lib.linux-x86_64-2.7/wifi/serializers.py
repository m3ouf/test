from rest_framework import serializers


class WifiSubscriberSerializer(serializers.Serializer):
    ip = serializers.CharField()
    mobileNo = serializers.CharField()
    password = serializers.CharField()
    userAgent = serializers.CharField()
    userType = serializers.CharField()
    activationCode = serializers.CharField()
    service = serializers.CharField()

    def __init__(self, *args, **kwargs):
        # import ipdb; ipdb.set_trace()
        wifiFunction = kwargs.pop('wifiFunction', False)
        super(WifiSubscriberSerializer, self).__init__(*args, **kwargs)
        if wifiFunction == 'loginWIFISubscriber':
            self.fields.pop('mobileNo')
            self.fields.pop('password')
            self.fields.pop('userAgent')
            self.fields.pop('activationCode')
            self.fields.pop('service')
            self.fields.pop('userType')
        elif wifiFunction == 'registerWIFISubscriber':
            self.fields.pop('password')
            self.fields.pop('activationCode')
            self.fields.pop('service')
        elif wifiFunction == 'checkTEWIFISubscriber':
            self.fields.pop('mobileNo')
            self.fields.pop('ip')
            self.fields.pop('userAgent')
            self.fields.pop('activationCode')
            self.fields.pop('userType')
            self.fields.pop('service')
        elif wifiFunction == 'loginTEWIFISubscriber':
            self.fields.pop('mobileNo')
            self.fields.pop('userAgent')
            self.fields.pop('activationCode')
            self.fields.pop('service')
            self.fields.pop('userType')
        elif wifiFunction == 'manageSubscriberDevices':
            self.fields.pop('mobileNo')
            self.fields.pop('password')
            self.fields.pop('service')
            self.fields.pop('activationCode')
        elif wifiFunction == 'sendActivationCode':
            self.fields.pop('mobileNo')
            self.fields.pop('ip')
            self.fields.pop('password')
            self.fields.pop('userAgent')
            self.fields.pop('service')
            self.fields.pop('userType')
        elif wifiFunction == 'forgetPassword':
            pass
