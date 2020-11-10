from django.conf.urls import patterns, url, include
#from rest_framework import routers
#from auth.views import UserView
import views

 
#router = routers.DefaultRouter()
#router.register(r'accounts', UserView, 'list')

urlpatterns = patterns(
    '',
    #url(r'', include(router.urls)),
    #url(r'^auth/$', views.AuthView.as_view(), name='authenticate')
    url(r'^login/$', 'auth.views.login'),
    url(r'^logout/$', 'auth.views.logout'),
)