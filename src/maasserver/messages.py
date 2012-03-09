# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Messages."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []


from maasserver.models import (
    Node,
    )
from django.db.models.signals import (
    post_delete,
    post_save,
    )
from maasserver.rabbit import RabbitProducer
from django.core.serializers.json import DjangoJSONEncoder
from functools import partial
from abc import (
    ABCMeta,
    abstractmethod,
    )


class MESSENGER_MESSAGE:
    CREATED = 'created'
    UPDATED = 'updated'
    DELETED = 'deleted'


class Messenger:

    __metaclass__ = ABCMeta

    def __init__(self, klass, producer):
        self.klass = klass
        self.producer = producer

    @abstractmethod
    def create_msg(self, event_name, instance):
        """Return a message from the given event_name and instance."""

    def update_obj(self, sender, instance, created, **kwargs):
        event_name = (
            MESSENGER_MESSAGE.CREATED if created
            else MESSENGER_MESSAGE.UPDATED)
        message = self.create_msg(event_name, instance)
        self.producer.publish(message)

    def delete_obj(self, sender, instance, **kwargs):
        message = self.create_msg(MESSENGER_MESSAGE.DELETED, instance)
        self.producer.publish(message)

    def register(self):
        post_save.connect(
            receiver=partial(self.update_obj), weak=False, sender=self.klass)
        post_delete.connect(
            partial(self.delete_obj), weak=False, sender=self.klass)


class MaaSMessenger(Messenger):

    def create_msg(self, event_name, instance):
        event_key = self.event_key(event_name, instance)
        return DjangoJSONEncoder().encode({
            'instance':
                {k: v for k, v in instance.__dict__.items()
                 if not k.startswith('_')},
            'event_key': event_key,

        })

    def event_key(self, event_name, instance):
        return "%s.%s|%s" % (
            instance.__class__.__name__, event_name, instance.pk)


producer = RabbitProducer()

MaaSMessenger(Node, producer).register()
