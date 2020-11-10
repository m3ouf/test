from django.conf.urls import url, patterns
from .views import Subscribers, SubscribersLogin, TESubscribersLogin, SubscriberDevices, \
    SubscriberActivationCode, SubscriberForgetPassword, ADSLSubscribersLogin

urlpatterns = patterns('',
                       url(r'^subscribers/(?P<mobile_no>\d+)/login/?$', SubscribersLogin.as_view(), name='loginWIFISubscriber'),
                       url(r'^teSubscribers/(?P<subscriberId>\d+)/login/?$', TESubscribersLogin.as_view(), name='loginTEWIFISubscriber'),
                       url(r'^adslSubscribers/(?P<subscriberId>\d+)/login/?$', ADSLSubscribersLogin.as_view(), name='loginADSLSubscriber'),
                       url(r'^subscribers/?$', Subscribers.as_view(), name='registerWIFIUser'),
                       url(r'^subscribers/(?P<mobile_no>\d+)/devices/?$', SubscriberDevices.as_view(), name='manageSubscriberDevices'),
                       url(r'^subscribers/(?P<mobile_no>\d+)/activationCode/?$', SubscriberActivationCode.as_view(), name='sendActivationCode'),
                       url(r'^subscribers/(?P<mobile_no>\d+)/password/?$', SubscriberForgetPassword.as_view(), name='forgetPassword')
                       )
