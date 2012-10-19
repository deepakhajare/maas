# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Command: start the cluster controller."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'add_arguments',
    'run',
    ]

from grp import getgrnam
import httplib
import json
import os
from pwd import getpwnam
from time import sleep
from urllib2 import (
    HTTPError,
    URLError,
    )

from apiclient.maas_client import (
    MAASClient,
    MAASDispatcher,
    NoAuth,
    )
from celery.app import app_or_default
from celery.log import (
    get_task_logger,
    setup_logging_subsystem,
    )
from provisioningserver.network import discover_networks


task_logger = get_task_logger(name=__name__)


class ClusterControllerRejected(Exception):
    """Request to become a cluster controller has been rejected."""


def add_arguments(parser):
    """For use by :class:`MainScript`."""
    parser.add_argument(
        'server_url', metavar='URL', help="URL to the MAAS region controller.")
    parser.add_argument(
        '--user', '-u', metavar='USER', default='maas',
        help="System user identity that should run the cluster controller.")
    parser.add_argument(
        '--group', '-g', metavar='GROUP', default='maas',
        help="System group that should run the cluster controller.")


def log_error(exception):
    task_logger.info(
        "Could not register with region controller: %s."
        % exception.reason)


def make_anonymous_api_client(server_url):
    """Create an unauthenticated API client."""
    return MAASClient(NoAuth(), MAASDispatcher(), server_url)


def get_cluster_uuid():
    """Read this cluster's UUID from the config."""
    return app_or_default().conf.CLUSTER_UUID


def get_maas_celery_log():
    """Read location for MAAS Celery log file from the config."""
    return app_or_default().conf.MAAS_CELERY_LOG


def get_maas_celerybeat_db():
    """Read location for MAAS Celery schedule file from the config."""
    return app_or_default().conf.MAAS_CLUSTER_CELERY_DB


def register(server_url):
    """Request Rabbit connection details from the domain controller.

    Offers this machine to the region controller as a potential cluster
    controller.

    :param server_url: URL to the region controller's MAAS API.
    :return: A dict of connection details if this cluster controller has been
        accepted, or `None` if there is no definite response yet.  If there
        is no definite response, retry this call later.
    :raise ClusterControllerRejected: if this system has been rejected as a
        cluster controller.
    """
    known_responses = {httplib.OK, httplib.FORBIDDEN, httplib.ACCEPTED}

    interfaces = json.dumps(discover_networks())
    client = make_anonymous_api_client(server_url)
    cluster_uuid = get_cluster_uuid()
    try:
        response = client.post(
            'api/1.0/nodegroups/', 'register',
            interfaces=interfaces, uuid=cluster_uuid)
    except HTTPError as e:
        status_code = e.code
        if e.code not in known_responses:
            log_error(e)
            # Unknown error.  Keep trying.
            return None
    except URLError as e:
        log_error(e)
        # Unknown error.  Keep trying.
        return None
    else:
        status_code = response.getcode()

    if status_code == httplib.OK:
        # Our application has been approved.  Proceed.
        return json.loads(response.read())
    elif status_code == httplib.ACCEPTED:
        # Our application is still waiting for approval.  Keep trying.
        return None
    elif status_code == httplib.FORBIDDEN:
        # Our application has been rejected.  Give up.
        raise ClusterControllerRejected(
            "This system has been rejected as a cluster controller.")
    else:
        raise AssertionError("Unexpected return code: %r" % status_code)


def start_celery(connection_details, user, group):
    broker_url = connection_details['BROKER_URL']
    uid = getpwnam(user).pw_uid
    gid = getgrnam(group).gr_gid

    # Copy environment, but also tell celeryd what broker to listen to.
    env = dict(os.environ, CELERY_BROKER_URL=broker_url)

    command = [
        'celeryd',
        '--logfile=%s' % get_maas_celery_log(),
        '--schedule=%s' % get_maas_celerybeat_db(),
        '--loglevel=INFO',
        '--beat',
        '-Q', get_cluster_uuid(),
        ]

    # Change gid first, just in case changing the uid might deprive
    # us of the privileges required to setgid.
    os.setgid(gid)
    os.setuid(uid)

    os.execvpe(command[0], command, env=env)


def request_refresh(server_url):
    client = make_anonymous_api_client(server_url)
    try:
        client.post('api/1.0/nodegroups/', 'refresh_workers')
    except URLError as e:
        task_logger.warn(
            "Could not request secrets from region controller: %s"
            % e.reason)


def start_up(server_url, connection_details, user, group):
    """We've been accepted as a cluster controller; start doing the job.

    This starts up celeryd, listening to the broker that the region
    controller pointed us to, and on the appropriate queue.
    """
    # Get the region controller to send out credentials.  If it arrives
    # before celeryd has started up, we should find the message waiting
    # in our queue.  Even if we're new and the queue did not exist yet,
    # the arriving task will create the queue.
    request_refresh(server_url)
    start_celery(connection_details, user=user, group=group)


def run(args):
    """Start the cluster controller.

    If this system is still awaiting approval as a cluster controller, this
    command will keep looping until it gets a definite answer.
    """
    setup_logging_subsystem(loglevel="INFO", logfile=get_maas_celery_log())
    connection_details = register(args.server_url)
    while connection_details is None:
        sleep(60)
        connection_details = register(args.server_url)
    start_up(
        args.server_url, connection_details, user=args.user, group=args.group)
