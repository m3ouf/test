DPI_XML_REQUEST = """<soap-env:Envelope
    xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:ns1="http://ws.reportingservices.sandvine.com">
      <soap-env:Header xmlns:svns1="http://services.sandvine.com">
        <svns1:username>spbuser</svns1:username>
        <svns1:password>sandvine</svns1:password>
      </soap-env:Header>
      <soap-env:Body>
    <ns1:RunTimeSeriesReportRequest>
        <ReportDefinition>Historical.TimeSeries.Subscriber.ApplicationProtocol</ReportDefinition>
        <CsvAttachmentFormat>
            <Compression>GZip</Compression>
            <Encoding>UTF-8</Encoding>        <Headers>false</Headers>
        </CsvAttachmentFormat>
        <TimeSeriesReportQuery>
            <QueryFields><QueryField>Subscriber.Name</QueryField><QueryField>ApplicationProtocol.DisplayName</QueryField><QueryField>TotalBytes</QueryField></QueryFields>
            <QueryFilters><QueryFilter>
                                <QueryField>Subscriber.Name</QueryField>
                                <Criteria>In</Criteria>
                                <Value>%(subscriber_id)s</Value>
                            </QueryFilter></QueryFilters>
            <QueryOrderings><QueryOrdering><QueryField>Subscriber.Name</QueryField><OrderingType>Ascending</OrderingType></QueryOrdering><QueryOrdering><QueryField>TotalBytes</QueryField><OrderingType>Descending</OrderingType></QueryOrdering></QueryOrderings>
            <TimeSeries>
                <Start>%(start_date)s</Start>
                <End>%(end_date)s</End>
                <TimeZone>Europe/Athens</TimeZone>
            </TimeSeries>
            <ReturnAllDimensionsInAllTimePeriods>false</ReturnAllDimensionsInAllTimePeriods>
        </TimeSeriesReportQuery>
    </ns1:RunTimeSeriesReportRequest>
      </soap-env:Body>
    </soap-env:Envelope>"""