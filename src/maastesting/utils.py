# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing utilities."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "age_file",
    "content_from_file",
    "extract_word_list",
    "get_write_time",
    "preexec_fn",
    "retries",
    ]

import os
import re
import signal
from time import (
    sleep,
    time,
    )

from provisioningserver.utils import atomic_write
from testtools.content import Content
from testtools.content_type import UTF8_TEXT


def age_file(path, seconds):
    """Backdate a file's modification time so that it looks older."""
    stat_result = os.stat(path)
    atime = stat_result.st_atime
    mtime = stat_result.st_mtime
    os.utime(path, (atime, mtime - seconds))


def get_write_time(path):
    """Return last modification time of file at `path`."""
    return os.stat(path).st_mtime


def content_from_file(path):
    """Alternative to testtools' version.

    This keeps an open file-handle, so it can obtain the log even when the
    file has been unlinked.
    """
    fd = open(path, "rb")

    def iterate():
        fd.seek(0)
        return iter(fd)

    return Content(UTF8_TEXT, iterate)


def extract_word_list(string):
    """Return a list of words from a string.

    Words are any string of 1 or more characters, not including commas,
    semi-colons, or whitespace.
    """
    return re.findall("[^,;\s]+", string)


def preexec_fn():
    # Revert Python's handling of SIGPIPE. See
    # http://bugs.python.org/issue1652 for more info.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def retries(timeout=30, delay=1):
    """Helper for retrying something, sleeping between attempts.

    Yields ``(elapsed, remaining)`` tuples, giving times in seconds.

    @param timeout: From now, how long to keep iterating, in seconds.
    @param delay: The sleep between each iteration, in seconds.
    """
    start = time()
    end = start + timeout
    for now in iter(time, None):
        if now < end:
            yield now - start, end - now
            sleep(min(delay, end - now))
        else:
            break


def incremental_write(content, filename):
    """Write the given `content` into the file `filename` and
    increment the modification time by 1 sec.
    """
    old_mtime = None
    if os.path.exists(filename):
        old_mtime = os.stat(filename).st_mtime
    atomic_write(content, filename)
    increment_age(filename, old_mtime=old_mtime)


def increment_age(filename, old_mtime=None, delta=1000):
    """Increment the modification time by 1 sec compared to the given
    `old_mtime`.

    This function is used to manage the modification time of files
    for which we need to see an increment in the modification time
    each time the file is modified.  This is the case for DNS zone
    files which only get properly reloaded if BIND sees that the
    modification time is > to the time it has in its database.

    Since the resolution of the modification time is one second,
    we want to manually set the modification time in the past
    the first time the file is written and increment the mod
    time by 1 manually each time the file gets written again.

    We also want to be careful not to set the modification time in
    the future (mostly because BIND doesn't deal with that well).

    Finally, note that the access time is set to the same value as
    the modification time.
    """
    now = time()
    if old_mtime is None:
        # Set modification time in the past to have room for
        # sub-second modifications.
        new_mtime = now - delta
    else:
        # If the modification time can be incremented by 1 sec
        # without being in the future, do it.  Otherwise we give
        # up and set it to 'now'.
        if old_mtime + 1 <= now:
            new_mtime = old_mtime + 1
        else:
            new_mtime = old_mtime
    os.utime(filename, (new_mtime, new_mtime))
