from subprocess import Popen
from django.test.simple import DjangoTestSuiteRunner


class CustomTestRunner(DjangoTestSuiteRunner):
    """Custom test runner; ensures that the test database cluster is up."""

    def setup_databases(self, *args, **kwargs):
        """Fire up the db cluster, then punt to original implementation."""
        process = Popen(['bin/maasdb', 'start', './db/'])
        retval = process.wait()
        if retval != 0:
            raise RuntimeError("Failed to start database cluster.")
        return super(CustomTestRunner, self).setup_databases(*args, **kwargs)
