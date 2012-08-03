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
    post_save,
    pre_save,
    )


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
    flag = '_field_updated_%s' % field_name

    # Record if the field we're interested in has changed.
    def pre_save_callback(sender, instance, **kwargs):
        try:
            old_instance = model.objects.get(pk=instance.pk)
        except model.DoesNotExist:
            pass  # object is new.
        else:
            old_value = getattr(old_instance, field_name)
            new_value = getattr(instance, field_name)
            setattr(instance, flag, (old_value, new_value))
    pre_save.connect(pre_save_callback, sender=model, weak=False)

    # Call the `callback` if the field has been marked 'dirty'.
    def post_save_callback(sender, instance, created, **kwargs):
        delta = getattr(instance, flag, False)
        if delta:
            (old_value, new_value) = delta
            if old_value != new_value:
                callback(instance, old_value)
    post_save.connect(post_save_callback, sender=model, weak=False)
