from django.views.decorators.http import require_http_methods
from shared.decorators import check_params
from shared.common import log_action
from django.http import HttpResponse
from mw1_backend.configs import IPTV_USER, IPTV_PASS
from client import IPTVClient
import json
import re
import inspect

def _release_session_and_return(session_id, request, fn_name, return_response, transaction_id):
    client = IPTVClient()
    result = client.release_iptv_session(session_id)
    if not result['action_result']:
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
        }
        log_action(fn_name, request, response, transaction_id=transaction_id)

    log_action(fn_name, request, return_response, transaction_id=transaction_id)
    return HttpResponse(json.dumps(return_response), mimetype="application/json")



@require_http_methods(["POST"])
@check_params('customerNumber', 'packageName', 'macAddress', 'transactionId')
def create_customer(request):
    client = IPTVClient()
    customer_number = request.POST['customerNumber']
    package_name = request.POST['packageName']
    mac_address = request.POST['macAddress']
    transaction_id = request.POST['transactionId']
    result = client.create_iptv_session()
    if not result['action_result']:
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
            }
        log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
        return HttpResponse(json.dumps(response), mimetype="application/json")
    session_id = result['session_id']

    subscription_result = client.fetch_tv_subscriptions(session_id, customer_number)
    if subscription_result['action_result']:
        response = {
            'success': False,
            'msg': 'Subscriber exists.'
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)

    result = client.create_customer(session_id=session_id, customer_number=customer_number)

    if not result['action_result'] and not result['action_error_message'].endswith('already exists. '):

        response = {
            'success': False,
            'msg': result.get('action_error_message'),
            }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)
    result = client.order_tv_subscription(session_id, customer_number, package_name, mac_address)
    if not result['action_result']:
        client.remove_iptv_customer(session_id, customer_number)
        if "STB" in result['action_error_message'] and "is already on subscription" in result['action_error_message']:
            order_id = re.findall("[\d]{5}", result['action_error_message'])[0]
            single_subscription_result = client.fetch_tv_subscription(session_id, order_id)
            if single_subscription_result['action_result']:
                error_msg = "STB already assigned to subscriber (%s)" % \
                            single_subscription_result['subscription'].customerNumber
            else:
                error_msg = "STB already assigned to another subscriber"
            response = {
                'success': False,
                'msg': error_msg,
                }
            return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                               return_response=response, transaction_id=transaction_id)

        response = {'success': False, 'msg': result.get('action_error_message'), }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)

    response = {'success': True, 'msg': ""}
    return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3], return_response=response,
                     transaction_id=transaction_id)



@require_http_methods(["POST"])
@check_params('customerNumber', 'transactionId')
def block_iptv_subscription(request):
    client = IPTVClient()
    customer_number = request.POST['customerNumber']
    result = client.create_iptv_session()
    transaction_id = request.POST['transactionId']
    if not result['action_result']:
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
        }
        log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
        return HttpResponse(json.dumps(response), mimetype="application/json")
    session_id = result['session_id']

    result = client.fetch_tv_subscriptions(session_id, customer_number)
    if not result['action_result']:
        response = {
            'success':  False,
            'msg': result.get('action_error_message'),
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)
    if not result['subscription'][0] or not result['subscription'][0].tvSubscriptionId:
        response = {
            'success': False,
            'msg': "Subscriber (%s) has no IPTV subscriptions." % customer_number,
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)
    subscription_id = result['subscription'][0].tvSubscriptionId
    result = client.block_tv_subscription(session_id, subscription_id)
    if not result['action_result']:
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)

    response = {'success': True, 'msg': ""}
    return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                       return_response=response, transaction_id=transaction_id)



@require_http_methods(["POST"])
@check_params('customerNumber', 'transactionId')
def unblock_iptv_subscription(request):

    client = IPTVClient()
    customer_number = request.POST['customerNumber']
    result = client.create_iptv_session()
    transaction_id = request.POST['transactionId']
    if not result['action_result']:
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
        }
        log_action(inspect.stack()[0][3], request, response, transaction_id)
        return HttpResponse(json.dumps(response), mimetype="application/json")
    session_id = result['session_id']


    result = client.fetch_tv_subscriptions(session_id, customer_number)
    if not result['action_result']:
        response = {
            'success':  False,
            'msg': result.get('action_error_message'),
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)
    if not result['subscription'][0] or not result['subscription'][0].tvSubscriptionId:
        response = {
            'success': False,
            'msg': "Subscriber (%s) has no IPTV subscriptions." % customer_number,
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)
    subscription_id = result['subscription'][0].tvSubscriptionId
    result = client.unblock_tv_subscription(session_id, subscription_id)
    if not result['action_result']:
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)

    response = {'success': True, 'msg': ""}
    return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                       return_response=response, transaction_id=transaction_id)



@require_http_methods(["POST"])
@check_params('customerNumber', 'packageName', 'transactionId')
def add_or_change_iptv_package(request):
    client = IPTVClient()
    customer_number = request.POST['customerNumber']
    package_name = request.POST['packageName']
    transaction_id = request.POST['transactionId']
    result = client.create_iptv_session()
    if not result['action_result']:
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
        }
        log_action(inspect.stack()[0][3], request, response, transaction_id)
        return HttpResponse(json.dumps(response), mimetype="application/json")
    session_id = result['session_id']
    result = client.fetch_tv_subscriptions(session_id, customer_number)
    if not result['action_result']:
        response = {
            'success':  False,
            'msg': result.get('action_error_message'),
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)
    if not result['subscription'][0] or not result['subscription'][0].tvSubscriptionId:
        response = {
            'success': False,
            'msg': "Subscriber (%s) has no IPTV subscriptions." % customer_number,
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)
    subscription_id = result['subscription'][0].tvSubscriptionId
    result = client.add_or_change_package(session_id, subscription_id, package_name)
    if not result['action_result']:
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)

    response = {'success': True, 'msg': ''}
    return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)



@require_http_methods(["POST"])
@check_params('customerNumber', 'macAddress', 'transactionId')
def add_or_change_iptv_stb(request):
    client = IPTVClient()
    customer_number = request.POST['customerNumber']
    mac_address = request.POST['macAddress']
    transaction_id = request.POST['transactionId']

    result = client.create_iptv_session()
    if not result['action_result']:
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
        }
        log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
        return HttpResponse(json.dumps(response), mimetype="application/json")
    session_id = result['session_id']
    result = client.fetch_tv_subscriptions(session_id, customer_number)
    if not result['action_result']:
        response = {
            'success':  False,
            'msg': result.get('action_error_message'),
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                               return_response=response, transaction_id=transaction_id)
    if not result['subscription'][0] or not result['subscription'][0].tvSubscriptionId:
        response = {
            'success': False,
            'msg': "Subscriber (%s) has no IPTV subscriptions." % customer_number,
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)
    subscription_id = result['subscription'][0].tvSubscriptionId

    result = client.add_or_replace_stb(session_id, subscription_id, customer_number, mac_address)
    if not result['action_result']:
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                               return_response=response, transaction_id=transaction_id)

    response = {'success': True, 'msg': ''}
    return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)



@require_http_methods(["GET"])
@check_params('customerNumber', 'transactionId')
def query_user_info(request):
    client = IPTVClient()
    customer_number = request.GET['customerNumber']
    transaction_id = request.GET['transactionId']
    result = client.create_iptv_session()
    if not result['action_result']:
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
        }
        log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
        return HttpResponse(json.dumps(response), mimetype="application/json")
    session_id = result['session_id']

    result = client.fetch_tv_subscriptions(session_id, customer_number)

    if not result['action_result']:
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)

    if not result['subscription'][0] or not result['subscription'][0].tvSubscriptionId:
        response = {
            'success': False,
            'msg': "Subscriber (%s) has no IPTV subscriptions." % customer_number,
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)
    subscription = result['subscription'][0]
    status = subscription.status
    package = subscription.packages[0].name if len(subscription.packages) else None
    stb = subscription.stbs[0].macAddress if hasattr(subscription, 'stbs') else None

    response = {'success': True, 'msg': '', 'status': status, 'package': package, 'stb': stb}
    return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)


@require_http_methods(["POST"])
@check_params('customerNumber', 'macAddress', 'transactionId')
def remove_iptv_stb(request):
    client = IPTVClient()
    customer_number = request.POST['customerNumber']
    mac_address = request.POST['macAddress']
    transaction_id = request.POST['transactionId']
    result = client.create_iptv_session()
    if not result['action_result']:
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
        }
        log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
        return HttpResponse(json.dumps(response), mimetype="application/json")
    session_id = result['session_id']
    result = client.fetch_tv_subscriptions(session_id, customer_number)
    if not result['action_result']:
        response = {
            'success':  False,
            'msg': result.get('action_error_message'),
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)
    if not result['subscription'][0].tvSubscriptionId:
        response = {
            'success': False,
            'msg': "Subscriber (%s) has no IPTV subscriptions." % customer_number,
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)

    subscription_id = result['subscription'][0].tvSubscriptionId
    result = client.remove_stb(session_id, subscription_id, customer_number, mac_address)
    if not result['action_result']:
        if "STB" in result['action_error_message'] and "does not exist on subscription" \
        in result['action_error_message']:
            response = {
                'success': False,
                'msg': "STB (%s) is not assigned to subscriber (%s)" % (mac_address, customer_number),
            }
            return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                               return_response=response, transaction_id=transaction_id)
        response = {
            'success': False,
            'msg': result.get('action_error_message'),
        }
        return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                           return_response=response, transaction_id=transaction_id)

    response = {'success': True, 'msg': ''}
    return _release_session_and_return(session_id, request, fn_name=inspect.stack()[0][3],
                                       return_response=response, transaction_id=transaction_id)