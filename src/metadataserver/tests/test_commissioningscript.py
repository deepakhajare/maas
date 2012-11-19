# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test custom commissioning scripts."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import codecs
from random import randint

from maasserver.testing import reload_object
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from metadataserver.fields import Bin
from metadataserver.models import CommissioningScript


def make_script_name(base_name=None, number=None):
    """Make up a name for a commissioning script."""
    if base_name is None:
        base_name = 'script'
    if number is None:
        number = randint(0, 99)
    return factory.make_name(
        '%0.2d-%s' % (number, factory.make_name(base_name)))


def make_script_content(recognizable_text='script'):
    """Make up content for a commissioning script."""
    text = "%s-%s" % (recognizable_text, factory.getRandomString())
    return Bin(text.encode('ascii'))


def list_names(scripts):
    """List the respective names for `scripts`."""
    return [script.name for script in scripts]


class TestCommissioningScript(TestCase):

    def test_store_script_creates_script(self):
        name = make_script_name()
        content = factory.getRandomString()
        CommissioningScript.objects.store_script(name, content)
        stored_script = CommissioningScript.objects.get(name=name)
        self.assertEqual(content, stored_script.content)

    def test_store_script_overwrites_script(self):
        name = make_script_name()
        CommissioningScript.objects.create(
            name=name, content=make_script_content('old'))
        new_content = make_script_content('new')
        CommissioningScript.objects.store_script(name, new_content)
        stored_script = CommissioningScript.objects.filter(name=name)
        self.assertEqual(1, len(stored_script))
        self.assertEqual(new_content, stored_script[0].content)

    def test_get_scripts_returns_nothing_if_no_scripts_defined(self):
        self.assertItemsEqual([], CommissioningScript.objects.get_scripts())

    def test_get_scripts_retrieves_all_scripts(self):
        script = CommissioningScript.objects.store_script(
            make_script_name(), make_script_content())
        self.assertItemsEqual(
            [script], CommissioningScript.objects.get_scripts())

    def test_get_scripts_ignores_overwritten_scripts(self):
        name = make_script_name()
        CommissioningScript.objects.store_script(
            name, make_script_content('old'))
        new_content = make_script_content('new')
        stored_script = CommissioningScript.objects.store_script(
            name, new_content)
        self.assertItemsEqual(
            [stored_script],
            CommissioningScript.objects.get_scripts())
        self.assertEqual(new_content, reload_object(stored_script).content)

    def test_get_scripts_orders_by_name(self):
        names = [make_script_name(number=number) for number in [99, 1, 25, 8]]
        for name in names:
            CommissioningScript.objects.store_script(
                name, make_script_content(name))
        self.assertEqual(
            sorted(names),
            list_names(CommissioningScript.objects.get_scripts()))

    def test_drop_script_removes_script(self):
        name = make_script_name()
        CommissioningScript.objects.store_script(name, make_script_content())
        CommissioningScript.objects.drop_script(name)
        self.assertItemsEqual([], CommissioningScript.objects.get_scripts())

    def test_drop_script_leaves_other_scripts_alone(self):
        doomed_script = make_script_name('doomed')
        unaffected_script = make_script_name('unaffected')
        CommissioningScript.objects.store_script(
            doomed_script, make_script_content(doomed_script))
        CommissioningScript.objects.store_script(
            unaffected_script, make_script_content(unaffected_script))
        CommissioningScript.objects.drop_script(doomed_script)
        self.assertIn(
            unaffected_script,
            list_names(CommissioningScript.objects.get_scripts()))

    def test_drop_script_tolerates_nonexistent_script(self):
        CommissioningScript.objects.drop_script(
            make_script_name('nonexistent'))
        # The test is that we get here without errors.
        pass

    def test_scripts_may_be_binary(self):
        name = make_script_name()
        # Some binary data that would break just about any kind of text
        # interpretation.
        binary = Bin(codecs.BOM64_LE + codecs.BOM64_BE + b'\x00\xff\x00')
        CommissioningScript.objects.store_script(name, binary)
        [stored_script] = CommissioningScript.objects.get_scripts()
        self.assertEqual(binary, stored_script.content)
