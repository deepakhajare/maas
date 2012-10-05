# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A proxy that looks like MAASClient.

This actually passes the requests on to a django.test.client.Client, to avoid
having to go via a real HTTP server.
"""


class MAASDjangoTestClient:
    """Wrap the Django testing Client to look like a MAASClient."""

    def __init__(self, django_client):
        self.django_client = django_client

    def get(self, path, op=None, **kwargs):
        kwargs['op'] = op
        return self.django_client.get(path, kwargs)

    def post(self, path, op=None, **kwargs):
        kwargs['op'] = op
        return self.django_client.post(path, kwargs)

    def put(self, path, **kwargs):
        return self.django_client.put(path, kwargs)

    def delete(self, path):
        return self.django_client.delete(path)
