# Copyright 2012 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from maasserver.models import Config
from ZeroconfService import ZeroconfService

class AvahiService(object):

    def get_maas_name(self):
        site_name = Config.objects.get_config('maas_name')
        return site_name

    def __init__(self):
        site_name = "%s MAAS Server" % self.get_maas_name()
        self.service = ZeroconfService(name=site_name,
                                       port=80,
                                       stype="_maas._tcp")
        self.service.publish()


    def maas_title_changed(self, sender, instance, created, **kwargs):
        self.service.unpublish()
        site_name = "%s MAAS Server" % self.get_maas_name()
        self.service = ZeroconfService(name=site_name,
                                       port=80,
                                       stype="_maas._tcp")
        self.service.publish()


service = AvahiService()
Config.objects.config_changed_connect('maas_name', service.maas_title_changed)
