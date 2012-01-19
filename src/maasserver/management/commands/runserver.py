from django.conf import settings
from django.core.management.commands.runserver import BaseRunserverCommand
from oops import Config
from oops_datedir_repo import DateDirRepo
from oops_wsgi import install_hooks, make_app


class Command(BaseRunserverCommand):
    """Customized "runserver" command that wraps the WSGI handler."""

    def get_handler(self, *args, **kwargs):
        wsgi_handler = BaseRunserverCommand.get_handler(self, *args, **kwargs)
        oops_config = Config()
        oops_repository = DateDirRepo(settings.OOPS_REPOSITORY, 'maas')
        oops_config.publishers.append(oops_repository.publish)
        install_hooks(oops_config)
        return make_app(wsgi_handler, oops_config)
