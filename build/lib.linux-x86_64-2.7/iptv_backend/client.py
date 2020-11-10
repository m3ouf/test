from shared.decorators import Singleton
from mw1_backend.configs import  PYCURL_TIMEOUT, IPTV_WSDL, IPTV_ENDPOINT, IPTV_USER, IPTV_PASS
from suds.client import Client
from suds import WebFault, TypeNotFound
import logging
import re

logger = logging.getLogger(__name__)


@Singleton
class IPTVClient(object):
    def __init__(self):
        self.client = Client(IPTV_WSDL)
        self.client.set_options(location=IPTV_ENDPOINT, timeout=PYCURL_TIMEOUT)

    def _format_error(self, error_msg):
        result = re.search("'(.*)'", error_msg)
        return result.groups()[0] if result else ""

    def create_iptv_session(self):
        try:
            session_id = self.client.service.createSession(userName=IPTV_USER, password=IPTV_PASS)
            return {'action_result': True,
                    'action_error_message': "",
                    'session_id': session_id
            }
        except WebFault as e:
            return {'action_result': False,
                    'action_error_message': self._format_error(str(e))}

    def release_iptv_session(self, session_id):
        try:
            self.client.service.releaseSession(sessionId=session_id)
            return {'action_result': True,
                    'action_error_message': "",
            }
        except WebFault as e:
            return {'action_result': False,
                    'action_error_message': self._format_error(str(e))}

    def fetch_tv_subscriptions(self, session_id, customer_number):
        try:
            subscriptions = self.client.service.fetchTVSubscriptions(sessionId=session_id,
                                                                     customerNumber=customer_number)
            return {'action_result': True,
                    'action_error_message': "",
                    'subscription': subscriptions}

        except WebFault as e:
            return {'action_result': False,
                    'action_error_message': self._format_error(str(e))}

    def create_customer(self, session_id, customer_number):
        try:
            customer_data = self.client.factory.create("Customer")
            customer_data.customerNumber = customer_number
            customer_data.customerName = customer_number
            customer_data.currencyCode = "EGP"
            self.client.service.createCustomer(sessionId=session_id, customer=customer_data)
            return {'action_result': True,
                    'action_error_message': ""}

        except WebFault as e:
            return {'action_result': False,
                    'action_error_message': self._format_error(str(e))}

    def _get_regional_headends(self, session_id):
        return self.client.service.getRegionalHeadEnds(sessionId=session_id)

    def order_tv_subscription(self, session_id, customer_number, package_name, mac_address):
        try:


            regional_headends = self._get_regional_headends(session_id)

            region_he = self.client.factory.create("RegionalHeadEnd")
            region_he.name = regional_headends[0].name



            tv_subscription = self.client.factory.create("TVSubscription")
            tv_subscription.customerNumber = customer_number
            tv_subscription.vodEnabled = True
            tv_subscription.regionalHeadEnd = region_he
            tv_subscription.pinCode = 1234

            package = self.client.factory.create("ChannelPackage")
            package.name = package_name
            tv_subscription.packages = [package]

            stb = self.client.factory.create("STB")
            stb.macAddress = mac_address
            stb.model = "amino"
            tv_subscription.stbs = [stb]
            portal_info = self.client.factory.create("TVPortalInformation")
            portal_info.firstName = customer_number
            portal_info.lastName = "User"
            portal_info.email = customer_number
            tv_subscription.portalInformation = portal_info
            self.client.service.orderTVSubscription(sessionId=session_id,
                                                                          tvSubscription=tv_subscription)
            return {'action_result': True,
                    'action_error_message': ""}
        except WebFault as e:
            return {'action_result': False,
                    'action_error_message': self._format_error(str(e))}

    def fetch_tv_subscription(self, session_id, tv_subscription_id):
        try:
            subscription = self.client.service.fetchTVSubscription(sessionId=session_id,
                                                                     tvSubscriptionId=tv_subscription_id)
            return {'action_result': True,
                    'action_error_message': "",
                    'subscription': subscription}

        except WebFault as e:
            return {'action_result': False,
                    'action_error_message': self._format_error(str(e))}

    def block_tv_subscription(self, session_id, subscription_id):
        try:
            self.client.service.blockTVSubscription(sessionId=session_id, tvSubscriptionId=subscription_id)
            return {'action_result': True,
                    'action_error_message': ""}
        except WebFault as e:
            return {'action_result': False,
                    'action_error_message': self._format_error(str(e))}

    def unblock_tv_subscription(self, session_id, subscription_id):
        try:
            self.client.service.unBlockTVSubscription(sessionId=session_id, tvSubscriptionId=subscription_id)
            return {'action_result': True,
                    'action_error_message': ""}

        except WebFault as e:
            return {'action_result': False,
                    'action_error_message': self._format_error(str(e))}

    def _remove_channel_package(self, session_id, subscription_id, packages):

        try:

            self.client.service.removeChannelPackage(sessionId=session_id, tvSubscriptionId=subscription_id,
                                                     channelPackage=packages)
            return {'action_result': True,
                    'action_error_message': ""}

        except WebFault as e:
            return {'action_result': False,
                    'action_error_message': self._format_error(str(e))}

    def _add_channel_package(self, session_id, subscription_id, package):
        try:
            channel_package = self.client.factory.create("ChannelPackage")
            channel_package.name = package
            self.client.service.addChannelPackage(sessionId=session_id, tvSubscriptionId=subscription_id,
                                                     channelPackage=[channel_package])
            return {'action_result': True,
                    'action_error_message': ""}

        except WebFault as e:
            return {'action_result': False,
                    'action_error_message': self._format_error(str(e))}


    def add_or_change_package(self, session_id, subscription_id, package_name):
        result = self.fetch_tv_subscription(session_id, subscription_id)
        if not result['action_result']:
            return result
        packages = result['subscription']['packages']
        result = self._remove_channel_package(session_id, subscription_id, packages)
        if not result['action_result']:
            return result
        result = self._add_channel_package(session_id, subscription_id, package_name)
        if not result['action_result'] and not result['action_error_message'].endswith("can not be added again."):
            return result
        return {'action_result': True}

    def remove_stb(self, session_id, subscription_id, customer_number, mac_address):
        try:
            stb = self.client.factory.create("STB")
            stb.model = "amino"
            stb.macAddress = mac_address
            self.client.service.removeSTB(sessionId=session_id, tvSubscriptionId=subscription_id, stb=stb)
            return {'action_result': True, 'action_error_message': ""}
        except WebFault as e:
            return {'action_result': False,
                    'action_error_message': self._format_error(str(e))}

    def _add_stb(self, session_id, subscription_id, customer_number, mac_address):
        try:
            stb = self.client.factory.create("STB")
            stb.customerNumber = customer_number
            stb.model = "amino"
            stb.macAddress = mac_address
            stb.languageCode = "en"
            stb.status = "A"
            self.client.service.addSTB(session_id, subscription_id, stb)
            return {'action_result': True, 'action_error_message': ""}

        except WebFault as e:
            return {'action_result': False,
                    'action_error_message': self._format_error(str(e))}

    def add_or_replace_stb(self, session_id, subscription_id, customer_number, mac_address):
        result = self.fetch_tv_subscription(session_id, subscription_id)
        if not result['action_result']:
            return result
        stb = result['stb']
        if stb and mac_address == stb.get('mac_address', ""):
            return {'action_result': True}
        elif stb and mac_address != stb.get('mac_address', ""):
            self.remove_stb(session_id, subscription_id, customer_number, stb['mac_address'])

        result = self._add_stb(session_id, subscription_id, customer_number, mac_address)
        if not result['action_result'] and not result['action_error_message'].endswith("can not be added again."):
            return result
        return {'action_result': True}

    def remove_iptv_customer(self, session_id, customer_number):
        try:
            self.client.service.removeCustomer(sessionId=session_id, customerNumber=customer_number)
        except WebFault as e:
            return {'action_result': False,
                    'action_error_message': self._format_error(str(e))}
