from django.utils.log import AdminEmailHandler
from django.core.mail.message import EmailMultiAlternatives
from django.conf import settings


class ErrorNotifier(AdminEmailHandler):
    """
    sends a custom email for admins.
    """
    def emit(self, record):
        if not getattr(settings, "ADMINS", None):
            return
        subject = self.format_subject(record.getMessage())
        message = getattr(record, "email_body", record.getMessage())
        mail = EmailMultiAlternatives(u'%s%s' % (settings.EMAIL_SUBJECT_PREFIX, subject), message,
                                      settings.SERVER_EMAIL, [a[1] for a in settings.ADMINS],)
        mail.send(fail_silently=False)

