from django.conf.urls import patterns, url
import views

urlpatterns = patterns('',
    url(r'^create_or_change_service/?$', 'ldap_backend.views.create_or_change_ldap_service',
        name='create_or_change_ldap_service'),
    url(r'^remove_service/?$', 'ldap_backend.views.remove_ldap_service', name='remove_ldap_service'),
    url(r'^get_ldap_services/?$', 'ldap_backend.views.get_ldap_services', name='get_ldap_services'),
    url(r'^check_user_exists/?$', 'ldap_backend.views.check_user_exists', name='check_user_exists'),
    url(r'^get_full_profile/?$', 'ldap_backend.views.get_full_profile', name='get_full_profile'),
    url(r'^delete_option_pack/?$', 'ldap_backend.views.delete_option_pack', name='delete_option_pack'),
    url(r'^wifi/subscribers/?$', views.WifiSubscriber.as_view(), name='create_or_change_wifi_service'),
    url(r'^wifi/subscribers/(?P<adslUserName>\S+)/?$', views.WifiSubscriberDetails.as_view()),



)