# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Signal utilities."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'connect_to_field_change',
    ]

from django.db.models.signals import (
    post_init,
    post_save,
    pre_save,
    )


missing = object()


def connect_to_field_change(callback, model, field_name):
    """Call the provided callback when a field is modified on a model.

    The provided `callback` method will be called when the value of the field
    named `fieldname` of an object of type `model` is changed.

    The signature of the callback method should be the following:

    >>> def callback(instance, old_value):
        ...
        pass

    Where `instance` is the object which has just being saved to the database
    and `old_value` is the old value of the field (different from the value of
    the field in `instance`).
    """
    original_flag = '_field_original_value_%s' % field_name
    last_seen_flag = '_field_last_seen_value_%s' % field_name

    # Record the original value of the field we're interested in.
    def post_init_callback(sender, instance, **kwargs):
        original_value = getattr(instance, field_name)
        setattr(instance, original_flag, original_value)
    post_init.connect(post_init_callback, sender=model, weak=False)

    # Record the current value of the field.
    def pre_save_callback(sender, instance, **kwargs):
        current_value = getattr(instance, field_name)
        setattr(instance, last_seen_flag, current_value)
    pre_save.connect(pre_save_callback, sender=model, weak=False)

    # Call the `callback` if the field has changed.
    def post_save_callback(sender, instance, created, **kwargs):
        original_value = getattr(instance, original_flag, missing)
        new_value = getattr(instance, last_seen_flag, missing)
        # Call the callback method is the field has changed.
        if original_value != new_value:
            callback(instance, original_value)
    post_save.connect(post_save_callback, sender=model, weak=False)
