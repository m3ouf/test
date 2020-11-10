from ldap_profile import LDAPClient
from shared.decorators import check_params, handle_connection_error
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from shared.common import log_action, send_404_error_message
from serializers import WifiSubscriberSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from forms import CreateOrChangeForm
import json
import logging
import inspect
import re

logger = logging.getLogger(__name__)
ADSL_PATTERN = re.compile(r"^([a-zA-Z0-9]+)\@tedata.net.eg")

@require_http_methods(["POST"])
@check_params('userName', 'transactionId')
@handle_connection_error
def create_or_change_ldap_service(request):
    form = CreateOrChangeForm(request.POST)
    if not form.is_valid():
        error_msg = ""
        for k, v in form.errors.items():
            error_msg += "%s: %s\n" % (k, ", ".join(v))
        return HttpResponse(json.dumps({'success': True, 'msg': error_msg, 'form_error': True}),
                            content_type="application/json")

    user_name = form.cleaned_data['userName'].encode('utf-8').strip()
    service_name = form.cleaned_data['serviceName'].encode('utf-8').strip()
    transaction_id = form.cleaned_data['transactionId'].encode('utf-8').strip()

    logger.debug("Creating or changing LDAP service (%s) for user (%s), transaction ID: ", service_name, user_name,
                 transaction_id)
    ldap_client = LDAPClient()
    result = ldap_client.add_or_change_service(user_name, service_name, request_params=form.cleaned_data)
    if not result.get('user_exists', True):
        response = {
            'success': True,
            'msg': "User ({0}) has no profile on AAA".format(user_name),
            'user_exists': False
        }
        log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
        ldap_client.disconnect()
        return HttpResponse(json.dumps(response), content_type="application/json")

    response = {
        'success': result['action_result'],
        'msg': result.get('action_error_message'),
    }
    log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
    ldap_client.disconnect()
    return HttpResponse(json.dumps(response), content_type="application/json")


@require_http_methods(["POST"])
@check_params('userName', 'serviceName', 'transactionId')
@handle_connection_error
def remove_ldap_service(request):
    user_name = request.POST['userName'].encode('utf-8').strip()
    service_name = request.POST['serviceName'].encode('utf-8').strip()
    transaction_id = request.POST['transactionId'].encode('utf-8').strip()
    logger.debug("Removing LDAP service (%s) for user (%s), transaction ID: ", service_name, user_name,
                 transaction_id)
    ldap_client = LDAPClient()
    result = ldap_client.remove_service(user_name, service_name)
    response = {
        'success': result['action_result'],
        'msg': result.get('action_error_message')
    }
    log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
    ldap_client.disconnect()
    return HttpResponse(json.dumps(response), content_type="application/json")

@require_http_methods(["GET"])
@check_params('userName', 'transactionId')
@handle_connection_error
def get_ldap_services(request):
    user_name = request.GET['userName'].encode('utf-8').strip()
    transaction_id = request.GET['transactionId'].encode('utf-8').strip()
    ldap_client = LDAPClient()
    result = ldap_client.get_subscriber_services(user_name)
    services = result.get('services') or []
    response = {
        'success': result['action_result'],
        'msg': result.get('action_error_message'),
        'services': services
    }
    log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
    ldap_client.disconnect()
    return HttpResponse(json.dumps(response), content_type="application/json")


@require_http_methods(["GET"])
@check_params('userName', 'transactionId')
@handle_connection_error
def check_user_exists(request):
    user_name = request.GET['userName'].encode('utf-8').strip()
    transaction_id = request.GET['transactionId'].encode('utf-8').strip()
    ldap_client = LDAPClient()
    result = ldap_client.check_user_exists(user_name)
    response = {
        'success': False if result.get('user_exists') is None else True,
        'msg': result.get('action_error_message'),
        'user_exists': result.get('user_exists')
    }
    log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
    ldap_client.disconnect()
    return HttpResponse(json.dumps(response), content_type="application/json")


@require_http_methods(["GET"])
@check_params('userName', 'transactionId')
@handle_connection_error
def get_full_profile(request):
    user_name = request.GET['userName'].encode('utf-8').strip()
    transaction_id = request.GET['transactionId'].encode('utf-8').strip()
    ldap_client = LDAPClient()
    result = ldap_client.get_user_profile(user_name)
    response = {
        'success': result['action_result'],
        'msg': result.get('action_error_message'),
        'profile': result.get('profile')
    }
    log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
    ldap_client.disconnect()
    return HttpResponse(json.dumps(response), content_type="application/json")


@require_http_methods(["POST"])
@check_params('userName', 'transactionId')
@handle_connection_error
def delete_option_pack(request):
    user_name = request.POST['userName'].encode('utf-8').strip()
    transaction_id = request.POST['transactionId'].encode('utf-8').strip()
    ldap_client = LDAPClient()
    result = ldap_client.delete_option_pack(user_name)
    response = {
        'success': result['action_result'],
        'msg': result.get('action_error_message'),
    }
    log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
    ldap_client.disconnect()
    return HttpResponse(json.dumps(response), content_type="application/json")


class WifiSubscriber(APIView):
    def post(self, request, *args, **kwargs):
        serializer = WifiSubscriberSerializer(data=request.data)
        if not serializer.is_valid():
            return send_404_error_message(serializer)

        adsl_subscriber = serializer.validated_data['adslUserName'].encode('utf-8').strip()
        wifi_subscriber = ADSL_PATTERN.sub(r"\1@wifi.tedata.net.eg", adsl_subscriber)
        password = serializer.validated_data['password'].encode('utf-8').strip()
        service = serializer.validated_data['serviceName'].encode('utf-8').strip()
        transaction_id = serializer.validated_data['transactionId'].encode('utf-8').strip()

        logger.debug("Creating or changing WiFi service (%s) for user (%s), transaction ID: ", service, wifi_subscriber,
                     transaction_id)
        ldap_client = LDAPClient()
        result = ldap_client.add_wifi_service(adsl_subscriber, wifi_subscriber, service, password)

        if result.get('user_exists', False):
            response = {
                'success': True,
                'msg': "User ({0}) already has a WiFi profile on AAA".format(adsl_subscriber),
                'user_exists': True
            }
            return Response(response, status=status.HTTP_200_OK)

        response = {
            'success': result['action_result'],
            'msg': result.get('action_error_message'),
        }
        log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
        ldap_client.disconnect()
        return Response(response, status=status.HTTP_200_OK)


class WifiSubscriberDetails(APIView):
    def get(self, request, adslUserName, format=None):
        """returns wifi service assigned to user"""
        serializer = WifiSubscriberSerializer(data=request.query_params, is_get=True)
        if not serializer.is_valid():
            return send_404_error_message(serializer)

        adsl_subscriber = adslUserName.strip("/ ")
        wifi_subscriber = ADSL_PATTERN.sub(r"\1@wifi.tedata.net.eg", adsl_subscriber)
        transaction_id = serializer.validated_data['transactionId'].encode('utf-8').strip()

        ldap_client = LDAPClient()
        result = ldap_client.get_subscriber_services(wifi_subscriber)

        if not result['action_result']:
            response = {
                'success': result['action_result'],
                'msg': result.get('action_error_message')
            }
            return Response(response, status=status.HTTP_200_OK)

        if not result.get('user_exists', True):
            response = {
                'success': True,
                'msg': "User ({0}) has no WiFi profile on AAA".format(adsl_subscriber),
                'user_exists': False
            }
            return Response(response, status=status.HTTP_200_OK)


        services = result.get('services') or []
        response = {
            'success': result['action_result'],
            'msg': result.get('action_error_message'),
            'services': services
        }
        log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
        ldap_client.disconnect()
        return Response(response, status=status.HTTP_200_OK)

    def put(self, request, adslUserName, format=None):
        serializer = WifiSubscriberSerializer(data=request.data, is_update=True)
        if not serializer.is_valid():
            return send_404_error_message(serializer)

        adsl_subscriber = adslUserName.strip("/ ")
        wifi_subscriber = ADSL_PATTERN.sub(r"\1@wifi.tedata.net.eg", adsl_subscriber)
        service = serializer.validated_data['serviceName'].encode('utf-8').strip()
        transaction_id = serializer.validated_data['transactionId'].encode('utf-8').strip()


        logger.debug("Updating WiFi service (%s) for user (%s), transaction ID: ", service, wifi_subscriber,
                     transaction_id)
        ldap_client = LDAPClient()
        result = ldap_client.update_wifi_service(wifi_subscriber, service)
        if not result.get('user_exists', True):
            response = {
                'success': True,
                'msg': "User ({0}) has no WiFi profile on AAA".format(adsl_subscriber),
                'user_exists': False
            }
            return Response(response, status=status.HTTP_200_OK)

        response = {
            'success': result['action_result'],
            'msg': result.get('action_error_message'),
        }
        log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
        ldap_client.disconnect()
        return Response(response, status=status.HTTP_200_OK)

    def delete(self, request, adslUserName, format=None):
        serializer = WifiSubscriberSerializer(data=request.data, is_delete=True)
        if not serializer.is_valid():
            return send_404_error_message(serializer)

        adsl_subscriber = adslUserName.strip("/ ")
        wifi_subscriber = ADSL_PATTERN.sub(r"\1@wifi.tedata.net.eg", adsl_subscriber)
        transaction_id = serializer.validated_data['transactionId'].encode('utf-8').strip()
        ldap_client = LDAPClient()
        result = ldap_client.get_subscriber_services(wifi_subscriber)
        if not result['action_result']:
            response = {
                'success': result['action_result'],
                'msg': result.get('action_error_message'),
            }
            return Response(response, status=status.HTTP_200_OK)

        if not result.get('user_exists', True):
            response = {
                'success': True,
                'msg': "User ({0}) has no WiFi profile on AAA".format(adsl_subscriber),
                'user_exists': False
            }
            return Response(response, status=status.HTTP_200_OK)

        services = result.get('services')
        if not services:
            response = {
                'success': True,
                'msg': ""
            }
            return Response(response, status=status.HTTP_200_OK)
        service = services[0]
        logger.debug("Removing WiFi service (%s) for user (%s), transaction ID: ", service, wifi_subscriber,
                     transaction_id)

        result = ldap_client.remove_service(wifi_subscriber, service, is_adsl=False)
        response = {
            'success': result['action_result'],
            'msg': result.get('action_error_message')
        }
        if not response['success']:
            return Response(response, status=status.HTTP_200_OK)
        log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
        ldap_client.disconnect()
        return Response(response, status=status.HTTP_200_OK)