from shared.decorators import Singleton
from suds.plugin import MessagePlugin
from lxml import etree
from mw1_backend.configs import QPS_NS
from dateutil import parser as time_parser

class SessionPlugin(MessagePlugin):
    def received(self, context):
        """The problem this function solves is the following ...
        We need to retrieve the services names (ordered by the startTime) but the retrieved session is not
        well-formatted and dealing with the object provided by SUDs is a hell !
        so we override the received function which is handed the raw xml response, we parse it with xpath effeciently
        . The problem now is to return the parsed values as the next function in the pipeline of SUDs is waiting
         for an xml file. So in order to achieve that, we initialized a singleton object, populated it with the
         retrieved session, and we call it again in the client, and because it's singleton once it's initialized
         it preserves its attributes' values.
         """
        xml = context.reply
        parser = etree.XMLParser(remove_blank_text=True)
        response_dom = etree.fromstring(xml, parser)
        sessions = []
        namespaces = {'ns': QPS_NS}
        session_doms = response_dom.findall('.//ns:session', namespaces=namespaces)
        for session_dom in session_doms:
            session_objects = session_dom.xpath('./ns:sessionObject',  namespaces=namespaces)
            session_time = session_dom.xpath('./ns:sessionObject/ns:entry[child::ns:string[text()="startTime"]]',
                                             namespaces=namespaces)
            for session_object in session_objects:
                device_sessions = session_object.xpath('ns:entry[child::ns:string[text()="deviceSessions"]]',
                                                       namespaces=namespaces)

                for ds in device_sessions:
                    entries = ds.xpath('./ns:list/ns:map/'
                                       'ns:entry[child::ns:string[text() = "services" or text() = "asr9KServices"]]/'
                                       'ns:list/ns:map/ns:entry[child::ns:string[text() = "serviceCode"]]',
                                       namespaces=namespaces)
                    if len(entries) == 0:
                        entries = ds.xpath('./ns:list/ns:map/' 'ns:entry[child::ns:string[text() ='
                                           ' "featureData"]]/''ns:list/ns:map/ns:entry[child::ns:string[text() ='
                                           ' "chargingPredefinedRules"]]/''ns:map/ns:entry[child::ns:string]',
                                           namespaces=namespaces)

                        for entry in entries:
                            service_name = entry.getchildren()[0].text
                            start_time = time_parser.parse(session_time[0].getchildren()[1].text)
                            sessions.append((service_name, start_time))
                    else:
                        for entry in entries:
                            service_name = entry.getchildren()[1].text
                            start_time = time_parser.parse(session_time[0].getchildren()[1].text)
                            sessions.append((service_name, start_time))

        session_info = SessionInfo()
        session_info.sessions = sessions


@Singleton
class SessionInfo(object):
    """A placeholder for sessions, sessions are retrieved after parsing the xml file."""
    pass
