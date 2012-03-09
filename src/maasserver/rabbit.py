# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Rabbit messaging."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []


from amqplib import client_0_8 as amqp
from django.conf import settings


def connect():
    """Connect to AMQP."""
    return amqp.Connection(
        host=settings.RABBITMQ_HOST,
        userid=settings.RABBITMQ_USERID,
        password=settings.RABBITMQ_PASSWORD,
        virtual_host=settings.RABBITMQ_VIRTUAL_HOST,
        insist=False)


class RabbitProducer:

    def __init__(self):
        self._connection = None
        self._channel = None

    def get_connection(self):
        if self._connection is None:
            self._connection = connect()
        return self._connection

    def get_channel(self):
        if self._channel is None:
            self._channel = self.get_connection().channel()
            self._channel.exchange_declare(
                exchange=settings.RABBITMQ_EXCHANGE_NAME,
                type='direct', durable=True,
                auto_delete=False)
            self._channel.queue_declare(
                queue=settings.RABBITMQ_QUEUE_NAME, durable=True,
                exclusive=False, auto_delete=False)
            self._channel.queue_bind(
                 queue=settings.RABBITMQ_QUEUE_NAME,
                exchange=settings.RABBITMQ_EXCHANGE_NAME,
                routing_key=settings.RABBITMQ_ROUTING_KEY)
        return self._channel

    def publish(self, message):
        msg = amqp.Message(message)
        channel = self.get_channel()
        channel.basic_publish(
            exchange=settings.RABBITMQ_EXCHANGE_NAME,
            routing_key=settings.RABBITMQ_ROUTING_KEY, msg=msg)
