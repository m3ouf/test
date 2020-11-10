from django.db import models


class PCRFProfileLog(models.Model):
    username = models.CharField(max_length=128)
    service_name = models.CharField(max_length=128)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    total_debited = models.FloatField()
    total_amount = models.FloatField()
    original_amount = models.FloatField()
    amount = models.FloatField()


class TopupLog(models.Model):
    credit_id = models.CharField(max_length=128, primary_key=True)
    start_date = models.DateTimeField()
    basic_amount = models.FloatField()
    remaining = models.FloatField()
    pcrf_profile = models.ForeignKey(PCRFProfileLog)