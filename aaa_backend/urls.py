from django.conf.urls import patterns, url
import views

urlpatterns = patterns('',
    url(r'^get_user_by_ip/?$', 'aaa_backend.views.get_user_by_ip', name='get_user_by_ip'),
    url(r'^get_user_by_name/?$', 'aaa_backend.views.get_user_by_name', name='get_user_by_name'),
    url(r'^send_start_coa/?$', 'aaa_backend.views.send_start_coa', name='send_start_coa'),
    url(r'^send_stop_coa/?$', 'aaa_backend.views.send_stop_coa', name='send_stop_coa'),
    url(r'^get_full_sessions/?$', 'aaa_backend.views.get_full_session', name='get_full_session'),
    url(r'^portal/migration/?$', views.PortalServiceMigrationView.as_view()),

)