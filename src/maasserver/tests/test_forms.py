# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test forms."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from django import forms
from django.core.exceptions import ValidationError
from django.http import QueryDict
from maasserver.forms import (
    ConfigForm,
    HostnameFormField,
    NewUserCreationForm,
    NodeWithMACAddressesForm,
    validate_hostname,
    UIAdminNodeEditForm,
    UINodeEditForm
    )
from maasserver.models import (
    ARCHITECTURE,
    Config,
    DEFAULT_CONFIG,
    NODE_AFTER_COMMISSIONING_ACTION_CHOICES,
    POWER_TYPE_CHOICES,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
import random


class NodeWithMACAddressesFormTest(TestCase):

    def get_QueryDict(self, params):
        query_dict = QueryDict('', mutable=True)
        for k, v in params.items():
            if isinstance(v, list):
                query_dict.setlist(k, v)
            else:
                query_dict[k] = v
        return query_dict

    def test_NodeWithMACAddressesForm_valid(self):

        form = NodeWithMACAddressesForm(
            self.get_QueryDict({
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', '9a:bb:c3:33:e5:7f'],
                'architecture': ARCHITECTURE.i386,
                }))

        self.assertTrue(form.is_valid())
        self.assertEqual(
            ['aa:bb:cc:dd:ee:ff', '9a:bb:c3:33:e5:7f'],
            form.cleaned_data['mac_addresses'])
        self.assertEqual(ARCHITECTURE.i386, form.cleaned_data['architecture'])

    def test_NodeWithMACAddressesForm_simple_invalid(self):
        # If the form only has one (invalid) MAC Address field to validate,
        # the error message in form.errors['mac_addresses'] is the
        # message from the field's validation error.
        form = NodeWithMACAddressesForm(
            self.get_QueryDict({
                'mac_addresses': ['invalid'],
                'architecture': ARCHITECTURE.i386,
                }))

        self.assertFalse(form.is_valid())
        self.assertEqual(['mac_addresses'], list(form.errors))
        self.assertEqual(
            ['Enter a valid MAC address (e.g. AA:BB:CC:DD:EE:FF).'],
            form.errors['mac_addresses'])

    def test_NodeWithMACAddressesForm_multiple_invalid(self):
        # If the form has multiple MAC Address fields to validate,
        # if one or more fields are invalid, a single error message is
        # present in form.errors['mac_addresses'] after validation.
        form = NodeWithMACAddressesForm(
            self.get_QueryDict({
                'mac_addresses': ['invalid_1', 'invalid_2'],
                'architecture': ARCHITECTURE.i386,
                }))

        self.assertFalse(form.is_valid())
        self.assertEqual(['mac_addresses'], list(form.errors))
        self.assertEqual(
            ['One or more MAC Addresses is invalid.'],
            form.errors['mac_addresses'])

    def test_NodeWithMACAddressesForm_empty(self):
        # Empty values in the list of MAC Addresses are simply ignored.
        form = NodeWithMACAddressesForm(
            self.get_QueryDict({
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', ''],
                'architecture': ARCHITECTURE.i386,
                }))

        self.assertTrue(form.is_valid())

    def test_NodeWithMACAddressesForm_save(self):
        form = NodeWithMACAddressesForm(
            self.get_QueryDict({
                'mac_addresses': ['aa:bb:cc:dd:ee:ff', '9a:bb:c3:33:e5:7f'],
                'architecture': ARCHITECTURE.i386,
                }))
        node = form.save()

        self.assertIsNotNone(node.id)  # The node is persisted.
        self.assertSequenceEqual(
            ['aa:bb:cc:dd:ee:ff', '9a:bb:c3:33:e5:7f'],
            [mac.mac_address for mac in node.macaddress_set.all()])


class TestOptionForm(ConfigForm):
    field1 = forms.CharField(label="Field 1", max_length=10)
    field2 = forms.BooleanField(label="Field 2", required=False)


class ConfigFormTest(TestCase):

    def test_form_valid_saves_into_db(self):
        value = factory.getRandomString(10)
        form = TestOptionForm({'field1': value, 'field2': False})
        result = form.save()

        self.assertTrue(result)
        self.assertEqual(value, Config.objects.get_config('field1'))
        self.assertFalse(Config.objects.get_config('field2'))

    def test_form_invalid_does_not_save_into_db(self):
        value_too_long = factory.getRandomString(20)
        form = TestOptionForm({'field1': value_too_long, 'field2': False})
        result = form.save()

        self.assertFalse(result)
        self.assertIn('field1', form._errors)
        self.assertIsNone(Config.objects.get_config('field1'))
        self.assertIsNone(Config.objects.get_config('field2'))

    def test_form_loads_initial_values(self):
        value = factory.getRandomString()
        Config.objects.set_config('field1', value)
        form = TestOptionForm()

        self.assertItemsEqual(['field1'], form.initial)
        self.assertEqual(value, form.initial['field1'])

    def test_form_loads_initial_values_from_default_value(self):
        value = factory.getRandomString()
        DEFAULT_CONFIG['field1'] = value
        form = TestOptionForm()

        self.assertItemsEqual(['field1'], form.initial)
        self.assertEqual(value, form.initial['field1'])


class FormWithHostname(forms.Form):
    hostname = HostnameFormField()


class NodeEditForms(TestCase):

    def test_UINodeEditForm_contains_limited_set_of_fields(self):
        form = UINodeEditForm()

        self.assertEqual(
            ['hostname', 'after_commissioning_action'], list(form.fields))

    def test_UINodeEditForm_changes_node(self):
        node = factory.make_node()
        hostname = factory.getRandomString()
        after_commissioning_action = factory.getRandomChoice(
            NODE_AFTER_COMMISSIONING_ACTION_CHOICES)

        form = UINodeEditForm(
            data={
                'hostname': hostname,
                'after_commissioning_action': after_commissioning_action,
                },
            instance=node)
        form.save()

        self.assertEqual(hostname, node.hostname)
        self.assertEqual(
            after_commissioning_action, node.after_commissioning_action)

    def test_UIAdminNodeEditForm_contains_limited_set_of_fields(self):
        form = UIAdminNodeEditForm()

        self.assertEqual(
            ['hostname', 'after_commissioning_action', 'power_type', 'owner'],
            list(form.fields))

    def test_UIAdminNodeEditForm_changes_node(self):
        node = factory.make_node()
        hostname = factory.getRandomString()
        after_commissioning_action = factory.getRandomChoice(
            NODE_AFTER_COMMISSIONING_ACTION_CHOICES)
        power_type = factory.getRandomChoice(POWER_TYPE_CHOICES)
        owner = random.choice([factory.make_user() for i in range(10)])
        form = UIAdminNodeEditForm(
            data={
                'hostname': hostname,
                'after_commissioning_action': after_commissioning_action,
                'power_type': power_type,
                'owner': owner.id,
                },
            instance=node)
        form.save()

        self.assertEqual(hostname, node.hostname)
        self.assertEqual(
            after_commissioning_action, node.after_commissioning_action)
        self.assertEqual(power_type, node.power_type)
        self.assertEqual(owner, node.owner)

    def test_UIAdminNodeEditForm_owner_choices_contains_active_users(self):
        form = UIAdminNodeEditForm()
        user = factory.make_user()
        user_ids = [choice[0] for choice in form.fields['owner'].choices]

        self.assertItemsEqual(['', user.id], user_ids)


class TestHostnameFormField(TestCase):

    def test_validate_hostname_validates_valid_hostnames(self):
        self.assertIsNone(validate_hostname('host.example.com'))
        self.assertIsNone(validate_hostname('host.my-example.com'))
        self.assertIsNone(validate_hostname('my-example.com'))
        #  No ValidationError.

    def test_validate_hostname_does_not_validate_invalid_hostnames(self):
        self.assertRaises(ValidationError, validate_hostname, 'invalid-host')

    def test_validate_hostname_does_not_validate_too_long_hostnames(self):
        self.assertRaises(ValidationError, validate_hostname, 'toolong' * 100)

    def test_hostname_field_validation_cleaned_data_if_hostname_valid(self):
        form = FormWithHostname({'hostname': 'host.example.com'})

        self.assertTrue(form.is_valid())
        self.assertEqual('host.example.com', form.cleaned_data['hostname'])

    def test_hostname_field_validation_error_if_invalid_hostname(self):
        form = FormWithHostname({'hostname': 'invalid-host'})

        self.assertFalse(form.is_valid())
        self.assertItemsEqual(['hostname'], list(form.errors))
        self.assertEqual(
            ["Enter a valid hostname (e.g. host.example.com)."],
            form.errors['hostname'])


class TestNewUserCreationForm(TestCase):

    def test_fields_order(self):
        form = NewUserCreationForm()

        self.assertEqual(
            ['username', 'last_name', 'email', 'password1', 'password2',
                'is_superuser'],
            list(form.fields))
