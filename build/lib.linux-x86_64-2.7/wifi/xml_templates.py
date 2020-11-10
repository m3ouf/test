SEND_SMS = '''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sms="SMS">
   <soapenv:Header/>
   <soapenv:Body>
      <sms:SendSMSRequest>
         <sms:User>WE-WiFi</sms:User>
         <sms:Password>12345</sms:Password>
         <sms:Mobile>%s</sms:Mobile>
         <sms:Message>%s</sms:Message>
      </sms:SendSMSRequest>
   </soapenv:Body>
</soapenv:Envelope>'''

COA_REQUEST = """<envelope>
                        <header/>
                        <body>
                            <request action="WIFI_LOGON">
                                <attributes>
                                    <attribute name="Framed-IP-Address" value="%s" />
                                    <attribute name="Cisco-User-Name" value="%s@wifi.tedata.net.eg" />
                                    <attribute name="Cisco-Subscriber-Password" value="49494949494949494949494949494949b773dfd724cb6df6605e21aee9379d26" />
                                    <attribute name="Cisco-AVPAIR" value="subscriber:command=account-logon" />
                                </attributes>
                            </request>
                        </body>
                    </envelope>"""

SBR_SESSION = """<envelope>
            <header/>
            <body>
                    <request action="query">
                            <attributes>
                                    <attribute name="Framed-IP-Address" value="%s" />
                            </attributes>
                    </request>
            </body>
            </envelope>"""
