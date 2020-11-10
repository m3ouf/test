from django.db import models
from .fields import IPNetworkField
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
import re
import netaddr




def validate_port_name(value):
    if not re.match(r'^[a-z]+\-[0-9]\/[0-9]\/[0-9]\/?([0-9]+)?$', value):
        raise ValidationError("Invalid port name")


def validate_router_name(value):
    if not re.match(r'^[A-Z0-9]+\-[A-Z0-9]+\-[A-Z0-9]+\-[A-Z0-9]+$', value):
        raise ValidationError("Invalid Router name")


class Router(models.Model):
    name = models.CharField(unique=True, max_length=128)

    class Meta:
        db_table = "Router"

    def __unicode__(self):
        return self.name


class RouterPort(models.Model):
    name = models.CharField(max_length=32, validators=[validate_port_name])
    used = models.BooleanField(default=False)
    router = models.ForeignKey(Router, related_name='ports')

    def __unicode__(self):
        return "%s:%s:%s" % (self.id, self.name, "Taken" if self.used else "Available")

    class Meta:
        db_table = "RouterPort"


class RouterNetwork(models.Model):
    network_ip = IPNetworkField(unique=True)
    router = models.ForeignKey(Router, related_name='networks')

    def __unicode__(self):
        return unicode(self.network_ip)

    class Meta:
        db_table = "RouterNetwork"


class MSAN(models.Model):
    code = models.CharField(unique=True, max_length=20)
    name = models.CharField(max_length=512)
    h248_subnet = IPNetworkField(unique=True)
    gateway_interface = models.GenericIPAddressField(unique=True)
    traffic_shelf1 = models.GenericIPAddressField(unique=True)
    traffic_shelf2 = models.GenericIPAddressField(unique=True, null=True, blank=True)
    traffic_shelf3 = models.GenericIPAddressField(unique=True, null=True, blank=True)
    traffic_vlan = models.PositiveIntegerField(default=941)

    manage_subnet = IPNetworkField()
    manage_gw_subnet = IPNetworkField(unique=True)
    manage_gw_ip = models.GenericIPAddressField()
    manage_shelf1 = models.GenericIPAddressField(unique=True)
    manage_shelf2 = models.GenericIPAddressField(unique=True, null=True, blank=True)
    manage_shelf3 = models.GenericIPAddressField(unique=True, null=True, blank=True)
    manage_vlan = models.PositiveIntegerField(default=942)

    router = models.ForeignKey(Router, null=True, blank=True)

    def delete(self, using=None):
        if hasattr(self, 'tedatamsan'):
            self.tedatamsan.delete()
        super(MSAN, self).delete(using)

    class Meta:
        db_table = "MSAN"


class TEDataMsan(models.Model):
    msan = models.OneToOneField(MSAN, unique=True)
    router_port = models.OneToOneField(RouterPort, unique=True)
    router_backup_port = models.OneToOneField(RouterPort, unique=True, null=True, blank=True, related_name="backup_port")
    manage_vlan = models.PositiveIntegerField(default=400)
    manage_gw_subnet = IPNetworkField(unique=True)
    manage_gw_ip = models.GenericIPAddressField()
    shelf1 = models.GenericIPAddressField(unique=True)
    shelf2 = models.GenericIPAddressField(unique=True, null=True, blank=True)
    shelf3 = models.GenericIPAddressField(unique=True, null=True, blank=True)

    def __unicode__(self):
        return "%s <--> %s" % (self.msan.name, self.router_port.router.name)

    def save(self, *args, **kwargs):
        self.router_port.used = True
        self.router_port.save()
        if self.router_backup_port:
            self.router_backup_port.used = True
            self.router_backup_port.save()
        super(TEDataMsan, self).save(*args, **kwargs)

    def delete(self, using=None):
        self.router_port.used = False
        self.router_port.save()
        if self.router_backup_port:
            self.router_backup_port.used = False
            self.router_backup_port.save()
        super(TEDataMsan, self).delete(using)

    class Meta:
        db_table = "TEDataMSAN"

# ###################### NorthStar replacement ###################


class Zone(models.Model):
    name = models.CharField(max_length=128, unique=True)

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = "CoreAccessZone"

class Pop(models.Model):
    name = models.CharField(max_length=128, unique=True)
    zone = models.ForeignKey(Zone, related_name='pops')

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.name)

    class Meta:
        db_table = "CoreAccessPop"

class PopDevice(models.Model):
    name = models.CharField(max_length=128, unique=True)
    pop = models.ForeignKey(Pop, related_name='devices')

    def __unicode__(self):
        return "{0}:{1}".format(self.id, self.name)

    class Meta:
        db_table = "CoreAccessPopDevice"

class AllocatedSubnet(models.Model):
    network_ip = IPNetworkField(unique=True)
    device = models.ForeignKey(PopDevice, related_name='networks')

    @property
    def free_ips(self):
        return self.network_ip.numhosts - sum(network.network_ip.numhosts for network in self.assigned_subnets.all())

    def __unicode__(self):
        return "{0}:{1}".format(self.id, unicode(self.network_ip))

    class Meta:
        db_table = "CoreAccessAllocatedSubnet"

class AssignedSubnet(models.Model):
    network_ip = IPNetworkField(unique=True)
    account_number = models.CharField(max_length=128)
    name = models.CharField(max_length=64, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    allocated_subnet = models.ForeignKey(AllocatedSubnet, related_name='assigned_subnets')

    def __unicode__(self):
        return unicode(self.network_ip)

    class Meta:
        db_table = "CoreAccessAssignedSubnet"



def validate_model(sender, **kwargs):
    if (sender is TEDataMsan or sender is MSAN or sender is RouterNetwork or sender is RouterPort or sender is Router) \
            and 'raw' in kwargs and not kwargs['raw']:
        kwargs['instance'].full_clean()

pre_save.connect(validate_model, dispatch_uid='validate_models')


