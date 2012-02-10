# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Django command: run the server.  Overrides the default implementation."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = ['Command']

from django.conf import settings
from django.core.management.commands.runserver import BaseRunserverCommand
import oops
from oops_datedir_repo import DateDirRepo
from oops_wsgi import (
    install_hooks,
    make_app,
    )


error_template = """
<html>
<head><title>Oops! - %(id)s</title></head>
<body>
<h1>Oops!</h1>
<p>
  Something broke while generating this page.
</p>
<p>
  If the problem persists, please
  <a href="https://bugs.launchpad.net/maas/">file a bug</a>.  Make a note of
  the "oops id": <strong>%(id)s</strong>
</p>
</html>
""".lstrip()


def render_error(report):
    """Produce an HTML error report, in raw bytes (not unicode)."""
    return (error_template % report).encode('ascii')


class Command(BaseRunserverCommand):
    """Customized "runserver" command that wraps the WSGI handler."""

    def get_handler(self, *args, **kwargs):
        """Overridable from `BaseRunserverCommand`: Obtain a WSGI handler."""
        wsgi_handler = super(Command, self).get_handler(self, *args, **kwargs)

        # Wrap the WSGI handler in an oops handler.  This catches (most)
        # exceptions bubbling up out of the app, and stores them as
        # oopses in the directory specified by the OOPS_REPOSITORY
        # configuration setting.
        # Django's debug mode causes it to handle exceptions itself, so
        # don't expect oopses when DEBUG is set to True.
        oops_config = oops.Config()
        oops_repository = DateDirRepo(settings.OOPS_REPOSITORY, 'maasserver')
        oops_config.publishers.append(oops_repository.publish)
        install_hooks(oops_config)
        return make_app(wsgi_handler, oops_config, error_render=render_error)
