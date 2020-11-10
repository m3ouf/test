from django.db import models


class MacTal(models.Model):
    mac = models.CharField(max_length=150)
    msisdn = models.CharField(max_length=150)
    service = models.CharField(max_length=150)

    def __unicode__(self):
        return self.msisdn

    class Meta:
        db_table = 'wfws_mactal'
        managed = False



class WiFiLogs(models.Model):

    subscriber_id = models.CharField(max_length=150)
    fn_name = models.CharField(max_length=150)
    message = models.CharField(max_length=500)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.NullBooleanField()
    payload = models.TextField()

    class Meta:
        managed = False