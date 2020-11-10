from abc import ABCMeta, abstractmethod, abstractproperty
from Exscript import Account
from Exscript.protocols import Telnet
from mw1_backend.configs import TELNET_DEBUG_LEVEL, PYCURL_TIMEOUT


class QuerySnmpBehavior:
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_adsl_attributes(self, service_port_index):
        """The signature is not strict ... it can differ from an implementation to another"""
        pass


class GetSnmpBehavior:
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_snmp(self, host_address, oid):
        pass


class SetSnmpBehavior:
    __metaclass__ = ABCMeta

    @abstractmethod
    def set_snmp(self, host_address, values):
        pass


class TelnetBehavior:
    __metaclass__ = ABCMeta
    telnet_username = None
    telnet_password = None
    exscript_driver = None

    def __init__(self, host_address, port=23):
        self.host_address = host_address
        self.port = port

    def __enter__(self):
        self.account = Account(self.telnet_username, password=self.telnet_password)
        self.conn = Telnet(debug=TELNET_DEBUG_LEVEL, connect_timeout=PYCURL_TIMEOUT)
        self.conn.connect(self.host_address, port=self.port)
        self.conn.set_driver(self.exscript_driver())
        self.conn.login(self.account)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.send('exit\r')
        self.conn.close(force=True)

    def execute(self, command):
        self.conn.execute(command)
        return self.conn.response



class TelnetClient:
    __metaclass__ = ABCMeta

    @abstractmethod
    def provision_subscriber(self):
        pass

class SnmpClient:
    __metaclass__ = ABCMeta

    query_behavior = None
    get_behavior = None
    set_behavior = None


    @abstractmethod
    def get_snmp(self, host_address, oid):
        pass

    @abstractmethod
    def set_snmp(self, host_address, values):
        pass

    @abstractmethod
    def provision_subscriber(self, host_address, port, card):
        pass