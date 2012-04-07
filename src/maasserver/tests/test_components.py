# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test maasserver components module."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []


import random

from maasserver import components
from maasserver.components import (
    discard_persistent_error,
    get_persistent_errors,
    PERSISTENT_COMPONENTS_ERRORS,
    persistent_error_sensor,
    register_persistent_error,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase


def get_random_error():
    return random.choice(PERSISTENT_COMPONENTS_ERRORS.keys())


class PersistentErrorsUtilitiesTest(TestCase):

    def setUp(self):
        super(PersistentErrorsUtilitiesTest, self).setUp()
        self._PERSISTENT_ERRORS = set()
        self.patch(components, '_PERSISTENT_ERRORS', self._PERSISTENT_ERRORS)

    def test_register_persistent_error_registers_error(self):
        error = get_random_error()
        register_persistent_error(error)
        self.assertItemsEqual([error], self._PERSISTENT_ERRORS)

    def test_register_persistent_error_does_not_register_error_twice(self):
        error = get_random_error()
        register_persistent_error(error)
        register_persistent_error(error)
        self.assertItemsEqual([error], self._PERSISTENT_ERRORS)

    def test_discard_persistent_error_discards_error(self):
        error = get_random_error()
        register_persistent_error(error)
        discard_persistent_error(error)
        self.assertItemsEqual([], self._PERSISTENT_ERRORS)

    def test_discard_persistent_error_can_be_called_many_times(self):
        error = get_random_error()
        register_persistent_error(error)
        discard_persistent_error(error)
        discard_persistent_error(error)
        self.assertItemsEqual([], self._PERSISTENT_ERRORS)

    def get_persistent_errors_returns_text_for_error_codes(self):
        errors = PERSISTENT_COMPONENTS_ERRORS.keys()
        for error in errors:
            register_persistent_error(error)
        error_messages = get_persistent_errors()
        self.assertEqual(len(errors), len(error_messages))
        self.assertItemsEqual(
            [unicode] * len(errors),
            [type(error_message) for error_message in error_messages])

    def test_error_sensor_does_not_modify_method(self):
        # The decorator @persistent_error_sensor does not modify the
        # decorated method's behaviour.
        error = get_random_error()
        message = factory.getRandomString()

        @persistent_error_sensor(NotImplementedError, error)
        def test_method():
            return message

        self.assertEquals(message, test_method())

    def test_error_sensor_does_not_modify_method_if_exception(self):
        # The decorator @persistent_error_sensor does not modify the
        # decorated method's behaviour (when the method raises the
        # decorator's exception).
        error = get_random_error()

        @persistent_error_sensor(NotImplementedError, error)
        def test_method():
            raise NotImplementedError

        self.assertRaises(NotImplementedError, test_method)

    def test_error_sensor_does_not_modify_method_if_other_exception(self):
        # The decorator @persistent_error_sensor does not modify the
        # decorated method's behaviour (when the method raises an
        # unknown exception).
        error = get_random_error()

        @persistent_error_sensor(NotImplementedError, error)
        def test_method():
            raise ValueError

        self.assertRaises(ValueError, test_method)

    def test_error_sensor_registers_error_if_exception_raised(self):
        # The decorator @persistent_error_sensor does not modify the
        # decorated method's behaviour.
        error = get_random_error()

        @persistent_error_sensor(NotImplementedError, error)
        def test_method():
            raise NotImplementedError

        try:
            test_method()
        except NotImplementedError:
            pass
        self.assertItemsEqual([error], self._PERSISTENT_ERRORS)

    def test_error_sensor_registers_does_not_register_unknown_error(self):
        error = get_random_error()

        @persistent_error_sensor(NotImplementedError, error)
        def test_method():
            raise ValueError

        try:
            test_method()
        except ValueError:
            pass
        self.assertItemsEqual([], self._PERSISTENT_ERRORS)

    def test_error_sensor_discards_error_if_method_runs_successfully(self):
        error = get_random_error()
        register_persistent_error(error)

        @persistent_error_sensor(NotImplementedError, error)
        def test_method():
            pass

        test_method()
        self.assertItemsEqual([], self._PERSISTENT_ERRORS)

    def test_error_sensor_does_not_discard_error_if_unknown_exception(self):
        error = get_random_error()
        register_persistent_error(error)

        @persistent_error_sensor(ValueError, error)
        def test_method():
            raise NotImplementedError

        try:
            test_method()
        except NotImplementedError:
            pass
        self.assertItemsEqual([error], self._PERSISTENT_ERRORS)
