from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
     url(r'^admin/', include(admin.site.urls)),
     url(r'^aaa_ws/', include('aaa_backend.urls')),
     url(r'^pcrf_ws/', include('pcrf_backend.urls')),
     url(r'^ldap_ws/', include('ldap_backend.urls')),
     url(r'^dpi_ws/', include('dpi_backend.urls')),
     url(r'^iptv_ws/', include('iptv_backend.urls')),
     url(r'^physical_ws/', include('physical_adsl_backend.urls')),
     url(r'^nst/', include('nst.urls')),
     url(r'^auth/', include('auth.urls')),
     url(r'^wifi/', include('wifi.urls')),
)
