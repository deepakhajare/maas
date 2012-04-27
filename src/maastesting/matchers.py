# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""testtools custom matchers"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    'ContainsAll',
]

from testtools.matchers import (
    MatchesAll,
    Contains,
    )


def ContainsAll(items):
    """Matches if the matchee contains all the provided items."""
    return MatchesAll(*[Contains(item) for item in items], first_only=False)
