import logging
import time
import ldap
from ldap import modlist
from mw1_backend.configs import LDAP_SLEEP_TIME, LDAP_HOST, VALID_OPTION_PACK_ZONES
from .models import SBRMember, SBRProduct, SBRSubscribedProduct, WifiAdslMapping
from django.db import IntegrityError
from shared.common import send_error_mail
import string
import crypt
import random

logger = logging.getLogger(__name__)


class LDAPClient(object):
    def __init__(self):
        import ldap
        from mw1_backend.configs import LDAP_USER, LDAP_HOST, LDAP_TIMEOUT, LDAP_PASSWORD

        self.server = ldap.initialize(LDAP_HOST)
        self.server.set_option(ldap.OPT_NETWORK_TIMEOUT, LDAP_TIMEOUT)
        self.server.simple_bind_s(LDAP_USER, LDAP_PASSWORD)

    def _crypt_password(self, user_password):
        char_set = string.ascii_uppercase + string.digits
        salt = ''.join(random.sample(char_set, 8))
        salt = '$1$' + salt + '$'
        pwd = "{CRYPT}" + crypt.crypt(str(user_password), salt)
        return pwd

    def _exec_profile_change(self, user_id, mod_attrs, operation='modify', is_adsl=True):
        """performs an operation on ldap server
        :param operation: modify or add
        """
        logger.debug("Changing LDAP profile for user (%s)", user_id)
        try:
            if is_adsl:
                dn = 'uid={0},ou=tedata.net.eg,ou=corporate,ou=email,o=TE Data,c=eg'.format(str(user_id))
            else:  # wifi subscriber
                dn = "uid={0},ou=telive.net,ou=corporate,ou=email,o=TE Data,c=eg".format(
                    str(user_id))
            if operation == 'modify':
                self.server.modify_s(dn, mod_attrs)
            else:
                self.server.add_s(dn, modlist.addModlist(mod_attrs))
                time.sleep(LDAP_SLEEP_TIME)
                logger.info("User (%s) was added to LDAP", user_id)
            logger.info("User (%s)'s LDAP profile changed", user_id)
            return {'action_result': True, 'action_error_message': ''}
        except ldap.SERVER_DOWN:
            logger.error("Connection to LDAP server (%s) timedout", LDAP_HOST)
            return {'action_result': False, 'action_error_message': "Connection to LDAP server (%s) timedout"
                                                                    " (Timeout was reached)" % LDAP_HOST}
        except ldap.NO_SUCH_ATTRIBUTE:
            logger.warn("Subscriber %s already has no optionpack attributes", user_id)
            return {'action_result': True, 'action_error_message': ''}
        except Exception as e:
            logger.error("Error happened while contacting LDAP, msg: (%s)", str(e))
            return {'action_result': False, 'action_error_message': "Error happened while contacting LDAP, msg: (%s)" %
                                                                    str(e)}

    def add_new_user_profile(self, user_id, service):
        logger.debug("Adding an LDAP profile for user (%s)", user_id)
        user_id = user_id.encode('utf-8').strip()
        attrs = {'cn': '%s' % user_id, 'sn': '%s' % user_id,
                 'objectclass': ['top', 'person', 'inetOrgPerson', 'organizationalPerson',
                                 'radiusprofile', 'TEdataSubscriber'], 'uid': '%s' % user_id,
                 'radiusLoginService': service}

        SBRMember.objects.using('service').get_or_create(username=user_id)
        SBRSubscribedProduct.objects.using('service').filter(username=user_id).delete()  # just in case
        products = SBRProduct.objects.using('service').filter(service_name=service)
        if products:
            product = products[0]
            SBRSubscribedProduct.objects.using('service').create(username=user_id, service_name=service,
                                                             product_id=product.id)
        return self._exec_profile_change(user_id, attrs, operation='add')

    def get_user_profile(self, user_id):
        logger.debug("Getting user (%s)'s LDAP profile", user_id)
        try:
            if "wifi" in user_id:
                ldap_profile = self.server.search_s('ou=telive.net,ou=corporate,ou=email,o=TE Data,c=eg', ldap.SCOPE_SUBTREE, '(uid=%s)' % user_id)
            else:
                ldap_profile = self.server.search_s('ou=tedata.net.eg,ou=corporate,ou=email,o=TE Data,c=eg', ldap.SCOPE_SUBTREE, '(uid=%s)' % user_id)
            logger.info("Got user (%s)'s LDAP profile", user_id)
            return {'action_result': True, 'profile': ldap_profile, 'action_error_message': ''}
        except ldap.SERVER_DOWN:
            logger.error("connection to LDAP server (%s) timedout", LDAP_HOST)
            return {'action_result': False, 'action_error_message': "self to LDAP server (%s) timedout"
                                                                    " (Timeout was reached)" % LDAP_HOST}
        except Exception as e:
            logger.error("Error happened while contacting LDAP, msg: (%s)", str(e))
            return {'action_result': False, 'action_error_message': "Error happened while contacting LDAP, msg: (%s)" %
                                                                    str(e)}

    def check_user_exists(self, user_id):
        logger.debug("Checking user (%s) exists in ldap records", user_id)
        user_id = user_id.encode('utf-8').strip()
        result = self.get_user_profile(user_id)
        if not result['action_result']:
            return result
        logger.info("user (%s) exists: (%s)", user_id, bool(result['profile']))
        return {'action_result': True, 'user_exists': bool(result['profile']), 'action_error_message': ''}

    def get_subscriber_services(self, user_id):
        user_id = user_id.encode('utf-8').strip()
        result = self.check_user_exists(user_id)
        # if an LDAP connection error happened, return the error.
        if not result['action_result']:
            return result
        if not result['user_exists']:
            return {'action_result': True, 'action_error_message': "subscriber %s doesn't exists" % user_id,
                    'user_exists': False}

        result = self.get_user_profile(user_id)
        if not result['action_result']:
            return result

        profile = result['profile'][0][1]
        if not profile.get('radiusLoginService'):
            return {'action_result': True, 'services': [], 'action_error_message': ''}
        services = [service for service in profile.get('radiusLoginService')[0].split(",") if service]
        return {'action_result': True, 'services': services, 'action_error_message': ''}

    def replace_ldap_services(self, user_id, new_services, is_adsl=False):
        logger.info("replacing LDAP services for user (%s) with (%s)", user_id, new_services)

        mod_attrs = [(ldap.MOD_REPLACE, 'radiusLoginService', ",".join(new_services))]
        if is_adsl:
            SBRSubscribedProduct.objects.using('service').filter(username=user_id).delete()
            SBRMember.objects.using('service').get_or_create(username=user_id)
            products = SBRProduct.objects.using('service').filter(service_name__in=new_services)

            for product in products:
                SBRSubscribedProduct.objects.using('service').create(username=user_id, service_name=product.service_name,
                                                                 product_id=product.id)
            return self._exec_profile_change(user_id, mod_attrs, is_adsl=is_adsl)
        else:
            if len(new_services):
                WifiAdslMapping.objects.filter(wifi_username=user_id).update(service_name=new_services[0])
            else:
                WifiAdslMapping.objects.filter(wifi_username=user_id).delete()
            return self._exec_profile_change(user_id, mod_attrs, is_adsl=is_adsl)


        return self._exec_profile_change(user_id, mod_attrs)

    def replace_option_pack(self, user_id, request_params):
        logger.info("replacing OptionPack services on LDAP for user (%s) with (%s)", user_id, request_params)

        if request_params['isVrf']:
            radius_reply_item = ['cisco-avpair = "lcp:interface-config=ip vrf forwarding {0}"'.format(
                request_params['vrfName']), 'cisco-avpair += "lcp:interface-config=ip address {0} {1}"'.format(
                request_params['wanPeIp'], request_params['wanMask'])]
        else:
            radius_reply_item = 'cisco-avpair = "lcp:interface-config=ip vrf forwarding {0}.BB"'.format(
                request_params['zone']) if request_params['zone'] in VALID_OPTION_PACK_ZONES else []
        mod_attrs = [(ldap.MOD_REPLACE, 'radiusFramedIPAddress', str(request_params['wanIp'])),
                     (ldap.MOD_REPLACE, 'radiusFramedIPNetmask', str(request_params['wanMask'])),
                     (ldap.MOD_REPLACE, 'radiusFramedRoute', "{0} {1} {2}".format(request_params['lanIp'],
                                                                                  request_params['lanMask'],
                                                                                  request_params['wanIp'])),
                     (ldap.MOD_REPLACE, 'radiusGroupName', [str(request_params['lanIp'])]),
                     (ldap.MOD_REPLACE, 'radiusReplyItem', radius_reply_item),
                     ]
        return self._exec_profile_change(user_id, mod_attrs, operation='modify')

    def delete_option_pack(self, user_id):
        mod_attrs = [(ldap.MOD_DELETE, 'radiusFramedIPAddress', []),
                     (ldap.MOD_DELETE, 'radiusFramedIPNetmask', []),
                     (ldap.MOD_DELETE, 'radiusFramedRoute', []),
                     (ldap.MOD_DELETE, 'radiusGroupName', []),
                     (ldap.MOD_DELETE, 'radiusReplyItem', [])
                     ]

        return self._exec_profile_change(user_id, mod_attrs, operation='modify')

    def add_or_change_service(self, user_id, new_service, request_params=False):
        logger.debug("Adding or changing service (%s) for user (%s)", new_service, user_id)
        user_id = user_id.encode('utf-8').strip()
        new_service = new_service.encode('utf-8').strip()
        result = self.check_user_exists(user_id)
        # if an LDAP connection error happened, return the error.
        if not result['action_result']:
            return result

        if not result['user_exists'] and request_params['isOptionPack']:
            return {'action_result': True, 'action_error_message': "Can't add option pack ... "
                                                                    "subscriber {0} doesn't exist".format(user_id),
                    'user_exists': False}
        if request_params['isOptionPack']:
            return self.replace_option_pack(user_id, request_params)

        if not result['user_exists']:
            # create the user, assign the service .. whether it succeeds or not .. it's a final step .. return.
            result = self.add_new_user_profile(user_id, new_service)
            return result
            # user exists .. query services, replace old monthly services with new ones.
        result = self.get_subscriber_services(user_id)
        if not result['action_result']:
            return result
        services = result['services']
        if new_service in services:
            # service already exists .. no need to re-add it
            return {'action_result': True, 'action_error_message': ''}
        if not services:
            return self.replace_ldap_services(user_id, [new_service], is_adsl=True)
        new_services = services[:]

        # Change for adding services start with D for Gaming packages
        if new_service.startswith('MONTHLY') or new_service.startswith("D") or new_service.startswith("QUOTA"):
            # check if subscriber has monthly or gaming or quota services in his old services
            monthly_quota_flag = bool(filter(lambda service: service.startswith('MONTHLY') or
                                                             service.startswith("D") or
                                                             service.startswith("QUOTA"), services))
            if monthly_quota_flag:
                for service in services:
                    if service.startswith('MONTHLY') or service.startswith("D") or service.startswith("QUOTA"):
                        new_services.remove(service)
                        new_services.append(new_service)
            else:
                new_services.append(new_service)
        else:
            new_services.append(new_service)

        return self.replace_ldap_services(user_id, new_services, is_adsl=True)

    def remove_service(self, user_id, service_name, is_adsl=True):
        logger.debug("Removing service (%s) from user (%s)'s profile", service_name, user_id)
        user_id = user_id.encode('utf-8').strip()
        result = self.get_subscriber_services(user_id)
        if not result['action_result'] or result.get('user_exists', False):
            return result
        services = result['services']
        if not service_name in services:
            logger.info("service (%s) is already removed from user (%s)'s profile", service_name, user_id)
            return {'action_result': True, 'action_error_message': ''}
        services.remove(service_name)
        logger.info("service (%s) removed from user (%s)'s profile .. commiting to LDAP ..", service_name, user_id)
        return self.replace_ldap_services(user_id, services, is_adsl)

    def reset_profile(self, user_id):
        logger.debug("reseting profile for user (%s)", user_id)
        return self.replace_ldap_services(user_id, [])

    def add_wifi_subscriber(self, wifi_subscriber, password, venue_subscriber=False, service_name='WIFI_SERVICE',
                            adsl_subscriber=None):
        attrs = {}
        attrs['cn'] = 'WiFi'
        attrs['sn'] = 'User'
        attrs['mail'] = str(wifi_subscriber)

        attrs['radiusLoginService'] = service_name
        attrs['objectclass'] = ['top', 'person', 'inetOrgPerson', 'organizationalPerson', 'radiusprofile',
                                'TEdataSubscriber']
        attrs['radiusAuthType'] = 'PAP'
        attrs['radiusProfileDn'] = 'cn=BHH-wifi-users,ou=radius-profiles,o=TE Data,c=eg'
        attrs['dialupAccess'] = 'Accept'
        attrs['uid'] = str(wifi_subscriber)

        if venue_subscriber:
            attrs['mobile'] = str(wifi_subscriber)
            attrs['uid'] += "@wifi.tedata.net.eg"
            attrs['mail'] += "@wifi.tedata.net.eg"
            attrs['userPassword'] = '%s' % self._crypt_password(password)
            attrs['radiususerPassword'] = '%s' % self._crypt_password(password)
            wifi_subscriber += "@wifi.tedata.net.eg"
        else:
            attrs['userPassword'] = password
            attrs['radiususerPassword'] = password
            attrs['radiusCheckItem'] = 'NAS-Port-Id = "{0}"'.format(str(wifi_subscriber))
            WifiAdslMapping.objects.filter(wifi_username=wifi_subscriber).delete()
            WifiAdslMapping.objects.create(wifi_username=wifi_subscriber, adsl_username=adsl_subscriber,
                                                        service_name=service_name)

        return self._exec_profile_change(wifi_subscriber, attrs, operation='add', is_adsl=False)

    def add_wifi_service(self, adsl_subscriber, wifi_subscriber, service, password):
        logger.debug("Adding  WiFi service (%s) for user (%s)", service, wifi_subscriber)

        result = self.check_user_exists(wifi_subscriber)

        if not result['action_result']:
            return result
        # if wifi subscriber exists ... we cannot re-add him.
        if result['user_exists']:
            return {'action_result': True, 'action_error_message': "subscriber {0} exists".format(wifi_subscriber),
                    'user_exists': True}

        return self.add_wifi_subscriber(wifi_subscriber, password, service_name=service,
                                        adsl_subscriber=adsl_subscriber)

    def update_wifi_service(self, wifi_subscriber, service):
        logger.debug("Updating  WiFi service (%s) for user (%s)", service, wifi_subscriber)
        result = self.check_user_exists(wifi_subscriber)
        if not result['action_result']:
            return result
        # if wifi subscriber doesn't exist ... we cannot update him
        if not result['user_exists']:
            return {'action_result': True,
                    'action_error_message': "subscriber {0} doesn't exist".format(wifi_subscriber),
                    'user_exists': False}

        result = self.get_subscriber_services(wifi_subscriber)
        if not result['action_result']:
            return result
        services = result['services']
        if service in services:
            # service already exists .. no need to re-add it
            return {'action_result': True, 'action_error_message': ''}
        return self.replace_ldap_services(wifi_subscriber, [service], is_adsl=False)

    def reset_user_password(self, user_id, password, is_adsl=True):
        logger.info("Changing LDAP password for user (%s)", user_id)
        password = '%s' % self._crypt_password(password)
        mod_attrs = [(ldap.MOD_REPLACE, 'userPassword', password),
                     (ldap.MOD_REPLACE, 'radiususerPassword', password)]
        return self._exec_profile_change(user_id, mod_attrs, is_adsl=is_adsl)

    def disconnect(self):
        logger.debug("Disconnecting client")
        self.server.unbind_s()


