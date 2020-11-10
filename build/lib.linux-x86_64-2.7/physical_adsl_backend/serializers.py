from rest_framework import serializers
from django.core.validators import RegexValidator
from .models import GPONDevice


class IpValidator(RegexValidator):
    regex = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
    message = 'Invalid Ip Address.'


class NetworkDeviceSerializer(serializers.Serializer):
    pk = serializers.IntegerField(read_only=True)
    deviceIp = serializers.CharField(max_length=128, validators=[IpValidator()])
    communityId = serializers.CharField(max_length=128)
    portNumber = serializers.IntegerField()
    cardNumber = serializers.IntegerField()
    shelfNumber = serializers.IntegerField(required=False)
    frame = serializers.IntegerField()
    transactionId = serializers.CharField(max_length=128)


class NetworkDeviceUpdateSerializer(NetworkDeviceSerializer):
    enable = serializers.BooleanField()


class GPONDeviceSerializer(serializers.ModelSerializer):
    device_model = serializers.ReadOnlyField(source="device_model.model_name")

    class Meta:
        model = GPONDevice
        fields = ['name', 'ip_address', 'device_model', 'id']


class GponOperationsGetSerializer(serializers.Serializer):
    frame = serializers.IntegerField()
    slot = serializers.IntegerField()
    port = serializers.IntegerField()
    ontId = serializers.IntegerField()
    hostAddress = serializers.CharField(max_length=128, validators=[IpValidator()])
    deviceType = serializers.CharField(max_length=128)
    transactionId = serializers.CharField(max_length=128)
    portOperation = serializers.CharField()