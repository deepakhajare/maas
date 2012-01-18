from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import (
    CreateView,
    ListView,
    )
from maasserver.models import Node


class NodeView(ListView):

    context_object_name = "node_list"

    def get_queryset(self):
        node = get_object_or_404(Node, name__iexact=self.args[0])
        return Node.objects.filter(node=node)


class NodesCreateView(CreateView):

    model = Node
#    template_name = 'maasserver/node_create.html'
    success_url = '/'
