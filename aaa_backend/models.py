from django.db import models


class AAASession(models.Model):
    id = models.BigIntegerField(primary_key=True, db_column="Sbr_UniqueSessionId")
    cisco_account_info = models.CharField(max_length=84, db_column="CiscoAccountInfo")
    account_session_id = models.CharField(max_length=24, db_column="Sbr_AcctSessionId")
    framed_ip_address = models.IntegerField(db_column="Sbr_Ipv4Address")
    nas_name = models.CharField(max_length=39, db_column="Sbr_NasName")
    nas_ip_address = models.IntegerField(db_column="Sbr_NasIpv4Address")
    nas_port = models.BigIntegerField(db_column="Sbr_NasPort")
    nas_port_id = models.CharField(max_length=84, db_column="NasPortID")
    service_name = models.CharField(max_length=24, db_column="ServiceName")
    subscriber_id = models.CharField(max_length=24, db_column="Sbr_UserName")
    creation_time = models.DateTimeField(db_column="Sbr_CreationTime")
    calling_station_id = models.CharField(db_column="Sbr_CallingStationId", max_length=24)

    class Meta:
        db_table = "Sbr_CurrentSessions"
        managed = False