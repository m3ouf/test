import json
import logging
import pycurl
import MySQLdb
import ldap
import socket
from django.http import HttpResponse
from django.db import OperationalError
from socket import timeout
from mw1_backend.configs import LDAP_HOST
from shared.common import send_error_mail, send_404_error_message
from xml.sax import SAXParseException

logger = logging.getLogger(__name__)


def check_params(*required_args):
    """parameterized decorator, it makes sure that specific http parameters exist in both HTTP GET and POST requests."""

    def param_checker(func):
        def match_params(request, *args, **kwargs):
            logger.debug("Checking for required parameters.")
            if not request:
                result = {
                    'success': False,
                    'msg': 'Function needs a valid request object'
                }
                return HttpResponse(json.dumps(result), status=400)
            provided_args = request.REQUEST
            unprovided_args = []
            for argument in required_args:
                if not argument in provided_args:
                    unprovided_args.append(argument)

            if len(unprovided_args):
                logger.error('arguments %s are required but not provided' % unprovided_args)
                result = {
                    'success': False,
                    'msg': 'arguments %s are required but not provided' % unprovided_args
                }
                return HttpResponse(json.dumps(result), status=400)
            return func(request, *args, **kwargs)

        return match_params

    return param_checker


def permission_required(required_permission):
    """parameterized decorator, it makes sure that user has sufficient permissions to perform the action."""

    def param_checker(func):
        def match_params(request, *args, **kwargs):
            logger.debug("Checking for required permissions.")
            if not request:
                result = {
                    'success': False,
                    'msg': 'Function needs a valid request object'
                }
                return HttpResponse(json.dumps(result), status=400)
            if request.user.has_perm(required_permission):
                return func(request, *args, **kwargs)
            return HttpResponse(json.dumps({'error': True, 'error_message': 'Insufficient permissions'}),
                                status=401, mimetype="application/json")

        return match_params

    return param_checker


def timeout_handler(func):
    """Used internally inside the AAA client to indicate a connection error which allows us to reconnect to the DR site
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (timeout, pycurl.error) as e:
            logger.error(str(e))
            return {'action_result': False, 'connection_error': True, 'action_error_message': '(Timeout was reached)'}

    return wrapper


def xml_error_handler(func):
    """handles SAXParserExceptions"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SAXParseException as e:
            logger.error("Subscriber has a corrupted profile")
            return {'action_result': False, 'connection_error': False,
                    'action_error_message': "subscriber does not exist"}
    return wrapper


def handle_connection_error(func):
    """"""

    def wrapper(*args, **kwargs):

        try:
            return func(*args, **kwargs)
        except (MySQLdb.OperationalError, OperationalError) as e:
            send_error_mail("MySQL Connection Error, %s" % str(e))
            return HttpResponse(json.dumps({'success': False, 'msg': "MySQL Connection Error (Timeout was reached)"}),
                                content_type="application/json")

        except ldap.SERVER_DOWN:
            send_error_mail("LDAP Connection Error")
            response = {'success': False,
                        'msg': "Couldn't connect to LDAP server on (%s), (Timeout was reached)" % LDAP_HOST}
            return HttpResponse(json.dumps(response), content_type="application/json")

    return wrapper


class Singleton(object):
    """Implements the singleton pattern"""

    def __init__(self, klass):
        self.decoreted_class = klass
        self.instance = None

    def __call__(self, *args, **kwargs):
        if not self.instance:
            self.instance = self.decoreted_class(*args, **kwargs)
        return self.instance


def validate_inputs(required_arg):
    """deprecates check_params"""
    def param_checker(func):
        def match_params(ctx, request, *args, **kwargs):
            data = request.query_params if request.method == 'GET' else request.data
            serializer = required_arg(data=data)
            if not serializer.is_valid():
                return send_404_error_message(serializer)
            kwargs['serializer'] = serializer
            return func(ctx, request, *args, **kwargs)
        return match_params
    return param_checker