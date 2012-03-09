# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Rabbit messaging."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []


from maastesting import TestCase
from rabbitfixture.server import RabbitServer
from maasserver.rabbit import RabbitProducer
from django.conf import settings
from maasserver.testing.factory import factory
from maasserver import rabbit


class TestRabbitProducer(TestCase):

    def setUp(self):
        super(TestRabbitProducer, self).setUp()
        self.rabbit_server = self.useFixture(RabbitServer())
        self.rabbit_env = self.rabbit_server.runner.environment
        self.old_connect = rabbit.connect
        rabbit.connect = self.rabbit_env.get_connection

    def tearDown(self):
        super(TestRabbitProducer, self).tearDown()
        rabbit.connect = self.old_connect

    def create_producer(self):
        producer = RabbitProducer()
        producer._connection = self.rabbit_env.get_connection()
        return producer

    def get_command_output(self, command):
        # Returns the output of the given rabbit command.
        return self.rabbit_env.rabbitctl(str(command))[0]

    def test_get_connection(self):
        producer = RabbitProducer()
        connection = producer.get_connection()
        self.assertEqual(producer._connection, connection)

    def test_get_channel(self):
        producer = RabbitProducer()
        channel = producer.get_channel()
        self.assertEqual(producer._channel, channel)
        self.assertTrue(channel.is_open)
        self.assertIn(
            settings.RABBITMQ_QUEUE_NAME,
            self.get_command_output('list_queues'))
        self.assertIn(
            settings.RABBITMQ_EXCHANGE_NAME,
            self.get_command_output('list_exchanges'))

    def test_publish(self):
        message_content = factory.getRandomString()
        producer = RabbitProducer()
        producer.publish(message_content)
        channel = producer.get_channel()
        message = channel.basic_get(settings.RABBITMQ_QUEUE_NAME)
        self.assertEqual(message_content, message.body)
