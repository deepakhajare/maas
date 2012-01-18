from subprocess import check_call, PIPE
from django.test.simple import DjangoTestSuiteRunner

from testresources import OptimisingTestSuite


class MaaSTestRunner(DjangoTestSuiteRunner):
    """Custom test runner; ensures that the test database cluster is up."""

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        suite = super(MaaSTestRunner, self).build_suite(
            test_labels, extra_tests, **kwargs)
        return OptimisingTestSuite(suite)

    def setup_databases(self, *args, **kwargs):
        """Fire up the db cluster, then punt to original implementation."""
        check_call(
            ['bin/maasdb', 'start', './db/', 'disposable'], stdout=PIPE)
        return super(MaaSTestRunner, self).setup_databases(*args, **kwargs)
