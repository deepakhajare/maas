# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Config forms utilities."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'DictCharField',
    'DictCharWidget',
    ]

from collections import OrderedDict

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.forms.fields import Field
from django.forms.util import ErrorList
from django.utils.safestring import mark_safe


SKIP_CHECK_NAME = 'skip_check'


class DictCharField(forms.MultiValueField):
    """A field to edit a dictionary of strings.  Each entry in the
    dictionary correspond to a sub-field.

    The field is constructed with a list of tuples containing the name of the
    sub-fields and the sub-field themselves.  An optional parameter
    'skip_check' allows to store an arbitrary dictionary in the field,
    bypassing any validation made by the sub-fields.

    For instance a DictCharField created with the following list:
    [
        ('field1', forms.CharField(label="Field 1"),
        ('field2', forms.CharField(label="Field 2"),
    ]
    Will produce dictionaries of the form:
    {'field1': 'subvalue1', 'field2': 'subvalue2'}
    """

    def __init__(self, field_items, skip_check=False, *args,
                 **kwargs):
        self.field_dict = OrderedDict(field_items)
        self.skip_check = skip_check
        # if skip_check: add a BooleanField to the list of fields, this will
        # be used to skip the validation of the fields and accept arbitrary
        # data.
        if skip_check:
            self.field_dict[SKIP_CHECK_NAME] = forms.BooleanField(
                required=False)
        self.names = [name for name in self.field_dict.keys()]
        # Create the DictCharWidget with init values from the list of fields.
        self.fields = self.field_dict.values()
        self.widget = DictCharWidget(
            [field.widget for field in self.fields],
            self.names,
            [field.label for field in self.fields],
            skip_check=skip_check,
            )
        # Upcall to Field and not MultiValueField to avoid setting all the
        # subfields' 'required' attributes to False.
        Field.__init__(self, *args, **kwargs)

    def compress(self, data):
        if data:
            if isinstance(data, dict):
                return data
            else:
                return dict(zip(self.names, data))
        return None

    def clean(self, value):
        """Validates every value in the given list. A value is validated
        against the corresponding Field in self.fields.

        This is an adapted version of Django's MultiValueField_ clean method.

        The differences are:
        - the method is splitted into clean_global and
             clean_individual_fields;
        - the field and value corresponding to the SKIP_CHECK_NAME boolean
            field are removed;
        - each individual field 'required' attribute is used instead of the
            DictCharField's 'required' attribute.  This allows a more
            fine-grained control of what's required and what's not required.

        .. _MultiValueField: http://code.djangoproject.com/
            svn/django/tags/releases/1.3.1/django/forms/fields.py
        """
        if isinstance(value, dict):
            return value
        else:
            result = self.clean_global(value)
            if result is None:
                return None
            else:
                return self.clean_sub_fields(value)

    def clean_global(self, value):
        # Remove the value corresponding to the SKIP_CHECK_NAME boolean field
        # if required.
        value = value if not self.skip_check else value[:-1]
        if not value or isinstance(value, (list, tuple)):
            is_empty = (
                not value or
                not [v for v in value if v not in validators.EMPTY_VALUES])
            if is_empty:
                if self.required:
                    raise ValidationError(self.error_messages['required'])
                else:
                    return None
            else:
                return True
        else:
            raise ValidationError(self.error_messages['invalid'])

    def clean_sub_fields(self, value):
        clean_data = []
        errors = ErrorList()
        # Remove the field corresponding to the SKIP_CHECK_NAME boolean field
        # if required.
        fields = self.fields if not self.skip_check else self.fields[:-1]
        for i, field in enumerate(fields):
            try:
                field_value = value[i]
            except IndexError:
                field_value = None
            # Check the field's 'required' field instead of the global
            # 'required' field to allow subfields to be required or not.
            if field.required and field_value in validators.EMPTY_VALUES:
                errors.append(
                    '%s: %s' % (field.label, self.error_messages['required']))
                continue
            try:
                clean_data.append(field.clean(field_value))
            except ValidationError, e:
                # Collect all validation errors in a single list, which we'll
                # raise at the end of clean(), rather than raising a single
                # exception for the first error we encounter.
                errors.extend(
                    ['%s: %s' % (field.label, message)
                    for message in e.messages])
        if errors:
            raise ValidationError(errors)

        out = self.compress(clean_data)
        self.validate(out)
        return out


def get_all_prefixed_values(data, name):
    result = {}
    prefix = name + '_'
    for key, value in data.items():
        if key.startswith(prefix):
            new_key = key[len(prefix):]
            if new_key != SKIP_CHECK_NAME:
                result[new_key] = value
    return result


class DictCharWidget(forms.widgets.MultiWidget):
    """A widget to display the content of a dictionary.  Each key will
    correspond to a subwidget.  Although there is no harm in using this class
    directly, note that this is mostly destined to be used internally
    by DictCharField.

    The customization compared to Django's MultiWidget_ are:
    - DictCharWidget displays all the subwidgets inside a fieldset tag;
    - DictCharWidget displays a label for each subwidget;
    - DictCharWidget names each subwidget 'main_widget_sub_widget_name'
        instead of 'main_widget_0';
    - DictCharWidget has the (optional) ability to skip all the validation
        are instead fetch all the values prefixed by 'main_widget_' in the
        input data.

    To achieve that, we customize:
    - 'render' which returns the HTML code to display this widget;
    - 'id_for_label' which return the HTML ID attribute for this widget
        for use by a label.  This widget is composed of multiple widgets so
        the id of the first widget is used;
    - 'value_from_datadict' which fetches the value of the data to be
        processed by this form give a 'data' dictionary.  We need to
        customize that because we've changed the way MultiWidget names
        sub-widgets;
    - 'decompress' which takes a single "compressed" value and returns a list
        of values to be used by the widgets.

    .. _MultiWidget: http://code.djangoproject.com/
        svn/django/tags/releases/1.3.1/django/forms/widgets.py
    """

    def __init__(self, widgets, names, labels, skip_check=False, attrs=None):
        self.names = names
        self.labels = labels
        self.skip_check = skip_check
        super(DictCharWidget, self).__init__(widgets, attrs)

    def render(self, name, value, attrs=None):
        # value is a list of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, list):
            value = self.decompress(value)
        output = ['<fieldset>']
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(
                    final_attrs, id='%s_%s' % (id_, self.names[i]))
            # Add label to each sub-field.
            label_for = ' for="%s"' % final_attrs['id'] if id_ else ''
            output.append(
                '<label%s>%s</label>' % (
                    label_for, self.labels[i]))
            output.append(
                widget.render(
                    name + '_%s' % self.names[i], widget_value, final_attrs))
        output.append('</fieldset>')
        return mark_safe(self.format_output(output))

    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += '_%s' % self.names[0]
        return id_

    def value_from_datadict(self, data, files, name):
        """Extract the values for each widget from a data dict (QueryDict)."""
        skip_check = (
            self.skip_check and
            self.widgets[-1].value_from_datadict(
                data, files, name + '_%s' % self.names[-1]))
        if skip_check:
            # If the skip_check option is on and the value of the boolean
            # field is true: simply return all the values from 'data' which
            # are prefixed by the name of thie widget.
            return get_all_prefixed_values(data, name)
        else:
            return [
                widget.value_from_datadict(
                    data, files, name + '_%s' % self.names[i])
                for i, widget in enumerate(self.widgets)]

    def decompress(self, value):
        if value is not None:
            return [value.get(name, None) for name in self.names]
        else:
            return [None] * len(self.names)
