from django.db import models


class NSTPermissions(models.Model):
    """Custom permissions for each web service"""

    class Meta:
        permissions = (
            ('allowed_user_actions', 'NST: Get Allowed User Actions'),
            ('get_basic_info', 'NST: Get BasicInfo Logs'),
            ('get_pcrf_logs', 'NST: Get PCRF Logs'),
            ('get_topups_logs', 'NST: Get Topups Logs'),
            ('get_allowed_services', 'NST: Get allowed Services'),
            ('subscriber_logs', 'NST: Subscriber Logs'),
            ('get_daily_usage', 'NST: Daily Usage'),
            ('get_dpi_daily_usage', 'NST: DPI Daily Usage'),
            ('get_sbr_daily_usage', 'NST: SBR Daily Usage'),
            ('remove_allowed_service', 'NST: Remove Allowed Service'),
            ('add_allowed_service', 'NST: Add Allowed Service'),
            ('decrypt_password', 'NST: Decrypt Password'),
            ('nst_get_full_ldap_profile', 'NST: Get full LDAP profile'),
            ('nst_get_pcrf_profile', 'NST: Get PCRF Profile'),
            ('nst_get_pcrf_services', 'NST: Get PCRF Services'),
            ('nst_check_ldap_user_exists', 'NST: Check LDAP User Exists'),
            ('nst_get_aaa_user_by_name', 'NST: Get AAA User by Name'),
            ('nst_get_aaa_user_by_ip', 'NST: Get AAA User by IP'),
            ('nst_get_aaa_full_sessions', 'NST: Get AAA Full Sessions'),
            ('nst_get_pcrf_session', 'NST: Get PCRF Session'),
            ('remove_ldap_service', 'NST: Remove LDAP Service'),
            ('remove_pcrf_user', 'NST: Remove PCRF User'),
            ('nst_create_change_ldap', 'NST: Create/Change LDAP Service'),
            ('nst_create_change_pcrf', 'NST: Create/Change PCRF Service'),
            ('nst_remove_suspended_service', 'NST: Remove SUSPENDED Service'),
            ('nst_add_suspended_service', 'NST: Add SUSPENDED Service'),
            ('nst_remove_portalredir_service', 'NST: Remove Portal Redirection Service'),
            ('nst_credit_subscriber', 'NST: Credit Subscriber'),
            ('nst_get_analytics', 'NST: Get Analytics'),
            ('nst_topups_analytics', 'NST: Topups Analytics'),
            ('nst_debit_subscriber', 'NST: Debit Subscriber'),
            ('nst_cyber_crime', 'NST: Cyber Crime'),
            ('nst_get_wifi_report', 'NST: Query WiFi Reports'),
            ('nst_get_wifi_venues', 'NST: Get WiFi Venues'),
            ('nst_provision_wifi_venue', 'NST: Provision WiFi Venue'),
            ('nst_view_msan_ip_plans', 'NST: View MSAN IP Plans'),
            ('nst_provision_msan_ip_plans', 'NST: Provision MSAN IP Plans'),
            ('nst_query_msan_plan', 'NST: Query MSAN Plan'),
            ('nst_update_msan_ip_plans', 'NST: Update MSAN IP Plans'),
            ('nst_remove_msan_ip_plans', 'NST: Remove MSAN IP Plans'),
            ('nst_provision_tedata_msan', 'NST: Provision TE Data MSAN'),
            ('nst_get_tedata_router_port', 'NST: Get tedata router port'),
            ('nst_get_tedata_router', 'NST: Get tedata router'),
            ('nst_get_tedata_msan_plan', 'NST: Get TeData MSAN Plan'),
            ('nst_view_tedata_management_div', 'NST: View TE Data-MSAN Management Div'),
            ('nst_remove_tedata_management_div', 'NST: Remove TE Data-MSAN Management Div'),
            ('nst_list_routers', 'NST: List TeData Routers'),
            ('nst_manage_tedata_routers', 'NST: Manage TE Data Routers'),
            ('nst_optionpack', 'NST: Option Pack'),
            ('nst_provision_gpon_device', 'NST: Provision GPON Device'),
            ('nst_provision_gpon_subscriber', 'NST: Provision GPON Subscriber'),
			('nst_manage_static_ips', 'NST: Manage Static Ips'),
            ('nst_assign_static_ips', "NST: Assign Static Ips"),
            ('nst_get_wifi_logs', "NST: Get WiFi Logs"),
            ('nst_usage_calculator', "NST: Usage Calculator"),
            ('nst_reset_subscriber_password', "NST: Reset Subscriber Password"),
            ('nst_hard_reset_subscriber_password', "NST: Hard Reset Subscriber Password")
        )


class CyberCrimeSession(models.Model):
    id = models.BigIntegerField(primary_key=True, db_column="ID")
    user_name = models.CharField(max_length=50, db_column="USER_NAME")
    record_type = models.CharField(max_length=10, db_column='RECORD_TYPE')
    session_id = models.CharField(max_length=255, db_column="SESSION_ID")
    event_time = models.DateTimeField(db_column='EVENT_TIME')
    time_stamp = models.BigIntegerField(max_length=20, db_column="TIME_STAMP")
    source_ip = models.CharField(max_length=15, db_column="SOURCE_IP_ADDRESS")
    mac = models.CharField(max_length=12, db_column="MAC")

    class Meta:
        db_table = "cdr"
        managed = False


class SBRDailyUsage(models.Model):
    """Online Daily usage"""
    username = models.CharField(max_length=60, db_column="USER_NAME")
    service_name = models.CharField(max_length=60, db_column="SERVICE_NAME")
    date = models.DateField(db_column="USAGE_DATE")
    upload = models.BigIntegerField(db_column="INPUT_BYTES")
    download = models.BigIntegerField(db_column="OUTPUT_BYTES")
    # device_service = models.CharField(max_length=30,  db_column="device_service")

    def __unicode__(self):
        return "Usage of: %s" % self.date

    class Meta:
        db_table = "daily_usage"
        managed = False


class NASTool(models.Model):
    nasport_id = models.CharField(max_length=300, db_index=True)
    long_name = models.CharField(max_length=300, db_index=True)
    short_name = models.CharField(max_length=300, db_index=True)
    nasport_ip = models.IPAddressField()
    management_ip = models.IPAddressField()
    dslam_ip = models.IPAddressField()
    type = models.CharField(max_length=300, null=True, blank=True)
    card = models.CharField(max_length=2, null=True, blank=True)
    port = models.CharField(max_length=2, null=True, blank=True)
    ap = models.CharField(max_length=128, null=True, blank=True)
    index = models.CharField(max_length=64, null=True, blank=True)
    index2 = models.CharField(max_length=64, null=True, blank=True)
    index3 = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        db_table = 'wfws_nastool'
        managed = False


    def save(self, *args, **kwargs):
        self.using = 'wifi_db'
        super(NASTool, self).save(*args, **kwargs)  # Call the "real" save() method.


class SubscriberLogs(models.Model):

    host_name = models.CharField(max_length=20, db_column='host_name')
    date_time = models.DateField(db_column="date_time")
    user_name = models.CharField(max_length=50, db_column='user_name',primary_key=True)
    service_name = models.CharField(max_length=100, db_column='service_name')
    nas_port_id_ldap = models.CharField(max_length=120, db_column='nas_port_id_ldap')
    nas_port = models.CharField(max_length=50, db_column='nas_port')
    status = models.CharField(max_length=10, db_column='status')
    reject_reason = models.CharField(max_length=50, db_column='reject_reason')
    nas_port_id_request = models.CharField(max_length=100, db_column='nas_port_id_request')
    nas_ipaddress = models.CharField(max_length=15, db_column='nas_ipaddress')

    class Meta:
        db_table = 'VAS_Log'
        managed = False