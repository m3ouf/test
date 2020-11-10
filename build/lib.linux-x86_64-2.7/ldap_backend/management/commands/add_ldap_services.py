#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError
from ldap_backend.ldap_profile import LDAPClient
from mw1_backend.configs import LDAP_PASSWORD, LDAP_HOST
import logging


logger = logging.getLogger(__name__)
CNT_THREASHOLD = 10000


class Command(BaseCommand):
    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError("\nUsage:\n\tpython management.py add_ldap_services <file_name>")
        client = LDAPClient()
        raw_users = open(args[0]).readlines()
        pairs = [[item.strip() for item in line.split(',')] for line in raw_users]
        users_cnt = 1
        logger.info("Starting to reset provided users")
        for pair in pairs:
            if users_cnt % CNT_THREASHOLD == 0:
                logger.info("User %d reached", users_cnt)

            try:
                username = pair[0]
                service_name = pair[1]
                add_change_result = client.add_or_change_service(username, service_name)
                if not add_change_result['action_result']:
                    logger.error(add_change_result['action_error_message'])

            except IndexError:
                logger.error("Malformed entry %s" % pair)
            users_cnt += 1
        logger.info("Finished reseting users.")