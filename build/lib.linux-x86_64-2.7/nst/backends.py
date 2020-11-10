from datetime import datetime
from aaa_backend.client import AAAClient
from mw1_backend.configs import RADIUS_SERVER_1, RADIUS_SERVER_2, RADIUS_SERVER_3, RADIUS_SERVER_4, \
    RADIUS_GREP_CMD, LOG_FILE_PATH, RAMSIS_GREP_CMD
import subprocess
import logging
from .models import SubscriberLogs
from django.db import connections
from shared.common import FlatSeralizer
import re

logger = logging.getLogger(__name__)


def _parse_files(username, host, file_path_today, grep_cmd):
    error_msg = ""
    error = False
    cmd_command = grep_cmd % {'username': username,
                              'host': host,
                              'today_file_path': file_path_today}

    proc = subprocess.Popen(cmd_command, stdout=subprocess.PIPE, shell=True)
    logs, errors = proc.communicate()
    if errors:
        logger.error("Error while querying logs, errors: \n %s", errors)
        error_msg = "Error while querying logs, errors: \n %s" % errors
        error = True
    lines = filter(lambda line: line != '', logs.split('\n'))
    logs = []
    for line in lines:
        fields = line.split(";")
        try:
            entry = {'datetime': fields[0].strip("\""),
                     'action': fields[1].strip("\""),
                     'reject_reason': fields[2].strip("\""),
                     'username': fields[3].strip("\""),
                     'nas_port_id_req': fields[5].strip("\""),
                     'nas_port_id_ldap': fields[6].strip("\""),
                     'nas_ip_add': fields[7].strip("\""),
                     'nas_port': fields[8].strip("\"")}
            logs.append(entry)
        except IndexError:
            # fields my be missing entries
            logger.warn("Missing entry at user %s's logs", username)

    if not logs:
        error_msg = "User not found"

    return {'error': error, 'error_message': error_msg, 'logs': logs}


def _parse_backup_file(username):
    error_msg = ""
    error = False
    cmd_command = RAMSIS_GREP_CMD % {'username': username}

    proc = subprocess.Popen(cmd_command, stdout=subprocess.PIPE, shell=True)
    logs, errors = proc.communicate()
    if errors:
        logger.error("Error while querying backup logs, errors: \n %s", errors)
        error_msg = "Error while querying backup logs, errors: \n %s" % errors
        error = True
    lines = [{'line': line} for line in filter(lambda line: line != '', logs.split('\n'))]

    if not lines:
        error_msg = "User not found"

    return {'error': error, 'error_message': error_msg, 'lines': lines}


def get_subscriber_logs(username):
    now_dt = datetime.now().date()
    today = datetime.strftime(now_dt, '%Y%m%d')
    file_path_today = LOG_FILE_PATH % {'date': today}
    host1_res = _parse_files(username, RADIUS_SERVER_1, file_path_today, RADIUS_GREP_CMD)
    host2_res = _parse_files(username, RADIUS_SERVER_2, file_path_today, RADIUS_GREP_CMD)
    host3_res = _parse_files(username, RADIUS_SERVER_3, file_path_today, RADIUS_GREP_CMD)
    host4_res = _parse_files(username, RADIUS_SERVER_4, file_path_today, RADIUS_GREP_CMD)
    backup_res = _parse_backup_file(username)
    return host1_res, host2_res, host3_res, host4_res, backup_res


def get_subscriber_database_logs(start_date, dates_diff, username=None, nas_port=None):
    logs = None
    if username:
        matches = re.search(r"([\w\d]+@tedata\.net\.eg)|^([\w\d]+)$", username)
        if matches:
            if matches.group(1):
                # logs = SubscriberLogs.objects.using('subscriber_logs').filter(user_name__istartswith="{0}".format(username))
                query_params = "user_name LIKE '{0}%'".format(matches.group(1))
            elif matches.group(2):
                # logs = SubscriberLogs.objects.using('subscriber_logs').filter(user_name__istartswith="{0}@".format(username)) | SubscriberLogs.objects.using('subscriber_logs').filter(user_name__exact="{0}".format(username))
                query_params = "user_name LIKE '{0}@%'".format(matches.group(2))
            else:
                results = {
                    'error': True,
                    'error_message': 'Wrong submitted Subscriber ID.',
                    'logs': []
                }
                return results
        else:
            results = {
                'error': True,
                'error_message': 'You should submit a valid Subscriber ID.',
                'logs': []
            }
            return results
    elif nas_port:
        # logs = SubscriberLogs.objects.using('subscriber_logs').filter(nas_port_id_ldap__iexact="NAS-Port-Id = \"{0}\"".format(nas_port))
        query_params = "nas_port_id_request = \"{0}\"".format(nas_port)

    cursor = connections['subscriber_logs'].cursor()

    query = """SELECT * FROM VAS_Log PARTITION (%s) WHERE date_time >= '%s' AND %s;""" % (dates_diff, start_date.isoformat(), query_params)

    cursor.execute(query)

    logs = cursor.fetchall()
    formatted_data = []
    for host_name, date_time, user_name, service_name, nas_port_id_ldap, nas_port, status,\
        reject_reason, nas_port_id_request, nas_ipaddress in logs:
        formatted_data.append([user_name, host_name, service_name, nas_port_id_ldap, nas_port, status,
                               reject_reason, nas_port_id_request, nas_ipaddress, date_time.isoformat()])
    # serializer = FlatSeralizer('user_name', 'host_name', 'service_name', 'nas_port_id_ldap', 'nas_port', 'status',
    #                            'reject_reason', 'nas_port_id_request', 'nas_ipaddress', 'date_time', append_list=True)
    # data = serializer.serialize(logs)
    results = {
        'error': False,
        'error_message': '',
        'logs': formatted_data
    }
    return results


def get_ip_by_username(username):
    aaa_client = AAAClient()
    result = aaa_client.get_session_by_name(username.encode('utf-8').strip())
    return result.get('IpAddress')
