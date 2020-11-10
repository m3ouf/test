import datetime
import json
import operator
import crypt
import logging
import calendar
import time
import re
import random
import mw1_backend.configs
from mw1_backend.configs import ANALYTICS_STARTING_MONTH_DIFF
from shared.models import BasicInfo, OnlineDailyUsage, ProvisionPCRFService
from ldap_backend.models import SBRProduct
from pcrf_backend.models import PCRFProfileLog, TopupLog
from django.http import HttpResponse
from django.db.models import Q, Sum
from django.db import Error
from django.core.exceptions import ObjectDoesNotExist
from shared.decorators import handle_connection_error
from backends import get_subscriber_logs, get_ip_by_username, get_subscriber_database_logs
from ldap_backend.ldap_profile import LDAPClient
from pcrf_backend.views import get_profile as pcrf_get_profile, get_services as pcrf_get_services, \
    get_session as pcrf_get_session, remove_user as pcrf_remove_user, \
    create_or_change_service as pcrf_create_or_change_service, \
    add_topup, debit_user
from ldap_backend.views import get_full_profile as get_full_ldap_profile, check_user_exists as check_ldap_user_exists, \
    remove_ldap_service as ldap_remove_service, create_or_change_ldap_service as ldap_create_or_change_service,\
    delete_option_pack as ldap_delete_optionpack_subscriber
from aaa_backend.views import get_user_by_ip, get_user_by_name, get_full_session as get_full_aaa_session, send_stop_coa, send_start_coa
from auth.utils import token_required
from shared.decorators import permission_required
import MySQLdb
from shared.common import validate_date_string
from django.db import connection, connections
from .forms import SBRDailyUsageForm, CyberCrimeForm, WifiReportForm, WifiVenueForm
from .models import CyberCrimeSession, SBRDailyUsage, NASTool
from dateutil.relativedelta import relativedelta
from django.views.decorators.http import require_http_methods
from shared.common import FlatSeralizer
from dpi_backend.views import get_dpi_usage
from wifi.models import WiFiLogs

logger = logging.getLogger(__name__)


def construct_db_query(request, basic_query, ordering_col, default_ordering, or_queries, model, database='default'):
    request_start = int(request.GET.get('iDisplayStart'))
    request_length = int(request.GET.get('iDisplayLength'))
    s_echo = request.GET.get('sEcho')

    ordering_arr = {
        'asc': '',
        'desc': '-'
    }

    ordering_param = ordering_arr.get(request.GET.get('sSortDir_0'), '-') + ordering_col.get(
        request.GET.get('iSortCol_0'), default_ordering)

    if or_queries:
        info = model.objects.using(database).filter(reduce(operator.or_, or_queries), **basic_query).order_by(
            ordering_param)
    else:
        info = model.objects.using(database).filter(**basic_query).order_by(ordering_param)
    count = info.count()
    if request_length > 0:
        info = info[request_start: request_start + request_length]

    result = {
        "sEcho": s_echo,
        "iTotalRecords": count,
        "iTotalDisplayRecords": count,
        "aaData": [],
    }
    return info, result


@token_required
# @permission_required("nst.get_basic_info")
def get_basic_info(request):
    try:
        user_name = request.GET['userName'].encode('utf-8').strip()
        transaction_id = request.GET['transactionId'].encode('utf-8').strip()
        logger.debug("Getting session for user (%s), transaction id: (%s)", user_name, transaction_id)
        query = {'user_name': user_name}
        query_result = BasicInfo.objects.filter(**query)
        result = {'data': []}
        for i in query_result:
            aaData = [
                i.transaction_id,
                i.fn_name,
                i.fn_location,
                i.api_access_time.strftime("%Y-%m-%d %H:%M:%S") if i.api_access_time else "",
                i.access_time.strftime("%Y-%m-%d %H:%M:%S") if i.access_time else "",
                i.client_ip,
                i.request_service,
                i.success,
                i.error_msg,
                i.error_code
            ]
            try:
                if i.provisionpcrfservice:
                    aaData.append(i.id)
            except:
                aaData.append(False)

            result['data'].append(aaData)

        response = {
            'success': True,
            'msg': 'Request completed successfully!',
            'basic_info': result.get('data')
        }
    except:
        response = {
            'success': False,
            'msg': 'An Error happened!',
        }
    # log_action('get_basic_info', request, response, transaction_id=transaction_id)
    return HttpResponse(json.dumps(response), mimetype="application/json")


@token_required
# @permission_required("nst.get_pcrf_logs")
def get_pcrf_logs(request):
    try:
        user_name = request.GET['userName'].encode('utf-8').strip()
        transaction_id = request.GET['transactionId'].encode('utf-8').strip()
        logger.debug("Getting session for user (%s), transaction id: (%s)", user_name, transaction_id)
        query = {'username': user_name}
        query_result = PCRFProfileLog.objects.filter(**query)
        result = {'data': []}
        for i in query_result:
            aaData = [
                i.service_name,
                i.start_date.strftime("%Y-%m-%d %H:%M:%S") if i.start_date else "",
                i.end_date.strftime("%Y-%m-%d %H:%M:%S") if i.end_date else "",
                i.total_debited,
                i.total_amount,
                i.original_amount,
                i.amount,
                i.topuplog_set.count(),
                i.id
            ]
            try:
                if i.provisionpcrfservice:
                    aaData.append(i.id)
            except:
                aaData.append(False)

            result['data'].append(aaData)

        response = {
            'success': True,
            'msg': 'Request completed successfully!',
            'pcrf_logs': result.get('data')
        }
    except:
        response = {
            'success': False,
            'msg': 'An Error happened!',
        }
    # log_action('get_basic_info', request, response, transaction_id=transaction_id)
    return HttpResponse(json.dumps(response), mimetype="application/json")


def get_topups_logs(request, pcrf_log_id):
    ordering_col = {
        '1': 'credit_id',
        '2': 'start_date',
        '3': 'basic_amount',
        '4': 'remaining',
    }
    query = {'pcrf_profile': pcrf_log_id}

    or_queries = []

    info, result = construct_db_query(request, query, ordering_col, 'start_date', or_queries,
                                      TopupLog)

    for i in info:
        result['aaData'].append([
            i.credit_id,
            i.start_date.strftime("%Y-%m-%d %H:%M:%S") if i.start_date else "",
            i.basic_amount,
            i.remaining,
        ])
    return HttpResponse(json.dumps(result), content_type='application/json')


def get_provision_pcrf_info(request, basic_info_id):
    ordering_col = {
        '1': 'start_date',
        '2': 'end_date',
        '3': 'carry_over',
        '4': 'reset_consumed',
    }
    query = {'basic_info': basic_info_id}

    or_queries = []

    info, result = construct_db_query(request, query, ordering_col, 'start_date', or_queries,
                                      ProvisionPCRFService)

    for i in info:
        result['aaData'].append([
            i.start_date.strftime("%Y-%m-%d %H:%M:%S") if i.start_date else "",
            i.end_date.strftime("%Y-%m-%d %H:%M:%S") if i.start_date else "",
            i.carry_over,
            i.reset_consumed,
        ])
    return HttpResponse(json.dumps(result), content_type='application/json')


def provision_pcrf_info(request, basic_info_id):
    html = """
    <div class="modal-content">
        <div class="modal-header">
            <button type="button" class="close" data-dismiss="modal" aria-hidden="true"></button>
            <h3 id="myModalLabel">Provision PCRFInfo </h3>
        </div>
        <div class="modal-body">
            <table cellpadding="0" cellspacing="0" border="0" class="table table-striped"
                   id="provision_pcrf_info_table" align="center">
                <thead>
                <tr>
                    <th>Start Date</th>
                    <th>End Date</th>
                    <th>Carry Over</th>
                    <th>Reset Consumed</th>
                </tr>
                </thead>
                <tbody>
                </tbody>
                <tfoot>
                <tr>
                    <th>Start Date</th>
                    <th>End Date</th>
                    <th>Carry Over</th>
                    <th>Reset Consumed</th>
                </tr>
                </tfoot>
            </table>
        </div>
        <div class="modal-footer">
            <button class="btn" data-dismiss="modal" aria-hidden="true">Close</button>
        </div>

        <script>
            $('#provision_pcrf_info_table').dataTable().fnDestroy();
            var attrs = {
                "bJQueryUI" : true,
                "bAutoWidth" : false,
                "bProcessing" : true,
                "bServerSide" : true,
                "sAjaxSource" : 'http://{0}:{1}/nst/get_provision_pcrf_info/'.format(BACKEND_HOST, BACKEND_PORT) + %s
                + '/',
                "sPaginationType" : "full_numbers",
                "iDisplayLength" : 10, "aLengthMenu" : [[10, 20, 50, 100, -1], [10, 20, 50, 100, "All"]],
                "sDom": '<"clear"><"row"<"col-xs-4"f><"col-xs-4"CR><"col-xs-3"l>r>'+
                    't'+
                    '<"row"<"col-xs-4"i><"col-xs-8"p>>',
                "oLanguage": {
                    "sSearch": "",
                    "sLengthMenu": "_MENU_ Records/Page",
                },
            };
            $('#provision_pcrf_info_table').dataTable(attrs);
            $(".dataTables_length select").addClass("form-control input-sm");

        </script>
    </div>

    """ % basic_info_id
    return HttpResponse(html)


def topups_logs(_, pcrf_log_id):
    html = """
    <div class="modal-content">
        <div class="modal-header">
            <button type="button" class="close" data-dismiss="modal" aria-hidden="true"></button>
            <h3 id="myModalLabel">Topups</h3>
        </div>
        <div class="modal-body">
            <table cellpadding="0" cellspacing="0" border="0" class="table table-striped"
                   id="topups_info_table" align="center">
                <thead>
                <tr>
                    <th>ID</th>
                    <th>Start Date</th>
                    <th>Basic Amount</th>
                    <th>Remaining</th>
                </tr>
                </thead>
                <tbody>
                </tbody>
                <tfoot>
                <tr>
                    <th colspan="2" class="text-right">Total</th>
                    <th>Basic Amount</th>
                    <th>Remaining</th>
                </tr>
                </tfoot>
            </table>
        </div>
        <div class="modal-footer">
            <button class="btn" data-dismiss="modal" aria-hidden="true">Close</button>
        </div>

        <script>
            $('#topups_info_table').dataTable().fnDestroy();
            function fromBytesToHumanReadable(input) {
                if (input == 0) {
                    return "0 Bytes"
                }
                if (input) {
                    var gigs = 0;
                    var bytesMinusGigs = 0;
                    var megs = 0;
                    var bytesMinusMegs = 0;
                    var kilos = 0;
                    var bytesMinusKilos = 0;
                    gigs = Math.floor(input / 1073741824)
                    bytesMinusGigs = input - (gigs * 1073741824)
                    megs = Math.floor(bytesMinusGigs / 1048576)
                    bytesMinusMegs = bytesMinusGigs - megs * 1048576
                    kilos = Math.floor(bytesMinusMegs / 1024)
                    bytesMinusKilos = Math.round((bytesMinusMegs - (kilos * 1024)) * 10000) / 10000
                    return gigs + " GB " + megs + " MB " + kilos + " KB " + bytesMinusKilos + " Bytes";
                }
            }
            var attrs = {
                "bJQueryUI" : true,
                "bAutoWidth" : false,
                "bProcessing" : true,
                "bServerSide" : true,
                "sAjaxSource" : 'http://{0}:{1}/nst/get_topups_logs/'.format(BACKEND_HOST, BACKEND_PORT) + %s + '/',
                "sPaginationType" : "full_numbers",
                "iDisplayLength" : 10, "aLengthMenu" : [[10, 20, 50, 100, -1], [10, 20, 50, 100, "All"]],
                "sDom": '<"clear"><"row"<"col-xs-4"f><"col-xs-4"CR><"col-xs-3"l>r>'+
                    't'+
                    '<"row"<"col-xs-4"i><"col-xs-8"p>>',
                "oLanguage": {
                    "sSearch": "",
                    "sLengthMenu": "_MENU_ Records/Page",
                },
                "columnDefs": [
                    {
                        "targets": [2, 3],
                        "render": function(data, type, row) {
                            return fromBytesToHumanReadable(data);
                        }
                    }
                ],
                "footerCallback": function ( row, data, start, end, display ) {
                    var api = this.api(), data;
                    var total=0;
                    var pageTotal=0;
                    // Remove the formatting to get integer data for summation
                    var intVal = function ( i ) {
                        return typeof i === 'string' ?
                            i.replace(/[\$,]/g, '')*1 :
                            typeof i === 'number' ?
                                i : 0;
                    };
                    // Upload Column
                    // Total over all pages
                    data = api.column( 3 ).data();
                    total = data.length ?
                        data.reduce( function (a, b) {
                                return intVal(a) + intVal(b);
                        } ) : 0;
                    // Update footer
                    $( api.column( 3 ).footer() ).html(
                        fromBytesToHumanReadable(total)
                    );
                    // Upload Column
                    // Total over all pages
                    data = api.column( 2 ).data();
                    total = data.length ?
                        data.reduce( function (a, b) {
                                return intVal(a) + intVal(b);
                        } ) : 0;
                    // Update footer
                    $( api.column( 2 ).footer() ).html(
                        fromBytesToHumanReadable(total)
                    );
                }
            }
            $('#topups_info_table').dataTable(attrs);
            $(".dataTables_length select").addClass("form-control input-sm");

        </script>
    </div>

    """ % pcrf_log_id
    return HttpResponse(html)


@handle_connection_error
@token_required
@permission_required("nst.get_allowed_services")
def get_allowed_services(request):
    try:
        serializer = FlatSeralizer('service_name')
        if request.GET.get("service_type") == 'capped':
            services = serializer.serialize(SBRProduct.objects.using('service').
                                            filter(Q(service_name__icontains='cap') |
                                                   Q(service_name__icontains='tal2a') |
                                                   Q(service_name__startswith='D') |
                                                   Q(service_name__icontains='quota')))
        elif request.GET.get("service_type") == 'unlimited':
            services = serializer.serialize(SBRProduct.objects.using('service').
                                            filter(~Q(service_name__icontains='cap') &
                                                   ~Q(service_name__icontains='tal2a') &
                                                   ~Q(service_name__icontains='quota') &
                                                   Q(service_name__startswith='MONTHLY_')))
        elif request.GET.get("service_type") == 'all':
            serializer = FlatSeralizer('id', 'service_name', append_list=True)
            services = [[service] for service in serializer.serialize(SBRProduct.objects.using('service').all())]

        else:
            response = {
                'error': True,
                'error_message': "Illegal Service type."
            }
            return HttpResponse(json.dumps(response), content_type="application/json", status=200)

        response = {
            'error': False,
            'services': services
        }
        return HttpResponse(json.dumps(response), content_type="application/json", status=200)
    except Error as e:
        logger.error("Error while querying database for services, %s ", str(e))
        response = {
            'error': True,
            'error_message': "Couldn't retrieve services .. please contact service administrator."
        }
        return HttpResponse(json.dumps(response), content_type="application/json", status=200)


@handle_connection_error
@token_required
@permission_required("nst.subscriber_logs")
def subscriber_logs(request):
    username = request.GET.get('userName', "").encode("utf-8").strip()
    result = get_subscriber_logs(username)
    response = {
        "host1_results": result[0],
        "host2_results": result[1],
        "host3_results": result[2],
        "host4_results": result[3],
        'backup_host_results': result[4]
    }
    return HttpResponse(json.dumps(response), content_type="application/json", status=200)


@handle_connection_error
@token_required
@permission_required("nst.subscriber_logs")
def subscriber_database_logs(request):
    username = request.GET.get('userName', "").encode("utf-8").strip()
    nas_port = request.GET.get('nasPort', "").encode("utf-8").strip()
    try:
        if nas_port.startswith("NAS-Port-Id"):
            nas_port = re.findall(r'NAS-Port-Id = "(.+)"|"(.+)', nas_port)[0]
            nas_port = "".join(nas_port)
    except IndexError:
        results = {
                'error': True,
                'error_message': 'You should submit a valid NAS Port ID.',
                'logs': []
            }
        return HttpResponse(json.dumps(results), content_type="application/json", status=200)
    nas_port = nas_port.strip('" ')
    try:
        start_date = request.GET.get('startDate', "").encode("utf-8").strip().split("-")
        if not start_date == ['']:
            start_date = datetime.date(int(start_date[0]),
                                       int(start_date[1]),
                                       int(start_date[2]))
        else:
            start_date = datetime.date(datetime.datetime.today().year, datetime.datetime.today().month,datetime.datetime.today().day)
    except:
        start_date = datetime.date(datetime.datetime.today().year, datetime.datetime.today().month,datetime.datetime.today().day)
    end_date = datetime.datetime.today()
    dates_diff = ",".join(_date_range(start_date, end_date))
    if username:
        result = get_subscriber_database_logs(start_date, dates_diff, username=username)
    elif nas_port:
        result = get_subscriber_database_logs(start_date, dates_diff, nas_port=nas_port)
    return HttpResponse(json.dumps(result), content_type="application/json", status=200)


@handle_connection_error
@token_required
@permission_required("nst.remove_allowed_service")
def remove_allowed_service(request):
    try:
        allowed_service = request.POST.get('serviceName')

        SBRProduct.objects.using('sbr').filter(service_name=allowed_service).delete()
        response = {
            'error': False,
            'error_message': ''
        }
    except Error as e:
        logger.error("Error while deleting service %s from db, %s", allowed_service, str(e))
        response = {
            'error': True,
            'error_message': "Couldn't remove services .. please contact service administrator."
        }

    return HttpResponse(json.dumps(response), content_type="application/json", status=200)


@handle_connection_error
@token_required
@permission_required("nst.add_allowed_service")
def add_allowed_service(request):
    allowed_service = request.POST.get('serviceName')
    try:
        SBRProduct.objects.using('sbr').get_or_create(service_name=allowed_service)
        response = {
            'error': False,
            'error_message': ''
        }

    except Error as e:
        logger.error("Error while inserting service %s into database, %s", allowed_service, str(e))
        response = {
            'error': True,
            'error_message': "Couldn't add services .. please contact service administrator."
        }

    return HttpResponse(json.dumps(response), content_type="application/json", status=200)


@handle_connection_error
@token_required
@permission_required("nst.decrypt_password")
def decrypt_password(request):
    """
    Checks that a given username exists on LDAP backend, and provided user is correct.
    """
    user_name = request.GET.get('userName')
    password = request.GET.get('password')
    ldap_client = LDAPClient()
    result = ldap_client.get_user_profile(user_name)
    try:
        c_password = result['profile'][0][1]['radiususerPassword'][0][7:]
        password_match = crypt.crypt(password, c_password) == c_password
        result = {'success': password_match}
    except KeyError:
        logger.error("Error while quering user %s LDAP Password" % user_name)
        result = {'success': False}
    return HttpResponse(json.dumps(result), content_type='application/json')


# next views are wrappers for other views

@handle_connection_error
#@token_required
#@permission_required("nst.nst_get_full_ldap_profile")
def nst_get_full_ldap_profile(request):
    return get_full_ldap_profile(request)


@handle_connection_error
@token_required
@permission_required("nst.nst_get_pcrf_profile")
def nst_get_pcrf_profile(request):
    return pcrf_get_profile(request)


@handle_connection_error
@token_required
@permission_required("nst.nst_get_pcrf_services")
def nst_get_pcrf_services(request):
    return pcrf_get_services(request)


@handle_connection_error
@token_required
@permission_required("nst.nst_check_ldap_user_exists")
def nst_check_ldap_user_exists(request):
    return check_ldap_user_exists(request)


@handle_connection_error
@token_required
@permission_required("nst.nst_get_aaa_user_by_name")
def nst_get_aaa_user_by_name(request):
    return get_user_by_name(request)


@handle_connection_error
@token_required
@permission_required("nst.nst_get_aaa_user_by_ip")
def nst_get_aaa_user_by_ip(request):
    return get_user_by_ip(request)


@handle_connection_error
@token_required
@permission_required("nst.nst_get_pcrf_session")
def nst_get_pcrf_session(request):
    return pcrf_get_session(request)


@handle_connection_error
@token_required
@permission_required("nst.nst_get_aaa_full_sessions")
def nst_get_aaa_full_sessions(request):
    return get_full_aaa_session(request)


@handle_connection_error
@token_required
@permission_required("nst.remove_ldap_service")
def remove_ldap_service(request):
    return ldap_remove_service(request)


@token_required
@permission_required("nst.remove_pcrf_user")
def remove_pcrf_user(request):
    return pcrf_remove_user(request)


@handle_connection_error
@token_required
@permission_required("nst.nst_create_change_ldap")
def create_or_change_ldap_service(request):
    return ldap_create_or_change_service(request)


@handle_connection_error
@token_required
@permission_required("nst.nst_create_change_pcrf")
def create_or_change_pcrf_service(request):
    return pcrf_create_or_change_service(request)


@handle_connection_error
@token_required
@permission_required("nst.nst_credit_subscriber")
def credit_subscriber(request):
    return add_topup(request)


@handle_connection_error
@token_required
@permission_required("nst.nst_credit_subscriber")
def debit_subscriber(request):
    return debit_user(request)


@handle_connection_error
@token_required
@permission_required("nst.send_stop_coa")
def nst_send_stop_coa(request):
    return send_stop_coa(request)

@handle_connection_error
@token_required
@permission_required("nst.send_start_coa")
def nst_send_start_coa(request):
    return send_start_coa(request)


@handle_connection_error
@token_required
@permission_required("nst.get_daily_usage")
def nst_get_daily_usage(request, subscriber_id, start_date, end_date):
    try:
        logger.debug("viewOnlineDailyUsage, (%s), (%s), (%s)", subscriber_id, start_date, end_date)
        start_date = validate_date_string(start_date=start_date)
        if not start_date:
            result = {
                'error': True,
                'error_message': "Invalid Start Date.."
            }
            return HttpResponse(json.dumps(result), content_type="application/json")
        end_date = validate_date_string(end_date=end_date)
        if not end_date:
            result = {
                'error': True,
                'error_message': "Invalid End Date.."
            }
            return HttpResponse(json.dumps(result), content_type="application/json")
        logger.debug("Validating subscriber_id (%s)", subscriber_id)
        try:
            ordering_col = {
                '1': 'service_name',
                '2': 'date',
                '3': 'upload',
                '4': 'download',
                '5': 'charged_bytes',
                '6': 'device_service'
            }
            or_queries = []

            if bool(request.GET.get('sSearch_0')):
                search_q = request.GET.get('sSearch_0')
                or_queries.append(Q(service_name__icontains=search_q))

            query = {'username': subscriber_id}

            if bool(request.GET.get('sSearch')):
                search_q = request.GET.get('sSearch')
                or_queries.append(Q(service_name__icontains=search_q))
                or_queries.append(Q(download__icontains=search_q))
                or_queries.append(Q(upload__icontains=search_q))
                or_queries.append(Q(charged_bytes__icontains=search_q))
                or_queries.append(Q(device_service__icontains=search_q))

            if bool(request.GET.get('sSearch_1')):
                dt = datetime.datetime.strptime(request.GET.get('sSearch_1'), '%Y-%m-%d')
                dt_min = datetime.datetime.combine(dt.date(), datetime.time.min)
                dt_max = datetime.datetime.combine(dt.date(), datetime.time.max)
                query['date__range'] = (dt_min, dt_max)
            elif start_date and end_date:
                dt_min = datetime.datetime.combine(start_date.date(), datetime.time.min)
                dt_max = datetime.datetime.combine(end_date.date(), datetime.time.max)
                query['date__range'] = (dt_min, dt_max)

            if bool(request.GET.get('sSearch_2')):
                search_q = request.GET.get('sSearch_2')
                or_queries.append(Q(upload__icontains=search_q))

            if bool(request.GET.get('sSearch_3')):
                search_q = request.GET.get('sSearch_3')
                or_queries.append(Q(download__icontains=search_q))

            if bool(request.GET.get('sSearch_4')):
                search_q = request.GET.get('sSearch_4')
                or_queries.append(Q(charged_bytes__icontains=search_q))

            info, result = construct_db_query(request, query, ordering_col, 'username', or_queries, OnlineDailyUsage, 'daily_usage_db')

            for i in info:
                result['aaData'].append([
                    i.service_name,
                    i.date.strftime("%Y-%m-%d %H:%M:%S") if i.date else "",
                    i.upload,
                    i.download,
                    i.charged_bytes,
                    i.device_service
                ])
            return HttpResponse(json.dumps(result), content_type='application/json')
        except:
            result = {
                'error': True,
                'error_message': "Error happened at backend servers.."
            }
            return HttpResponse(json.dumps(result), content_type="application/json")
    except Exception as e:
        logger.error(str(e))
        result = {
            'error': True,
            'error_message': "Error Happened!"
        }
        return HttpResponse(json.dumps(result), content_type="application/json")


def _months_diff(start_date, end_date):
    return (end_date.year - start_date.year) * 12 + end_date.month - start_date.month


def _date_range(start_date, end_date):
    start_date = start_date - relativedelta(days=1)
    for month in range(_months_diff(start_date, end_date) + 1):
        result_date = start_date + relativedelta(months=month)
        yield "s%s%02d" % (result_date.year, result_date.month)

@handle_connection_error
@token_required
@permission_required("nst.get_sbr_daily_usage")
def nst_get_sbr_daily_usage(request):
    try:
        form = SBRDailyUsageForm(request.GET)
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

        subscriber_id = form.cleaned_data['subscriber_id']
        start_date = form.cleaned_data['start_date']
        database_start_date = datetime.date(year=2014, month=10, day=15)
        if start_date < database_start_date:
            start_date = database_start_date
        end_date = form.cleaned_data['end_date']
        dates_diff = ",".join(_date_range(start_date, end_date))
        logger.debug("view SBR Daily Usage, (%s), (%s), (%s)", subscriber_id, start_date, end_date)
        cursor = connections['unified_db'].cursor()

        query = """SELECT
                net.usage_date,
                net.service_name,
                sum(net.diff_output) as OUTPUT_BYTES,
                sum(net.diff_input) as INPUT_BYTES
                FROM ( SELECT
                part.user_name,
                date(part.event_time) as usage_date,
                part.time_stamp,
                part.session_id,
                part.service_name,
                @ob := part.OUTPUT_OCTETS+(part.OUTPUT_GIGAWORDS*4294967295) as output_bytes,
                @ib := part.INPUT_OCTETS+(part.INPUT_GIGAWORDS*4294967295) as input_bytes,
                if ( part.session_id = @last_si and part.record_type != "Start", @ob - @last_ob, @ob ) as diff_output,
                if ( part.session_id = @last_si and part.record_type != "Start", @ib - @last_ib, @ib ) as diff_input,
                @last_ob := @ob,
                @last_ib := @ib,
                @last_si := part.session_id
                FROM cdr PARTITION (%s) part,
                (SELECT @ob :=0, @ib :=0, @last_ob :=0, @last_ib :=0, @last_si := '') SQLVars
                WHERE user_name = '%s' AND service_name != 'WALLED_GARDEN_SERVICE'
                AND service_name != 'SUSPENDED_SERVICE' AND
                time_stamp >= unix_timestamp(DATE( DATE_SUB( STR_TO_DATE('%s', '%%Y-%%m-%%d') , INTERVAL 1 DAY ) ))
                 AND
                time_stamp < unix_timestamp(DATE( DATE_ADD( STR_TO_DATE('%s', '%%Y-%%m-%%d') , INTERVAL 1 DAY ) ))
                order by session_id,service_name,time_stamp) as net
                where time_stamp >= unix_timestamp('%s')
                group by usage_date,service_name order by usage_date;
                """ % (dates_diff, subscriber_id, start_date.isoformat(),
                       end_date.isoformat(), start_date.isoformat())

        cursor.execute(query)

        data = cursor.fetchall()

        formatted_data = []
        for event_date, service_name, download, upload in data:
            formatted_data.append([event_date.isoformat(), service_name, download, upload, download + upload])

        result = {
            'error': False,
            'error_message': None,
            'results': formatted_data
        }

        return HttpResponse(json.dumps(result), content_type='application/json')


    except Exception as e:

        logger.error(str(e))
        result = {
            'error': True,
            'error_message': "Error Happened!"
        }
        return HttpResponse(json.dumps(result), content_type="application/json")


@handle_connection_error
@token_required
@permission_required("nst.get_dpi_daily_usage")
def nst_get_dpi_daily_usage(request):
    try:
        form = SBRDailyUsageForm(request.GET)
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
        formatted_data = get_dpi_usage(request)
        return HttpResponse(formatted_data, content_type='application/json')


    except Exception as e:

        logger.error(str(e))
        result = {
            'error': True,
            'error_message': "Error Happened!"
        }
        return HttpResponse(json.dumps(result), content_type="application/json")


def _query_db_for_aggregates(cursor, query, months, consumption_percentages, total_debited, total_allowed,
                             subscribers_count,
                             avg_subscriber_consumption):
    cursor.execute(query)
    service_stats = cursor.fetchall()
    for row in service_stats:
        months.append(row[2])
        total_debited['data'].append(round(row[0], 2))
        total_allowed['data'].append(round(row[1], 2))
        subscribers_count['data'].append(row[3])
        consumption_percentages['data'].append(round((float(row[0]) / float(row[1])) * 100, 2))
        avg_subscriber_consumption['data'].append(round(float(row[0]) / float(row[3]), 2))


def _query_db_for_subscribers_count(cursor, query, subscribers_excessive_consumption, months):
    cursor.execute(query)
    service_stats = cursor.fetchall()
    for row in service_stats:
        subscribers_excessive_consumption['data'].append(row[0])
        months.append(row[1])


@token_required
@permission_required("nst.nst_get_analytics")
@require_http_methods(["GET"])
def nst_per_service_analytics(request):
    cur_new = connection.cursor()
    # form = ServiceAnalyticForm(request.GET)
    # if not form.is_valid():
    # error_message = ""
    # for k, v in form.errors.items():
    # error_message += "field %s has errors: %s" % (k, ",".join(v))
    #     return HttpResponse(json.dumps({'error': True, 'error_message': error_message}),
    #                         content_type='application/json')
    # service_names = form.cleaned_data['service_names']
    service_names = request.GET.getlist('service_names')
    start_date = datetime.date.today() - relativedelta(months=ANALYTICS_STARTING_MONTH_DIFF)
    end_date = datetime.date.today()

    if start_date < datetime.date(year=2014, month=7, day=1):  # I'm so so so sorry :'(
        db_configs = {
            'USER': 'mw1',
            'PASSWORD': 'MW_PASS',
            'HOST': '213.158.181.41',
        }
        if getattr(mw1_backend.configs, 'DEVELOPMENT', False):
            db_configs = {
                'USER': 'root',
                'PASSWORD': 'root',
                'HOST': 'localhost',
            }

        old_db = MySQLdb.connect(host=db_configs['HOST'], user=db_configs['USER'], passwd=db_configs['PASSWORD'],
                                 db="mw1_db")

    logger.debug("Getting statistics for %s", service_names)
    months = []
    consumption_percentages = {'name': "Consumed Percentage", "data": []}
    total_debited = {'name': 'Total Consumption (GB)', 'data': []}
    total_allowed = {'name': "Total Quota (GB)", 'data': []}
    subscribers_count = {'name': 'Subscribers Count', 'data': []}
    avg_subscriber_consumption = {'name': 'Average Consumption per Subscriber (GB)', 'data': []}
    subscribers_excessive_consumption = {'name': "Subscribers With Excessive Consumption", 'data': []}
    subscribers_months = []

    if 'All' in service_names:
        if start_date < datetime.date(year=2014, month=7, day=1):
            cur_old = old_db.cursor()
            query = "SELECT SUM(total_debited)/1024/1024/1024 AS `Sum of total debits`," \
                    "SUM(total_amount)/1024/1024/1024 AS `Sum of total allowed`,MONTH(start_date)," \
                    "COUNT(distinct(username)) FROM pcrf_backend_pcrfprofilelog " \
                    "WHERE MONTH(start_date) >= %(start_month)s AND " \
                    "MONTH(start_date) < 7 AND YEAR(start_date) = 2014 " \
                    "GROUP BY 3 ORDER BY 3 ;" % {'start_month': start_date.month}
            _query_db_for_aggregates(cur_old, query, months, consumption_percentages, total_debited, total_allowed,
                                     subscribers_count,
                                     avg_subscriber_consumption)

            query = "SELECT COUNT(distinct(username)),MONTH(start_date) FROM pcrf_backend_pcrfprofilelog" \
                    " WHERE total_debited >= original_amount and  MONTH(start_date) >= %(start_month)s AND " \
                    "MONTH(start_date) < 7 AND YEAR(start_date) = 2014 " \
                    "GROUP BY 2 ORDER BY 2 ;" % {'start_month': start_date.month}

            _query_db_for_subscribers_count(cur_old, query, subscribers_excessive_consumption, subscribers_months)

            query = "SELECT SUM(total_debited)/1024/1024/1024 AS `Sum of total debits`," \
                    "SUM(total_amount)/1024/1024/1024 AS `Sum of total allowed`,MONTH(start_date)," \
                    "COUNT(distinct(username)) FROM pcrf_backend_pcrfprofilelog " \
                    "WHERE start_date >= '%(start_date)s' AND start_date < '%(end_date)s' " \
                    "GROUP BY 3 ORDER BY YEAR(start_date),3 ;" % {'start_date': datetime.date(2014, 7, 1).isoformat(),
                                                                  'end_date': datetime.date(end_date.year,
                                                                                            end_date.month,
                                                                                            1).isoformat()}

            _query_db_for_aggregates(cur_new, query, months, consumption_percentages, total_debited, total_allowed,
                                     subscribers_count, avg_subscriber_consumption)

            query = "SELECT COUNT(distinct(username)),MONTH(start_date) FROM pcrf_backend_pcrfprofilelog " \
                    "WHERE total_debited >= original_amount AND  start_date >= '%(start_date)s' AND " \
                    "start_date < '%(end_date)s' " \
                    "GROUP BY 2 ORDER BY YEAR(start_date),2 " % {'start_date': datetime.date(2014, 7, 1).isoformat(),
                                                                 'end_date': datetime.date(end_date.year,
                                                                                           end_date.month,
                                                                                           1).isoformat()}

            _query_db_for_subscribers_count(cur_new, query, subscribers_excessive_consumption, subscribers_months)

        else:
            query = "SELECT SUM(total_debited)/1024/1024/1024 AS `Sum of total debits`," \
                    "SUM(total_amount)/1024/1024/1024 AS `Sum of total allowed`,MONTH(start_date)," \
                    "COUNT(distinct(username)) FROM pcrf_backend_pcrfprofilelog " \
                    "WHERE start_date >= '%(start_date)s' AND start_date < '%(end_date)s' " \
                    "GROUP BY 3 ORDER BY YEAR(start_date),3 ;" % {'start_date': start_date.isoformat(),
                                                                  'end_date': datetime.date(end_date.year,
                                                                                            end_date.month,
                                                                                            1).isoformat()}

            _query_db_for_aggregates(cur_new, query, months, consumption_percentages, total_debited, total_allowed,
                                     subscribers_count,
                                     avg_subscriber_consumption)

            query = "SELECT COUNT(distinct(username)),MONTH(start_date) FROM pcrf_backend_pcrfprofilelog " \
                    "WHERE total_debited >= original_amount AND  start_date >= '%(start_date)s' AND " \
                    "start_date < '%(end_date)s' " \
                    "GROUP BY 2 ORDER BY YEAR(start_date),2 ;" % {'start_date': start_date.isoformat(),
                                                                  'end_date': datetime.date(end_date.year,
                                                                                            end_date.month,
                                                                                            1).isoformat()}

            _query_db_for_subscribers_count(cur_new, query, subscribers_excessive_consumption, subscribers_months)

        months = [calendar.month_name[month] for month in months]
        subscribers_months = [calendar.month_name[month] for month in subscribers_months]

        collective_stats = {'service_names': service_names, 'months': months, 'total_debited': total_debited,
                            'total_allowed': total_allowed, 'subscribers_count': subscribers_count,
                            'consumption_percentages': consumption_percentages,
                            'avg_subscriber_consumption': avg_subscriber_consumption,
                            'subscribers_excessive_consumption': subscribers_excessive_consumption,
                            'subscribers_months': subscribers_months
        }
        return HttpResponse(json.dumps({'error': False, 'collective_stats': collective_stats}),
                            content_type='application/json')
    if len(service_names) > 1:
        service_names = tuple(map(lambda x: str(x), service_names))
        service_cond = "service_name in %(service_names)s " % {'service_names': service_names}
    elif len(service_names) == 1:
        service_name = service_names[0]
        service_cond = "service_name = '%(service_name)s' " % {'service_name': service_name}
    else:
        return HttpResponse(json.dumps({'error': True, 'error_message': "No service selected."}),
                            content_type='application/json')

    if start_date < datetime.date(year=2014, month=7, day=1):
        cur_old = old_db.cursor()
        query = "SELECT SUM(total_debited)/1024/1024/1024 AS `Sum of total debits`," \
                "SUM(total_amount)/1024/1024/1024 AS `Sum of total allowed`,MONTH(start_date)," \
                "COUNT(distinct(username)) FROM pcrf_backend_pcrfprofilelog " \
                "WHERE MONTH(start_date) >= %(start_month)s AND " \
                "MONTH(start_date) < 7 AND YEAR(start_date) = 2014 AND " \
                "%(service_cond)s" \
                "GROUP BY 3 ORDER BY 3 ;" % {'start_month': start_date.month, 'service_cond': service_cond}

        _query_db_for_aggregates(cur_old, query, months, consumption_percentages, total_debited, total_allowed,
                                 subscribers_count, avg_subscriber_consumption)

        query = "SELECT COUNT(distinct(username)),MONTH(start_date) FROM pcrf_backend_pcrfprofilelog " \
                "WHERE total_debited >= original_amount and  MONTH(start_date) >=  %(start_month)s AND " \
                "MONTH(start_date) < 7 AND YEAR(start_date) = 2014 AND %(service_cond)s " \
                "GROUP BY 2 ORDER BY 2 ;" % {'start_month': start_date.month, 'service_cond': service_cond}

        _query_db_for_subscribers_count(cur_old, query, subscribers_excessive_consumption, subscribers_months)

        query = "SELECT SUM(total_debited)/1024/1024/1024 AS `Sum of total debits`," \
                "SUM(total_amount)/1024/1024/1024 AS `Sum of total allowed`,MONTH(start_date)," \
                "COUNT(distinct(username)) FROM pcrf_backend_pcrfprofilelog " \
                "WHERE start_date >= '%(start_date)s' AND start_date < '%(end_date)s' AND " \
                "%(service_cond)s" \
                "GROUP BY 3 ORDER BY YEAR(start_date),3 ;" % {'start_date': datetime.date(2014, 7, 1).isoformat(),
                                                              'end_date': datetime.date(end_date.year, end_date.month,
                                                                                        1).isoformat(),
                                                              'service_cond': service_cond}

        _query_db_for_aggregates(cur_new, query, months, consumption_percentages, total_debited, total_allowed,
                                 subscribers_count,
                                 avg_subscriber_consumption)

        query = "SELECT COUNT(distinct(username)),MONTH(start_date) FROM pcrf_backend_pcrfprofilelog " \
                "WHERE total_debited >= original_amount AND start_date >= '%(start_date)s' AND " \
                "start_date < '%(end_date)s' AND " \
                "%(service_cond)s" \
                "GROUP BY 2 ORDER BY YEAR(start_date),2 ;" % {'start_date': datetime.date(2014, 7, 1).isoformat(),
                                                              'end_date': datetime.date(end_date.year, end_date.month,
                                                                                        1).isoformat(),
                                                              'service_cond': service_cond}

        _query_db_for_subscribers_count(cur_new, query, subscribers_excessive_consumption, subscribers_months)

    else:
        query = "SELECT SUM(total_debited)/1024/1024/1024 AS `Sum of total debits`," \
                "SUM(total_amount)/1024/1024/1024 AS `Sum of total allowed`,MONTH(start_date)," \
                "COUNT(distinct(username)) FROM pcrf_backend_pcrfprofilelog " \
                "WHERE  start_date >= '%(start_date)s' AND " \
                "start_date < '%(end_date)s' AND " \
                "%(service_cond)s" \
                "GROUP BY 3 ORDER BY YEAR(start_date),3 ;" % {'start_date': start_date.isoformat(),
                                                              'end_date': datetime.date(end_date.year,
                                                                                        end_date.month, 1).isoformat(),
                                                              'service_cond': service_cond}

        _query_db_for_aggregates(cur_new, query, months, consumption_percentages, total_debited, total_allowed,
                                 subscribers_count,
                                 avg_subscriber_consumption)

        query = "SELECT COUNT(distinct(username)),MONTH(start_date) FROM pcrf_backend_pcrfprofilelog " \
                "WHERE total_debited >= original_amount AND start_date >= '%(start_date)s' AND " \
                "start_date < '%(end_date)s' AND " \
                "'%(service_cond)s'" \
                "GROUP BY 2 ORDER BY YEAR(start_date),2 ;" % {'start_date': start_date.isoformat(),
                                                              'end_date': datetime.date(end_date.year,
                                                                                        end_date.month, 1).isoformat(),
                                                              'service_cond': service_cond}

        _query_db_for_subscribers_count(cur_new, query, subscribers_excessive_consumption, subscribers_months)

    months = [calendar.month_name[month] for month in months]
    subscribers_months = [calendar.month_name[month] for month in subscribers_months]

    collective_stats = {'service_name': service_names, 'months': months, 'total_debited': total_debited,
                        'total_allowed': total_allowed, 'subscribers_count': subscribers_count,
                        'consumption_percentages': consumption_percentages,
                        'avg_subscriber_consumption': avg_subscriber_consumption,
                        'subscribers_excessive_consumption': subscribers_excessive_consumption,
                        'subscribers_months': subscribers_months}

    return HttpResponse(json.dumps({'error': False, 'collective_stats': collective_stats}),
                        content_type='application/json')


def _query_db_for_variable_dict(cursor, query, variable_dict):
    cursor.execute(query)
    service_stats = cursor.fetchall()
    for row in service_stats:
        variable_dict['data'].append(row[0])
        variable_dict['months'].append(row[1])
    variable_dict['months'] = [calendar.month_name[month] for month in variable_dict['months']]
    return variable_dict


@token_required
@permission_required("nst.topups_analytics")
@require_http_methods(["GET"])
def topups_analytics(request):
    try:
        cur_new = connection.cursor()
        start_date = datetime.date.today() - relativedelta(months=ANALYTICS_STARTING_MONTH_DIFF)
        if start_date < datetime.date(year=2014, month=7, day=1):
            start_date = datetime.date(year=2014, month=7, day=1)
        end_date = datetime.date.today()
        if start_date < datetime.date(year=2014, month=7, day=1):  # Daif: I'm so so so sorry :'(, Bingo: We should be!
            db_configs = {
                'USER': 'mw1',
                'PASSWORD': 'MW_PASS',
                'HOST': '213.158.181.41',
            }
            if getattr(mw1_backend.configs, 'DEVELOPMENT', False):
                db_configs = {
                    'USER': 'root',
                    'PASSWORD': 'root',
                    'HOST': 'localhost',
                }

        logger.debug("Getting Topups Statistics.")
        avg_topups_statistics = {'name': 'Average Customer Topups in GB', "data": [], 'months': []}
        percentage_topups_statistics = {'name': 'Percentage of Usage vs Remaining', "data": [], 'months': []}
        no_of_users_consumed_their_topups = {'name': 'Number of users who consumed all their Topups', "data": [],
                                             'months': []}

        query = "SELECT (SUM(pcrf_backend_topuplog.basic_amount)/1024/1024/1024) / " \
                "COUNT(distinct(pcrf_backend_pcrfprofilelog.username)) AS `Avg of Topups`," \
                "MONTH(pcrf_backend_topuplog.start_date) AS `Months` " \
                "FROM pcrf_backend_topuplog, pcrf_backend_pcrfprofilelog " \
                "WHERE pcrf_backend_topuplog.pcrf_profile_id=pcrf_backend_pcrfprofilelog.id " \
                "AND pcrf_backend_topuplog.start_date >= '%(start_date)s' AND pcrf_backend_topuplog.start_date < '%(end_date)s' " \
                "GROUP BY 2 ORDER BY 2 ;" % {'start_date': start_date.isoformat(),
                                             'end_date': datetime.date(end_date.year, end_date.month, 1).isoformat()}

        avg_topups_statistics = _query_db_for_variable_dict(cur_new, query, avg_topups_statistics)

        query = "SELECT (SUM(remaining)/SUM(basic_amount))*100 ,MONTH(pcrf_backend_topuplog.start_date) " \
                "FROM pcrf_backend_topuplog " \
                "WHERE pcrf_backend_topuplog.start_date >= '%(start_date)s' " \
                "AND pcrf_backend_topuplog.start_date < '%(end_date)s' " \
                "GROUP BY 2 ORDER BY 2 ;" % {'start_date': start_date.isoformat(),
                                             'end_date': datetime.date(end_date.year, end_date.month, 1).isoformat()}

        percentage_topups_statistics = _query_db_for_variable_dict(cur_new, query, percentage_topups_statistics)

        query = "SELECT count(*), MONTH(pcrf_backend_topuplog.start_date) " \
                "FROM pcrf_backend_topuplog " \
                "WHERE start_date >= '%(start_date)s' AND start_date < '%(end_date)s' " \
                "AND remaining - basic_amount = 0 and basic_amount != 0 " \
                "GROUP BY 2 ORDER BY 2 ;" % {'start_date': start_date.isoformat(),
                                             'end_date': datetime.date(end_date.year, end_date.month, 1).isoformat()}

        no_of_users_consumed_their_topups = _query_db_for_variable_dict(cur_new, query,
                                                                        no_of_users_consumed_their_topups)

        return HttpResponse(json.dumps({
            'error': False,
            'charts': {
                'avg_topups_statistics': avg_topups_statistics,
                'percentage_topups_statistics': percentage_topups_statistics,
                'no_of_users_consumed_their_topups': no_of_users_consumed_their_topups
            }
        }), content_type='application/json')

    except:
        return HttpResponse(
            json.dumps({'error': True, 'error_message': "An error happened getting the Topups charts."}),
            content_type='application/json')


@handle_connection_error
@token_required
@permission_required("nst.nst_cyber_crime")
def query_cyber_crime_by_datetime(request):
    try:
        ip_address = request.GET.get('ipAddress')
        start_time = request.GET.get('start_time')
        pattern = '%Y-%m-%d %H:%M:%S'
        start_epoch = int(time.mktime(time.strptime(start_time, pattern)))

        users_1 = CyberCrimeSession.objects.using('unified_db').filter(source_ip=ip_address,
                                                                       event_time__lte=start_time) \
            .order_by('-time_stamp')
        users_2 = CyberCrimeSession.objects.using('unified_db').filter(source_ip=ip_address,
                                                                       event_time__gt=start_time) \
            .order_by('time_stamp')
        user_1 = users_1[0] if len(users_1) else None
        user_2 = users_2[0] if len(users_2) else None
        response = {'error': False, 'message': '', 'user_name': '', 'sessions': []}
        if user_1 and user_2:
            if user_1.session_id == user_2.session_id \
                    and user_1.user_name == user_2.user_name \
                    and user_1.record_type != 'Stop' \
                    and user_2.record_type != 'Start':
                response = {'error': False,
                            'message': '',
                            'user_name': user_1.user_name,
                            'sessions': [
                                [
                                    user_1.session_id,
                                    user_1.record_type,
                                    user_1.mac
                                ],
                                [
                                    user_2.session_id,
                                    user_2.record_type,
                                    user_2.mac
                                ]
                            ]
                }
                return HttpResponse(json.dumps(response))
        elif user_1 and not user_2:
            if user_1.record_type != 'Stop' and user_1.time_stamp + 32400 >= long(time.time()):
                online_ip = get_ip_by_username(user_1.user_name)
                if user_1.source_ip == online_ip:
                    response = {'error': False,
                                'warning': True,
                                'message': '',
                                'user_name': user_1.user_name,
                                'sessions': [
                                    [
                                        user_1.session_id,
                                        user_1.record_type,
                                        user_1.mac
                                    ]
                                ]
                    }
                    return HttpResponse(json.dumps(response))

        response = {'error': False, 'message': 'No Users Found'}
        return HttpResponse(json.dumps(response))
    except:
        return HttpResponse(json.dumps({'error': True, 'message': 'An error happened at our backend servers,'
                                                                  'please contact the system administrator'}))


@handle_connection_error
@token_required
@permission_required("nst.nst_cyber_crime")
def query_cyber_crime_by_date_range(request):
    try:
        form = CyberCrimeForm(request.GET)
        if not form.is_valid():
            error_msg = ""
            for k, v in form.errors.items():
                error_msg += "%s: %s\n" % (k, ", ".join(v))
            return HttpResponse(json.dumps({'error': True, 'message': error_msg}), content_type="application/json")

        ip_address = form.cleaned_data.get('ipAddress')
        start_date = form.cleaned_data.get('startDate')
        end_date = form.cleaned_data.get('endDate')

        query = {"source_ip": ip_address, "event_time__gte": start_date,
                 "event_time__lte": end_date + datetime.timedelta(days=1)
                 if start_date == end_date else end_date}
        cdrs = CyberCrimeSession.objects.using('unified_db').filter(**query).order_by('-time_stamp')
        sessions = [[cdr.session_id, cdr.record_type, cdr.user_name, cdr.event_time.isoformat(),
                     cdr.time_stamp, cdr.source_ip, cdr.mac] for cdr in cdrs]

        response = {
            'error': False,
            'message': "",
            "sessions": sessions
        }

        return HttpResponse(json.dumps(response), content_type="application/json")

    except:
        return HttpResponse(json.dumps({'error': True, 'message': 'An error happened at our backend servers,'
                                                                  'please contact the system administrator'}),
                            content_type="application/json")


@handle_connection_error
@token_required
@permission_required("nst.nst_get_wifi_report")
def get_wifi_report(request):
    """
    :returns nas_port_id, long_name, usage_date, users_count, sessions_count, total_session_time, output_bytes,
    input_bytes, total bandwidth per user (input bytes + output bytes) / total users,
    session_time_per_session_id (total_session_time/sessions_count)
    """
    try:
        form = WifiReportForm(request.GET)
        if not form.is_valid():
            error_msg = ""
            for k, v in form.errors.items():
                error_msg += "%s\n" % ",".join(v)
            return HttpResponse(json.dumps({'error': True, 'message': error_msg}), content_type="application/json")

        all_enabled = request.GET.get('all_enabled')
        start_date = form.cleaned_data['start_date']
        if not request.GET.get('end_date'):
            end_date = start_date
        else:
            end_date = form.cleaned_data['end_date']
        dates_diff = ",".join(_date_range(start_date, end_date))

        cursor = connections['unified_db'].cursor()
        if bool(all_enabled):
            query = """SELECT
                    display.nas_port_id,
                    tewifi.long_name,
                    CAST(sum(display.USERS_COUNT) as SIGNED) as Users_Count,
                    CAST(sum(display.SESSIONS_COUNT) as SIGNED) as Sessions_Count,
                    CAST(sum(display.Total_SESSION_TIME) as SIGNED) as Total_Session_Time,
                    CAST(sum(display.OUTPUT_BYTES) as SIGNED) as Output_Bytes,
                    CAST(sum(display.INPUT_BYTES) as SIGNED) as Input_Bytes,
                    CAST(sum((display.INPUT_BYTES + display.OUTPUT_BYTES) / display.USERS_COUNT) as SIGNED) as Total_Bandwith_Per_User,
                    CAST(sum(display.Total_SESSION_TIME / display.SESSIONS_COUNT) as SIGNED) as Total_Session_Time_Per_Session
                    FROM
                    ( SELECT
                    net.nas_port_id,
                    net.usage_date,
                    net.time_stamp,
                    count(distinct net.user_name) as USERS_COUNT,
                    count(distinct net.session_id) as SESSIONS_COUNT,
                    sum(net.diff_sessiontime) as Total_SESSION_TIME,
                    sum(net.diff_output) as OUTPUT_BYTES,
                    sum(net.diff_input) as INPUT_BYTES FROM
                    ( SELECT
                    part.nas_port_id,
                    part.user_name,
                    date(part.event_time) as usage_date,
                    part.time_stamp,
                    part.session_id,
                    @ob := part.OUTPUT_OCTETS+(part.OUTPUT_GIGAWORDS*4294967295) as output_bytes,
                    @ib := part.INPUT_OCTETS+(part.INPUT_GIGAWORDS*4294967295) as input_bytes,
                    if ( part.session_id = @last_si, @ob - @last_ob, @ob ) as diff_output,
                    if ( part.session_id = @last_si, @ib - @last_ib, @ib ) as diff_input,
                    if ( part.session_id = @last_si, part.session_time - @last_st, part.session_time) as diff_sessiontime,
                    @last_ob := @ob, @last_ib := @ib, @last_st := part.session_time, @last_si := part.session_id
                    FROM cdr partition (%(dates_diff)s) part,
                    (select @ob :=0, @ib :=0, @last_ob :=0, @last_ib :=0, @last_st :=0, @last_si := '') SQLVars
                    where record_type != 'Start' AND service_name = 'WIFI_SERVICE'
                    AND time_stamp >= unix_timestamp(DATE( DATE_SUB( STR_TO_DATE('%(start_date)s', '%%Y-%%m-%%d') , INTERVAL 1 DAY ) ))
                    AND time_stamp < unix_timestamp(DATE( DATE_ADD( STR_TO_DATE('%(end_date)s', '%%Y-%%m-%%d') , INTERVAL 1 DAY ) ))
                    order by nas_port_id,user_name,session_id,time_stamp) as net group by nas_port_id,usage_date
                    order by usage_date) as display
                    join tewifi.wfws_nastool as tewifi on substr(display.nas_port_id,3,9) = substr(tewifi.nasport_id, 3, 9)
                    where time_stamp >= unix_timestamp('%(start_date)s') group by tewifi.long_name;""" % {
            'dates_diff': dates_diff, 'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()}

            cursor.execute(query)
            data = cursor.fetchall()

            response = {
                'error': False,
                'message': "",
                "sessions": data
            }

            return HttpResponse(json.dumps(response), content_type="application/json")

        query = """SELECT
            display.nas_port_id,
            tewifi.long_name,
            CAST(sum(display.USERS_COUNT) as SIGNED) as Users_Count,
            CAST(sum(display.SESSIONS_COUNT) as SIGNED) as Sessions_Count,
            sum(display.Total_SESSION_TIME) as Total_Session_Time,
            sum(display.OUTPUT_BYTES) as Output_Bytes,
            sum(display.INPUT_BYTES) as Input_Bytes,
            sum((display.INPUT_BYTES + display.OUTPUT_BYTES) / display.USERS_COUNT) as Total_Bandwith_Per_User,
            sum(display.Total_SESSION_TIME / display.SESSIONS_COUNT) as Total_Session_Time_Per_Session
            FROM
            ( SELECT
            net.nas_port_id,
            net.usage_date,
            net.time_stamp,
            count(distinct net.user_name) as USERS_COUNT,
            count(distinct net.session_id) as SESSIONS_COUNT,
            sum(net.diff_sessiontime) as Total_SESSION_TIME,
            sum(net.diff_output) as OUTPUT_BYTES,
            sum(net.diff_input) as INPUT_BYTES FROM
            ( SELECT
            part.nas_port_id,
            part.user_name,
            date(part.event_time) as usage_date,
            part.time_stamp,
            part.session_id,
            @ob := part.OUTPUT_OCTETS+(part.OUTPUT_GIGAWORDS*4294967295) as output_bytes,
            @ib := part.INPUT_OCTETS+(part.INPUT_GIGAWORDS*4294967295) as input_bytes,
            if ( part.session_id = @last_si, @ob - @last_ob, @ob ) as diff_output,
            if ( part.session_id = @last_si, @ib - @last_ib, @ib ) as diff_input,
            if ( part.session_id = @last_si, part.session_time - @last_st, part.session_time) as diff_sessiontime,
            @last_ob := @ob, @last_ib := @ib, @last_st := part.session_time, @last_si := part.session_id
            FROM cdr partition (%s) part,
            (select @ob :=0, @ib :=0, @last_ob :=0, @last_ib :=0, @last_st :=0, @last_si := '') SQLVars
            where record_type != 'Start' AND service_name = 'WIFI_SERVICE'
            AND time_stamp >= unix_timestamp(DATE( DATE_SUB( STR_TO_DATE('%s', '%%Y-%%m-%%d') , INTERVAL 1 DAY ) ))
            AND time_stamp < unix_timestamp(DATE( DATE_ADD( STR_TO_DATE('%s', '%%Y-%%m-%%d') , INTERVAL 1 DAY ) ))
            order by nas_port_id,user_name,session_id,time_stamp) as net group by nas_port_id,usage_date
            order by usage_date) as display
            join tewifi.wfws_nastool as tewifi on substr(display.nas_port_id,3,9) = substr(tewifi.nasport_id, 3, 9)
            where time_stamp >= unix_timestamp('%s') group by nas_port_id;""" % (
            dates_diff, start_date.isoformat(),
            end_date.isoformat(), start_date.isoformat())

        cursor.execute(query)
        data = cursor.fetchall()

        response = {
            'error': False,
            'message': "",
            "sessions": data
        }
        return HttpResponse(json.dumps(response), content_type="application/json")

    except:
        return HttpResponse(json.dumps({'error': True, 'message': 'An error happened at our backend servers,'
                                                                  'please contact the system administrator'}),
                            content_type="application/json")


@handle_connection_error
#@token_required
#@permission_required("nst.nst_get_wifi_venues")
def get_wifi_venues(request):
    try:
        logger.debug("getWifiVenues")
        try:
            ordering_col = {
                '1': 'nasport_id',
                '2': 'long_name',
                '3': 'short_name',
                '4': 'type',
                '5': 'card',
                '6': 'port',
                '7': 'index',
                '8': 'index2',
                '9': 'index3'
            }
            or_queries = []

            # if bool(request.GET.get('sSearch_0')):
            #     search_q = request.GET.get('sSearch_0')
            #     or_queries.append(Q(service_name__icontains=search_q))

            query = {}

            if bool(request.GET.get('sSearch')):
                search_q = request.GET.get('sSearch')
                or_queries.append(Q(long_name__icontains=search_q))
                or_queries.append(Q(short_name__icontains=search_q))
                or_queries.append(Q(nasport_id__icontains=search_q))
            #
            # if bool(request.GET.get('sSearch_1')):
            #     dt = datetime.datetime.strptime(request.GET.get('sSearch_1'), '%Y-%m-%d')
            #     dt_min = datetime.datetime.combine(dt.date(), datetime.time.min)
            #     dt_max = datetime.datetime.combine(dt.date(), datetime.time.max)
            #     query['date__range'] = (dt_min, dt_max)
            # elif start_date and end_date:
            #     dt_min = datetime.datetime.combine(start_date.date(), datetime.time.min)
            #     dt_max = datetime.datetime.combine(end_date.date(), datetime.time.max)
            #     query['date__range'] = (dt_min, dt_max)
            #
            # if bool(request.GET.get('sSearch_2')):
            #     search_q = request.GET.get('sSearch_2')
            #     or_queries.append(Q(upload__icontains=search_q))
            #
            # if bool(request.GET.get('sSearch_3')):
            #     search_q = request.GET.get('sSearch_3')
            #     or_queries.append(Q(download__icontains=search_q))
            #
            # if bool(request.GET.get('sSearch_4')):
            #     search_q = request.GET.get('sSearch_4')
            #     or_queries.append(Q(charged_bytes__icontains=search_q))

            info, result = construct_db_query(request, query, ordering_col, 'nasport_id', or_queries, NASTool, 'wifi_db')

            for i in info:
                result['aaData'].append([
                    i.nasport_id,
                    i.long_name,
                    i.short_name,
                    i.nasport_ip,
                    i.management_ip,
                    i.dslam_ip,
                    i.type,
                    i.card,
                    i.port,
                    i.ap,
                    i.index,
                    i.index2,
                    i.index3,
                    i.id
                ])
            return HttpResponse(json.dumps(result), content_type='application/json')
        except:
            result = {
                'error': True,
                'error_message': "Error happened at backend servers.."
            }
            return HttpResponse(json.dumps(result), content_type="application/json")
    except Exception as e:
        logger.error(str(e))
        result = {
            'error': True,
            'error_message': "Error Happened!"
        }
        return HttpResponse(json.dumps(result), content_type="application/json")


@handle_connection_error
@token_required
@permission_required("nst.nst_provision_wifi_venue")
def provision_wifi_venue(request):
    try:
        if request.POST.get('action') == 'edit':
            vid = request.POST.get('vid')
            current_venue_instance = NASTool.objects.using('wifi_db').get(pk=vid)
            provision_form = WifiVenueForm(request.POST, instance=current_venue_instance)
            message = "WiFi Venue Editted Successfully!"
        else:
            provision_form = WifiVenueForm(request.POST)
            message = "WiFi Venue Provisioned Successfully!"
        if not provision_form.is_valid():
            result = {
                'error': True,
                'error_message': "Errors happened in form submission!",
                'form_errors': provision_form.errors
            }

            return HttpResponse(json.dumps(result), content_type="application/json")
        provision_form = provision_form.save(commit=False)
        provision_form.save(using='wifi_db')


        response = {
            'error': False,
            'message': message
        }
        return HttpResponse(json.dumps(response), content_type="application/json")
    except:
        result = {
            'error': True,
            'error_message': "Error Happened!"
        }
        return HttpResponse(json.dumps(result), content_type="application/json")


@handle_connection_error
@token_required
@permission_required("nst.remove_allowed_service")
def remove_wifi_venue(request):
    try:
        wifi_venue_id = request.POST.get('wifi_venue_id')

        NASTool.objects.using('wifi_db').filter(id=wifi_venue_id).delete()
        response = {
            'error': False,
            'error_message': ''
        }
    except Error as e:
        logger.error("Error while deleting WiFi Venue %s from db, %s", wifi_venue_id, str(e))
        response = {
            'error': True,
            'error_message': "Couldn't remove WiFi Venues .. please contact service administrator."
        }

    return HttpResponse(json.dumps(response), content_type="application/json", status=200)


@handle_connection_error
@token_required
@permission_required("nst.optionpack")
def query_optionpack_subscriber(request):
    result = {
        'error': True,
        'error_message': ''
    }
    subscriber_id = request.GET.get('subscriber_id')
    ldap_client = LDAPClient()
    subscriber_profile = ldap_client.get_user_profile(subscriber_id)
    if not subscriber_profile:
        result['error_message'] = 'Subscriber {0} has no AAA profile'.format(subscriber_id)
        return HttpResponse(json.dumps(result))
    profile = subscriber_profile['profile'][0][1]
    if not 'radiusFramedIPAddress' in profile:
        error_msg = "User {0} has no option pack".format(subscriber_id)
        result['error_message'] = error_msg
        return HttpResponse(json.dumps(result))

    option_pack_items = {}

    for k in set(['radiusFramedIPAddress', 'radiusFramedIPNetmask', 'radiusFramedRoute', 'radiusGroupName']):
        option_pack_items[k] = profile[k][0]

    option_pack_items['radiusReplyItem'] = profile['radiusReplyItem']
    result['subscriber_id'] = subscriber_id
    result['profile'] = option_pack_items
    result['error'] = False
    return HttpResponse(json.dumps(result))


@handle_connection_error
@token_required
@permission_required("nst.optionpack")
def provision_optionpack_subscriber(request):
    response = create_or_change_ldap_service(request)
    return response


@handle_connection_error
@token_required
@permission_required("nst.optionpack")
def delete_optionpack_subscriber(request):
    response = ldap_delete_optionpack_subscriber(request)
    return response


@token_required
@permission_required("nst.nst_get_wifi_logs")
def get_wifi_logs(request):
    try:
        subscriber_id = request.GET['subscriber_id'].encode('utf-8').strip()
        logger.debug("Getting WiFi Logs for Subscriber ID (%s)", subscriber_id)
        query = {'subscriber_id': subscriber_id}
        query_result = WiFiLogs.objects.using('wifi_db').filter(**query).order_by('timestamp')
        result = {'data': []}
        for i in query_result:
            aaData = [
                i.subscriber_id,
                i.fn_name,
                i.message,
                i.timestamp.strftime("%Y-%m-%d %H:%M:%S") if i.timestamp else "",
                i.payload,
                i.status,
                i.status
            ]

            result['data'].append(aaData)

        response = {
            'success': True,
            'msg': 'Request completed successfully!',
            'wifi_logs': result.get('data')[::-1]
        }
    except:
        response = {
            'success': False,
            'msg': 'An Error happened!',
        }
    # log_action('get_basic_info', request, response, transaction_id=transaction_id)
    return HttpResponse(json.dumps(response), mimetype="application/json")


@require_http_methods(["POST"])
@token_required
@permission_required("nst.nst_reset_subscriber_password")
def reset_subscriber_password(request):
    user_name = request.POST['userName'].encode('utf-8').strip()
    password = request.POST.get('password', '').encode('utf-8').strip()
    transaction_id = request.POST['transactionId'].encode('utf-8').strip()
    if not (password and request.user.has_perm("nst.nst_hard_reset_subscriber_password")):
        password = int(random.random()*100000000)
    logger.debug("Resetting LDAP password for user (%s), transaction ID: ", user_name,
                 transaction_id)
    ldap_client = LDAPClient()
    result = ldap_client.reset_user_password(user_name, password)
    response = {
        'success': result['action_result'],
        'msg': result.get('action_error_message'),
        'new_password': password
    }
    # log_action(inspect.stack()[0][3], request, response, transaction_id=transaction_id)
    ldap_client.disconnect()
    return HttpResponse(json.dumps(response), content_type="application/json")
