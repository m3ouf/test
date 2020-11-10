from django.db import models


class BasicInfo(models.Model):
    """Basic information that are common to all Web services"""
    FN_LOCATION_CHOICES = (('fe', 'frontend'), ('be', 'backend'))
    # Request Fields
    transaction_id = models.CharField(max_length=64)
    fn_name = models.CharField(max_length=128)  # function name
    fn_location = models.CharField(max_length=16, choices=FN_LOCATION_CHOICES, default='backend')
    api_access_time = models.DateTimeField(null=True)  # time at which the request has arrived.
    access_time = models.DateTimeField(auto_now_add=True)  # time at which the api has done the job and about to return
    client_ip = models.GenericIPAddressField()
    key = models.CharField(max_length=128, null=True)
    request_service = models.CharField(max_length=128, null=True)
    user_name = models.CharField(max_length=512)
    online = models.NullBooleanField()

    # Response fields
    success = models.BooleanField(default=False)
    error_msg = models.TextField(null=True)
    error_code = models.CharField(max_length=32, null=True)
    status = models.CharField(null=True, max_length=512)  # active or inactive


    class Meta:
        db_table = "BasicInfo"


class ProvisionPCRFService(models.Model):
    """
    Request information about provisioning a PCRF service.
    """
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    carry_over = models.NullBooleanField()
    reset_consumed = models.BooleanField(default=False)
    basic_info = models.OneToOneField(BasicInfo)

    class Meta:
        db_table = "ProvisionPCRFService"


class BalanceAction(models.Model):
    """
    Request Information about balance .. which are credit and debit subscriber
    """
    BALANCE_CHOICES = (
        ('credit', 'Credit'),
        ('debit', 'Debit')
    )
    action_type = models.CharField(choices=BALANCE_CHOICES, max_length=512) # debit or credit
    amount = models.FloatField()
    basic_info = models.OneToOneField(BasicInfo)

    class Meta:
        db_table = "BalanceAction"


class SubscribedService(models.Model):
    """
    Response Information about subscribed services in user's profile.
    """
    service_name = models.CharField(max_length=512)
    basic_info = models.ForeignKey(BasicInfo, null=True)

    class Meta:
        db_table = "SubscribedService"


class QuotaProfile(models.Model):
    """
    Response information about PCRF Profile.
    """
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    basic_quota = models.FloatField()
    service = models.CharField(max_length=128)
    total_allowed_quota = models.FloatField()
    total_consumed_quota = models.FloatField()

    # next fields are calculated at frontend
    total_topup_quota = models.FloatField(null=True)
    remaining_topup_quota = models.FloatField(null=True)
    consumed_topup_quota = models.FloatField(null=True)

    basic_info = models.OneToOneField(BasicInfo)

    class Meta:
        db_table = "QuotaProfile"


class Topup(models.Model):
    """
    Response Information about Topups found at user's profile.
    """
    start_date = models.DateTimeField()
    remaining = models.FloatField(default=0)
    basic_amount = models.FloatField(default=0)
    basic_info = models.ForeignKey(BasicInfo, null=True)
    quota_profile = models.ForeignKey(QuotaProfile, null=True)

    class Meta:
        db_table = "Topup"


class COA(models.Model):
    basic_info = models.ForeignKey(BasicInfo)
    session_ip = models.GenericIPAddressField()
    nas_ip = models.GenericIPAddressField()
    nas_port_id = models.CharField(null=True, max_length=128)
    client_mac_address = models.CharField(max_length=64, null=True)
    started_service = models.CharField(max_length=128, null=True)
    stopped_service = models.CharField(max_length=128, null=True)
    started_coa_result = models.BooleanField(default=False)
    stopped_coa_result = models.BooleanField(default=False)
    started_coa_error_msg = models.CharField(max_length=128, null=True)
    stopped_coa_error_msg = models.CharField(max_length=128, null=True)

    class Meta:
        db_table = "COA"


# class OnlineService(models.Model):
#     coa = models.ForeignKey(COA)
#     service_name = models.CharField(max_length=128)
#
#     class Meta:
#         db_table = "OnlineCOAService"


class OnlineDailyUsage(models.Model):
    """Online Daily usage"""
    username = models.CharField(max_length=60, db_column="user_name")
    service_name = models.CharField(max_length=60, db_column="service_code")
    date = models.DateField(db_column="timestamp")
    upload = models.BigIntegerField(db_column="in_bytes")
    download = models.BigIntegerField(db_column="out_bytes")
    charged_bytes = models.BigIntegerField(db_column="total_bytes")
    device_service = models.CharField(max_length=30,  db_column="device_service")

    def __unicode__(self):
        return "Usage of: %s" % self.date

    class Meta:
        db_table = "qps_usage_day"


class PhysicalHomeWifiLog(models.Model):
    transaction_id = models.CharField(max_length=64)
    fn_name = models.CharField(max_length=128)  # function name
    fn_location = models.CharField(max_length=16, default='backend')
    api_access_time = models.DateTimeField(null=True)  # time at which the request has arrived.
    access_time = models.DateTimeField(auto_now_add=True)  # time at which the api has done the job and about to return
    client_ip = models.GenericIPAddressField()
    key = models.CharField(max_length=128, null=True)
    device_ip = models.GenericIPAddressField()
    community_id = models.CharField(max_length='512')
    port_number = models.PositiveIntegerField()
    card_number = models.PositiveIntegerField()
    shelf_number = models.IntegerField()

    # Response fields
    success = models.BooleanField(default=False)
    error_msg = models.TextField(null=True)
    error_code = models.CharField(max_length=32, null=True)
    enabled = models.NullBooleanField(null=True)

    class Meta:
        db_table = "PhysicalHomeWifiLog"