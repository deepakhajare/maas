# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test forms."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from django import forms
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
    )
from django.http import QueryDict
from maasserver.enum import (
    ARCHITECTURE,
    NODE_AFTER_COMMISSIONING_ACTION_CHOICES,
    NODE_STATUS,
    )
from maasserver.forms import (
    APIAdminNodeEditForm,
    ConfigForm,
    EditUserForm,
    get_action_form,
    get_node_edit_form,
    HostnameFormField,
    MACAddressForm,
    NewUserCreationForm,
    NodeActionForm,
    NodeWithMACAddressesForm,
    ProfileForm,
    remove_None_values,
    UIAdminNodeEditForm,
    UINodeEditForm,
    validate_hostname,
    )
from maasserver.models import (
    Config,
    MACAddress,
    )
from maasserver.models.config import DEFAULT_CONFIG
from maasserver.node_action import (
    AcceptAndCommission,
    Delete,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from provisioningserver.enum import POWER_TYPE_CHOICES
from testtools.testcase import ExpectedException


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
        # If the form only has one (invalid) MAC address field to validate,
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
        # If the form has multiple MAC address fields to validate,
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
            ['One or more MAC addresses is invalid.'],
            form.errors['mac_addresses'])

    def test_NodeWithMACAddressesForm_empty(self):
        # Empty values in the list of MAC addresses are simply ignored.
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
            [
                'hostname',
                'after_commissioning_action',
            ], list(form.fields))

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
            [
                'hostname',
                'after_commissioning_action',
                'power_type',
            ],
            list(form.fields))

    def test_UIAdminNodeEditForm_changes_node(self):
        node = factory.make_node()
        hostname = factory.getRandomString()
        after_commissioning_action = factory.getRandomChoice(
            NODE_AFTER_COMMISSIONING_ACTION_CHOICES)
        power_type = factory.getRandomChoice(POWER_TYPE_CHOICES)
        form = UIAdminNodeEditForm(
            data={
                'hostname': hostname,
                'after_commissioning_action': after_commissioning_action,
                'power_type': power_type,
                },
            instance=node)
        form.save()

        self.assertEqual(hostname, node.hostname)
        self.assertEqual(
            after_commissioning_action, node.after_commissioning_action)
        self.assertEqual(power_type, node.power_type)

    def test_remove_None_values_removes_None_values_in_dict(self):
        random_input = factory.getRandomString()
        self.assertEqual(
            {random_input: random_input},
            remove_None_values({
                random_input: random_input,
                factory.getRandomString(): None
                }))

    def test_remove_None_values_leaves_empty_dict_untouched(self):
        self.assertEqual({}, remove_None_values({}))

    def test_APIAdminNodeEditForm_contains_limited_set_of_fields(self):
        form = APIAdminNodeEditForm({}, instance=factory.make_node())

        self.assertEqual(
            [
                'hostname',
                'after_commissioning_action',
                'power_type',
                'power_parameters',
            ],
            list(form.fields))

    def test_APIAdminNodeEditForm_changes_node(self):
        node = factory.make_node()
        hostname = factory.getRandomString()
        after_commissioning_action = factory.getRandomChoice(
            NODE_AFTER_COMMISSIONING_ACTION_CHOICES)
        power_type = factory.getRandomChoice(POWER_TYPE_CHOICES)
        power_parameters_field = factory.getRandomString()
        form = APIAdminNodeEditForm(
            data={
                'hostname': hostname,
                'after_commissioning_action': after_commissioning_action,
                'power_type': power_type,
                'power_parameters_field': power_parameters_field,
                'power_parameters_skip_check': True,
                },
            instance=node)
        form.save()

        self.assertEqual(
            (hostname, after_commissioning_action, power_type,
                {'field': power_parameters_field}),
            (node.hostname, node.after_commissioning_action, node.power_type,
                node.power_parameters))

    def test_get_node_edit_form_returns_UIAdminNodeEditForm_if_admin(self):
        admin = factory.make_admin()
        self.assertEqual(UIAdminNodeEditForm, get_node_edit_form(admin))

    def test_get_node_edit_form_returns_UINodeEditForm_if_non_admin(self):
        user = factory.make_user()
        self.assertEqual(UINodeEditForm, get_node_edit_form(user))

    def test_get_node_edit_form_returns_APIAdminNodeEdit_if_admin_api(self):
        admin = factory.make_admin()
        self.assertEqual(APIAdminNodeEditForm, get_node_edit_form(admin, True))

    def test_get_node_edit_form_returns_UINodeEditForm_if_non_admin_api(self):
        user = factory.make_user()
        self.assertEqual(UINodeEditForm, get_node_edit_form(user, True))


class TestNodeActionForm(TestCase):

    def test_get_action_form_creates_form_class_with_attributes(self):
        user = factory.make_admin()
        form_class = get_action_form(user)

        self.assertEqual(user, form_class.user)

    def test_get_action_form_creates_form_class(self):
        user = factory.make_admin()
        node = factory.make_node(status=NODE_STATUS.DECLARED)
        form = get_action_form(user)(node)

        self.assertIsInstance(form, NodeActionForm)
        self.assertEqual(node, form.node)

    def test_get_action_form_for_admin(self):
        admin = factory.make_admin()
        node = factory.make_node(status=NODE_STATUS.DECLARED)
        form = get_action_form(admin)(node)

        self.assertItemsEqual(
            [AcceptAndCommission.display, Delete.display],
            form.actions)

    def test_get_action_form_for_user(self):
        user = factory.make_user()
        node = factory.make_node(status=NODE_STATUS.DECLARED)
        form = get_action_form(user)(node)

        self.assertIsInstance(form, NodeActionForm)
        self.assertEqual(node, form.node)
        self.assertItemsEqual({}, form.actions)

    def test_save_performs_requested_action(self):
        admin = factory.make_admin()
        node = factory.make_node(status=NODE_STATUS.DECLARED)
        form = get_action_form(admin)(
            node, {NodeActionForm.input_name: AcceptAndCommission.display})
        form.save()
        self.assertEqual(NODE_STATUS.COMMISSIONING, node.status)

    def test_save_refuses_disallowed_action(self):
        user = factory.make_user()
        node = factory.make_node(status=NODE_STATUS.DECLARED)
        form = get_action_form(user)(
            node, {NodeActionForm.input_name: AcceptAndCommission.display})
        self.assertRaises(PermissionDenied, form.save)

    def test_save_refuses_unknown_action(self):
        user = factory.make_user()
        node = factory.make_node(status=NODE_STATUS.DECLARED)
        form = get_action_form(user)(
            node, {NodeActionForm.input_name: factory.getRandomString()})
        self.assertRaises(PermissionDenied, form.save)

    def test_save_double_checks_for_inhibitions(self):
        admin = factory.make_admin()
        node = factory.make_node(
            status=NODE_STATUS.ALLOCATED, owner=factory.make_user())
        form = get_action_form(admin)(
            node, {NodeActionForm.input_name: Delete.display})
        with ExpectedException(PermissionDenied, "You cannot delete.*"):
            form.save()


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


class TestUniqueEmailForms(TestCase):

    def assertFormFailsValidationBecauseEmailNotUnique(self, form):
        self.assertFalse(form.is_valid())
        self.assertIn('email', form._errors)
        self.assertEqual(
            ["User with this E-mail address already exists."],
            form._errors['email'])

    def test_ProfileForm_fails_validation_if_email_taken(self):
        another_email = '%s@example.com' % factory.getRandomString()
        factory.make_user(email=another_email)
        email = '%s@example.com' % factory.getRandomString()
        user = factory.make_user(email=email)
        form = ProfileForm(instance=user, data={'email': another_email})
        self.assertFormFailsValidationBecauseEmailNotUnique(form)

    def test_ProfileForm_validates_if_email_unchanged(self):
        email = '%s@example.com' % factory.getRandomString()
        user = factory.make_user(email=email)
        form = ProfileForm(instance=user, data={'email': email})
        self.assertTrue(form.is_valid())

    def test_NewUserCreationForm_fails_validation_if_email_taken(self):
        email = '%s@example.com' % factory.getRandomString()
        username = factory.getRandomString()
        password = factory.getRandomString()
        factory.make_user(email=email)
        form = NewUserCreationForm(
            {
                'email': email,
                'username': username,
                'password1': password,
                'password2': password,
            })
        self.assertFormFailsValidationBecauseEmailNotUnique(form)

    def test_EditUserForm_fails_validation_if_email_taken(self):
        another_email = '%s@example.com' % factory.getRandomString()
        factory.make_user(email=another_email)
        email = '%s@example.com' % factory.getRandomString()
        user = factory.make_user(email=email)
        form = EditUserForm(instance=user, data={'email': another_email})
        self.assertFormFailsValidationBecauseEmailNotUnique(form)

    def test_EditUserForm_validates_if_email_unchanged(self):
        email = '%s@example.com' % factory.getRandomString()
        user = factory.make_user(email=email)
        form = EditUserForm(
            instance=user,
            data={
                'email': email,
                'username': factory.getRandomString(),
            })
        self.assertTrue(form.is_valid())


class TestNewUserCreationForm(TestCase):

    def test_fields_order(self):
        form = NewUserCreationForm()

        self.assertEqual(
            ['username', 'last_name', 'email', 'password1', 'password2',
                'is_superuser'],
            list(form.fields))


class TestMACAddressForm(TestCase):

    def test_MACAddressForm_creates_mac_address(self):
        node = factory.make_node()
        mac = factory.getRandomMACAddress()
        form = MACAddressForm(node=node, data={'mac_address': mac})
        form.save()
        self.assertTrue(
            MACAddress.objects.filter(node=node, mac_address=mac).exists())

    def test_MACAddressForm_displays_error_message_if_mac_already_used(self):
        mac = factory.getRandomMACAddress()
        node = factory.make_mac_address(address=mac)
        node = factory.make_node()
        form = MACAddressForm(node=node, data={'mac_address': mac})
        self.assertFalse(form.is_valid())
        self.assertEquals(
            {'mac_address': ['This MAC address is already registered.']},
            form._errors)
        self.assertFalse(
            MACAddress.objects.filter(node=node, mac_address=mac).exists())
