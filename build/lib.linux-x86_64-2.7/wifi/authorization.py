from django.contrib.auth.models import User
from rest_framework import permissions, exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework import permissions


class KeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        if request.data.get('key', False):
            if request.data.get('key', False) == 'wifiUser':
                try:
                    user = User.objects.get(username='wifiUser')
                except User.DoesNotExist:
                    raise exceptions.AuthenticationFailed('Authentication key not valid, User doesn\'t exists.')
            else:
                raise exceptions.AuthenticationFailed('Authentication key not valid.')
        elif request.method == 'GET':
            if request.GET.get('key', False) == 'wifiUser':
                try:
                    user = User.objects.get(username='wifiUser')
                except User.DoesNotExist:
                    raise exceptions.AuthenticationFailed('Authentication key not valid, User doesn\'t exists.')
            else:
                raise exceptions.AuthenticationFailed('Authentication key not valid.')
        else:
            raise exceptions.AuthenticationFailed('Authentication key not provided.')
        return (user, None)
