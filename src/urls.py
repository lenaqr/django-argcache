from django.conf.urls import *

urlpatterns = patterns('',
                        (r'^view_all/?$', 'argcache.views.view_all'),
                        (r'^flush/([0-9]+)/?$', 'argcache.views.flush')
                        )
