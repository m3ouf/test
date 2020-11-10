#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError

from physical_adsl_backend.behaviors import ZteTelnetBehavior
import logging
import sys
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("*** Script started ***")
        if not len(sys.argv) == 3:
            raise CommandError("You need to specify a valid csv file\n"
            "usage: python manage.py configure_batch_zte sample.csv")

        telnet_behavior = ZteTelnetBehavior()

        with open(sys.argv[2]) as devices, open("/tmp/zte_batch_errors.txt", 'w') as errors:
            logger.info("Starting to process ZTEs")
            for line in devices:

                try:
                    ip = line.strip()
                    logger.info("handling IP %s", ip)

                    telnet_behavior.set_port_info(ip, "traffic-profile 123 ip cir 16384 cbs 2 pir 16384 pbs 2")
                    telnet_behavior.set_port_info(ip, "qos queue-map-profile 123 pvc-type pvc1 7 pvc2 6 pvc3 5 pvc4 4 pvc5 3 pvc6 2 pvc7 1 pvc8 0")
                except Exception as e:
                    errors.write(ip + ": " + str(e) + "\n")



            logger.info("Finished to process ZTEs")
        logger.info("*** Script finished ***")
