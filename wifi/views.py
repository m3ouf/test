import ldap
import crypt
import json

from ldap_backend.ldap_profile import LDAPClient
#from pcrf_backend.client import PCRFClient
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from shared.common import send_error_mail
from .authorization import KeyAuthentication
from .helpers import CustomJSONRenderer, wifiConnect, send_sms_request, check_user_type, add_new_subscriber_device, \
    check_mactal_exits, get_subscriber_session, log_wifi_action, convert_arabic_numerals
from .serializers import WifiSubscriberSerializer
import logging
import traceback
import uuid

logger = logging.getLogger(__name__)


class SubscribersLogin(APIView):
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = (KeyAuthentication,)

    def post(self, request, mobile_no):
        mobile_no = convert_arabic_numerals(mobile_no)
        logger.info("Trying to login subscriber..")
        log_wifi_action(mobile_no, "LoginWiFiSubscriber", "Request to login a WiFi Subscriber.", None, request.data)
        serializer = WifiSubscriberSerializer(data=request.data, wifiFunction='loginWIFISubscriber')
        if not serializer.is_valid():
            response = {
                'errorCode': 3001,
                'errorMessage': "Parameters %s required but not provided or not valid." % serializer.errors.keys(),
                'successStatus': False
            }
            return Response(response)
        # Checks if the subscriber already has session with a valid service other than redirect.
        session = get_subscriber_session(serializer.validated_data.get('ip'))
        if session and session != 'NULL':
            log_wifi_action(mobile_no, "LoginWiFiSubscriber", "Subscriber already has an online session, should access internet normally.", True)
            response = {
                'errorCode': 0,
                'errorMessage': "",
                'successStatus': True
            }
            return Response(response)
        mactal = check_mactal_exits(serializer.validated_data.get('ip'))
        if not mactal:
            log_wifi_action(mobile_no, "LoginWiFiSubscriber", "Tried to login a user that doesn't have a device on mactal.", False)
            logger.warning("Tried to login a user that doesn't have a device on mactal.")
            response = {
                'errorCode': 4010,
                'errorMessage': "Authorization failed.",
                'successStatus': False
            }
            return Response(response)

        coa_sent = wifiConnect(serializer.validated_data.get('ip'), mobile_no)
        if not coa_sent:
            log_wifi_action(mobile_no, "LoginWiFiSubscriber", "Sending COA Failed.", False)
            response = {
                'errorCode': 4010,
                'errorMessage': "Authorization failed.",
                'successStatus': False
            }
            return Response(response)
        log_wifi_action(mobile_no, "LoginWiFiSubscriber", "Sending COA Succeeded, subscriber should access internet now!", True)
        response = {
            'errorCode': 0,
            'errorMessage': "",
            'successStatus': True
        }
        return Response(response)


class TESubscribersLogin(APIView):
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = (KeyAuthentication,)

    def post(self, request, subscriberId):
        subscriberId = convert_arabic_numerals(subscriberId)
        log_wifi_action(subscriberId, "LoginTEWiFiSubscriber", "Request to login a TE WiFi Subscriber.", None, request.data)
        serializer = WifiSubscriberSerializer(data=request.data, wifiFunction='loginTEWIFISubscriber')
        if not serializer.is_valid():
            response = {
                'errorCode': 3001,
                'errorMessage': "Parameters %s required but not provided or not valid." % serializer.errors.keys(),
                'successStatus': False
            }
            return Response(response)
        # Checks if the subscriber already has session with a valid service other than redirect.
        session = get_subscriber_session(serializer.validated_data.get('ip'))
        if session and session != 'NULL':
            log_wifi_action(subscriberId, "LoginTEWiFiSubscriber", "Subscriber already has an online session, should access internet normally.", True)
            response = {
                'errorCode': 0,
                'errorMessage': "",
                'successStatus': True
            }
            return Response(response)
        # mactal = check_mactal_exits(serializer.validated_data.get('ip'))
        # if not mactal:
        #     logger.warning("Tried to login a user that doesn't have a device on mactal.")
        #     response = {
        #         'errorCode': 4010,
        #         'errorMessage': "Authorization failed.",
        #         'successStatus': False
        #     }
        #     return Response(response)
        susbcriberFullId = '%s@wifi.tedata.net.eg' % subscriberId
        password = serializer.validated_data.get('password')
        try:
            ldap_client = LDAPClient()
            result = ldap_client.get_user_profile(susbcriberFullId)
            if not bool(result.get('profile', False)):
                log_wifi_action(subscriberId, "LoginTEWiFiSubscriber", "Subscriber doesn't have profile on LDAP.", False)
                response = {
                    'errorCode': 4012,
                    'errorMessage': "Subscriber Not Found.",
                    'successStatus': False
                }
                return Response(response)
            c_password = result['profile'][0][1]['radiususerPassword'][0][7:]
            password_match = crypt.crypt(password, c_password) == c_password
            if not password_match:
                log_wifi_action(subscriberId, "LoginTEWiFiSubscriber", "Entered password doesn't match subscriber's LDAP Password.", False)
                response = {
                    'errorCode': 4011,
                    'errorMessage': "Authorization failed.",
                    'successStatus': False
                }
                return Response(response)
            coa_sent = wifiConnect(serializer.validated_data.get('ip'), subscriberId)
            if not coa_sent:
                log_wifi_action(subscriberId, "LoginTEWiFiSubscriber", "Sending COA Failed.", False)
                response = {
                    'errorCode': 4010,
                    'errorMessage': "Authorization failed.",
                    'successStatus': False
                }
                return Response(response)
            log_wifi_action(subscriberId, "LoginTEWiFiSubscriber", "Sending COA Succeeded, subscriber should access internet now!", True)
            response = {
                'errorCode': 0,
                'errorMessage': "",
                'successStatus': True
            }
            return Response(response)
        except ldap.SERVER_DOWN:
            log_wifi_action(subscriberId, "LoginTEWiFiSubscriber", "Internal Server Occurred: LDAP Server Down", False)
            response = {
                'errorCode': 4010,
                'errorMessage': "Authorization failed.",
                'successStatus': False
            }
            return Response(response)
        except:
            transaction_id = uuid.uuid4()
            log_wifi_action(subscriberId, "LoginTEWiFiSubscriber", "Internal Server Occurred: Please contact administrator with request ID: %s" % transaction_id, False)
            send_error_mail("Internal Server Occurred while trying to Login TE WiFi Subscriber with Subscriber ID: %s \n"
                "Transaction ID: %s \n"
                "Request Parameters: %s \n"
                "Traceback: %s" % (subscriberId, transaction_id, json.dumps(request.data), traceback.format_exc()), "[WiFi] [LoginTEWiFiSubscriber] MW Backend Error")
            logger.warning("Couldn't find password for Subscriber %s" % subscriberId)
            response = {
                'errorCode': 4010,
                'errorMessage': "Authorization failed.",
                'successStatus': False
            }
            return Response(response)


class ADSLSubscribersLogin(APIView):
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = (KeyAuthentication,)

    def post(self, request, subscriberId):
        subscriberId = convert_arabic_numerals(subscriberId)
        log_wifi_action(subscriberId, "LoginADSLWiFiSubscriber", "Request to Check ADSL Subscriber", None, request.data)
        serializer = WifiSubscriberSerializer(data=request.data, wifiFunction='checkTEWIFISubscriber')
        if not serializer.is_valid():
            response = {
                'errorCode': 3001,
                'errorMessage': "Parameters %s required but not provided or not valid." % serializer.errors.keys(),
                'successStatus': False
            }
            return Response(response)
        try:
            ldap_client = LDAPClient()
            result = ldap_client.get_user_profile("%s@tedata.net.eg" % subscriberId)
            try:
                if not bool(result.get('profile', False)):
                    log_wifi_action(subscriberId, "LoginADSLWiFiSubscriber", "Subscriber doesn't have profile on LDAP.", False)
                    response = {
                        'errorCode': 4013,
                        'errorMessage': "Subscriber Not Found",
                        'successStatus': False
                    }
                    return Response(response)
                c_password = result['profile'][0][1]['radiususerPassword'][0][7:]
                password_match = crypt.crypt(serializer.validated_data.get('password'), c_password) == c_password
                if not password_match:
                    log_wifi_action(subscriberId, "LoginADSLWiFiSubscriber", "Entered password doesn't match subscriber's LDAP Password.", False)
                    response = {
                        'errorCode': 4013,
                        'errorMessage': "Subscriber Not Found",
                        'successStatus': False
                    }
                    return Response(response)
                response = {
                    'errorCode': 0,
                    'errorMessage': "",
                    'successStatus': True
                }
                return Response(response)
            except KeyError:
                transaction_id = uuid.uuid4()
                log_wifi_action(subscriberId, "LoginTEWiFiSubscriber", "Internal Server Occurred: Couldn't fetch subscriber password, Please contact administrator with request ID: %s" % transaction_id, False)
                send_error_mail("Internal Server Occurred while trying to Check for ADSL Subscriber with Subscriber ID: %s \n"
                    "Transaction ID: %s \n"
                    "Request Parameters: %s \n"
                    "Traceback: %s" % (subscriberId, transaction_id, json.dumps(request.data), traceback.format_exc()), "[WiFi] [LoginADSLWiFiSubscriber] MW Backend Error")
                logger.error("Error while quering user %s LDAP Password" % "%s@tedata.net.eg" % subscriberId)
                response = {
                    'errorCode': 4010,
                    'errorMessage': "Authorization failed.",
                    'successStatus': False
                }
                return Response(response)
        except ldap.SERVER_DOWN:
            log_wifi_action(subscriberId, "LoginADSLWiFiSubscriber", "Internal Server Occurred: LDAP Server Down", False)
            response = {
                'errorCode': 4010,
                'errorMessage': "Authorization failed.",
                'successStatus': False
            }
            return Response(response)
        except:
            transaction_id = uuid.uuid4()
            log_wifi_action(subscriberId, "LoginTEWiFiSubscriber", "Internal Server Occurred: Please contact administrator with request ID: %s" % transaction_id, False)
            send_error_mail("Internal Server Occurred while trying to Check for ADSL Subscriber with Subscriber ID: %s \n"
                            "Transaction ID: %s \n"
                            "Request Parameters: %s \n"
                            "Traceback: %s" % (subscriberId, transaction_id, json.dumps(request.data), traceback.format_exc()), "[WiFi] [LoginADSLWiFiSubscriber] MW Backend Error")
            logger.warning("Couldn't find password for Subscriber %s" % subscriberId)
            response = {
                'errorCode': 4010,
                'errorMessage': "Authorization failed.",
                'successStatus': False
            }
            return Response(response)


class Subscribers(APIView):
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = (KeyAuthentication,)

    def post(self, request):
        serializer = WifiSubscriberSerializer(data=request.data, wifiFunction='registerWIFISubscriber')
        if not serializer.is_valid():
            response = {
                'errorCode': 3001,
                'errorMessage': "Parameters %s required but not provided or not valid." % serializer.errors.keys(),
                'successStatus': False
            }
            return Response(response)
        mobileNo = convert_arabic_numerals(serializer.validated_data.get('mobileNo'))
        log_wifi_action(mobileNo, "RegisterWiFiSubscriber", "Request to register a new subscriber.", None, request.data)
        subscriber_id = "%s@wifi.tedata.net.eg" % mobileNo
        try:
            password = 'teW!F!_%s' % mobileNo
            ldap_client = LDAPClient()
            #pcrf_client = PCRFClient()
            try:
                service_name = check_user_type(serializer.validated_data.get('userType'))
                if not service_name:
                    response = {
                        'errorCode': 4020,
                        'errorMessage': "Registration Failed",
                        'successStatus': False
                    }
                    return Response(response)
                user_added_to_ldap = ldap_client.add_wifi_subscriber(wifi_subscriber=mobileNo, password=password,
                                                                     venue_subscriber=True, service_name=service_name,
                                                                     adsl_subscriber=None)
            except ldap.ALREADY_EXISTS:
                # Subscriber already exists in LDAP.
                logger.warning('Tried to add a WiFi subscriber to LDAP, but the subscriber already exists..')
                log_wifi_action(mobileNo, "RegisterWiFiSubscriber", "Tried to add subscriber to LDAP but found subscriber already exists.", None)
                user_added_to_ldap = True
                # response = {
                #     'errorCode': 4021,
                #     'errorMessage': "Subscriber already exists",
                #     'successStatus': False
                # }
                # return Response(response)
            ldap_client.disconnect()

            #start_date = str(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).replace(" ", "T") + "+02:00"
            #end_date = str(datetime.now().replace(hour=23, minute=59, second=59, microsecond=59)).replace(" ", "T") + "+02:00"
            #user_added_to_pcrf = pcrf_client.provision_subscriber(subscriber_id=subscriber_id, service_name=service_name, start_date=start_date, end_date=end_date)

            if user_added_to_ldap:
                log_wifi_action(mobileNo, "RegisterWiFiSubscriber", "Adding subscriber to LDAP succeeded.", None)
                device_added_response = add_new_subscriber_device(serializer.validated_data.get('ip'),
                                                                  serializer.validated_data.get('userType'),
                                                                  mobileNo)
                return Response(device_added_response)
            else:
                log_wifi_action(mobileNo, "RegisterWiFiSubscriber", "Adding subscriber to LDAP Failed.", False)
                response = {
                    'errorCode': 4020,
                    'errorMessage': "Registration Failed",
                    'successStatus': False
                }
                return Response(response)
        except ldap.SERVER_DOWN:
            log_wifi_action(mobileNo, "RegisterWiFiSubscriber", "Internal Server Occurred: LDAP Server Down", False)
            logger.error("LDAP Server went down while registering a new WiFi user..")
            response = {
                'errorCode': 4020,
                'errorMessage': "Registration Failed",
                'successStatus': False
            }
            return Response(response)
        except:
            logger.error("Error while registering a new WiFi user (%s).." % subscriber_id)
            transaction_id = uuid.uuid4()
            log_wifi_action(mobileNo, "RegisterWiFiSubscriber", "Internal Server Occurred: Please contact administrator with request ID: %s" % transaction_id, False)
            send_error_mail("Internal Server Occurred while trying to Register a new WiFi Subscriber with Mobile Number: %s \n"
                "Transaction ID: %s \n"
                "Request Parameters: %s \n"
                "Traceback: %s" % (mobileNo, transaction_id, json.dumps(request.data), traceback.format_exc()), "[WiFi] [RegisterWiFiSubscriber] MW Backend Error")
            response = {
                'errorCode': 4020,
                'errorMessage': "Registration Failed",
                'successStatus': False
            }
            return Response(response)


class SubscriberDevices(APIView):
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = (KeyAuthentication,)

    def post(self, request, mobile_no):
        mobile_no = convert_arabic_numerals(mobile_no)
        log_wifi_action(mobile_no, "AddSubscriberDevice", "Request to add a new Subscriber Device.", None, request.data)
        serializer = WifiSubscriberSerializer(data=request.data, wifiFunction='manageSubscriberDevices')
        if not serializer.is_valid():
            response = {
                'errorCode': 3001,
                'errorMessage': "Parameters %s required but not provided or not valid." % serializer.errors.keys(),
                'successStatus': False
            }
            return Response(response)
        device_added_response = add_new_subscriber_device(serializer.validated_data.get('ip'), serializer.validated_data.get('userType'), mobile_no)
        return Response(device_added_response)


class SubscriberActivationCode(APIView):
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = (KeyAuthentication,)

    def post(self, request, mobile_no):
        mobile_no = convert_arabic_numerals(mobile_no)
        log_wifi_action(mobile_no, "SendActivationCode", "Request to send activation code.", None, request.data)
        serializer = WifiSubscriberSerializer(data=request.data, wifiFunction='sendActivationCode')
        if not serializer.is_valid():
            response = {
                'errorCode': 3001,
                'errorMessage': "Parameters %s required but not provided or not valid." % serializer.errors.keys(),
                'successStatus': False
            }
            return Response(response)
        sms_sent = send_sms_request(mobile_no, serializer.validated_data.get('activationCode'))
        if not sms_sent:
            log_wifi_action(mobile_no, "SendActivationCode", "Sending activation code failed.", False)
            response = {
                'errorCode': 4041,
                'errorMessage': "Message not sent.",
                'successStatus': False
            }
        else:
            log_wifi_action(mobile_no, "SendActivationCode", "Sending activation code succeeded.", True)
            response = {
                'errorCode': 0,
                'errorMessage': "",
                'successStatus': True
            }
        return Response(response)


class SubscriberForgetPassword(APIView):
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = (KeyAuthentication,)

    def post(self, request):
        serializer = WifiSubscriberSerializer(data=request.data, wifiFunction='registerWIFISubscriber')
        if not serializer.is_valid():
            response = {
                'errorCode': 3001,
                'errorMessage': "Parameters %s required but not provided or not valid." % serializer.errors.keys(),
                'successStatus': False
            }
            return Response(response)
