
from django.conf.urls.defaults import *
from django.views.generic import ListView
from piston.resource import Resource
from maasserver.models import Node
from maasserver.views import NodeView, NodesCreateView
from maasserver.api import (
    api_doc,
    NodeHandler,
    NodesHandler,
    NodeMacsHandler
    )


urlpatterns = patterns('maasserver.views',
    url(r'^$', ListView.as_view(model=Node), name='index'),
    url(r'^nodes/create/$', NodesCreateView.as_view(), name='node-create'),
    url(r'^nodes/([\w\-]+)/$', NodeView.as_view(), name='node-view'),
)

# Api.
node_handler = Resource(NodeHandler)
nodes_handler = Resource(NodesHandler)
node_macs_handler = Resource(NodeMacsHandler)

urlpatterns += patterns('maasserver.views',
    url(
        r'^api/nodes/(?P<system_id>[\w\-]+)/macs/(?P<mac_address>.+)/$',
        node_macs_handler, name='node_mac_handler'),
    url(
        r'^api/nodes/(?P<system_id>[\w\-]+)/macs/$', node_macs_handler,
        name='node_macs_handler'),

    url(
        r'^api/nodes/(?P<system_id>[\w\-]+)/$', node_handler,
        name='node_handler'),
    url(r'^api/nodes/$', nodes_handler, name='nodes_handler'),

    url(r'^api/doc/$', api_doc),
)

