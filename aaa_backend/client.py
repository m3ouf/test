from shared.decorators import Singleton
from xml_templates import COA_START_REQ, COA_STOP_REQ, COA_START_9K_REQ, COA_STOP_9K_REQ
from mw1_backend.configs import RADIUS_SESSION_ENDPOINT, SBR_AUTH_PASS, RADIUS_DR_SESSION_ENDPOINT, PYCURL_TIMEOUT, \
    RADIUS_REDIR_SESSION_ENDPOINT
from lxml import etree
from shared.decorators import timeout_handler
from .models import AAASession
import pycurl
import cStringIO
import logging
import struct
import socket

logger = logging.getLogger(__name__)


@Singleton
class AAAClient(object):
    @staticmethod
    @timeout_handler
    def _exec_xml_request(url, post_data, basic_auth_val=SBR_AUTH_PASS):
        """
        performs network connection with a remote server and returns a result.
        :param url: the url of the remote server.
        :param post_data: the data to be sent to the remote server.
        :returns: a string response from the remote server.
        """
        buf = cStringIO.StringIO()
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
        # curl.setopt(pycurl.VERBOSE, 1)
        curl.setopt(pycurl.CONNECTTIMEOUT, PYCURL_TIMEOUT)
        curl.setopt(pycurl.TIMEOUT, PYCURL_TIMEOUT)
        curl.perform()
        response = buf.getvalue()
        buf.close()
        return {
            'action_result': True,
            'action_error_message': '',
            'remote_response': response
        }

    @staticmethod
    def _ip2int(addr):
        return struct.unpack("!I", socket.inet_aton(addr))[0]

    @staticmethod
    def _int2ip(addr):
        return socket.inet_ntoa(struct.pack("!I", addr))

    @timeout_handler
    def _try_aaa_site(self, request_xml, end_point, parser):
        response = self._exec_xml_request(end_point, request_xml)
        if response.get('connection_error'):
            return response
        response_xml = response['remote_response']
        #logger.info(response_xml)
        result = parser(response_xml)
        return result

    def _send_xml_request(self, request_xml, parser, alt_ep=None, alt_dr_ep=None):
        response = self._try_aaa_site(request_xml, alt_ep if alt_ep else RADIUS_SESSION_ENDPOINT, parser)
        if response.get('connection_error'):
            logger.warn("Error happened while sending COA to (%s) .. trying the DR site (%s) ...",
                        RADIUS_SESSION_ENDPOINT, RADIUS_DR_SESSION_ENDPOINT)
            response = self._try_aaa_site(request_xml, alt_dr_ep if alt_dr_ep else RADIUS_DR_SESSION_ENDPOINT, parser)
        return response

    @staticmethod
    def _send_mysql_query(query, parser):
        sessions = AAASession.objects.using('sbr_sessions_1').filter(**query).order_by('-creation_time')[:1] or \
                   AAASession.objects.using('sbr_sessions_2').filter(**query).order_by('-creation_time')[:1]
        return parser(sessions)

    @staticmethod
    def _get_error_message(response_dom):
        error = "Error happened while retrieving session"

        if not response_dom.find(".//clientResponse/sessionResults[@type='failure']") is None and \
                response_dom.find(".//clientResponse/sessionResults[@type='failure']").getchildren():
            error = "SBR responded with a failure message"

        elif not response_dom.find(".//clientResponse/sessionResults[@type='timeout']") is None and \
                response_dom.find(".//clientResponse/sessionResults[@type='timeout']").getchildren():
            error = "SBR responded with a timeout message"

        elif not response_dom.find(".//clientResponse/sessionResults[@type='incomplete']") is None and \
                response_dom.find(".//clientResponse/sessionResults[@type='incomplete']").getchildren():
            error = "SBR responded with incomplete message"
        logger.error(error)
        return error

    def _get_success_items(self, response_dom):
        success_items = response_dom.find(".//clientResponse/sessionResults[@type='success']")
        if success_items is None or not bool(success_items.getchildren()):
            return {'action_result': False, 'action_error_message': self._get_error_message(response_dom)}
        return {'action_result': True, 'items': success_items}

    def _parse_aaa_session(self, sql_result):
        if not sql_result:
            return {'action_result': False, 'action_error_message': "No active session"}
        aaa_session = sql_result[0]
        return {'action_result': True, 'result': [
            {'Account-Info': aaa_session.cisco_account_info,
             'session_uid': aaa_session.account_session_id,
             'Framed-IP-Address': self._int2ip(aaa_session.framed_ip_address), 'Nas-Name': aaa_session.nas_name,
             'NAS-IP-Address': self._int2ip(aaa_session.nas_ip_address), 'Nas-Port': aaa_session.nas_port,
             'NAS-Port-ID': aaa_session.nas_port_id or aaa_session.calling_station_id,
             'Service-Info': aaa_session.service_name,
             'User-Name': aaa_session.subscriber_id
             }], 'action_error_message': ''}

    def _parse_coa_response(self, response_xml):
        try:
            parser = etree.XMLParser(remove_blank_text=True)
            response_dom = etree.fromstring(response_xml, parser)
            success_items = self._get_success_items(response_dom)
            if not success_items['action_result']:
                return success_items
            return {'action_result': True, 'action_error_message': ""}

        except etree.XMLSyntaxError, exp:
            logger.error("Failed to parse xml response from url %s: %s", RADIUS_SESSION_ENDPOINT, str(exp))
            return {'action_result': False, 'action_error_message': "Failed to parse xml response from url %s: %s" % (
                RADIUS_SESSION_ENDPOINT, str(exp))}

    def _get_aaa_session(self, query):
        parse_result = self._send_mysql_query(query, self._parse_aaa_session)
        if not parse_result['action_result']:
            return parse_result
        return {'action_result': True, 'sessions': parse_result['result'], 'action_error_message': ''}

    def _send_coa(self, service_name, session_result, coa_type, framed_ip=None, alt_ep=None, alt_dr_ep=None):
        xml_template = COA_START_REQ if coa_type == 'START' else COA_STOP_REQ

        coa_params = {
            'framed_ip_address': framed_ip if framed_ip else session_result['sessions'][0]['Framed-IP-Address'],
            'service_name': service_name
        }
        request_xml = xml_template % coa_params
        return self._send_xml_request(request_xml, self._parse_coa_response, alt_ep, alt_dr_ep)

    @staticmethod
    def _format_coa_result(session_result, coa_result):
        formatted_result = {
            'coa_result': coa_result['action_result'],
            'coa_error_message': coa_result['action_error_message']
        }
        if session_result:
            formatted_result.update({
                'session_ip': session_result['sessions'][0]['Framed-IP-Address'],
                'nas_ip': session_result['sessions'][0]['NAS-IP-Address'],
                'device_port': session_result['sessions'][0]['NAS-Port-ID'],
                'online_services': [session_result['sessions'][0]['Service-Info']],
            })
        return formatted_result


    @staticmethod
    def _format_multiple_coas_result(sessions, coa_results):
        results = []
        for i in range(len(coa_results)):
            results.append({
                'session_ip': sessions['sessions'][i]['Framed-IP-Address'],
                'nas_ip': sessions['sessions'][i]['NAS-IP-Address'],
                'device_port': sessions['sessions'][i]['NAS-Port-ID'],
                'online_services': [sessions['sessions'][i]['Service-Info']],
                'coa_result': coa_results[i]['action_result'],
                'coa_error_message': coa_results[i]['action_error_message']
            })
        return results

    def get_session_by_ip(self, ip_address):
        query = {'framed_ip_address': self._ip2int(ip_address)}
        session_result = self._get_aaa_session(query)
        if not session_result.get('action_result'):
            return session_result
        return {
            'action_result': True,
            'username': session_result['sessions'][0]['User-Name'],
            'action_error_message': ''
        }

    def get_session_by_name(self, subscriber_id):
        query = {'subscriber_id': subscriber_id}
        session_result = self._get_aaa_session(query)

        if not session_result.get('action_result'):
            return session_result
        return {
            'action_result': True,
            'IpAddress': session_result['sessions'][0]['Framed-IP-Address'],
            'action_error_message': ''
        }

    def send_start_coa(self, subscriber_id, service_name):
        query = {'subscriber_id': subscriber_id}
        session_result = self._get_aaa_session(query)
        if not session_result.get('action_result'):
            return session_result

        result = self._send_coa(service_name, session_result, coa_type='START')
        coa_result = self._format_coa_result(session_result, result)
        coa_result['started_service'] = service_name

        result['coa_result'] = coa_result
        return result

    def send_stop_coa(self, subscriber_id, service_name):
        query = {'subscriber_id': subscriber_id}
        session_result = self._get_aaa_session(query)
        if not session_result.get('action_result'):
            return session_result

        result = self._send_coa(service_name, session_result, coa_type='STOP')
        coa_result = self._format_coa_result(session_result, result)
        coa_result['stopped_service'] = service_name

        result['coa_result'] = coa_result
        return result

    def get_full_session(self, subscriber_id):
        query = {'subscriber_id': subscriber_id}
        session_result = self._get_aaa_session(query)
        if not session_result.get('action_result'):
            return session_result
        return {
            'action_result': True,
            'sessions': session_result['sessions'],
            'action_error_message': ''
        }

    def _send_multiple_coas(self, service_name, session_result, coa_type, alt_ep=None, alt_dr_ep=None):
        xml_template = COA_START_REQ if coa_type == 'START' else COA_STOP_REQ
        results = []
        for i in range(len(session_result['sessions'])):
            coa_params = {
                'framed_ip_address': session_result['sessions'][i]['Framed-IP-Address'],
                'service_name': service_name
            }
            request_xml = xml_template % coa_params
            results.append(self._send_xml_request(request_xml, self._parse_coa_response, alt_ep, alt_dr_ep))
        return results

    def start_redirect_coa(self, subscriber_id, service_name):
        query = {'subscriber_id': subscriber_id}
        session_result = self._get_aaa_session(query)
        if not session_result.get('action_result'):
            return session_result

        result = self._send_multiple_coas(service_name, session_result, coa_type='START',
                                          alt_ep=RADIUS_REDIR_SESSION_ENDPOINT, alt_dr_ep=RADIUS_REDIR_SESSION_ENDPOINT)
        coa_results = self._format_multiple_coas_result(session_result, result)
        return {'action_result': True, 'coa_results': coa_results}

    def stop_redirect_coa(self, ip, service_name):
        # query = {'framed_ip_address': self._ip2int(ip)}
        # session_result = self._get_aaa_session(query)
        # if not session_result.get('action_result'):
        #     return session_result

        result = self._send_coa(service_name, session_result=None, coa_type='STOP', framed_ip=ip,
                                          alt_ep=RADIUS_REDIR_SESSION_ENDPOINT, alt_dr_ep=RADIUS_REDIR_SESSION_ENDPOINT)
        return self._format_coa_result(session_result=None, coa_result=result)

