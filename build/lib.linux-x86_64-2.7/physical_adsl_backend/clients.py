from behaviors import QueryAllAttributesBehavior, DefaultSnmpGetBehavior, DefaultSnmpSetBehavior, \
    QueryDatabseAttributesBehavior, HuaweiTelnetBehavior, AlcatelTelnetBehavior, ZteTelnetBehavior, \
    JuniperTelnetBehavior, EricssonBanTelnetBehavior
from interfaces import SnmpClient, TelnetClient
from netsnmp import Varbind
from mw1_backend.configs import ADSL_FILTER_35, ADSL_FILTER_40, ADSL_DELETE_VALUE, ADSL_ADD_VALUE, ADSL_HUAWEI_ENABLE, \
    ADSL_HUAWEI_DISABLE, ZTE_ENABLE_PASS, FTTH_SPEEDS_MAPPING
from shared.decorators import Singleton
from collections import namedtuple
from Exscript.protocols.Exception import InvalidCommandException
import logging
import re
import time
import socket

logger = logging.getLogger(__name__)
JUNIPER_ERR_PATTERN_SEC = r"(ge-.*)\.942"
JUNIPER_ERR_PATTERN_QOS = r"(ge-.*)\.941"


def handle_telnet_connection(func):
    """used internally by clients to handle communication errors with remote telnet servers"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except socket.error as e:
            error = "Connection error, {0}".format(str(e))
            if func.__name__ == 'get_subscriber_status':
                return False, error, None
            else:
                return False, error

    return wrapper


class Huawei5600TClient(SnmpClient):
    def __init__(self):
        self.query_behavior = QueryAllAttributesBehavior()
        self.get_behavior = DefaultSnmpGetBehavior()
        self.set_behavior = DefaultSnmpSetBehavior()

    def get_snmp(self, host_address, oid):
        return self.get_behavior.get_snmp(host_address, oid)[0]

    def set_snmp(self, host_address, values):
        return self.set_behavior.set_snmp(host_address, values)

    def delete_subscriber(self, host_address, action_oid):
        # set action field to 6 in order to perform delete
        action_value = Varbind(action_oid, '', ADSL_DELETE_VALUE, "INTEGER")
        self.set_snmp(host_address, action_value)

    def _toggle_subscriber_status(self, host_address, status_oid, enable):
        status_value = ADSL_HUAWEI_ENABLE if enable else ADSL_HUAWEI_DISABLE
        action_value = Varbind(status_oid, '', status_value, "INTEGER")
        return self.set_snmp(host_address, action_value)

    def _provision_vci_35(self, host_address, port, card):
        query_oid = self.query_behavior.get_query_oid(port, card, 35)
        service_port_index = self.get_snmp(host_address, query_oid)
        if service_port_index is None:
            logger.error("Couldn't provision subscriber !!")
            return False, None
        oids = self.query_behavior.get_adsl_attributes(service_port_index)
        current_second_interface_index = self.get_snmp(host_address, oids.second_port_index)
        current_vlan = self.get_snmp(host_address, oids.vlan)
        current_inner_vlan = self.get_snmp(host_address, oids.inner_vlan)
        error = bool([x for x in [current_inner_vlan, ] if x is None])
        if error:
            logger.error("couldn't return adsl attributes")
            return False, None,

        adsl_values = [Varbind(oids.rx, '', "ip-traffic-table_{0}".format(ADSL_FILTER_35), "OctetString"),
                       Varbind(oids.tx, '', "ip-traffic-table_{0}".format(ADSL_FILTER_35), "OctetString")]

        CurrentValues = namedtuple('CurrentValues', ['service_index', 'second_index', 'vlan', 'inner_vlan'])
        current_values = CurrentValues(int(service_port_index), current_second_interface_index, current_vlan,
                                       int(current_inner_vlan))
        return self.set_snmp(host_address, adsl_values), current_values


    def _provision_vci_40(self, host_address, service_port_index, current_second_interface_index, vlan, inner_vlan):
        oids = self.query_behavior.get_adsl_attributes(service_port_index)

        adsl_values = [Varbind(oids.second_port_index, '', current_second_interface_index, "INTEGER"),
                       Varbind(oids.vpi, '', 0, "INTEGER"),
                       Varbind(oids.vci, '', 40, "INTEGER"),
                       Varbind(oids.vlan, '', vlan, "INTEGER"),
                       Varbind(oids.inner_vlan, '', str(inner_vlan), "INTEGER"),
                       Varbind(oids.adsl, '', ADSL_FILTER_35, "INTEGER"),
                       Varbind(oids.action, '', ADSL_ADD_VALUE, "INTEGER")]

        self.set_snmp(host_address, adsl_values)

        adsl_values = [Varbind(oids.rx, '', "ip-traffic-table_{0}".format(ADSL_FILTER_40), "OctetString"),
                       Varbind(oids.tx, '', "ip-traffic-table_{0}".format(ADSL_FILTER_40), "OctetString")]

        return self.set_snmp(host_address, adsl_values)

    def provision_subscriber(self, host_address, card, port, shelf=None):
        """provisions a subscriber twice .. once on vci 35 and once again on vci 40"""
        vci_35_result, current_values = self._provision_vci_35(host_address, port, card)
        if not vci_35_result:
            return False, "Can't create Vci 35"
        self._provision_vci_40(host_address, current_values.service_index + 2000, current_values.second_index,
                               current_values.vlan, current_values.inner_vlan + 2000)
        return True, None


    def update_subscriber(self, host_address, port, card, shelf, enable):
        """returns a tuple: status, error msg (if exists), port status"""
        query_oid = self.query_behavior.get_query_oid(port, card, 40)
        service_port_index = self.get_snmp(host_address, query_oid)
        if service_port_index is None:
            msg = "Couldn't update subscriber"
            logger.error(msg)
            return False, msg

        status_oid = self.query_behavior.get_enable_attribute(service_port_index)

        return self._toggle_subscriber_status(host_address, status_oid, enable), None

    @handle_telnet_connection
    def get_subscriber_status(self, host_address, port, card, shelf=None):
        query_oid = self.query_behavior.get_query_oid(port, card, 40)
        service_port_index = self.get_snmp(host_address, query_oid)
        if service_port_index is None:
            msg = "Couldn't get subscriber at {0}: {1}/{2}".format(host_address, card, port)
            logger.error(msg)
            return False, msg, None
        status_oid = self.query_behavior.get_enable_attribute(service_port_index)
        return True, None, self.get_snmp(host_address, status_oid) == "1"


class Huawei5600Client(TelnetClient):
    def __init__(self):
        self.telnet_behavior = HuaweiTelnetBehavior
        # self.pattern = re.compile(r"-{77}\r\n   (.*)\r\n  -{77}")
        self.port_info_pattern = r""

    @handle_telnet_connection
    def provision_subscriber(self, host_address, card, port, shelf=None):
        with self.telnet_behavior(host_address, '5600') as device:
            try:
                device.execute("config")
                try:
                    device.execute("traffic table index 7 ip car 24576 priority 7 priority-policy pvc-Setting")
                except InvalidCommandException as e:
                    if "Failed to create traffic descriptor record,the index has existed" in str(e):
                        pass

                location = "0/{0}/{1}".format(card, port)
                result = device.execute("display service-port port {0}\r".format(location))
                match = result.split("-----------------------------------------------------------------------------")[2]
                if not match:
                    return False
                splitted = match.split()
                PortInfo = namedtuple("PortInfo", ["vlan_id", "label"])
                info = PortInfo(splitted[0], splitted[-2])
                logger.info("fetched port info")
                device.execute("undo service-port port {0}\r".format(location))
                device.execute("y")
                device.execute("service-port vlan {0} adsl {1} vpi 0 vci 35 rx-cttr 7 tx-cttr 7".format(info.vlan_id,
                                                                                                        location))
                device.execute("stacking label {0}  vpi 0 vci 35 {1}".format(location, info.label))
                device.execute("service-port vlan {0} adsl {1} vpi 0 vci 40 rx-cttr 6 tx-cttr 6".format(info.vlan_id,
                                                                                                        location))
                device.execute("stacking label {0}  vpi 0 vci 40 {1}\r".format(location, int(info.label) + 1000))
                return True, None
            except InvalidCommandException as e:
                logger.error(str(e))
                return False, str(e)

    @handle_telnet_connection
    def get_subscriber_status(self, host_address, port, card, shelf=None):
        with self.telnet_behavior(host_address, '5600') as device:
            try:
                device.execute("config")
                location = "0/{0}/{1}".format(card, port)
                result = device.execute("display service-port port {0}\r".format(location))
                match = result.split("-----------------------------------------------------------------------------")[2]
                if not match:
                    return False, "malformed profile", None
                splitted = match.split()
                if len(splitted) != 28:
                    msg = "vci 40 is not configured"
                    logger.error(msg)
                    return False, msg, None

                return True, None, splitted[-3] == 'act/up'
            except InvalidCommandException as e:
                logger.error(str(e))
                return False, str(e), None

    @handle_telnet_connection
    def update_subscriber(self, host_address, port, card, shelf, enable):
        with self.telnet_behavior(host_address, '5600') as device:
            try:
                device.execute("config")
                location = "0/{0}/{1}".format(card, port)
                command = "{0}activate service-port port {1} VPi 0 VCi 40\r".format("" if enable else "de", location)
                device.execute(command)
                return True, None
            except InvalidCommandException as e:
                logger.error(str(e))
                return False, str(e)


class AlcatelClient(TelnetClient):
    card_shift = 0

    def __init__(self):
        self.telnet_behavior = AlcatelTelnetBehavior
        self.pattern = re.compile("network-vlan stacked:(\d+):(\d+)\r\n")

    @handle_telnet_connection
    def provision_subscriber(self, host_address, card, port, shelf=None):
        location = "1/1/{0}/{1}".format(card + self.card_shift, port)
        with self.telnet_behavior(host_address) as device:

            try:
                result = device.execute("info configure bridge port {0}:0:35".format(location))
                match = self.pattern.search(result, re.DOTALL)
                if not match:
                    msg = "No port info found for {0}".format(location)
                    logger.error(msg)
                    return False, msg

                match = match.groups()
                vlan = match[0]
                vlan_id = int(match[1])
                device.execute("configure bridge port {0}:0:35 vlan-id {1} qos priority:0".format(location, vlan_id))
                new_vlan_id = vlan_id + 1500 if vlan_id < 2500 else vlan_id - 1500
                device.execute("configure vlan id stacked:{0}:{1} mode cross-connect".format(vlan, new_vlan_id))
                device.execute("configure atm pvc {0}:0:40 no admin-down".format(location))
                device.execute("configure bridge port {0}:0:40".format(location))
                device.execute("no pvid")
                try:

                    device.execute("no vlan-id 101")
                except InvalidCommandException as e:
                    if 'instance does not exist' in str(e):
                        pass

                device.execute(
                    "configure bridge port {0}:0:40 vlan-id {1} network-vlan stacked:{2}:{1} vlan-scope local qos priority:3".format(
                        location, new_vlan_id, vlan))
                device.execute("configure bridge port {0}:0:40 pvid {1}".format(location, new_vlan_id))
            except InvalidCommandException as e:
                logger.error(str(e))
                return False, str(e)

        return True, None

    @handle_telnet_connection
    def get_subscriber_status(self, host_address, port, card, shelf=None):
        with self.telnet_behavior(host_address) as device:
            try:
                location = "1/1/{0}/{1}".format(card + self.card_shift, port)
                result = device.execute("info configure atm pvc {0}:0:40".format(location))
                return True, None, not "admin-down" in result


            except InvalidCommandException as e:
                logger.error(str(e))
                return False, str(e), None

    @handle_telnet_connection
    def update_subscriber(self, host_address, port, card, shelf, enable):
        with self.telnet_behavior(host_address) as device:
            try:
                location = "1/1/{0}/{1}".format(card + self.card_shift, port)
                device.execute("configure atm pvc {0}:0:40 {1}admin-down".format(location, "no " if enable else ""))
                return True, None

            except InvalidCommandException as e:
                logger.error(str(e))
                return False, str(e)


class IsamFd(AlcatelClient):
    pass


class IsamXd(AlcatelClient):
    card_shift = 3


class ZteClient(SnmpClient, TelnetClient):
    model = None  # to be overridden in children classes

    def __init__(self):
        self.query_behavior = QueryDatabseAttributesBehavior(self.model)
        self.get_behavior = DefaultSnmpGetBehavior()
        self.set_behavior = DefaultSnmpSetBehavior()
        self.telnet_behavior = ZteTelnetBehavior
        self.port_status_regex = re.compile(r"Pvc 2:\r\n  Admin Status(.*?)VPI/VCI", re.DOTALL)

    def get_snmp(self, host_address, oid):
        return self.get_behavior.get_snmp(host_address, oid)[0]

    def set_snmp(self, host_address, values):
        return self.set_behavior.set_snmp(host_address, values)

    def _configure_qos_settings(self, shelf, card, port, host_address):
        # QOS options
        location = "{0}/{1}/{2}".format(shelf, card, port)
        with self.telnet_behavior(host_address) as device:
            try:
                device.execute("conf t")
                device.execute("interface adsl_{0}".format(location))
                device.execute("qos queue-map-profile 123")
                device.execute("traffic-profile 123 pvc 1 direction egress")
                device.execute("traffic-profile 123 pvc 2 direction egress")
            except InvalidCommandException as e:
                logger.error(str(e))
                return False, str(e)

            return True, None

    @handle_telnet_connection
    def provision_subscriber(self, host_address, card, port, shelf):
        oids = self.query_behavior.get_adsl_attributes(shelf, card, port)
        if oids is None:
            msg = "No attributes were found for {0}/{1}/{2} on {3}".format(shelf, card, port, host_address)
            logger.error(msg)
            return False, msg

        outer_vlan = self.get_snmp(host_address, oids.outer_vlan_1)
        inner_vlan = self.get_snmp(host_address, oids.inner_vlan_1)

        error = bool([x for x in [outer_vlan, inner_vlan] if x is None])
        if error:
            msg = "can't retrieve adsl attributes for {0}/{1}/{2} on {3}".format(shelf, card, port, host_address)
            logger.error(msg)
            return False, msg

        adsl_values = [Varbind(oids.outer_vlan_2, '', outer_vlan, "INTEGER"),
                       Varbind(oids.inner_vlan_2, '', int(inner_vlan) + 1000, "INTEGER"),
                       Varbind(oids.vpi_2, '', 0, "INTEGER"),
                       Varbind(oids.vci_2, '', 40, "INTEGER")]

        result = self.set_snmp(host_address, adsl_values)
        if not result:
            msg = "can't create vci 40 for {0}/{1}/{2} on {3}".format(shelf, card, port, host_address)
            logger.error(msg)
            return False, msg

        return self._configure_qos_settings(shelf, card, port, host_address)

    @handle_telnet_connection
    def get_subscriber_status(self, host_address, port, card, shelf=None):
        with self.telnet_behavior(host_address) as device:
            try:
                location = "{0}/{1}/{2}".format(shelf, card, port)
                device.execute("terminal length 0")
                result = device.execute("show interface adsl_{0}".format(location))
                match = self.port_status_regex.findall(result)
                if not match:
                    return False, "Can't get port status", None
                match = match[0].strip(" \r\n:")
                return True, None, match == 'enable'

            except InvalidCommandException as e:
                logger.error(str(e))
                return False, str(e), None

    @handle_telnet_connection
    def update_subscriber(self, host_address, port, card, shelf, enable):
        with self.telnet_behavior(host_address) as device:
            try:
                location = "{0}/{1}/{2}".format(shelf, card, port)
                device.execute("terminal length 0")
                device.execute("conf t")
                device.execute("interface adsl_{0}".format(location))
                device.execute("pvc 2 {0}".format("enable" if enable else "disable"))
                return True, None

            except InvalidCommandException as e:
                logger.error(str(e))
                return False, str(e)


class ZteC30019Client(ZteClient):
    model = 'c300-19'


class ZteC30021Client(ZteClient):
    model = 'c300-21'


class Zte5200V2Client(ZteClient):
    model = '5200'
    telnet_port = 1123

    def __init__(self):
        super(Zte5200V2Client, self).__init__()
        self.port_status_regex = re.compile(r"ManageState\s*:\s*(.*)\r\npvid", re.DOTALL)

    def _configure_qos_settings(self, shelf, card, port, host_address):
        # QOS options
        location = "{0}/{1}/{2}".format(shelf, card, port)
        with self.telnet_behavior(host_address, self.telnet_port) as device:
            try:
                device.execute("enable")
                device.execute(ZTE_ENABLE_PASS)
                device.execute("dsl port atmpvc {0} pvc 2 vpi 0 vci 40".format(location))
                device.execute("qos schedulerprofile add a.prf")
                device.execute("qos port default-cos {0} cos 3 egress pvc 1".format(location))
                device.execute("qos port default-cos {0} cos 1 egress pvc 2".format(location))
                device.execute("qos port schedulerprofile {0} a.prf".format(location))
            except InvalidCommandException as e:
                logger.error(str(e))
                return False, str(e)

            return True, None

    @handle_telnet_connection
    def provision_subscriber(self, host_address, card, port, shelf):
        return self._configure_qos_settings(shelf, card, port, host_address)

    @handle_telnet_connection
    def get_subscriber_status(self, host_address, port, card, shelf=None):
        with self.telnet_behavior(host_address, self.telnet_port) as device:
            try:
                location = "{0}/{1}/{2}".format(shelf, card, port)

                device.execute("enable")
                device.execute(ZTE_ENABLE_PASS)

                result = device.execute("show dsl port {0} pvc 2".format(location))

                match = self.port_status_regex.findall(result)
                if not match:
                    return False, "Can't get port status", None
                match = match[0].strip()
                return True, None, match == 'enable'

            except InvalidCommandException as e:
                logger.error(str(e))
                return False, str(e), None

    @handle_telnet_connection
    def update_subscriber(self, host_address, port, card, shelf, enable):
        with self.telnet_behavior(host_address, self.telnet_port) as device:
            try:

                location = "{0}/{1}/{2}".format(shelf, card, port)
                device.execute("enable")
                device.execute(ZTE_ENABLE_PASS)
                device.execute("dsl port {0} {1} pvc 2".format("enable" if enable else "disable", location))
                return True, None

            except InvalidCommandException as e:
                logger.error(str(e))
                return False, str(e)


class Zte5200V3Client(ZteClient):
    model = '5200'

    def _configure_qos_settings(self, shelf, card, port, host_address):
        # QOS options
        location = "{0}/{1}/{2}".format(shelf, card, port)
        with self.telnet_behavior(host_address) as device:
            try:

                device.execute("conf t")
                device.execute("qos queue-block-profile qbp queue-number 2 queue0 60 0 queue1 40 0")
                device.execute("interface adsl_{0}".format(location))
                device.execute("qos cos default-cos 3 pvc 1")
                device.execute("qos cos default-cos 1 pvc 2")
                device.execute("qos queue-block-profile qbp")
            except InvalidCommandException as e:
                logger.error(str(e))
                return False, str(e)

            return True, None


class HuaweiFtthClient(TelnetClient):
    def __init__(self):
        self.telnet_behavior = HuaweiTelnetBehavior

    def get_port_status(self, frame, slot_no, port_no, ont_id, host_address):
        with self.telnet_behavior(host_address, 'GPON') as device:
            try:
                location = "{0}/ {1}/{2}".format(frame, slot_no, port_no)
                port_pattern = r"{0}\s+{1}\s+([\w]+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)".format(location,
                                                                                                     ont_id)
                PortInfo = namedtuple('PortInfo', ['serial_no', 'control_flag', 'run_state', 'config_state',
                                                   'match_state', 'dba'])
                device.execute("scroll 512")
                output = device.execute("display board {0}/{1}".format(frame, slot_no))
                match = re.search(port_pattern, output, re.DOTALL)
                if not match:
                    return {'success': False, 'msg': "Port does not exist"}
                port_info = PortInfo(*match.groups())
                return {'success': True, 'status': 'Up' if port_info.run_state.strip().lower() == 'up' else 'Down',
                        'admin_status': 'Enable' if port_info.control_flag.strip().lower() == 'active' else 'Disable'}

            except InvalidCommandException as e:
                msg = e.message
                logger.error(msg)
                if "frame does not exist" in e.message.lower() or "board does not exist" in e.message.lower() \
                        or 'parameter error' in e.message.lower():
                    msg = "Port does not exist"

                return {'success': False, 'msg': msg}

    def provision_subscriber(self):
        pass

    def get_port_speed(self, frame, slot_no, port_no, ont_id, host_address):
        with self.telnet_behavior(host_address, 'GPON') as device:
            try:
                device.execute("scroll 512")
                output = device.execute(
                    "display service-port port {0}/{1}/{2} ont {3}\r".format(frame, slot_no, port_no, ont_id))
                match = re.search(
                    r"\s+(\d+)\s+277\s+(\w+)\s+(\w+)\s+(\d+)\s+\/(\d+)\s+\/(\d+)\s+(\d+)"
                    r"\s+([\w+\W+])\s+(\w+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\w+)",
                    output, re.DOTALL)
                if not match:
                    return {'success': False, 'msg': "Port does not exist"}
                PortInfo = namedtuple('PortInfo', ['index', 'vlan_attr', 'port_type', 'f', 's', 'p', 'vpi', 'vci',
                                                   'flow_type', 'flow_para', 'rx', 'tx', 'state'])
                port_info = PortInfo(*match.groups())
                if port_info.tx not in FTTH_SPEEDS_MAPPING:
                    return {'success': False, 'msg': "Unrecognized speed"}

                return {'success': True, 'upload': FTTH_SPEEDS_MAPPING[port_info.tx],
                        'download': FTTH_SPEEDS_MAPPING[port_info.rx]}

            except InvalidCommandException as e:
                msg = e.message
                logger.error(msg)
                if "parameter error" in e.message.lower():
                    msg = "Port does not exist"
                elif "no service virtual port can be operated" in e.message.lower():
                    msg = "Port is down"
                return {'success': False, 'msg': msg}

    def reset_port(self, frame, slot, port, ont_id, host_address):
        with self.telnet_behavior(host_address, 'GPON') as device:
            try:
                device.execute("scroll 512")
                device.execute("config")
                device.execute("interface gpon {0}/{1}".format(frame, slot))
                device.execute("ont reset {0} {1}".format(port, ont_id))
                return {'success': True}

            except InvalidCommandException as e:
                msg = e.message
                logger.error(msg)
                if "the ont is not online" in e.message.lower():
                    msg = "The ONT is offline"
                return {'success': False, 'msg': msg}


class ZteFtthClient(TelnetClient):
    def __init__(self):
        self.telnet_behavior = ZteTelnetBehavior

    def get_port_status(self, frame, slot_no, port_no, ont_id, host_address):
        with self.telnet_behavior(host_address, 'GPON') as device:
            try:
                location = "{0}/{1}/{2}:{3}".format(frame, slot_no, port_no, ont_id)
                device.execute("terminal length 0")

                command_output = device.execute(
                    "show gpon onu state gpon-olt_{0}/{1}/{2} {3}".format(frame, slot_no, port_no,
                                                                          ont_id))
                match = re.search(r"{0}\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)".format(location), command_output)
                if not match:
                    return {'success': False, 'msg': "Port does not exist"}

                PortInfo = namedtuple('PortInfo', ['admin_state', 'omcc_state', 'o7_state', 'phase_state'])
                port_info = PortInfo(*match.groups())

                return {'success': True,
                        'status': 'Up' if port_info.omcc_state.strip().lower() == 'enable'
                                          and port_info.o7_state.strip().lower() == 'operation'
                                          and port_info.phase_state.strip().lower() == 'working' else 'Down',
                        'admin_status': 'Enable' if port_info.admin_state.strip().lower() == 'enable' else 'Disable'}

            except InvalidCommandException as e:
                logger.error(str(e))
                if "Device said:\nshow gpon remote-onu pppoe gpon-onu_{0}\r\n                                             ^\r\n% Invalid input detected at '^' marker.\r\n".format(
                        location):
                    return {'success': False, 'msg': "Port does not exist"}
                return {'success': False, 'msg': str(e)}

    def provision_subscriber(self):
        return {'success': False, 'msg': 'NotImplemented'}

    def get_port_speed(self, frame, slot_no, port_no, ont_id, host_address):
        with self.telnet_behavior(host_address, 'GPON') as device:
            try:
                device.execute("terminal length 0")
                command_output = device.execute(
                    "show gpon onu tcont gpon-olt_{0}/{1}/{2} {3}".format(frame, slot_no, port_no,
                                                                          ont_id))
                match = re.search(r"TCONT: 1.*?Profile Name: (\w+-\d+\w+)[\r\n]+Name", command_output, re.DOTALL)
                if not match:
                    return {'success': False, 'msg': "Port does not exist"}

                speed = match.group(1)

                if speed not in FTTH_SPEEDS_MAPPING:
                    return {'success': False, 'msg': "Unrecognized speed"}

                return {'success': True, 'download': FTTH_SPEEDS_MAPPING[speed]}

            except InvalidCommandException as e:
                logger.error(str(e))
                return {'success': False, 'msg': "Port does not exist"}


    def reset_port(self, frame, slot, port, ont_id, host_address):
        with self.telnet_behavior(host_address, 'GPON') as device:
            try:
                device.execute("terminal length 0")
                device.execute("conf t")
                device.execute( "pon-onu-mng gpon-onu_{0}/{1}/{2}:{3}".format(frame, slot, port, ont_id))
                device.execute("reboot")
                return {'success': True}

            except InvalidCommandException as e:
                logger.error(str(e))
                return {'success': False, 'msg': "Port does not exist"}


class EricssonFtthClient(TelnetClient):
    def __init__(self):
        self.telnet_behavior = EricssonBanTelnetBehavior

    def get_port_status(self, frame, slot_no, port_no, ont_id, host_address):
        with self.telnet_behavior(host_address, 'GPON') as device:
            try:

                location = "{0}-{1}-{2}".format(slot_no, port_no, ont_id)

                #port_pattern = r"ONT-{0}".format(location)

                output = device.execute("show ont ont-{0} state".format(location))

                match = re.search(r"ONT-{0}\s+([\w-]+)\s+(\w+)".format(location), output)
                if not match:
                    return {'success': False, 'msg': "Port does not exist"}

                PortInfo = namedtuple('PortInfo', ['operational_state', 'admin_state'])
                port_info = PortInfo(*match.groups())

                return {'success': True,
                        'status': 'Up' if port_info.operational_state == 'IS-NR' else 'Down',
                        'admin_status': 'Enable' if port_info.admin_state == 'ACT' else 'Disable'}

            except InvalidCommandException as e:
                logger.error(str(e))
                if "(error) txtcli: IISP Syntax error at ont-{0}".format(location) in str(e):
                    return {'success': False, 'msg': "Port does not exist"}
                return {'success': False, 'msg': str(e)}

    def provision_subscriber(self):
        return {'success': False, 'msg': 'NotImplemented'}

    def get_port_speed(self, frame, slot_no, port_no, ont_id, host_address):
        with self.telnet_behavior(host_address, 'GPON') as device:
            try:
                location = "{0}-{1}-{2}".format(slot_no, port_no, ont_id)
                command_output = device.execute("show gemvc ont-{0}".format(location))

                match = re.search(r"ONT-{0}\s+(\d+)\s+(\d+)\s+([\w\d]+)\s+([\w\d]+)\s+([\w\d-]+)\s+([\w\s-]+)\s+V1638400".format(location), command_output, re.DOTALL)

                if not match:
                    return {'success': False, 'msg': "Port does not exist"}
                PortInfo = namedtuple('PortInfo', ['gem', 'vlan', 'flowvc', 'lif', 'to', 'state'])
                port_info = PortInfo(*match.groups())
                speed = port_info.lif

                if speed not in FTTH_SPEEDS_MAPPING:
                    return {'success': False, 'msg': "Unrecognized speed"}

                return {'success': True, 'download': FTTH_SPEEDS_MAPPING[speed]}

            except InvalidCommandException as e:
                logger.error(str(e))
                return {'success': False, 'msg': "Port does not exist"}

    def reset_port(self, frame, slot, port, ont_id, host_address):
        with self.telnet_behavior(host_address, 'GPON') as device:
            try:
                location = "{0}-{1}-{2}".format(slot, port, ont_id)
                device.execute("enable")
                device.execute("remove ont ONT-{0}".format(location))
                device.execute("restore ont ONT-{0}".format(location))

                return {'success': True}

            except InvalidCommandException as e:
                logger.error(str(e))
                return {'success': False, 'msg': "Port does not exist"}


class IsamFdFtthClient(TelnetClient):
    def __init__(self):
        self.telnet_behavior = AlcatelTelnetBehavior

    def get_port_status(self, frame, slot_no, port_no, ont_id, host_address):
        with self.telnet_behavior(host_address, 'GPON') as device:
            try:
                location = "1/{0}/{1}/{2}/{3}".format(frame, slot_no, port_no, ont_id)

                port_pattern = r"{0}\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\d+.\d+|\w+)".format(location)

                output = device.execute("show equipment ont operational-data {0}".format(location))

                match = re.search(port_pattern, output)
                if not match:
                    return {'success': False, 'msg': "Port does not exist"}

                PortInfo = namedtuple('PortInfo', ['loss_of_signal', 'loss_of_ack', 'loss_of_gem', 'ont_disabled',
                                                   'inactive', 'dying_gasp', 'ont_olt_distance'])

                operational_port_info = PortInfo(*match.groups())

                output = device.execute("show interface port ont:{0}".format(location))
                admin_port_pattern = r"ont:{0}\s+(\w+)\s+(\w+)".format(location)
                match = re.search(admin_port_pattern, output)
                if not match:
                    return {'success': False, 'msg': "Port does not exist"}
                AdminPortInfo = namedtuple('AdminPortInfo', ['admin_status', 'op_status'])
                admin_port_info = AdminPortInfo(*match.groups())
                return {'success': True,
                        'status': 'Up' if operational_port_info.loss_of_signal.strip().lower() == 'no' else 'Down',
                        'admin_status': 'Enable' if admin_port_info.admin_status.strip().lower() == 'up' else 'Disable'}

            except InvalidCommandException as e:
                logger.error(str(e))
                if "Error : instance does not exist" in e.message.lower():
                    return {'success': False, 'msg': "Port does not exist"}
                return {'success': False, 'msg': str(e)}

    def provision_subscriber(self):
        return {'success': False, 'msg': 'NotImplemented'}

    def get_port_speed(self, frame, slot_no, port_no, ont_id, host_address):
        with self.telnet_behavior(host_address, 'GPON') as device:
            try:
                location = "1/{0}/{1}/{2}/{3}/14/1".format(frame, slot_no, port_no, ont_id)

                port_pattern = r"configure bridge port {0} vlan-id.*name:([\w\d_]+)?\r".format(location)

                output = device.execute("info configure bridge port {0} flat".format(location))

                match = re.search(port_pattern, output)
                if not match:
                    return {'success': False, 'msg': "Port does not exist"}

                speed = match.group(1)

                if speed not in FTTH_SPEEDS_MAPPING:
                    return {'success': False, 'msg': "Unrecognized speed"}

                return {'success': True, 'download': FTTH_SPEEDS_MAPPING[speed]}

            except InvalidCommandException as e:
                logger.error(str(e))
                if "Error : instance does not exist" in e.message.lower():
                    return {'success': False, 'msg': "Port does not exist"}
                return {'success': False, 'msg': str(e)}

    def reset_port(self, frame, slot, port, ont_id, host_address):
        with self.telnet_behavior(host_address, 'GPON') as device:
            try:
                location = "1/{0}/{1}/{2}/{3}".format(frame, slot, port, ont_id)
                device.execute("admin equipment ont interface {0} reboot with-active-image".format(location))
                return {'success': True}

            except InvalidCommandException as e:
                logger.error(str(e))
                return {'success': False, 'msg': "Port does not exist"}


class JuniperRouter(object):
    def __init__(self):
        self.telnet_behavior = JuniperTelnetBehavior
        self.interface_pattern = re.compile(r"(ge-\S*)")

    def set_router_acls(self, host_address):
        with JuniperTelnetBehavior(host_address) as router:
            # get ge interfaces
            router.execute("set cli screen-length 0")
            output = router.execute('show configuration | match 942 | display set | match "interfaces ge-"')
            if not output:
                return False
            results = output.split("\r\n")
            if len(output) < 2:
                return False, "invalid show command"
            matches = [self.interface_pattern.search(result) for result in results[1:]]
            interfaces = set()
            for match in matches:
                interface = match.group()
                if interface:
                    interfaces.add(interface)

            router.execute("configure private")
            router.execute(
                "set firewall filter MSAN-FILTER term DENY-ACCESS from source-prefix-list MSAN_TE_SOURCE_IPS")
            router.execute("set firewall filter MSAN-FILTER term DENY-ACCESS then reject")
            router.execute("set firewall filter MSAN-FILTER term ACCEPT-ACCESS then accept")
            router.execute("set policy-options prefix-list MSAN_TE_SOURCE_IPS 10.238.0.0/16")
            router.execute("set policy-options prefix-list MSAN_TE_SOURCE_IPS 10.239.0.0/16")

            for interface in interfaces:
                router.execute("set interfaces {0} unit 942 family inet filter output MSAN-FILTER".format(interface))

            try:

                router.execute("commit")
            except InvalidCommandException as e:
                # loop over failed interfaces
                failed_interfaces = re.findall(JUNIPER_ERR_PATTERN_SEC, str(e))
                for interface in failed_interfaces:
                    # this means the router should be configured with irb configurations
                    router.execute("delete interfaces {0} unit 942 family inet".format(interface))
                if failed_interfaces:
                    router.execute("set interfaces irb unit 942 family inet filter output MSAN-FILTER")
                    try:
                        router.execute("commit")
                    except InvalidCommandException as e:
                        return False, str(e)

            return True, None


    def set_router_qos(self, host_address):
        with JuniperTelnetBehavior(host_address) as router:
            # get ge interfaces
            router.execute("set cli screen-length 0")
            output = router.execute('show configuration | match 941 | display set | match "interfaces ge-"')
            if not output:
                return False
            results = output.split("\r\n")
            if len(output) < 2:
                return False, "invalid show command"
            matches = [self.interface_pattern.search(result) for result in results[1:]]
            interfaces = set()
            for match in matches:
                interface = match.group()
                if interface:
                    interfaces.add(interface)

            router.execute("configure private")
            router.execute("set firewall family inet filter VOICE-PRIMUM term MARK then forwarding-class Premium")
            router.execute("set firewall family inet filter VOICE-PRIMUM term MARK then accept")

            for interface in interfaces:
                router.execute("set interfaces {0} unit 941 family inet filter input VOICE-PRIMUM".format(interface))

            try:

                router.execute("commit")
            except InvalidCommandException as e:
                # loop over failed interfaces
                failed_interfaces = re.findall(JUNIPER_ERR_PATTERN_QOS, str(e))
                for interface in failed_interfaces:
                    # this means the router should be configured with irb configurations
                    router.execute("delete interfaces {0} unit 941 family inet".format(interface))
                if failed_interfaces:
                    router.execute("set interfaces irb unit 941 family inet filter input VOICE-PRIMUM")
                    try:
                        router.execute("commit")
                    except InvalidCommandException as e:
                        return False, str(e)

            return True, None


def get_client(model_no):
    """factory method that returns a Huawei client based on model number"""
    supported_models = {
        'Hu5600T': Huawei5600TClient,
        'Hu5600': Huawei5600Client,
        'IsamFd': IsamFd,
        'IsamXd': IsamXd,
        'ZteC30019': ZteC30019Client,
        'ZteC30021': ZteC30021Client,
        "ZteC5200V2": Zte5200V2Client,
        "ZteC5200V3": Zte5200V3Client,
        "HuaweiFtth": HuaweiFtthClient,
        'ZteFtth': ZteFtthClient,
        'EricssonFtth': EricssonFtthClient,
        'IsamFtth': IsamFdFtthClient
    }

    return supported_models.get(model_no, None)()
