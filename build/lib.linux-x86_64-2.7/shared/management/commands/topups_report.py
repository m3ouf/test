#!/usr/bin/env python
from django.core.management.base import BaseCommand
from shared.models import BasicInfo
import logging


logger = logging.getLogger(__name__)
CNT_THREASHOLD = 10000


class Command(BaseCommand):
    def handle(self, *args, **options):
        users = open('/tmp/users.csv', 'r')
        output_fe = open('/tmp/frontend.csv', 'w')
        ouput_be = open('/tmp/backend.csv', 'w')
        frontend_logs = ['username,ip,transaction id,topup value,access time\n']
        # Backend logs
        backend_logs = ['username,ip,transaction id,topup value\n']
        for user in users:
            user = user.strip()

            frontend_requests = BasicInfo.objects.filter(user_name=user, fn_location='frontend',
                                                         fn_name='addTOPUPQuota')
            user_logs = []
            for bi in frontend_requests:
                try:

                    bi.balanceaction  # throws DoesNotExist if no balanceaction
                    if bi.balanceaction.action_type == 'credit':
                        user_logs.append(",".join([user, str(bi.client_ip), str(bi.transaction_id),
                                                   str(bi.balanceaction.amount),
                                                   str(bi.api_access_time)]) + "\n")
                except:
                    pass

            if user_logs:
                frontend_logs += user_logs

            backend_requests = BasicInfo.objects.filter(user_name=user, fn_location='backend',
                                                        fn_name='add_topup', transaction_id__startswith='NST-')
            user_logs = []
            for bi in backend_requests:
                try:
                    bi.balanceaction
                    if bi.balanceaction.action_type == 'credit':
                        user_logs.append(",".join([user, str(bi.client_ip), str(bi.transaction_id),
                                                   str(bi.balanceaction.amount)]) + "\n")

                except:
                    pass
            if user_logs:
                backend_logs += user_logs



        ouput_be.write("".join(backend_logs))
        output_fe.write("".join(frontend_logs))
        logger.info("Finished report.")
