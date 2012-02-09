# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "logout",
    "NodeListView",
    "NodesCreateView",
    ]

from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm as PasswordForm
from django.contrib.auth.views import logout as dj_logout
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic import (
    CreateView,
    ListView,
    )
from maasserver.forms import ProfileForm
from maasserver.models import Node


def logout(request):
    messages.info(request, "You have been logged out.")
    return dj_logout(request, next_page=reverse('login'))


class NodeListView(ListView):

    context_object_name = "node_list"

    def get_queryset(self):
        return Node.objects.get_visible_nodes(user=self.request.user)


class NodesCreateView(CreateView):

    model = Node

    def get_success_url(self):
        return reverse('index')


def userprefsview(request):
    user = request.user
    tab = request.GET.get('tab', 0)
    if 'profile_submit' in request.POST:
        tab = 0
        profile_form = ProfileForm(
            request.POST, instance=user, prefix='profile')
        if profile_form.is_valid():
            messages.info(request, "Profile updated.")
            profile_form.save()
            return HttpResponseRedirect('%s?tab=%d' % (reverse('prefs'), tab))
    else:
        profile_form = ProfileForm(instance=user, prefix='profile')
    if 'password_submit' in request.POST:
        tab = 2
        password_form = PasswordForm(
            data=request.POST, user=user, prefix='password')
        if password_form.is_valid():
            messages.info(request, "Password updated.")
            password_form.save()
            return HttpResponseRedirect('%s?tab=%d' % (reverse('prefs'), tab))
    else:
        password_form = PasswordForm(user=user, prefix='password')

    return render_to_response(
        'maasserver/prefs.html',
        {
            'profile_form': profile_form,
            'password_form': password_form,
            'tab': tab  # Tab index to display.
        },
        context_instance=RequestContext(request))
