from django.conf.urls import patterns, url
import views

urlpatterns = patterns('',
    url(r'^create_or_change_service/?$', 'ldap_backend.views.create_or_change_ldap_service',name='create_or_change_ldap_service'),
    url(r'^remove_service/?$', 'ldap_backend.views.remove_ldap_service', name='remove_ldap_service'),
    url(r'^get_ldap_services/?$', 'ldap_backend.views.get_ldap_services', name='get_ldap_services'),
    url(r'^check_user_exists/?$', 'ldap_backend.views.check_user_exists', name='check_user_exists'),
    url(r'^wifi/subscribers/?$', views.WifiSubscriber.as_view(), name='create_or_change_wifi_service'),
    url(r'^wifi/subscribers/(?P<adslUserName>\S+)/?$', views.WifiSubscriberDetails.as_view()),
##current for NST
    url(r'^get_full_profile/?$', 'ldap_backend.views.get_full_profile', name='get_full_profile'),
##for cudb service
url(r'^create_or_change_cudb_service/?$', 'ldap_backend.views.create_or_change_cudb_service',name='create_or_change_cudb_service'),
url(r'^suspendSubscriberCUDB/?$', 'ldap_backend.views.suspendSubscriberCUDB', name='suspendSubscriberCUDB'),
url(r'^activateSubscriberCUDB/?$', 'ldap_backend.views.activateSubscriberCUDB', name='activateSubscriberCUDB'),
url(r'^getSubscriberStatusCUDB/?$', 'ldap_backend.views.getSubscriberStatusCUDB', name='getSubscriberStatusCUDB'),
url(r'^listAAAServicesCUDB/?$', 'ldap_backend.views.listAAAServicesCUDB', name='listAAAServicesCUDB'),
##new for optionPack
    url(r'^delete_option_pack/?$', 'ldap_backend.views.delete_option_pack', name='delete_option_pack'),
    url(r'^view_option_pack_cudb/?$', 'ldap_backend.views.view_option_pack_cudb', name='view_option_pack_cudb'),
    url(r'^create_or_change_optionpack/?$', 'ldap_backend.views.create_or_change_optionpack',name='create_or_change_optionpack'),
###new for cudb for lab only
    url(r'^create_or_change_NPID/?$', 'ldap_backend.views.create_or_change_NPID', name='create_or_change_NPID'),
    url(r'^remove_nas_port_id/?$', 'ldap_backend.views.remove_nas_port_id', name='remove_nas_port_id'),
    url(r'^add_or_edit_password/?$', 'ldap_backend.views.add_or_edit_password', name='add_or_edit_password'),
    url(r'^get_cudb_profile/?$', 'ldap_backend.views.get_cudb_profile', name='get_cudb_profile'),
    url(r'^get_full_cudb_profile/?$', 'ldap_backend.views.get_full_cudb_profile', name='get_full_cudb_profile'),
)
