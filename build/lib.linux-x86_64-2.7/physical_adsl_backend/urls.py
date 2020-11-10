from django.conf.urls import patterns, url
import views


urlpatterns = patterns('',
    url(r'^adsl/subscribers/?$', views.NetworkDeviceOperationsView.as_view()),
    url(r'^gpon/operations/?$', views.GponOperations.as_view()),


)