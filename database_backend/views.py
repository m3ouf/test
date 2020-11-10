from .models import MSAN, Router, TEDataMsan, TEDataMsan, RouterPort, Zone, Pop, PopDevice, AllocatedSubnet, \
    AssignedSubnet
from .serializers import MSANSerializer, RouterSerializer, RouterPortSerializer, RouterNetworkSerializer, \
    TEDataMSANSerializer, ZoneSerializer, PopSerializer, DeviceSerializer, AllocatedSubnetSerializer, \
    AssignedSubnetSerializer
from rest_framework import generics, status
from shared.renderers import CustomJSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from netaddr import IPNetwork
from .forms import SubnetForm
from django.http import Http404
from rest_framework.exceptions import APIException
from collections import OrderedDict
from django.db.models import Q
from helpers import get_msan_plans_reports
from django.http import HttpResponse
from openpyxl.writer.excel import save_virtual_workbook
from authorization import TokenAuthentication, IsPermitted, CanListCreateMSANs, CanUpdateCreateDestroyMSAN, \
    CanCreateTeDataMSAN, CanGetDeleteTeDataMSAN, CanGetUpdateCreateRouterPort, CanGetUpdateDeleteRouter, \
    CanAssignStaticIps, CanManageStaticIps
from django.db import connections
import socket
import struct
import operator
import bisect

SHELF1 = "Shelf1"
SHELF2 = "Shelf2"
BB_RANGE = "401-480"


class NotFound(APIException):
    status_code = status.HTTP_200_OK
    default_detail = '404'

    def __init__(self, detail=None):
        self.detail = detail or self.default_detail


def _filter_query_set(model, request, fields_lookup, allowed_fields, other_filters=None):
    other_filters = other_filters or {}
    lookup_index = request.query_params.get('order[0][column]')
    lookup_field = fields_lookup.get(int(lookup_index)) if lookup_index else None
    if not request.query_params or request.query_params.get('length', "") == "-1" or not lookup_field:
        return model.objects.all(), model.objects.count()

    length = int(request.query_params['length'])
    start = int(request.query_params['start'])
    ordering = "%s%s" % ("" if request.query_params['order[0][dir]'] == "asc" else "-", lookup_field)
    search_value = request.query_params['search[value]']
    query = model.objects.all()

    if search_value:
        search_filters = [Q(**{"%s__icontains" % f: search_value}) for f in allowed_fields]
        query = query.filter(reduce(operator.or_, search_filters))
    if other_filters:
        query = query.filter(**other_filters)

    count = query.count()
    return query.order_by(ordering)[start: start + length], count


class MSANList(generics.ListCreateAPIView):
    queryset = MSAN.objects.all()
    serializer_class = MSANSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    permission_classes = [CanListCreateMSANs]

    def get_queryset(self):
        fields_lookup = dict(zip(range(len(self.serializer_class.Meta.fields)), self.serializer_class.Meta.fields))
        allowed_fields = ['code', 'name', 'h248_subnet', 'manage_subnet']
        if self.request.query_params.get('columns[2][search][value]') == 'pending':
            other_filters = {'tedatamsan__isnull': True}
        elif self.request.query_params.get('columns[2][search][value]') == 'complete':
            other_filters = {'tedatamsan__isnull': False}
        else:
            other_filters = {}

        filtered_result, count = _filter_query_set(MSAN, self.request, fields_lookup, allowed_fields, other_filters)
        self.count = count  # used by render to determine if the query was filtered
        return filtered_result


class MSANDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = MSAN.objects.all()
    serializer_class = MSANSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    permission_classes = [CanUpdateCreateDestroyMSAN]


class RoutersList(generics.ListCreateAPIView):
    queryset = Router.objects.all()
    serializer_class = RouterSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsPermitted]
    required_permissions = set(["nst.nst_manage_tedata_routers"])  # to be checked by custom permissions verifier

    def get_queryset(self):
        fields_lookup = dict(zip(range(len(self.serializer_class.Meta.fields)), self.serializer_class.Meta.fields))
        allowed_fields = ['name']
        filtered_result, count = _filter_query_set(Router, self.request, fields_lookup, allowed_fields)
        self.count = count
        return filtered_result

    def create(self, request, *args, **kwargs):

        router_serializer = RouterSerializer(data=request.query_params)
        if router_serializer.is_valid():
            router_serializer.save()
            ports_list = request.data.getlist('port_inputs[]')
            ports = []
            for i in range(int(ports_list[1]) + 1):
                for j in range(int(ports_list[2]) + 1):
                    for k in range(10):
                        ports.append({'name': "%s-%s/%s/%s" % (ports_list[0], i, j, k), 'used': False,
                                      'router': router_serializer.instance.id})

            ports_serializer = RouterPortSerializer(data=ports, many=True)
            if not ports_serializer.is_valid():
                router_serializer.instance.delete()
                return Response(ports_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            octets = request.data.get("network_inputs").split(".")
            networks = []
            for oct3 in range(int(octets[2].strip("][").split("-")[0]),
                              int(octets[2].strip("][").split("-")[1]) + 1):
                networks.append({'network_ip': "%s.%s.%s.%s" % (octets[0], octets[1], oct3, octets[3]) + "/24",
                                 'router': router_serializer.instance.id})



            networks_serializer = RouterNetworkSerializer(data=networks, many=True)
            if not networks_serializer.is_valid():
                router_serializer.instance.delete()
                return Response(networks_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            ports_serializer.save()
            networks_serializer.save()
            return Response(router_serializer.data, status=status.HTTP_201_CREATED)

        return Response(router_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RouterDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Router.objects.all()
    serializer_class = RouterSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    permission_classes = [CanGetUpdateDeleteRouter]


def _subnets_overlap(subnets):
    # ranges will be a sorted list of alternating start and end addresses
    ranges = []
    for subnet in subnets:
        # find indices to insert start and end addresses
        first = bisect.bisect_left(ranges, subnet.first)
        last = bisect.bisect_right(ranges, subnet.last)
        # check the overlap conditions and return if one is met
        if first != last or first % 2 == 1:
            return True
        ranges[first:first] = [subnet.first, subnet.last]
    return False


def _calculate_subnets(supernet, mask, model, model_field):
    network = IPNetwork(supernet)
    all_subnets = set([unicode(subnet) for subnet in network.subnet(mask)])
    used_subnets = set(model.objects.all().values_list(model_field, flat=True))

    allowed_subnets = sorted(list(all_subnets - used_subnets),
                             key=lambda subnet: struct.unpack("!I", socket.inet_aton(subnet.split("/")[0]))[0])
    return used_subnets, allowed_subnets


class SubnetView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsPermitted]
    required_permissions = set(["nst.nst_manage_tedata_routers"])

    def get(self, request, pk, format=None):
        form = SubnetForm(request.query_params)
        if not form.is_valid():
            error_msg = ""
            for k, v in form.errors.items():
                error_msg += k + ": " + ", ".join(v) + "\n"
            result = {
                'error': True,
                'error_message': error_msg
            }
            return Response(result)

        network = IPNetwork(form.cleaned_data['network'])
        all_subnets = set([unicode(subnet) for subnet in network.subnet(form.cleaned_data['subnet'])])
        used_subnets = set(TEDataMsan.objects.all().values_list("manage_gw_subnet", flat=True))

        allowed_subnets = sorted(list(all_subnets - used_subnets),
                                 key=lambda subnet: struct.unpack("!I", socket.inet_aton(subnet.split("/")[0]))[0])

        return Response({'error': False, 'allowed_subnets': allowed_subnets, 'used_subnets': used_subnets})


class TEDataMSANList(generics.CreateAPIView):
    queryset = TEDataMsan.objects.all()
    serializer_class = TEDataMSANSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    permission_classes = [CanCreateTeDataMSAN]

    def get_queryset(self):
        fields_lookup = dict(zip(range(len(self.serializer_class.Meta.fields)), self.serializer_class.Meta.fields))
        allowed_fields = ['code', 'name']
        filtered_result, count = _filter_query_set(Router, self.request, fields_lookup, allowed_fields)
        self.count = count
        return filtered_result


class TEDataMSANDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = TEDataMsan.objects.all()
    serializer_class = TEDataMSANSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    permission_classes = [CanGetDeleteTeDataMSAN]
    lookup_field = "msan"

    def get(self, request, *args, **kwargs):
        try:
            return super(TEDataMSANDetail, self).retrieve(request, *args, **kwargs)
        except Http404:
            raise NotFound()


class RouterPortView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [CanGetUpdateCreateRouterPort]

    def get(self, request, pk, format=None):
        try:
            port = RouterPort.objects.get(pk=pk)
            subnet = IPNetwork(request.query_params.get('subnet'))
            supernet = subnet.supernet(24)[0]
            return Response({'error': False, 'port_name': port.name, 'router_name': port.router.name,
                             'management_subnet': str(supernet)})
        except Exception as e:
            return Response({'error': True, "message": str(e)})

    def put(self, request, pk, format=None):
        try:
            router_port = RouterPort.objects.get(pk=pk)
            if (not router_port.used) or (router_port.used and (not hasattr(router_port, 'backup_port') and
                                                                not hasattr(router_port, 'tedatamsan'))):
                router_port.used = not router_port.used
                router_port.save()
                return Response({'error': False, 'message': 'Port changed successfully.'})
            else:
                return Response({'error': True,
                                 "message": "You can't change a router port that is already attached to MSAN"})
        except Exception as e:
            return Response({'error': True, "message": str(e)})

    def post(self, request, router_id, format=None):
        try:
            router = Router.objects.get(pk = router_id)
            if router:
                router_port_name = request.DATA.get('router_port')
                router_port = RouterPortSerializer(data={'router': router.id, 'name': router_port_name})
                if router_port.is_valid():
                    new_router_port = router_port.save()
                    return Response({'error': False, 'message': 'Port added successfully.',
                                     'port_name': new_router_port.name, 'port_id': new_router_port.id})
                else:
                    raise Exception("Router port data is invalid.")
            else:
                return Response({'error': True, "message": "No router found to attach this port."})
        except Exception as e:
            return Response({'error': True, "message": str(e)})


class Report(APIView):

    def get(self, request, format=None):
        wb = get_msan_plans_reports()

        response = HttpResponse(save_virtual_workbook(wb),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response['Content-Disposition'] = "attachment; filename=msan_plans.xlsx"
        return response


class CoreAccessZoneList(generics.ListCreateAPIView):
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    #permission_classes = [CanManageStaticIps]

    def get_queryset(self):
        fields_lookup = dict(zip(range(len(self.serializer_class.Meta.fields)), self.serializer_class.Meta.fields))
        allowed_fields = ['name']
        filtered_result, count = _filter_query_set(Zone, self.request, fields_lookup, allowed_fields)
        self.count = count
        return filtered_result


class CoreAccessZoneDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    #permission_classes = [CanManageStaticIps]



class CoreAccessPopsDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Pop.objects.all()
    serializer_class = PopSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    #permission_classes = [CanManageStaticIps]



class CoreAccessPopsList(generics.ListCreateAPIView):
    queryset = Pop.objects.all()
    serializer_class = PopSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    #permission_classes = [CanManageStaticIps]


    def get_queryset(self):
        fields_lookup = dict(zip(range(len(self.serializer_class.Meta.fields)), self.serializer_class.Meta.fields))
        allowed_fields = ['name', 'zone__name']
        filtered_result, count = _filter_query_set(Pop, self.request, fields_lookup, allowed_fields)
        self.count = count
        return filtered_result


class CoreAccessDeviceList(generics.ListCreateAPIView):
    queryset = PopDevice.objects.all()
    serializer_class = DeviceSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    #permission_classes = [CanManageStaticIps]


    def get_queryset(self):
        fields_lookup = dict(zip(range(len(self.serializer_class.Meta.fields)), self.serializer_class.Meta.fields))
        allowed_fields = ['name', 'pop__name', 'pop__zone__name']
        filtered_result, count = _filter_query_set(PopDevice, self.request, fields_lookup, allowed_fields)
        self.count = count
        return filtered_result


class CoreAccessDeviceDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PopDevice.objects.all()
    serializer_class = DeviceSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    #permission_classes = [CanManageStaticIps]


class CoreAccessDeviceAvailableIps(APIView):
    @staticmethod
    def get_object(pk):
        try:
            return PopDevice.objects.get(pk=pk)
        except PopDevice.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        device = self.get_object(pk)
        if not 'netmask' in request.query_params or not request.query_params.get('netmask'):
            response = {
                'error': True,
                'message': "netmask is required but not provided"
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        netmask = int(request.query_params['netmask'])

        if len(device.networks.all()) == 0:
            response = {'error': True, 'message': 'The device has no allocated networks!!'}
            return Response(response, status=status.HTTP_200_OK)
        for allocated_network in device.networks.all():
            anetwork = IPNetwork(str(allocated_network.network_ip))
            candidates = anetwork.subnet(netmask)
            candidates_select = " as ip UNION ".join(["SELECT inet_aton('{0}')".format(str(ip.ip)) for ip in candidates]) + " as ip"
            query = "SELECT inet_ntoa(ip) AS ip FROM ({0}) as ip_table_temp " \
                    "WHERE ip_table_temp.ip NOT IN (select ip_table_temp.ip " \
                    "FROM (select SUBSTRING_INDEX(network_ip, '/', 1) AS network, " \
                    "inet_ntoa(POW(2, 32) - POW(2, 32 - {1})) AS " \
                    "netmask, inet_ntoa(POW(2, 32) - " \
                    "POW(2, 32 - SUBSTRING_INDEX(network_ip, '/', -1))) AS othernetmask " \
                    "from CoreAccessAssignedSubnet) AS network_table " \
                    "WHERE ip_table_temp.ip = (inet_aton(netmask)) & inet_aton(network) " \
                    " or (ip_table_temp.ip & inet_aton(othernetmask)) = inet_aton(network) ) " \
                    "LIMIT 1;".format(candidates_select, str(netmask))

            connection = connections['ip_plans']
            cursor = connection.cursor()
            cursor.execute(query)
            ips = cursor.fetchone()
            if ips:
                available_ip = ips[0]
                response = {'error': False, 'available_ip': "{0}/{1}".format(available_ip, netmask),
                            'allocated_network': str(allocated_network.id)}
                return Response(response, status=status.HTTP_200_OK)
        response = {'error': True, 'message': 'Allocated networks are exhausted on this device !'}
        return Response(response, status=status.HTTP_200_OK)



class AllocatedSubnetList(generics.ListCreateAPIView):
    queryset = AllocatedSubnet.objects.all()
    serializer_class = AllocatedSubnetSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    #permission_classes = [CanManageStaticIps]


    def get_queryset(self):
        fields_lookup = dict(zip(range(len(self.serializer_class.Meta.fields)), self.serializer_class.Meta.fields))
        allowed_fields = ['network_ip', 'device__name', 'device__pop__name', 'device__pop__zone__name']
        filtered_result, count = _filter_query_set(AllocatedSubnet, self.request, fields_lookup, allowed_fields)
        self.count = count
        return filtered_result


class AllocatedSubnetDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = AllocatedSubnet.objects.all()
    serializer_class = AllocatedSubnetSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    #permission_classes = [CanManageStaticIps]


    @staticmethod
    def get_allocated_subnet(pk):
        try:
            return AllocatedSubnet.objects.get(pk=pk)
        except AllocatedSubnet.DoesNotExist:
            raise Http404

    def update(self, request, pk, format=None):
        if not request.data.get('network_ip'):
            response = {
                'error': True,
                'message': "Network Ip field is required"
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        allocated_subnet = self.get_allocated_subnet(pk)
        serializer = AllocatedSubnetSerializer(allocated_subnet, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        error_msg = ""
        for k, v in serializer.errors.items():
            error_msg += k + ": " + ", ".join(v) + "\n"
        result = {
            'error': True,
            'message': error_msg
        }
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


def _validate_subnets_overlapping(request):
    existing_subnets = list(AssignedSubnet.objects.all().values_list('network_ip', flat=True))
    subnets = [IPNetwork(ip_address) for ip_address in existing_subnets if ip_address != request.data['network_ip']] + \
              [IPNetwork(request.data['network_ip'])]
    return _subnets_overlap(subnets)


class AssignedSubnetView(APIView):
    authentication_classes = [TokenAuthentication]
    #permission_classes = [CanManageStaticIps]


    def get(self, request, pk=None, format=None):
        form = SubnetForm(request.query_params)
        if not form.is_valid():
            error_msg = ""
            for k, v in form.errors.items():
                error_msg += k + ": " + ", ".join(v) + "\n"
            result = {
                'error': True,
                'message': error_msg
            }
            return Response(result)

        supernet = AllocatedSubnet.objects.get(id=form.cleaned_data['network'])
        used_subnets, allowed_subnets = _calculate_subnets(str(supernet.network_ip), form.cleaned_data['subnet'],
                                                           AssignedSubnet, "network_ip")

        return Response({'error': False, 'allowed_subnets': allowed_subnets, 'used_subnets': used_subnets})

    def post(self, request, format=None):
        serializer = AssignedSubnetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'error': False, 'message': "Network assigned successfully"},
                            status=status.HTTP_201_CREATED)
        error_msg = ""
        for k, v in serializer.errors.items():
            error_msg += k + ": " + ", ".join(v) + "\n"
        result = {
            'error': True,
            'message': error_msg
        }
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


class AssignedSubnetList(generics.ListAPIView):
    queryset = AssignedSubnet.objects.all()
    serializer_class = AssignedSubnetSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    #permission_classes = [CanManageStaticIps]


    def get_queryset(self):
        fields_lookup = dict(zip(range(len(self.serializer_class.Meta.fields)), self.serializer_class.Meta.fields))
        allowed_fields = ['network_ip', 'allocated_subnet__device__name', 'allocated_subnet__device__pop__name',
                          'allocated_subnet__device__pop__zone__name', 'name', 'phone', 'account_number']
        filtered_result, count = _filter_query_set(AssignedSubnet, self.request, fields_lookup, allowed_fields)
        self.count = count
        return filtered_result


class AssignedSubnetDetail(APIView):
    @staticmethod
    def get_object(pk):
        try:
            return AssignedSubnet.objects.get(pk=pk)
        except AssignedSubnet.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        assigned_subnet = self.get_object(pk)
        serializer = AssignedSubnetSerializer(assigned_subnet)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        assigned_subnet = self.get_object(pk)
        serializer = AssignedSubnetSerializer(assigned_subnet, data=request.data)
        if serializer.is_valid():
            if _validate_subnets_overlapping(request):
                return Response({'error': True, 'message': "Subnet conflicts with existing subnets"},
                                status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            return Response(serializer.data)

        error_msg = ""
        for k, v in serializer.errors.items():
            error_msg += k + ": " + ", ".join(v) + "\n"
        result = {
            'error': True,
            'message': error_msg
        }
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        assigned_subnet = self.get_object(pk)
        assigned_subnet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
