#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError
from mw1_backend.configs import SERVICES_DB_HOST, SERVICES_DB_NAME, SERVICES_DB_PASS, SERVICES_DB_USER
from pcrf_backend.pcrf_control import get_pcrf_profile
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
        with open('/tmp/qps_usages_diffs.csv', 'a') as qps_usages_diffs:
            for pair in result:
                users_cnt += 1
                if users_cnt % CNT_THREASHOLD == 0:
                    logger.info("User %d reached", users_cnt)
                subscriber_id = pair[0]
                profile_result = get_pcrf_profile(subscriber_id)
                if not profile_result['action_result']:
                    logger.error("%s", profile_result['action_error_message'])
                    continue
                qps_profile = profile_result['profile']
                if not 'start_date' in qps_profile:
                    logger.error("subscriber %s has no active bill cycle", subscriber_id)
                    continue
                start_date = parser.parse(qps_profile['start_date']).date()
                end_date = parser.parse(qps_profile['end_date']).date()
                total_debited = int(qps_profile['total_debited'])

                if start_date > datetime.date.today() - relativedelta(months=2):
                    aggregated = OnlineDailyUsage.objects.filter(username=subscriber_id, date__gte=start_date,
                                                                 date__lte=end_date).aggregate(Sum('charged_bytes'))
                    agg_charged_sum = aggregated['charged_bytes__sum']
                    if not agg_charged_sum:
                        agg_charged_sum = 0
                    epsilon = math.fabs(agg_charged_sum - total_debited)
                    if total_debited > agg_charged_sum and epsilon > 0.05 * total_debited:
                        qps_usages_diffs.write("%s,%s\n" % (subscriber_id, epsilon))
        logger.info("*** Script finished ***")