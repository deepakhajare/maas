# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test config forms utilities."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

from django import forms
from django.forms import widgets
from django.http import QueryDict
from maasserver.config_forms import (
    DictCharField,
    DictCharWidget,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import TestCase


testField = DictCharField(
        [
            ('field_a', forms.CharField(label='Field a')),
            ('field_b', forms.CharField(
                label='Field b', required=False, max_length=3)),
            ('field_c', forms.CharField(label='Field c', required=False)),
        ])


class TestForm(forms.Form):
    multi_field = testField


# A form where the DictCharField instance is constructed with skip_check=True.
class TestFormSkip(forms.Form):
    multi_field = DictCharField(
        [('field_a', forms.CharField(label='Field a', max_length=3))],
        skip_check=True)


# A form where the DictCharField instance is constructed with required=False.
class TestFormRequiredFalse(forms.Form):
    multi_field = DictCharField(
        [('field_a', forms.CharField(label='Field a'))],
        required=False)
    char_field = forms.CharField(label='Field a')


class DictCharFieldTest(TestCase):

    def test_DictCharField_init(self):
        self.assertEqual(['field_a', 'field_b', 'field_c'], testField.names)
        self.assertEqual(
            ['field_a', 'field_b', 'field_c'], testField.widget.names)
        self.assertEqual(
            [field.widget for field in testField.field_dict.values()],
            testField.widget.widgets)


class FormWithDictCharFieldTest(TestCase):

    def test_DictCharField_processes_QueryDict_into_a_dict(self):
        fielda_value = factory.getRandomString()
        fieldc_value = factory.getRandomString()
        data = QueryDict(
            'multi_field_field_a=%s&multi_field_field_c=%s' % (
                fielda_value, fieldc_value))
        form = TestForm(data)

        self.assertTrue(form.is_valid())
        self.assertEqual(
            {
                'field_a': fielda_value,
                'field_b': '',
                'field_c': fieldc_value,
            },
            form.cleaned_data['multi_field'])

    def test_DictCharField_honors_field_constraint(self):
        # Create a value that will fail validation because it's too long.
        fielda_value = factory.getRandomString(10)
        data = QueryDict('multi_field_field_b=%s' % fielda_value)
        form = TestForm(data)

        self.assertFalse(form.is_valid())
        self.assertEqual(
            {'multi_field': [
                'Field a: This field is required.',
                'Field b: Ensure this value has at '
                'most 3 characters (it has 10).']},
            form.errors)

    def test_DictCharField_skip_check_true_skips_validation(self):
        # Create a value that will fail validation because it's too long.
        fielda_value = factory.getRandomString(10)
        # multi_field_skip_check=true will make the form accept the value
        # even if it's not valid.
        data = QueryDict(
            'multi_field_field_a=%s&multi_field_skip_check=true' % (
                fielda_value))
        form = TestFormSkip(data)

        self.assertTrue(form.is_valid())
        self.assertEqual(
            {'field_a': fielda_value},
            form.cleaned_data['multi_field'])

    def test_DictCharField_skip_check_false(self):
        # Create a value that will fail validation because it's too long.
        fielda_value = factory.getRandomString(10)
        # Force the check with multi_field_skip_check=false.
        data = QueryDict(
            'multi_field_field_a=%s&multi_field_skip_check=false' % (
                fielda_value))
        form = TestFormSkip(data)

        self.assertFalse(form.is_valid())
        self.assertEqual(
            {
                'multi_field': [
                    "Field a: Ensure this value has at most 3 characters "
                    "(it has 10)."]
            },
            form.errors)

    def test_DictCharField_accepts_required_false(self):
        char_value = factory.getRandomString(10)
        data = QueryDict('char_field=%s' % (char_value))
        form = TestFormRequiredFalse(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(
            {'char_field': char_value, 'multi_field': None},
            form.cleaned_data)


class DictCharWidgetTest(TestCase):

    def test_DictCharWidget_id_for_label_uses_first_fields_name(self):
        names = [factory.getRandomString()]
        labels = [factory.getRandomString()]
        widget = DictCharWidget(
            [widgets.TextInput, widgets.TextInput], names, labels)
        self.assertEqual(
            ' _%s' % names[0],
            widget.id_for_label(' '))

    def test_DictCharWidget_renders_fieldset_with_label_and_field_names(self):
        names = [factory.getRandomString(), factory.getRandomString()]
        labels = [factory.getRandomString(), factory.getRandomString()]
        values = [factory.getRandomString(), factory.getRandomString()]
        widget = DictCharWidget(
            [widgets.TextInput, widgets.TextInput], names, labels)
        name = factory.getRandomString()
        self.assertEqual(
            '<fieldset>'
            '<label>%s</label>'
            '<input type="text" name="%s" value="%s" />'
            '<label>%s</label>'
            '<input type="text" name="%s" value="%s" />'
            '</fieldset>' %
                (
                    labels[0],
                     '%s_%s' % (name, names[0]), values[0],
                     labels[1],
                     '%s_%s' % (name, names[1]), values[1],
                ),
            widget.render(name, values))

    def test_DictCharWidget_value_from_datadict_values_from_data(self):
        # 'value_from_datadict' extracts the value of the fields from a
        # QueryDict and returns them in the sub widgets' order.
        names = [factory.getRandomString(), factory.getRandomString()]
        labels = [factory.getRandomString(), factory.getRandomString()]
        name = factory.getRandomString()
        field_1_value = factory.getRandomString()
        field_2_value = factory.getRandomString()
        # Create a query string with the field2 before the field1 and another
        # (unknown) value.
        data = QueryDict(
            '%s_%s=%s&%s_%s=%s&%s=%s' % (
                name, names[1], field_2_value,
                name, names[0], field_1_value,
                factory.getRandomString(), factory.getRandomString())
            )
        widget = DictCharWidget(
            [widgets.TextInput, widgets.TextInput], names, labels)
        self.assertEqual(
            [field_1_value, field_2_value],
            widget.value_from_datadict(data, None, name))
