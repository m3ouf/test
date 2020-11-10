from django.db import models


class ZteC30019Oids(models.Model):
    shelf = models.PositiveIntegerField()
    card = models.PositiveIntegerField()
    port = models.PositiveIntegerField()

    index_id = models.PositiveIntegerField()
    index_id_pvc_1 = models.PositiveIntegerField()
    index_id_pvc_2 = models.PositiveIntegerField()

    outer_vlan_1 = models.CharField(max_length=64)
    inner_vlan_1 = models.CharField(max_length=64)
    vpi_1 = models.CharField(max_length=64)
    vci_1 = models.CharField(max_length=64)
    outer_vlan_2 = models.CharField(max_length=64)
    inner_vlan_2 = models.CharField(max_length=64)
    vpi_2 = models.CharField(max_length=64)
    vci_2 = models.CharField(max_length=64)

    class Meta:
        db_table = "ZteC30019Oids"


class ZteC30021Oids(models.Model):
    shelf = models.PositiveIntegerField()
    card = models.PositiveIntegerField()
    port = models.PositiveIntegerField()

    index_id = models.PositiveIntegerField()
    index_id_pvc_1 = models.PositiveIntegerField()
    index_id_pvc_2 = models.PositiveIntegerField()

    outer_vlan_1 = models.CharField(max_length=64)
    inner_vlan_1 = models.CharField(max_length=64)
    vpi_1 = models.CharField(max_length=64)
    vci_1 = models.CharField(max_length=64)
    outer_vlan_2 = models.CharField(max_length=64)
    inner_vlan_2 = models.CharField(max_length=64)
    vpi_2 = models.CharField(max_length=64)
    vci_2 = models.CharField(max_length=64)

    class Meta:
        db_table = "ZteC30021Oids"


class Zte5200Oids(models.Model):
    shelf = models.PositiveIntegerField()
    card = models.PositiveIntegerField()
    port = models.PositiveIntegerField()

    index_id = models.PositiveIntegerField()
    index_id_pvc_1 = models.PositiveIntegerField()
    index_id_pvc_2 = models.PositiveIntegerField()

    outer_vlan_1 = models.CharField(max_length=64)
    inner_vlan_1 = models.CharField(max_length=64)
    vpi_1 = models.CharField(max_length=64)
    vci_1 = models.CharField(max_length=64)
    outer_vlan_2 = models.CharField(max_length=64)
    inner_vlan_2 = models.CharField(max_length=64)
    vpi_2 = models.CharField(max_length=64)
    vci_2 = models.CharField(max_length=64)

    class Meta:
        db_table = "Zte5200Oids"


class GPONBrand(models.Model):
    brand_name = models.CharField(max_length=100)


class GPONModel(models.Model):
    brand = models.ForeignKey('GPONBrand')
    model_name = models.CharField(max_length=100)


class GPONDevice(models.Model):
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(unique=True)
    device_model = models.ForeignKey('GPONModel')