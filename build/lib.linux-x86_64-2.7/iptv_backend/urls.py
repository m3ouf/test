from django.conf.urls import patterns, url
urlpatterns = patterns('',
    url(r'^create_iptv_customer/?$', 'iptv_backend.views.create_customer',
        name='create_iptv_customer'),
    url(r'^block_iptv_subscription/?$', 'iptv_backend.views.block_iptv_subscription',
        name='block_iptv_subscription'),
    url(r'^unblock_iptv_subscription/?$', 'iptv_backend.views.unblock_iptv_subscription',
        name='unblock_iptv_subscription'),
    url(r'^add_or_change_iptv_package/?$', 'iptv_backend.views.add_or_change_iptv_package',
        name='add_or_change_iptv_package'),
    url(r'^add_or_change_iptv_stb/?$', 'iptv_backend.views.add_or_change_iptv_stb',  name='add_or_change_iptv_stb'),
    url(r'^query_user_info/?$', 'iptv_backend.views.query_user_info', name='query_user_info'),
    url(r'^remove_iptv_stb/?$', 'iptv_backend.views.remove_iptv_stb', name='remove_iptv_stb'),

)