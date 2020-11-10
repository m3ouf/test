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
            raise CommandError("\nUsage:\n\tpython management.py reset_ldap_users <file_name>")
        client = LDAPClient(LDAP_HOST, LDAP_PASSWORD)
        raw_users = open(args[0]).readlines()
        users = [line.strip() for line in raw_users]
        users_cnt = 1
        logger.info("Starting to reset provided users")
        for user in users:
            if users_cnt % CNT_THREASHOLD == 0:
                logger.info("User %d reached", users_cnt)
            reset_result = client.reset_profile(user)
            if not reset_result['action_result']:
                logger.error(reset_result['action_error_message'])
            users_cnt += 1
        logger.info("Finished reseting users.")