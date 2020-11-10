from django.db import models
from mw1_backend.configs import PRODUCT_TABLE_NAME, MEMBER_TABLE, SUBSCRIBED_PRODUCT_TABLE, WIFI_ADSL_TABLE_NAME


class SBRProduct(models.Model):
    id = models.BigIntegerField(primary_key=True, db_column="ID")
    service_name = models.CharField(max_length=128, db_column="SERVICE_NAME")

    class Meta:
        db_table = PRODUCT_TABLE_NAME
        managed = False


class SBRMember(models.Model):
    id = models.BigIntegerField(primary_key=True, db_column="ID")
    username = models.CharField(max_length=128, db_column="USER_NAME")

    class Meta:
        db_table = MEMBER_TABLE
        managed = False

class LDAPStatus(models.Model):
    id = models.BigIntegerField(primary_key=True, db_column="id")
    username = models.CharField(max_length=128, db_column="username")
    status = models.BooleanField(default=False ,  db_column="status")
    service_name = models.CharField(max_length=128, null=True ,  db_column="service_name")

    class Meta:
        db_table = "ldap_request"
        managed = False

class SBRSubscribedProduct(models.Model):
    id = models.BigIntegerField(primary_key=True, db_column="ID")
    username = models.CharField(max_length=255, db_column="USER_NAME")
    service_name = models.CharField(max_length=255, db_column="SERVICE_NAME")
    product_id = models.CharField(max_length=255, db_column="PRODUCT_ID")

    class Meta:
        db_table = SUBSCRIBED_PRODUCT_TABLE
        managed = False

class WifiAdslMapping(models.Model):
    id = models.BigIntegerField(primary_key=True)
    wifi_username = models.CharField(max_length=255)
    adsl_username = models.CharField(max_length=255)
    service_name = models.CharField(max_length=255)

    class Meta:
        db_table = WIFI_ADSL_TABLE_NAME

