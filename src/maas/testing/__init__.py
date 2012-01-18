__all__ = []
__metaclass__ = type

import django.test
import testtools
import testresources


class TestCase(testtools.TestCase, django.test.TestCase):
    """`TestCase` for Metal as a Service.

    Supports test resources and fixtures.
    """

    # testresources.ResourcedTestCase does something similar to this class
    # (with respect to setUpResources and tearDownResources) but it explicitly
    # up-calls to unittest.TestCase instead of using super() even though it is
    # not guaranteed that the next class in the inheritance chain is
    # unittest.TestCase.

    resources = ()

    def setUp(self):
        super(TestCase, self).setUp()
        self.setUpResources()

    def setUpResources(self):
        testresources.setUpResources(
            self, self.resources, testresources._get_result())

    def tearDown(self):
        self.tearDownResources()
        super(TestCase, self).tearDown()

    def tearDownResources(self):
        testresources.tearDownResources(
            self, self.resources, testresources._get_result())
