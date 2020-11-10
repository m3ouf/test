from django.core.management.base import BaseCommand
from aaa_backend.client import AAAClient
from django.core.mail import EmailMessage
import logging
import fileinput
import datetime

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("*** Script started ***")
        aaa_client = AAAClient()
        now = datetime.datetime.now().isoformat()
        with open('/tmp/forced_migration_errors_{0}'.format(now), 'w', 1) as error_file:
            with open('/tmp/forced_migration_success_{0}'.format(now), 'w', 1) as success_file:
                for line in fileinput.input(args):
                    subscriber_id, service_name = [val.strip() for val in line.split(",")]
                    logger.info("Provisioning subscriber %s", subscriber_id)
                    try:
                        result = aaa_client.start_redirect_coa(subscriber_id, service_name)
                        if result['action_result']:
                            coa_results = result['coa_results']
                            success = bool(filter(lambda result: result['coa_result'] == True, coa_results))
                            if not success:
                                error_file.write("{0},{1}: {2}\n".format(subscriber_id, service_name, coa_results))
                            else:
                                success_file.write("{0},{1}\n".format(subscriber_id, service_name))
                        else:
                            error_file.write("{0},{1}: {2}\n".format(subscriber_id, service_name, result['action_error_message']))

                    except Exception as e:
                        error_file.write("{0},{1}: {2}\n".format(subscriber_id, service_name, e.message))

        with open('/tmp/forced_migration_errors_{0}'.format(now), 'r') as error_file:
            with open('/tmp/forced_migration_success_{0}'.format(now), 'r') as success_file:

                mail = EmailMessage('Forced Redirection Batch log {0}'.format(now),
                          'Kindly find the success and failure logs in the attachments.', 'network.vas@tedata.net',
                          ['ehab.afifi@tedata.net', 'farid.farouk@tedata.net', 'mahmoud.iaboelenin@tedata.net'])
                mail.attach('forced_migration_errors_{0}'.format(now), error_file.read(), 'text/plain')
                mail.attach('forced_migration_success_{0}'.format(now), success_file.read(), 'text/plain')
                mail.send()

        logger.info("*** Script finished ***")
