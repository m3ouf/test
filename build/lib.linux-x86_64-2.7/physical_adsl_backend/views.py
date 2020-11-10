from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status, generics
from .serializers import NetworkDeviceSerializer, NetworkDeviceUpdateSerializer, GPONDeviceSerializer, \
    GponOperationsGetSerializer
from shared.decorators import validate_inputs
from clients import get_client
from .models import GPONDevice
from django.http import Http404
from django.db.models import Q
from database_backend.authorization import TokenAuthentication, IsPermitted
from shared.renderers import CustomJSONRenderer
from shared.common import log_action
from Exscript.protocols.Exception import TimeoutException
import operator
import inspect


class NetworkDeviceOperationsView(APIView):

    def __str__(self):
        return "NetworkDeviceOperations"

    @validate_inputs(NetworkDeviceSerializer)
    def post(self, request, format=None, **kwargs):
        serializer = kwargs['serializer']
        card_number = serializer.validated_data['cardNumber']
        port_number = serializer.validated_data['portNumber']
        host_address = serializer.validated_data['deviceIp']
        community_id = serializer.validated_data['communityId']
        shelf_number = serializer.validated_data.get('shelfNumber')
        transaction_id = serializer.validated_data.get('transactionId')
        client = get_client(community_id)
        result, msg = client.provision_subscriber(host_address, card_number, port_number, shelf_number)
        if not result:
            response = {'success': False, 'msg': "Error while provisioning ADSL subscriber, {0}".format(msg)}
            log_action("{0}.{1}".format(str(self), 'post'), request, response, transaction_id)
            return Response(response, status=status.HTTP_200_OK)

        response = {'success': True, 'msg': None}
        log_action("{0}.{1}".format(str(self), 'post'), request, response, transaction_id)
        return Response(response, status=status.HTTP_201_CREATED)

    @validate_inputs(NetworkDeviceUpdateSerializer)
    def put(self, request, format=None, **kwargs):
        serializer = kwargs['serializer']
        card_number = serializer.validated_data['cardNumber']
        port_number = serializer.validated_data['portNumber']
        host_address = serializer.validated_data['deviceIp']
        shelf_number = serializer.validated_data.get('shelfNumber')
        enable = serializer.validated_data['enable']
        community_id = serializer.validated_data['communityId']
        transaction_id = serializer.validated_data.get('transactionId')
        client = get_client(community_id)
        result, msg = client.update_subscriber(host_address, port_number, card_number, shelf_number, enable)
        if not result:
            response = {'success': False, 'msg': "Error while updating ADSL subscriber, {0}".format(msg)}
            log_action("{0}.{1}".format(str(self), 'put'), request, response, transaction_id)
            return Response(response, status=status.HTTP_200_OK)

        response = {'success': True, 'msg': None}
        log_action("{0}.{1}".format(str(self), 'put'), request, response, transaction_id)
        return Response(response, status=status.HTTP_200_OK)


    @validate_inputs(NetworkDeviceSerializer)
    def get(self, request, format=None, **kwargs):
        serializer = kwargs['serializer']
        card_number = serializer.validated_data['cardNumber']
        port_number = serializer.validated_data['portNumber']
        host_address = serializer.validated_data['deviceIp']
        shelf_number = serializer.validated_data.get('shelfNumber')
        community_id = serializer.validated_data['communityId']
        transaction_id = serializer.validated_data.get('transactionId')

        client = get_client(community_id)
        result, msg, physical_status = client.get_subscriber_status(host_address, port_number, card_number, shelf_number)
        if not result:
            response = {'success': False, 'msg': "Error while getting ADSL subscriber, {0}".format(msg)}
            log_action("{0}.{1}".format(str(self), 'get'), request, response, transaction_id)
            return Response(response, status=status.HTTP_200_OK)

        response = {'success': True, 'enabled': physical_status, 'msg': None}
        log_action("{0}.{1}".format(str(self), 'get'), request, response, transaction_id)
        return Response(response, status=status.HTTP_200_OK)

# TODO: Move this to shared.helpers and import it here and in database_backend.views
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


class GPONDeviceList(generics.ListCreateAPIView):
    """
    List all GPON Devices, or create a new device.
    """
    queryset = GPONDevice.objects.all()
    serializer_class = GPONDeviceSerializer
    renderer_classes = [CustomJSONRenderer]
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsPermitted]
    required_permissions = set(["nst.nst_manage_tedata_routers"])  # to be checked by custom permissions verifier

    def get_queryset(self):
        fields_lookup = dict(zip(range(len(self.serializer_class.Meta.fields)), self.serializer_class.Meta.fields))
        allowed_fields = ['name']
        filtered_result, count = _filter_query_set(GPONDevice, self.request, fields_lookup, allowed_fields)
        self.count = count
        return filtered_result

    def create(self, request, *args, **kwargs):
        pass
        # router_serializer = GPONDeviceSerializer(data=request.query_params)
        # if router_serializer.is_valid():
        #     router_serializer.save()
        #     ports_list = request.data.getlist('port_inputs[]')
        #     ports = []
        #     for i in range(int(ports_list[1]) + 1):
        #         for j in range(int(ports_list[2]) + 1):
        #             for k in range(10):
        #                 ports.append({'name': "%s-%s/%s/%s" % (ports_list[0], i, j, k), 'used': False,
        #                               'router': router_serializer.instance.id})
        #
        #     ports_serializer = RouterPortSerializer(data=ports, many=True)
        #     if not ports_serializer.is_valid():
        #         router_serializer.instance.delete()
        #         return Response(ports_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #
        #     octets = request.data.get("network_inputs").split(".")
        #     networks = []
        #     for oct3 in range(int(octets[2].strip("][").split("-")[0]),
        #                          int(octets[2].strip("][").split("-")[1]) + 1):
        #         networks.append({'network_ip': "%s.%s.%s.%s" % (octets[0],octets[1], oct3, octets[3]) + "/24",
        #                          'router': router_serializer.instance.id})
        #
        #
        #
        #     networks_serializer = RouterNetworkSerializer(data=networks, many=True)
        #     if not networks_serializer.is_valid():
        #         router_serializer.instance.delete()
        #         return Response(networks_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #     ports_serializer.save()
        #     networks_serializer.save()
        #     return Response(router_serializer.data, status=status.HTTP_201_CREATED)
        #
        # return Response(router_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GPONDevicesDetail(APIView):
    """
    Retrieve, update or delete a GPON Device instance.
    """
    def get_object(self, pk):
        try:
            return GPONDevice.objects.get(pk=pk)
        except GPONDevice.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        snippet = self.get_object(pk)
        serializer = GPONDeviceSerializer(snippet)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        snippet = self.get_object(pk)
        serializer = GPONDeviceSerializer(snippet, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        snippet = self.get_object(pk)
        snippet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GponOperations(APIView):
    @validate_inputs(GponOperationsGetSerializer)
    def get(self, request, format=None, **kwargs):
        serializer = kwargs['serializer']
        frame = serializer.validated_data['frame']
        slot = serializer.validated_data['slot']
        port = serializer.validated_data['port']
        ont_id = serializer.validated_data['ontId']
        host_address = serializer.validated_data['hostAddress']
        device_type = serializer.validated_data['deviceType']
        transaction_id = serializer.validated_data['transactionId']
        port_operation = serializer.validated_data['portOperation']

        client = get_client(device_type)
        try:
            if port_operation == 'status':
                result = client.get_port_status(frame, slot, port, ont_id, host_address)
            elif port_operation == 'speed':
                result = client.get_port_speed(frame, slot, port, ont_id, host_address)

        except TimeoutException:
            return Response({'success': False, 'msg': "connection timeout"}, status=status.HTTP_200_OK)
        #log_action("{0}.{1}".format(str(self), 'get'), request, response, transaction_id)
        return Response(result, status=status.HTTP_200_OK)

    @validate_inputs(GponOperationsGetSerializer)
    def post(self, request, format=None, **kwargs):
        serializer = kwargs['serializer']
        frame = serializer.validated_data['frame']
        slot = serializer.validated_data['slot']
        port = serializer.validated_data['port']
        ont_id = serializer.validated_data['ontId']
        host_address = serializer.validated_data['hostAddress']
        device_type = serializer.validated_data['deviceType']
        transaction_id = serializer.validated_data['transactionId']
        port_operation = serializer.validated_data['portOperation']

        client = get_client(device_type)
        try:
            if port_operation == 'reset':
                result = client.reset_port(frame, slot, port, ont_id, host_address)

        except TimeoutException:
            return Response({'success': False, 'msg': "connection timeout"}, status=status.HTTP_200_OK)

        #log_action("{0}.{1}".format(str(self), 'get'), request, response, transaction_id)
        return Response(result, status=status.HTTP_200_OK)