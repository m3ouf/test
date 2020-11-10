"""Concrete implementation for SNMP behaviors"""
from interfaces import QuerySnmpBehavior, SetSnmpBehavior, GetSnmpBehavior, TelnetBehavior
from mw1_backend.configs import BASE_QUERY_VCI_35, BASE_QUERY_VCI_40, BASE_QUERY_INDEX, SNMP_GET_COMMUNITY, \
    SNMP_SET_COMMUNITY, SNMP_VERSION, BASE_VPI, BASE_OID, BASE_ACTION, BASE_INNER_VLAN, BASE_VLAN, \
    BASE_VCI, BASE_ENABLE, BASE_RX, BASE_TX, BASE_ADSL,  ALCATEL_TELNET_PASS, \
    ALCATEL_TELNET_USER, ZTE_TELNET_PASS, ZTE_TELNET_USER, TELNET_DEBUG_LEVEL, HUAWEI5600T_TELNET_PASS, \
    HUAWEI5600T_TELNET_USER, HUAWEI5600_TELNET_PASS, HUAWEI5600_TELNET_USER, JUNIPER_ROUTER_TELNET_USER, \
    JUNIPER_ROUTER_TELNET_PASS, HUAWEI_FTTH_TELNET_USER, HUAWEI_FTTH_TELNET_PASS, \
    ZTE_FTTH_TELNET_USER, ZTE_FTTH_TELNET_PASS, ERICSSON_FTTH_TELNET_USER, ERICSSON_FTTH_TELNET_PASS
from collections import namedtuple
from models import Zte5200Oids, ZteC30019Oids, ZteC30021Oids
from Exscript.util.interact import read_login
from Exscript.protocols import Telnet
from Exscript.protocols.drivers.junos import JunOSDriver
from Exscript.protocols.drivers.vxworks import VxworksDriver
from Exscript.protocols.drivers.isam import IsamDriver
from Exscript.protocols.drivers.zte import ZteDriver
from Exscript.protocols.drivers.ericsson_ban import EricssonBanDriver
from Exscript import Account
import netsnmp
import telnetlib
import time


class QueryAllAttributesBehavior(QuerySnmpBehavior):
    def get_query_oid(self, port, card, vci):
        oid = BASE_QUERY_VCI_35 if vci == 35 else BASE_QUERY_VCI_40
        query_oid = oid.format(BASE_QUERY_INDEX + port * 64 + 8192 * (card - 1))
        return query_oid

    def get_adsl_attributes(self, service_port_index):
        AdslAttributes = namedtuple('AdslAttributes', ["second_port_index", "vpi", "vci", "vlan", "inner_vlan",
                                                       "action", 'rx', 'tx', 'adsl'])
        attributes = AdslAttributes(BASE_OID.format(service_port_index),
                                    BASE_VPI.format(service_port_index), BASE_VCI.format(service_port_index),
                                    BASE_VLAN.format(service_port_index), BASE_INNER_VLAN.format(service_port_index),
                                    BASE_ACTION.format(service_port_index),
                                    BASE_RX.format(service_port_index), BASE_TX.format(service_port_index), BASE_ADSL.format(service_port_index))
        return attributes

    @staticmethod
    def get_enable_attribute(service_port_index):
        return BASE_ENABLE.format(service_port_index)


class QueryDatabseAttributesBehavior(QuerySnmpBehavior):
    def __init__(self, make):
        makes = {'c300-19': ZteC30019Oids, 'c300-21': ZteC30021Oids, '5200': Zte5200Oids}
        self.model = makes[make]

    def get_adsl_attributes(self, shelf, card, port):
        try:
            return self.model.objects.get(shelf=shelf, card=card, port=port)
        except self.model.DoesNotExist:
            return


class DefaultSnmpGetBehavior(GetSnmpBehavior):
    def get_snmp(self, host_address, oid):
        return netsnmp.snmpget(oid, Version=SNMP_VERSION, DestHost=host_address, Community=SNMP_GET_COMMUNITY)


class DefaultSnmpSetBehavior(SetSnmpBehavior):
    def set_snmp(self, host_address, values):
        values = [values] if type(values) == netsnmp.Varbind else values
        result = netsnmp.snmpset(*values, Version=SNMP_VERSION, DestHost=host_address, Community=SNMP_SET_COMMUNITY)
        return bool(result)


class HuaweiTelnetBehavior(TelnetBehavior):

    exscript_driver = VxworksDriver


    def __init__(self, host_address, model):
        super(HuaweiTelnetBehavior, self).__init__(host_address)
        credentials = {'5600T': (HUAWEI5600T_TELNET_USER, HUAWEI5600T_TELNET_PASS),
                       '5600': (HUAWEI5600_TELNET_USER, HUAWEI5600_TELNET_PASS),
                       'GPON': (HUAWEI_FTTH_TELNET_USER, HUAWEI_FTTH_TELNET_PASS)}
        self.telnet_username, self.telnet_password = credentials[model]


class AlcatelTelnetBehavior(TelnetBehavior):
    exscript_driver = IsamDriver

    def __init__(self, host_address, model='default'):
        super(AlcatelTelnetBehavior, self).__init__(host_address)
        credentials = {'GPON': (ALCATEL_TELNET_USER, ALCATEL_TELNET_PASS)}

        self.telnet_username, self.telnet_password = credentials.get(model, (ALCATEL_TELNET_USER, ALCATEL_TELNET_PASS))


class ZteTelnetBehavior(TelnetBehavior):
    # telnet_username = ZTE_TELNET_USER
    # telnet_password = ZTE_TELNET_PASS
    exscript_driver = ZteDriver

    def __init__(self, host_address, model='default'):
        super(ZteTelnetBehavior, self).__init__(host_address)
        credentials = {'GPON': (ZTE_FTTH_TELNET_USER, ZTE_FTTH_TELNET_PASS)}

        self.telnet_username, self.telnet_password = credentials.get(model, (ZTE_TELNET_USER, ZTE_TELNET_PASS))


class EricssonBanTelnetBehavior(TelnetBehavior):
    exscript_driver = EricssonBanDriver

    def __init__(self, host_address, model):
        super(EricssonBanTelnetBehavior, self).__init__(host_address)
        credentials = {'GPON': (ERICSSON_FTTH_TELNET_USER, ERICSSON_FTTH_TELNET_PASS)}

        self.telnet_username, self.telnet_password = credentials.get(model)


class JuniperTelnetBehavior(object):
    def __init__(self, host_address):
        self.host_address = host_address

    def __enter__(self):
        self.account = Account(JUNIPER_ROUTER_TELNET_USER, password=JUNIPER_ROUTER_TELNET_PASS)
        self.conn = Telnet(debug=TELNET_DEBUG_LEVEL, connect_timeout=None)
        self.conn.connect(self.host_address)
        self.conn.set_driver(JunOSDriver())
        self.conn.login(self.account)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.send('exit\r')
        self.conn.close(force=True)

    def execute(self, command):
        self.conn.execute(command)
        return self.conn.response




