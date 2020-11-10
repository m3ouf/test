from django.views.decorators.http import require_http_methods
from client import AAAClient
from shared.decorators import check_params, handle_connection_error
from shared.common import log_action
from django.http import HttpResponse
from .forms import IpInputForm
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from shared.decorators import validate_inputs
from .serializers import PortalServiceMigrationSerializer
import json
import logging
import inspect

logger = logging.getLogger(__name__)



@require_http_methods(["GET"])
@check_params('ipAddress', 'transactionId')
@handle_connection_error
def get_user_by_ip(request):
    form = IpInputForm(request.GET)
    if not form.is_valid():
        error_msg = ""
        for k, v in form.errors.items():
            error_msg += k + ": " + ", ".join(v) + "\n"
        logger.error(error_msg)
        result = {
            'error': True,
            'error_message': error_msg
        }
        return HttpResponse(json.dumps(result), content_type="application/json")

    logger.debug("Getting username for ip (%s)", request.GET['ipAddress'])
    aaa_client = AAAClient()
    result = aaa_client.get_session_by_ip(request.GET['ipAddress'].encode('utf-8').strip())
    response = {
        'success': result['action_result'],
        'msg': result.get('action_error_message'),
        'username': result.get('username')
    }

    log_action(inspect.stack()[0][3], request, response, transaction_id=request.GET['transactionId'])
    return HttpResponse(json.dumps(response), content_type="application/json")



@require_http_methods(["GET"])
@check_params('userName', 'transactionId')
@handle_connection_error
def get_user_by_name(request):
    logger.debug("Getting ip address for username (%s)", request.GET['userName'])
    aaa_client = AAAClient()
    result = aaa_client.get_session_by_name(request.GET['userName'].encode('utf-8').strip())
    response = {
        'success': result['action_result'],
        'msg': result.get('action_error_message'),
        'ipAddress': result.get('IpAddress')
    }

    log_action(inspect.stack()[0][3], request, response, transaction_id=request.GET['transactionId'])
    return HttpResponse(json.dumps(response), content_type="application/json")



@require_http_methods(["POST"])
@check_params('userName', 'serviceName', 'transactionId')
@handle_connection_error
def send_start_coa(request):
    subscriber_id = request.POST['userName'].encode('utf-8').strip()
    service_name = request.POST['serviceName'].encode('utf-8').strip()
    logger.debug("Sending Start Coa for Subscriber (%s), Service (%s)", subscriber_id, service_name)
    aaa_client = AAAClient()
    result = aaa_client.send_start_coa(subscriber_id, service_name)
    response = {
        'success': result['action_result'],
        'msg': result.get('action_error_message'),
    }
    log_action(inspect.stack()[0][3], request, response, start_coa=result.get('coa_result'),
               transaction_id=request.POST['transactionId'])
    return HttpResponse(json.dumps(response), content_type="application/json")



@require_http_methods(["POST"])
@check_params('userName', 'serviceName', 'transactionId')
@handle_connection_error
def send_stop_coa(request):
    subscriber_id = request.POST['userName'].encode('utf-8').strip()
    service_name = request.POST['serviceName'].encode('utf-8').strip()
    logger.debug("Sending Stop Coa for Subscriber (%s), Service (%s)", subscriber_id, service_name)
    aaa_client = AAAClient()
    result = aaa_client.send_stop_coa(subscriber_id, service_name)
    response = {
        'success': result['action_result'],
        'msg': result.get('action_error_message'),
    }

    log_action(inspect.stack()[0][3], request, response, stop_coas=[result['coa_result']]
               if result.get('coa_result') else None,
               transaction_id=request.POST['transactionId'])
    return HttpResponse(json.dumps(response), content_type="application/json")


@require_http_methods(["GET"])
@check_params('userName', 'transactionId')
@handle_connection_error
def get_full_session(request):
    logger.debug("Getting full session for username (%s)", request.GET['userName'])
    aaa_client = AAAClient()
    result = aaa_client.get_full_session(request.GET['userName'].encode('utf-8').strip())
    sessions = result.get('sessions')

    formatted_sessions = []

    if sessions:
        for session in sessions:
            formatted_session = {}
            for k, v in session.items():
                formatted_session[k.lower().replace('-', '_')] = v

            formatted_sessions.append(formatted_session)
    response = {
        'success': result['action_result'],
        'msg': result.get('action_error_message'),
        'sessions': formatted_sessions
    }

    log_action(inspect.stack()[0][3], request, response, transaction_id=request.GET['transactionId'])
    return HttpResponse(json.dumps(response), content_type="application/json")


class PortalServiceMigrationView(APIView):

    def __str__(self):
        return "PortalServiceMigration"

    @validate_inputs(PortalServiceMigrationSerializer)
    def post(self, request, format=None, **kwargs):
        serializer = kwargs['serializer']
        framed_ip_address = serializer.validated_data.get('framedIpAddress')
        subscriber_id = serializer.validated_data.get('subscriberId')
        service_name = serializer.validated_data['serviceName']
        operation = serializer.validated_data['operation']
        transaction_id = serializer.validated_data.get('transactionId')
        if operation == 'start' and subscriber_id is None:
            return Response({'success': False, 'msg': 'SubscriberId is required'})
        elif operation == 'stop' and framed_ip_address is None:
            return Response({'success': False, 'msg': 'framedIpAddress is required'})

        aaa_client = AAAClient()
        if operation == 'start':
            result = aaa_client.start_redirect_coa(subscriber_id, service_name)
        elif operation == 'stop':
            result = aaa_client.stop_redirect_coa(framed_ip_address, service_name)

        logger.info(result)
        return Response({'success': True, 'coa_result': result})