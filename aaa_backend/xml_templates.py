COA_START_REQ = """
<envelope>
    <header/>
    <body>
        <request action="SERV_TO_DWG">
            <attributes>
                <attribute name="Framed-IP-Address" value="%(framed_ip_address)s" />
                <attribute name="Cisco-AVPAIR" value="subscriber:command=activate-service" />
                <attribute name="Cisco-AVPAIR" value="subscriber:service-name=%(service_name)s" />
            </attributes>
        </request>
    </body>
</envelope>
"""

COA_STOP_REQ = """
<envelope>
    <header/>
    <body>
        <request action="SERV_TO_DWG">
            <attributes>
                <attribute name="Framed-IP-Address" value="%(framed_ip_address)s" />
                <attribute name="Cisco-AVPAIR" value="subscriber:command=deactivate-service" />
                <attribute name="Cisco-AVPAIR" value="subscriber:service-name=%(service_name)s" />
            </attributes>
        </request>
    </body>
</envelope>
"""

COA_START_9K_REQ = """
<envelope>
    <header/>
    <body>
        <request action="SERV_TO_DWG">
            <attributes>
                <attribute name="Framed-IP-Address" value="%(framed_ip_address)s" />
                <attribute name="Cisco-AVPAIR" value="subscriber:command=activate-service" />
                <attribute name="Cisco-AVPAIR" value=" subscriber:sa=%(service_name)s" />
            </attributes>
        </request>
    </body>
</envelope>
"""

COA_STOP_9K_REQ = """
<envelope>
    <header/>
    <body>
        <request action="SERV_TO_DWG">
            <attributes>
                <attribute name="Framed-IP-Address" value="%(framed_ip_address)s" />
                <attribute name="Cisco-AVPAIR" value="subscriber:command=deactivate-service" />
                <attribute name="Cisco-AVPAIR" value=" subscriber:sd=%(service_name)s" />
            </attributes>
        </request>
    </body>
</envelope>
"""