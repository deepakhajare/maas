from django.core.management.commands.runserver import BaseRunserverCommand


class Command(BaseRunserverCommand):
    """Customized "runserver" command that wraps the WSGI handler."""

    def get_handler(self, *args, **kwargs):
        wsgi_handler = BaseRunserverCommand.get_handler(self, *args, **kwargs)
        return wsgi_handler
