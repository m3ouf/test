import pycurl
import cStringIO
import uuid
import logging
import re
from datetime import datetime
from mw1_backend.configs import PYCURL_TIMEOUT
from dateutil import parser
from shared.models import BasicInfo, ProvisionPCRFService, BalanceAction, SubscribedService, \
    Topup, QuotaProfile, COA, PhysicalHomeWifiLog
from django.core.serializers.python import Serializer
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def get_ip(request):
    """
    extracts the IP address of the client .. it can detect if the client is behind a proxy or not.
    :param request: Django request object.
    :returns: string that represents the client's IP address.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    elif request.META.get('HTTP_X_REAL_IP'):
        ip = request.META.get('HTTP_X_REAL_IP')
    else:
        ip = request.META.get('REMOTE_ADDR')

    return ip


def exec_xml_request(url, post_data, basic_auth_val=None):
    """
    performs network connection with a remote server and returns a result.
    :param url: the url of the remote server.
    :param post_data: the data to be sent to the remote server.
    :returns: a string response from the remote server.
    """
    basic_auth_val = basic_auth_val or "cm9vdDpLZWxtZXRFbHNlcg=="
    buf = cStringIO.StringIO()
    #headers = ["Content-Type: text/xml"]
    headers = ["Content-Type: text/xml", 'Authorization: Basic %s' % basic_auth_val]
    curl = pycurl.Curl()

    curl.setopt(pycurl.HTTPHEADER, headers)
    curl.setopt(pycurl.POSTFIELDS, str(post_data))
    curl.setopt(pycurl.ENCODING, '')
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.WRITEFUNCTION, buf.write)
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.SSL_VERIFYPEER, 0)
    curl.setopt(pycurl.SSL_VERIFYHOST, 0)
    #curl.setopt(pycurl.VERBOSE, 1)
    curl.setopt(pycurl.CONNECTTIMEOUT, PYCURL_TIMEOUT)
    curl.setopt(pycurl.TIMEOUT, PYCURL_TIMEOUT)
    try:
        curl.perform()
    except pycurl.error, e:
        logger.error("Failed to connect to server on (%s), (%s)", url, e.args[1])
        buf.close()
        return {
            'error': True,
            'error_code': 500,
            'error_message': "Failed to connect to server on (%s), (%s)" % (url, e.args[1])
        }
    status_code = curl.getinfo(pycurl.HTTP_CODE)
    if status_code == 403:
        logger.error("Http 403 received .. check proxy settings.")
        return {
            'error': True,
            'error_message': 'Http 403 received .. check proxy settings.',
            'error_code': 501
        }
    response = buf.getvalue()
    buf.close()
    return {
        'error': False,
        'remote_response': response
    }


def convert_ntz_iso(dt):
    """converts time-zone aware datetime string to non-aware time-zone datetime object"""
    dt = parser.parse(dt)
    dt = dt.strftime('%Y-%m-%dT%H:%M:%S')
    return datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S')


def log_action(fn_name, request, response, transaction_id, start_coa=None, stop_coas=None):
    # extracts mandatory fields
    client_addr = get_ip(request)
    success = response['success']

    error_msg = response.get('msg')
    enable_db_logging = not bool(re.match(r"^get.*|^query.*|^check.*|^nst_get.*", fn_name, re.IGNORECASE))

    if fn_name.startswith("NetworkDeviceOperations"):
        device_ip = request.query_params.get('deviceIp') or request.data.get('deviceIp')
        community_id = request.query_params.get('communityId') or request.data.get('communityId')
        port_number = request.query_params.get('portNumber') or request.data.get('portNumber')
        card_number = request.query_params.get('cardNumber') or request.data.get('cardNumber')
        shelf_number = request.query_params.get('shelfNumber') or request.data.get('shelfNumber')
        enabled = response.get('enabled')

        logger.info("transaction id: {0}, service: {1}, client ip: {2}, success: {3}, error msg: {4}, device ip: {5}, "
                    "community id: {6}, port number: {7}, card number: {8}, shelf number: {9}, enabled: {10}".format(
            transaction_id, fn_name, client_addr, success, error_msg, device_ip, community_id, port_number,
            card_number, shelf_number, enabled))

        if enable_db_logging:
            PhysicalHomeWifiLog.objects.create(transaction_id=transaction_id, fn_name=fn_name, client_ip=client_addr,
                                               device_ip=device_ip, community_id=community_id, port_number=port_number,
                                               card_number=card_number, shelf_number=shelf_number, success=success,
                                               error_msg=error_msg, enabled=enabled)
        return

    function_name = fn_name
    transaction_id = transaction_id or str(uuid.uuid4())
    user_name = request.POST.get('userName') or request.GET.get('userName') or response.get("username") \
                    or request.GET.get("ipAddress") or request.POST.get("sessionId") or request.POST.get(
        'customerNumber') or \
                request.GET.get('customerNumber') or request.POST.get('adslUserName') or \
                request.parser_context.get('kwargs', {}).get('adslUserName')
    service_name = request.POST.get('serviceName')




    online = start_coa.get('online_session') if start_coa else None
    logger.info("type: BasicInfo, transaction ID: (%s), function name: (%s), client ip: (%s), success: (%s  ), "
                "error message: (%s): requested service: (%s), user name: (%s), online: (%s)",
                transaction_id, function_name,
                client_addr,
                success, error_msg,
                service_name,
                user_name,
                online
    )

    if enable_db_logging:
        basic_info = BasicInfo.objects.create(transaction_id=transaction_id, fn_name=function_name,
                                              client_ip=client_addr, success=success, error_msg=error_msg,
                                              request_service=service_name, user_name=user_name, online=online,
                                              fn_location='backend', key=request.user)

    # start date is mandatory for functions that take start date, and they are
    # pcrf functions ... we can safely add a new ProvisionPCRFService record
    if request.POST.get('startDate'):
        start_date = convert_ntz_iso(request.POST.get('startDate'))
        end_date = convert_ntz_iso(request.POST.get('endDate'))
        reset_consumed = True if request.POST.get('resetConsumedQuota') == 'true' else False
        logger.info(
            "type: ProvisionPCRFService, start date: (%s), end date: (%s), carry over: (%s), reset consumed: (%s), "
            "basic info: (%s)", start_date, end_date, request.POST.get('carryOver'), reset_consumed, basic_info.id
        )
        if enable_db_logging:
            ProvisionPCRFService.objects.create(start_date=start_date, end_date=end_date,
                                                carry_over=request.POST.get('carryOver'), reset_consumed=reset_consumed,
                                                basic_info=basic_info)

    try:
        if success and (request.GET.get('serviceType') == 'basic' or not request.GET.get('serviceType')):
            services = response['services']
            logger.info("Retrieved PCRF Services: (%s), basic info:(%s)", services, basic_info.id)
            if enable_db_logging:
                for service in services:
                    SubscribedService.objects.create(service_name=service, basic_info=basic_info)

    except:
        pass

    try:
        if success and (request.GET.get('serviceType') == 'topup'):
            topups = response['services']
            for topup in topups:
                logger.info("type: Topup, start date: (%s), remaining: (%s), basic amount: (%s), basic info: (%s)",
                            topup.startDate, topup.remaining, topup.basicAmount, basic_info.id
                )
                if enable_db_logging:
                    Topup.objects.create(start_date=topup['start_date'], remaining=topup['remaining'],
                                         basic_amount=topup['basic_amount'], basic_info=basic_info)

    except:
        pass

    try:
        if success:
            session = response['session'][0]['device_sessions']['services'][0]['serviceCode']
            if enable_db_logging:
                SubscribedService.objects.create(service_name=session, basic_info=basic_info)

    except:
        pass

    try:
        profile = response['profile']
        logger.info("type: QuotaProfile, start date: (%s), end date: (%s), basic quota: (%s), "
                    "service: (%s), total allowed quota: (%s)"
                    ", total consumed quota: (%s), total topup quota: (%s), remaining topup quota: (%s), "
                    "remaining topup quota: (%s), consumed topup quota: (%s), basic info: (%s)",
                    profile.startDate, profile.endDate, profile.basicQuota, profile.service,
                    profile.totalAllowedQuota, profile.totalConsumedQuota, profile.totalTopupQuota,
                    profile.remainingTopupQuota, profile.consumedTopupQuota, basic_info.id
        )
        if enable_db_logging:
            quota_profile = QuotaProfile.objects.create(start_date=profile['start_date'],
                                                        end_date=profile['end_date'],
                                                        basic_quota=profile['basic_amount'],
                                                        service=profile['account_balance_code'],
                                                        total_allowed_quota=profile['total_remaining'],
                                                        total_consumed_quota=profile['total_debited'], basic_info=basic_info
        )
        topups = response['topups']
        for topup in topups:
            logger.info("type: Topup, start date: (%s), remaining: (%s), basic amount: (%s), basic info: (%s)",
                        topup.startDate, topup.remaining, topup.basicAmount, basic_info.id
            )
            if enable_db_logging:
                Topup.objects.create(start_date=topup['start_date'], remaining=topup['remaining'],
                                     basic_amount=topup['basic_amount'], quota_profile=quota_profile)

    except:
        pass

    try:
        if success:
            debit_amount = request.POST['debitAmount']
            logger.info("type: BalanceAction, action type: debit, amount: (%s), basic info: (%s)",
                        debit_amount, basic_info.id
            )
            if enable_db_logging:
                BalanceAction.objects.create(action_type='debit', amount=debit_amount, basic_info=basic_info)

    except:
        pass

    try:
        if success:
            credit_amount = request.POST['creditAmount']
            logger.info("type: BalanceAction, action type: credit, amount: (%s), basic info: (%s)",
                        credit_amount, basic_info.id
            )
            if enable_db_logging:
                BalanceAction.objects.create(action_type='credit', amount=credit_amount, basic_info=basic_info)

    except:
        pass

    if stop_coas or start_coa:
        stop_coa = stop_coas[0] if stop_coas else None
        common_coa_info = start_coa or stop_coa

        coa_record = COA(basic_info=basic_info, session_ip=common_coa_info['session_ip'],
                         nas_ip=common_coa_info['nas_ip'], nas_port_id=common_coa_info['device_port'],
        )

        if start_coa:
            coa_record.started_service = start_coa['started_service']
            coa_record.started_coa_result = start_coa['coa_result']
            coa_record.started_coa_error_msg = start_coa.get('coa_error_message')
        if stop_coa:
            coa_record.stopped_service = stop_coa['stopped_service']
            coa_record.stopped_coa_result = stop_coa['coa_result']
            coa_record.stopped_coa_error_msg = stop_coa.get('coa_error_message')
        coa_record.save()
        logger.info("type: COA, session ip: (%s), nas ip: (%s), nas port id: (%s), started service: (%s), "
                    "started coa result: (%s), started coa error message: (%s), stopped service: (%s), "
                    "stopped coa result: (%s), stopped coa error message: (%s), basic info: (%s)",
                    coa_record.session_ip, coa_record.nas_ip, coa_record.nas_port_id, coa_record.started_service,
                    coa_record.started_coa_result, coa_record.started_coa_error_msg, coa_record.stopped_service,
                    coa_record.stopped_coa_result, coa_record.stopped_coa_error_msg, basic_info.id)
        for online_service in common_coa_info['online_services']:
            logger.info("type: OnlineService, service: (%s)", online_service)



def validate_date_string(**kwargs):
    """
    validates a date string to be in 'YYYY-MM-DD', if it is valid .. it Returns
    a date representation of the string, otherwise, it returns schema validation error.
    :param date_kind: startDate or endDate.
    """
    logger.debug("Validating start/end date")
    for k, v in kwargs.items():
        try:
            datetime.strptime(v, "%Y-%m-%d")  # check for the right format
            dt_obj = parser.parse(v)  # return the value in the required iso format
            logger.debug("Date string converted to a valid date object")
            return dt_obj
        except ValueError:
            logger.error("Date string (%s) didn't pass validation", v)
            return


def send_error_mail(msg, subject=u"MW Backend Error", level=logging.ERROR):
    error_logger = logging.getLogger("admin_logger")
    error = logger.makeRecord(
        logger.name, level, 0, 0,
        subject,
        None, None, "", None,
    )
    error.email_body = msg
    error_logger.handle(error)


class FlatSeralizer(Serializer):

    def __init__(self, *fields, **kwargs):
        self.fields = fields
        self.append_list=kwargs.get('append_list')
        super(FlatSeralizer, self).__init__()

    """"The situation is we need to serialize a given django model into a list of values.
    This class overrides the default behavior of django's serializer."""
    def end_object(self, obj):
        if self.append_list:
            self.objects.append([obj.__dict__[item].strftime('%Y-%m-%d %H:%M:%S') if type(obj.__dict__[item]) == datetime else obj.__dict__[item] for item in self.fields])
        else:
            self.objects.append(str(obj.__dict__[self.fields[0]]))


def send_404_error_message(serializer):
    error_msg = ""
    for k, v in serializer.errors.items():
        error_msg += "{0}: {1}\n".format(k, ", ".join(v))
    return Response({'error': True, 'message': error_msg}, status=status.HTTP_400_BAD_REQUEST)
