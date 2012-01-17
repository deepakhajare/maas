from django.test import TestCase

from maasserver.models import Node


class SimpleTest(TestCase):

    def test_can_create_nodes(self):
        self.assertEqual([], list(Node.objects.all()))
        n = Node(name='foo', status='NEW')
        n.save()
        self.assertEqual([n], list(Node.objects.all()))

    def test_no_nodes_exist_initially(self):
        self.assertEqual([], list(Node.objects.all()))

