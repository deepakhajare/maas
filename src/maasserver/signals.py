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

    The provided `callback` method will be called when the field named
    `fieldname` of an object of type `model` is changed.

    The signature of the callback method should be the following:

    >>> def callback(instance, old_field):
        pass

    Where `instance` is the object which has just being saved to the database
    and `old_field` is the old value of the field (different from the value of
    the field in `instance`).
    """
    flag = '_field_updated_%s' % field_name

    # Record if the field we're interested in has changed.
    def pre_save_callback(sender, instance, **kwargs):
        try:
            old_object = model.objects.get(pk=instance.pk)
        except model.DoesNotExist:
            pass  # object is new.
        else:
            old_field = getattr(old_object, field_name)
            if old_field != getattr(instance, field_name):
                setattr(instance, flag, old_field)
    pre_save.connect(pre_save_callback, sender=model, weak=False)

    # Call the `callback` if the field has been marked 'dirty'.
    def post_save_callback(sender, instance, created, **kwargs):
        if hasattr(instance, flag):
            callback(instance, getattr(instance, flag))
    post_save.connect(post_save_callback, sender=model, weak=False)
