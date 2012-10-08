# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Profile-related functionality."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'get_profile',
    'select_profile',
    ]

from itertools import islice


class InvalidProfile(Exception):
    """Unknown profile specified."""


def get_profile(profiles, profile_name):
    """Look up the named profile in `profiles`."""
    if profile_name not in profiles:
        raise InvalidProfile("'%s' is not an active profile." % profile_name)
    return profiles[profile_name]


def name_default_profile(profiles):
    """Return name of the default profile, or raise `NoDefaultProfile`."""
    profiles_sample = list(islice(profiles, 2))
    if len(profiles_sample) == 1:
        # There's exactly one profile.  That makes a sensible default.
        return profiles_sample[0]

    return None


def select_profile(profiles, profile_name=None):
    """Return name for the applicable profile: the given name, or the default.

    Returns None if no name was given and no default is available.
    """
    if profile_name is None:
        return name_default_profile(profiles)
    else:
        return profile_name
