#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError
from mw1_backend.configs import SERVICES_DB_HOST, SERVICES_DB_NAME, SERVICES_DB_PASS, SERVICES_DB_USER
from pcrf_backend.pcrf_control import get_pcrf_profile, get_pcrf_services
from dateutil.relativedelta import relativedelta
from dateutil import parser
from shared.models import OnlineDailyUsage
from django.db.models import Sum
import datetime
import logging
import MySQLdb
import math

logger = logging.getLogger(__name__)
CNT_THREASHOLD = 10000


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("*** Script started ***")
        logger.info("*** Connecting to DB ***")
        db = MySQLdb.connect(host=SERVICES_DB_HOST, user=SERVICES_DB_USER, passwd=SERVICES_DB_PASS,
                                  db=SERVICES_DB_NAME)
        cur = db.cursor()
        logger.info("*** Fetching Capped subscribers ***")
        cur.execute("SELECT USER_NAME FROM subscribed_product WHERE SERVICE_NAME like '%CAP%'")
        result = cur.fetchall()
        users_cnt = 0
        logger.info("*** Getting differences ***")
        with open('/tmp/qps_report_abuse.csv', 'w') as qps_usages_diffs:
            for pair in result:
                users_cnt += 1
                if users_cnt % CNT_THREASHOLD == 0:
                    logger.info("User %d reached", users_cnt)
                subscriber_id = pair[0]
                profile_result = get_pcrf_profile(subscriber_id)
                topup_result = get_pcrf_services(user_name=subscriber_id, service_type='topup')
                if not profile_result['action_result']:
                    continue
                qps_profile = profile_result['profile']
                if not 'start_date' in qps_profile:
                    continue
                start_date = parser.parse(qps_profile['start_date']).date()
                end_date = parser.parse(qps_profile['end_date']).date()
                topups = topup_result.get('services')
                service_name = qps_profile['account_balance_code']
                if topups:
                    for topup in topups:
                        total_topup_allowed += int(topup['basic_amount'])
                else:
                    total_topup_allowed = 0
                total_allowed = int(qps_profile['basic_amount']) + int(total_topup_allowed)
                if start_date > datetime.date.today() - relativedelta(months=1):
                    aggregated = OnlineDailyUsage.objects.filter(username=subscriber_id, date__gte=start_date,
                                                                 date__lte=end_date).aggregate(Sum('charged_bytes'))
                    agg_charged_sum = aggregated['charged_bytes__sum']
                    if not agg_charged_sum:
                        agg_charged_sum = 0
                    if total_allowed < agg_charged_sum:
                        epsilon = math.fabs(agg_charged_sum - total_allowed)
                        if ("_512_" in service_name and epsilon > 715827882) or ("_1024_" in service_name and epsilon > 1431655765) or ("_2048_" in service_name and epsilon > 2863311530 ) or ("_4096_" in service_name and epsilon > 5726623060) or ("_8192_" in service_name and epsilon > 11453246120) or ("_16384_" in service_name and epsilon > 22906492240) or ("_24576_" in service_name and epsilon > 34359738360) or ("_20480_" in service_name and epsilon > 28633115300):
                            qps_usages_diffs.write("%s,%s,%s,%s,%s\n" % (subscriber_id, service_name, total_allowed, agg_charged_sum, epsilon))
        logger.info("*** Script finished ***")
