from rest_framework import serializers
from django.core.validators import RegexValidator


class IpValidator(RegexValidator):
    regex = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
    message = 'Invalid Ip Address.'


class PortalServiceMigrationSerializer(serializers.Serializer):
    framedIpAddress = serializers.CharField(validators=[IpValidator()], required=False, allow_blank=True)
    subscriberId = serializers.CharField(required=False, allow_blank=True)
    serviceName = serializers.CharField()
    transactionId = serializers.CharField()
    operation = serializers.CharField()