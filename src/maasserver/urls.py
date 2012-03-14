# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""URL routing configuration."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import re

from django.conf import settings as django_settings
from django.conf.urls.defaults import (
    include,
    patterns,
    url,
    )
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.views import login
from django.views.generic.simple import (
    direct_to_template,
    redirect_to,
    )
from maasserver.models import Node
from maasserver.views import (
    AccountsAdd,
    AccountsDelete,
    AccountsEdit,
    AccountsView,
    combo_view,
    KeystoreView,
    logout,
    NodeListView,
    NodesCreateView,
    proxy_to_longpoll,
    settings,
    settings_add_archive,
    userprefsview,
    )


def adminurl(regexp, view, *args, **kwargs):
    view = user_passes_test(lambda u: u.is_superuser)(view)
    return url(regexp, view, *args, **kwargs)


# URLs accessible to anonymous users.
urlpatterns = patterns('maasserver.views',
    url(
        r'^%s' % re.escape(django_settings.YUI_COMBO_URL), combo_view,
        name='yui-combo'),
    url(r'^accounts/login/$', login, name='login'),
    url(
        r'^robots\.txt$', direct_to_template,
        {'template': 'maasserver/robots.txt', 'mimetype': 'text/plain'},
        name='robots'),
    url(
        r'^favicon\.ico$', redirect_to, {'url': '/static/img/favicon.ico'},
        name='favicon'),
    url(r'^accounts/(?P<userid>\w+)/sshkeys/$', KeystoreView),
)

# URLs for logged-in users.
urlpatterns += patterns('maasserver.views',
    url(r'^account/prefs/$', userprefsview, name='prefs'),
    url(r'^accounts/logout/$', logout, name='logout'),
    url(
        r'^$',
        NodeListView.as_view(template_name="maasserver/index.html"),
        name='index'),
    url(r'^nodes/$', NodeListView.as_view(model=Node), name='node-list'),
    url(
        r'^nodes/create/$', NodesCreateView.as_view(), name='node-create'),
)

if django_settings.LONGPOLL_SERVER_URL is not None:
    urlpatterns += patterns('maasserver.views',
        url(
            r'^%s$' % re.escape(django_settings.LONGPOLL_SERVER_URL),
            proxy_to_longpoll, name='proxy-to-longpoll'),
        )

# URLs for admin users.
urlpatterns += patterns('maasserver.views',
    adminurl(r'^settings/$', settings, name='settings'),
    adminurl(
        r'^settings/archives/add/$', settings_add_archive,
        name='settings-add-archive'),
    adminurl(r'^accounts/add/$', AccountsAdd.as_view(), name='accounts-add'),
    adminurl(
        r'^accounts/(?P<username>\w+)/edit/$', AccountsEdit.as_view(),
        name='accounts-edit'),
    adminurl(
        r'^accounts/(?P<username>\w+)/view/$', AccountsView.as_view(),
        name='accounts-view'),
    adminurl(
        r'^accounts/(?P<username>\w+)/del/$', AccountsDelete.as_view(),
        name='accounts-del'),
)


# API URLs.
urlpatterns += patterns('',
    (r'^api/1\.0/', include('maasserver.urls_api'))
    )
