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
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
    )
from django.http import QueryDict
from maasserver.forms import (
    ConfigForm,
    EditUserForm,
    get_action_form,
    HostnameFormField,
    NewUserCreationForm,
    NODE_ACTIONS,
    NodeActionForm,
    NodeWithMACAddressesForm,
    ProfileForm,
    UIAdminNodeEditForm,
    UINodeEditForm,
    validate_hostname,
    )
from maasserver.models import (
    ARCHITECTURE,
    Config,
    DEFAULT_CONFIG,
    NODE_AFTER_COMMISSIONING_ACTION_CHOICES,
    NODE_PERMISSION,
    NODE_STATUS,
    NODE_STATUS_CHOICES_DICT,
    POWER_TYPE_CHOICES,
    )
from maasserver.provisioning import get_provisioning_api_proxy
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase
from testtools.matchers import (
    AllMatch,
    Equals,
    )


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

        self.assertSequenceEqual(
            ['hostname', 'after_commissioning_action', 'power_type'],
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


class NodeActionsTests(TestCase):
    """Test the structure of NODE_ACTIONS."""

    def test_NODE_ACTIONS_initial_states(self):
        allowed_states = set(NODE_STATUS_CHOICES_DICT.keys() + [None])

        self.assertTrue(set(NODE_ACTIONS.keys()) <= allowed_states)

    def test_NODE_ACTIONS_dict(self):
        actions = sum(NODE_ACTIONS.values(), [])
        keys = ['permission', 'display', 'execute', 'message']
        self.assertThat(
            [sorted(action.keys()) for action in actions],
            AllMatch(Equals(sorted(keys))))


class TestNodeActionForm(TestCase):

    def test_available_action_methods_for_declared_node_admin(self):
        # Check which transitions are available for an admin on a
        # 'Declared' node.
        admin = factory.make_admin()
        node = factory.make_node(status=NODE_STATUS.DECLARED)
        form = get_action_form(admin)(node)
        actions = form.available_action_methods(node, admin)
        self.assertEqual(
            ["Accept & commission"],
            [action['display'] for action in actions])
        # All permissions should be ADMIN.
        self.assertEqual(
            [NODE_PERMISSION.ADMIN] * len(actions),
            [action['permission'] for actions in actions])

    def test_available_action_methods_for_declared_node_simple_user(self):
        # A simple user sees no actions for a 'Declared' node.
        user = factory.make_user()
        node = factory.make_node(status=NODE_STATUS.DECLARED)
        form = get_action_form(user)(node)
        self.assertItemsEqual(
            [], form.available_action_methods(node, user))

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
            ["Accept & commission"],
            form.action_dict)

    def test_get_action_form_for_user(self):
        user = factory.make_user()
        node = factory.make_node(status=NODE_STATUS.DECLARED)
        form = get_action_form(user)(node)

        self.assertIsInstance(form, NodeActionForm)
        self.assertEqual(node, form.node)
        self.assertItemsEqual({}, form.action_dict)

    def test_get_action_form_node_for_admin_save(self):
        admin = factory.make_admin()
        node = factory.make_node(status=NODE_STATUS.DECLARED)
        form = get_action_form(admin)(
            node, {NodeActionForm.input_name: "Accept & commission"})
        form.save()

        self.assertEqual(NODE_STATUS.COMMISSIONING, node.status)

    def test_get_action_form_for_user_save(self):
        user = factory.make_user()
        node = factory.make_node(status=NODE_STATUS.DECLARED)
        form = get_action_form(user)(
            node, {NodeActionForm.input_name: "Enlist node"})

        self.assertRaises(PermissionDenied, form.save)

    def test_get_action_form_for_user_save_unknown_trans(self):
        user = factory.make_user()
        node = factory.make_node(status=NODE_STATUS.DECLARED)
        form = get_action_form(user)(
            node, {NodeActionForm.input_name: factory.getRandomString()})

        self.assertRaises(PermissionDenied, form.save)

    def test_start_action_starts_ready_node_for_admin(self):
        node = factory.make_node(status=NODE_STATUS.READY)
        form = get_action_form(factory.make_admin())(
            node, {NodeActionForm.input_name: "Start node"})
        form.save()

        power_status = get_provisioning_api_proxy().power_status
        self.assertEqual('start', power_status.get(node.system_id))

    def test_start_action_starts_allocated_node_for_owner(self):
        node = factory.make_node(
            status=NODE_STATUS.READY, owner=factory.make_user())
        form = get_action_form(node.owner)(
            node, {NodeActionForm.input_name: "Start node"})
        form.save()

        power_status = get_provisioning_api_proxy().power_status
        self.assertEqual('start', power_status.get(node.system_id))


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
