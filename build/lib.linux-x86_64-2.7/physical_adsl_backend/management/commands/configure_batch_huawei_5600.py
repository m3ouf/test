#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError

from physical_adsl_backend.behaviors import HuaweiTelnetBehavior
from mw1_backend.configs import ALCATEL_H5600_TELNET_USER, ALCATEL_H5600_TELNET_PASS
import logging
import sys
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("*** Script started ***")
        if not len(sys.argv) == 3:
            raise CommandError("You need to specify a valid csv file\n"
            "usage: python manage.py configure_batch_huawei_5600 sample.csv")


        with open(sys.argv[2]) as devices, open("/tmp/huawei_5600_batch_errors.txt", 'w') as errors:
            logger.info("Starting to process Huaweis 5600")
            for line in devices:

                try:
                    ip = line.strip()
                    logger.info("handling IP %s", ip)
                    with HuaweiTelnetBehavior(ip, '5600') as telnet_behavior:
                        telnet_behavior.execute("traffic table index 7 ip car 24576 priority 7 priority-policy pvc-Setting")
                except Exception as e:
                    errors.write(ip + ": " + str(e) + "\n")
            logger.info("Finished to process Huaweis 5600")
        logger.info("*** Script finished ***")
