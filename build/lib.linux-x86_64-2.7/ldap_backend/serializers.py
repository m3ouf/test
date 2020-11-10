from rest_framework import serializers
from django.core.validators import RegexValidator


class SubscriberIdValidator(RegexValidator):
    regex = r'^[a-zA-Z0-9]+\@tedata.net.eg$'
    message = 'Invalid ADSL Username.'


class WifiSubscriberSerializer(serializers.Serializer):
    pk = serializers.IntegerField(read_only=True)
    adslUserName = serializers.CharField(max_length=128, required=False, validators=[SubscriberIdValidator])
    password = serializers.CharField(max_length=128)
    serviceName = serializers.CharField(max_length=128)
    transactionId = serializers.CharField(max_length=128)

    def __init__(self, *args, **kwargs):
        is_delete = kwargs.pop('is_delete', False)
        is_update = kwargs.pop('is_update', False)
        is_get = kwargs.pop('is_get', False)
        super(WifiSubscriberSerializer, self).__init__(*args, **kwargs)
        if is_delete:
            self.fields.pop('password')
            self.fields.pop('serviceName')
        if is_update:
            self.fields.pop('password')
        if is_get:
            self.fields.pop('password')
            self.fields.pop('serviceName')


