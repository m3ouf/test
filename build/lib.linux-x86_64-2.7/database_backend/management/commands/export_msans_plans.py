from django.core.management.base import BaseCommand
from database_backend.helpers import get_msan_plans_reports
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("*** Script started ***")
        logger.info("*** Parsing file ***")
        wb = get_msan_plans_reports()

        wb.save('generated.xlsx')

        logger.info("*** Script finished ***")