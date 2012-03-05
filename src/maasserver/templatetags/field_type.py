# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from django import template

register = template.Library()

@register.filter('field_type')
def field_type(field):
    type = field.field.widget.__class__.__name__
    return type
