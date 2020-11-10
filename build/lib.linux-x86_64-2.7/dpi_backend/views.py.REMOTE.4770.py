import urllib2
import re # import regex
from django.http import HttpResponse
from shared.decorators import check_params, handle_connection_error
from forms import InputForm
import logging
import json
import gzip
import StringIO
from mw1_backend.configs import DPI_URL
from .xml_templates import DPI_XML_REQUEST
#from auth.utils import token_required

logger = logging.getLogger(__name__)

@check_params('subscriber_id', 'start_date', 'end_date')
def get_dpi_usage(request):
    form = InputForm(request.GET)
    if not form.is_valid():
        error_msg = ""
        for k, v in form.errors.items():
            error_msg += "%s: %s\n" % (k, ", ".join(v))
        return HttpResponse(json.dumps({'success': False, 'msg': error_msg}), content_type="application/json")

    subscriber_id = form.cleaned_data['subscriber_id']
    start_date = form.cleaned_data['start_date']
    end_date = form.cleaned_data['end_date']
    logger.debug("Getting Subscriber ID: (%s) , start date: (%s), end date: (%s)", subscriber_id, start_date, end_date)

    data = DPI_XML_REQUEST % {'subscriber_id': subscriber_id, 'start_date': start_date, 'end_date': end_date}
    headers = {'Content-Type': 'text/xml'}
    req = urllib2.Request(DPI_URL, data, headers)
    response = urllib2.urlopen(req)
    xml = response.read()
    res = re.findall("@example.jaxws.sun.com>\r\nContent-Type: application/x-gzip\r\nContent-Transfer-Encoding: binary\r\n\r\n(.*)\r\n--uuid", xml, re.DOTALL)
    if res and not res[0] == "\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00":
        # gets the gzip binary data into an object to extract .gz file to plain text
        fio = StringIO.StringIO(res[0])
        final = gzip.GzipFile(fileobj=fio)
        results = []
        for line in final.readlines():
            line = line.split(',')
            results.append([line[1], line[2].replace("\n", "")])
        response = {"error": False, "errorMessage": "", "results": results}
        return HttpResponse(json.dumps(response), content_type="application/json")

    response = {"error": True, "type": "warning", "errorMessage": "Subscriber not found."}
    return HttpResponse(json.dumps(response), content_type="application/json")

