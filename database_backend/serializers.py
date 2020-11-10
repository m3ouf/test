from rest_framework.serializers import ModelSerializer, StringRelatedField, ReadOnlyField, Field, \
    HyperlinkedModelSerializer, HyperlinkedRelatedField, PrimaryKeyRelatedField, RelatedField
from .models import MSAN, Router, RouterPort, TEDataMsan, RouterNetwork, Zone, Pop, PopDevice, AllocatedSubnet, \
    AssignedSubnet


class MSANSerializer(ModelSerializer):
    class Meta:
        model = MSAN
        fields = ['code', 'name', 'h248_subnet', 'gateway_interface', 'traffic_shelf1', 'traffic_shelf2',
                  'traffic_shelf3',
                  'traffic_vlan', 'manage_subnet', 'manage_gw_subnet', 'manage_gw_ip', 'manage_shelf1',
                  'manage_shelf2',
                  'manage_shelf3', 'manage_vlan', 'id', 'tedatamsan']

    def __init__(self, *args, **kwargs):
        super(MSANSerializer, self).__init__(*args, **kwargs)

        if self.context['request'].QUERY_PARAMS.get('idCodeNameOnly'):
            existing = set(self.fields)
            allowed = set(['id', 'code', 'name', 'tedatamsan'])
            for field in existing - allowed:
                self.fields.pop(field)
        else:
            self.fields.pop('tedatamsan')


class RouterSerializer(ModelSerializer):
    ports = StringRelatedField(many=True)
    networks = StringRelatedField(many=True)

    class Meta:
        model = Router
        fields = ['name', 'ports', 'networks', 'id']


class RouterPortSerializer(ModelSerializer):
    class Meta:
        model = RouterPort
        fields = ['name', 'used', 'router']


class RouterNetworkSerializer(ModelSerializer):
    class Meta:
        model = RouterNetwork
        fields = ['network_ip', 'router']


class TEDataMSANSerializer(ModelSerializer):
    msan = PrimaryKeyRelatedField(queryset=MSAN.objects.all())
    router_port = PrimaryKeyRelatedField(queryset=RouterPort.objects.all())
    router_backup_port = PrimaryKeyRelatedField(allow_null=True, queryset=RouterPort.objects.all())

    class Meta:
        model = TEDataMsan
        fields = ['id', 'msan', 'router_port', 'router_backup_port', 'manage_vlan', 'manage_gw_subnet', 'manage_gw_ip', 'shelf1', 'shelf2',
                  'shelf3']

# ### Core Access ###
class ZoneSerializer(ModelSerializer):
    pops = StringRelatedField(many=True)
    class Meta:
        model = Zone
        fields = ['name', 'id', 'pops']

    def __init__(self, *args, **kwargs):
        super(ZoneSerializer, self).__init__(*args, **kwargs)

        if self.context['request'].QUERY_PARAMS.get('idNameOnly'):
            existing = set(self.fields)
            allowed = set(['id', 'name'])
            for field in existing - allowed:
                self.fields.pop(field)

class PopSerializer(ModelSerializer):
    devices = StringRelatedField(many=True, read_only=True)
    zone_name = ReadOnlyField(source='zone.name')

    class Meta:
        model = Pop
        fields = ['name', 'zone_name', 'id', 'zone', 'devices']


class DeviceSerializer(ModelSerializer):
    networks = StringRelatedField(many=True, read_only=True)
    zone_name = ReadOnlyField(source='pop.zone.name')
    pop_name = ReadOnlyField(source='pop.name')

    class Meta:
        model = PopDevice
        fields = ['name', 'zone_name', 'pop_name', 'id', 'pop', 'networks']


class AllocatedSubnetSerializer(ModelSerializer):
    assigned_subnets = StringRelatedField(many=True, read_only=True)
    device_name = ReadOnlyField(source="device.name")
    zone_name = ReadOnlyField(source='device.pop.zone.name')
    pop_name = ReadOnlyField(source='device.pop.name')

    class Meta:
        model = AllocatedSubnet
        fields = ['network_ip', 'device_name', 'pop_name', 'zone_name', 'id', 'device', 'assigned_subnets', 'free_ips']


class AssignedSubnetSerializer(ModelSerializer):
    device_name = ReadOnlyField(source="allocated_subnet.device.name")
    pop_name = ReadOnlyField(source='allocated_subnet.device.pop.name')
    zone_name = ReadOnlyField(source='allocated_subnet.device.pop.zone.name')

    class Meta:
        model = AssignedSubnet
        fields = ['network_ip', 'device_name', 'pop_name', 'zone_name', 'account_number', 'name', 'phone', 'id', 'allocated_subnet']

    def __init__(self, *args, **kwargs):
        super(AssignedSubnetSerializer, self).__init__(*args, **kwargs)

        if self.context and self.context['request'].QUERY_PARAMS.get('idCodeNameOnly'):
            existing = set(self.fields)
            allowed = set(['network_ip', 'account_number', 'id'])
            for field in existing - allowed:
                self.fields.pop(field)
