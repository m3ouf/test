#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError

from physical_adsl_backend.clients import JuniperRouter
import logging
import sys
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("*** Script started ***")
        if not len(sys.argv) == 3:
            raise CommandError("You need to specify a valid csv file\n"
            "usage: python vlan942_msan2msan_blocking ips.csv")
        juniper_router = JuniperRouter()

        with open(sys.argv[2]) as routers, open("/tmp/vlan942_msan2msan_blocking_errors.txt", 'w', 1) as errors:
            logger.info("Starting to process Juniper routers")
            #import ipdb;ipdb.set_trace()

            for line in routers:

                try:
                    ip = line.strip()
                    logger.info("handling IP %s", ip)
                    result, err = juniper_router.set_router_acls(ip)
                    if not result:
                        errors.write(ip + ": " + err + "\n")
                except Exception as e:
                    errors.write(ip + ": " + str(e) + "\n")



            logger.info("Finished to process Juniper routers")
        logger.info("*** Script finished ***")
