from rest_framework import authentication, permissions, exceptions
from auth.models import Token
from datetime import datetime


class TokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', None)
        if auth_header is not None:
            tokens = auth_header.split(' ')
            if len(tokens) == 2 and tokens[0] == 'Token':
                token = tokens[1]
                try:
                    stored_token = Token.objects.get(token=token)
                    if datetime.now() > stored_token.expires:
                        stored_token.delete()
                        return None

                    return stored_token.user, None
                except Token.DoesNotExist:
                    raise exceptions.AuthenticationFailed('Unkown session')
        raise exceptions.AuthenticationFailed("Header doesn't contain authentication token")


class IsPermitted(permissions.BasePermission):
    def has_permission(self, request, view):
        return view.required_permissions < request.user.get_all_permissions()


class CanListCreateMSANs(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == 'POST':
            return 'nst.nst_provision_msan_ip_plans' in request.user.get_all_permissions()
        elif request.method == 'GET':
            return 'nst.nst_view_msan_ip_plans' in request.user.get_all_permissions()
        else:
            return False


class CanUpdateCreateDestroyMSAN(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == 'GET':
            return 'nst.nst_query_msan_plan' in request.user.get_all_permissions()
        elif request.method == 'PUT':
            return 'nst.nst_update_msan_ip_plans' in request.user.get_all_permissions()
        elif request.method == 'DELETE':
            return 'nst.nst_remove_msan_ip_plans' in request.user.get_all_permissions()
        else:
            return False


class CanCreateTeDataMSAN(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == 'POST':
            return 'nst.nst_provision_tedata_msan' in request.user.get_all_permissions()
        else:
            return False


class CanGetDeleteTeDataMSAN(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == 'GET':
            return 'nst.nst_get_tedata_msan_plan' in request.user.get_all_permissions()
        elif request.method == 'DELETE':
            return 'nst.nst_remove_tedata_management_div' in request.user.get_all_permissions()
        else:
            return False


class CanGetUpdateCreateRouterPort(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == 'GET':
            return 'nst.nst_get_tedata_router_port' in request.user.get_all_permissions()
        elif request.method == 'DELETE' or request.method == 'POST' or request.method == 'PUT':
            return 'nst.nst_manage_tedata_routers' in request.user.get_all_permissions()
        else:
            return False


class CanGetUpdateDeleteRouter(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == 'GET':
            return 'nst.nst_get_tedata_router' in request.user.get_all_permissions()
        else:
            return 'nst.nst_manage_tedata_routers' in request.user.get_all_permissions()



class CanManageStaticIps(permissions.BasePermission):
    def has_permission(self, request, view):
        return "nst.nst_manage_static_ips" in request.user.get_all_permissions()


class CanAssignStaticIps(permissions.BasePermission):
    def has_permission(self, request, view):
        return "nst.nst_assign_static_ips" in request.user.get_all_permissions()


