from django.conf.urls import patterns, url
urlpatterns = patterns('',
    url(r'^create_or_change_service/?$', 'pcrf_backend.views.create_or_change_service',
        name='create_or_change_pcrf_service'),

    url(r'^get_services/?$', 'pcrf_backend.views.get_services', name='get_pcrf_services'),

    url(r'^add_topUp/?$', 'pcrf_backend.views.add_topup',  name='add_topup'),

    url(r'^get_profile/?$', 'pcrf_backend.views.get_profile', name='get_profile'),

    url(r'^get_session/?$', 'pcrf_backend.views.get_session', name='get_session'),

    url(r'^debit_user/?$', 'pcrf_backend.views.debit_user',  name='debit_pcrf_user'),

    url(r'^remove_user/?$', 'pcrf_backend.views.remove_user', name='remove_user'),
    url(r'^reset_session/?$', 'pcrf_backend.views.reset_session', name='reset_session'),
    url(r'^remove_redirection/?$', 'pcrf_backend.views.remove_redirection', name='remove_redirection'),
)
