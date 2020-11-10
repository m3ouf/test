from django.conf.urls import url, patterns
from database_backend import views
from physical_adsl_backend.views import GPONDeviceList, GPONDevicesDetail


urlpatterns = patterns('',
    url(r'^basic_info/?$', 'nst.views.get_basic_info', name='get_basic_info'),
    url(r'^pcrf_info/?$', 'nst.views.get_pcrf_logs', name='get_pcrf_logs'),
    url(r'^get_topups_logs/(?P<pcrf_log_id>.+)/$', 'nst.views.get_topups_logs', name='get_topups_logs'),
    url(r'^get_provision_pcrf_info/(?P<basic_info_id>.+)/$', 'nst.views.get_provision_pcrf_info', name='get_provision_pcrf_info'),
    url(r'^topups_logs/(?P<pcrf_log_id>.+)/$', 'nst.views.topups_logs', name='topups_logs'),
    url(r'^provision_pcrf_info/(?P<basic_info_id>.+)/$', 'nst.views.provision_pcrf_info', name='provision_pcrf_info'),
    url(r'^dp/?$', 'nst.views.decrypt_password', name='decrypt_password'),
    url(r'^allowed_services', 'nst.views.get_allowed_services', name="get_allowed_services"),
    url(r'^subscriber_logs', 'nst.views.subscriber_database_logs', name="subscriber_logs"),
    url(r'^subscriber_database_logs', 'nst.views.subscriber_database_logs', name="subscriber_database_logs"),
    url(r'^remove_allowed_service', 'nst.views.remove_allowed_service', name="remove_allowed_service"),
    url(r'^add_allowed_service', 'nst.views.add_allowed_service', name="add_allowed_service"),

    # url(r'^allowed_user_actions', 'nst.views.allowed_user_actions', name="allowed_user_actions"),

    #url(r'^get_ldap_services/?$', 'nst.views.get_ldap_services', name='nst_get_ldap_services'),
    url(r'^get_full_ldap_profile/?$', 'nst.views.nst_get_full_ldap_profile'),
    url(r'^reset_subscriber_password/?$', 'nst.views.reset_subscriber_password'),


    url(r'^get_pcrf_profile/?$', 'nst.views.nst_get_pcrf_profile'),
    url(r'^get_pcrf_services/?$', 'nst.views.nst_get_pcrf_services'),
    url(r'^check_ldap_user_exists/?$', 'nst.views.nst_check_ldap_user_exists'),
    url(r'^get_aaa_user_by_name/?$', 'nst.views.nst_get_aaa_user_by_name'),
    url(r'^get_aaa_user_by_ip/?$', 'nst.views.nst_get_aaa_user_by_ip'),
    url(r'^get_aaa_full_sessions/?$', 'nst.views.nst_get_aaa_full_sessions'),
    url(r'^get_pcrf_session/?$', 'nst.views.nst_get_pcrf_session'),

    url(r'^remove_ldap_service/?$', 'nst.views.remove_ldap_service'),
    url(r'^remove_pcrf_user/?$', 'nst.views.remove_pcrf_user'),
    url(r'^create_or_change_ldap_service/?$', 'nst.views.create_or_change_ldap_service'),
    url(r'^create_or_change_pcrf_service/?$', 'nst.views.create_or_change_pcrf_service'),
    url(r'^credit_subscriber/?$', 'nst.views.credit_subscriber'),
    url(r'^debit_subscriber/?$', 'nst.views.debit_subscriber'),
    url(r'^daily_usage/(?P<subscriber_id>.+)/(?P<start_date>.+)/(?P<end_date>.+)/$', 'nst.views.nst_get_daily_usage',
        name='get_daily_usage'),

    url(r'^sbr_daily_usage/$', 'nst.views.nst_get_sbr_daily_usage',
        name='sbr_get_daily_usage'),
    url(r'^dpi_daily_usage/$', 'nst.views.nst_get_dpi_daily_usage', name='get_dpi_daily_usage'),

    url(r'^send_stop_coa/?$', 'nst.views.nst_send_stop_coa'),
    url(r'^send_start_coa/?$', 'nst.views.nst_send_start_coa'),

    url(r'^nst_per_service_analytics/?$', 'nst.views.nst_per_service_analytics', name='nst_per_service_analytics'),
    url(r'^nst_topups_analytics/?$', 'nst.views.topups_analytics', name='nst_topups_analytics'),

    url(r'^query_cyber_crime/?$', 'nst.views.query_cyber_crime_by_datetime'),
    url(r'^query_cyber_crime_by_date_range/?$', 'nst.views.query_cyber_crime_by_date_range'),
    url(r'^wifi_report/?$', 'nst.views.get_wifi_report'),
    url(r'^get_wifi_venues/?$', 'nst.views.get_wifi_venues'),
    url(r'^provision_wifi_venue/?$', 'nst.views.provision_wifi_venue'),
    url(r'^remove_wifi_venue/?$', 'nst.views.remove_wifi_venue'),

    url(r'^msans/?$', views.MSANList.as_view()),
    url(r'^msans/(?P<pk>[0-9]+)/?$', views.MSANDetail.as_view(), name='msan-detail'),

    url(r'^msans/tedata/?$', views.TEDataMSANList.as_view()),
    url(r'^msans/tedata/(?P<msan>[0-9]+)/?$', views.TEDataMSANDetail.as_view()),

    url(r'^routers/?$', views.RoutersList.as_view()),
    url(r'^routers/(?P<pk>[0-9]+)/?$', views.RouterDetail.as_view()),
    url(r'^routers/(?P<pk>[0-9]+)/subnets/?$', views.SubnetView.as_view()),
    url(r'^routers/(?P<router_id>[0-9]+)/ports/?$', views.RouterPortView.as_view()),

    url(r'ports/(?P<pk>[0-9]+)/?', views.RouterPortView.as_view()),
    url(r'msan-plans-report/?', views.Report.as_view()),
    url(r'^coreAccess/zones/?$', views.CoreAccessZoneList.as_view()),
    url(r'coreAccess/zones/(?P<pk>[0-9]+)/?$', views.CoreAccessZoneDetail.as_view()),
    url(r'coreAccess/pops/?$', views.CoreAccessPopsList.as_view()),
    url(r'coreAccess/pops/(?P<pk>[0-9]+)/?$', views.CoreAccessPopsDetail.as_view()),
    url(r'coreAccess/devices/?$', views.CoreAccessDeviceList.as_view()),
    url(r'coreAccess/devices/(?P<pk>[0-9]+)/?$', views.CoreAccessDeviceDetail.as_view()),
    url(r'coreAccess/devices/(?P<pk>[0-9]+)/availableIps/?$', views.CoreAccessDeviceAvailableIps.as_view()),
    url(r'coreAccess/allocatedSubnets/?$', views.AllocatedSubnetList.as_view()),
    url(r'coreAccess/allocatedSubnets/(?P<pk>[0-9]+)/?$', views.AllocatedSubnetDetail.as_view()),
	url(r'gpondevices/?', GPONDeviceList.as_view()),
    url(r'gpondevice/(?P<pk>[0-9]+)/$', GPONDevicesDetail.as_view()),

    url(r'query_optionpack_subscriber/', 'nst.views.query_optionpack_subscriber', name='query_optionpack_subscriber'),
    url(r'delete_optionpack_subscriber/', 'nst.views.delete_optionpack_subscriber', name='delete_optionpack_subscriber'),
    url(r'provision_optionpack_subscriber/', 'nst.views.provision_optionpack_subscriber', name='provision_optionpack_subscriber'),


    url(r'coreAccess/assignedSubnets/?$', views.AssignedSubnetList.as_view()),
    url(r'coreAccess/allocatedSubnets/subnets/?$', views.AssignedSubnetView.as_view()),
    url(r'coreAccess/assignedSubnets/(?P<pk>[0-9]+)/?$', views.AssignedSubnetDetail.as_view()),
   url(r'^wifi_logs/?$', 'nst.views.get_wifi_logs', name='get_wifi_logs'),

)
