# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Preseed generation."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "get_preseed_template",
    ]

from os.path import join

from django.conf import settings


def get_preseed_template(filenames):
    assert not isinstance(filenames, basestring)
    for location in settings.PRESEED_TEMPLATE_LOCATIONS:
        for filename in filenames:
            filepath = join(location, filename)
            try:
                with open(filepath, "rb") as stream:
                    content = stream.read()
                    return filepath, content  # TODO: return a template.
            except IOError:
                pass  # Ignore.
    else:
        return None
