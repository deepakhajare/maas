#!/usr/bin/env python2.7
# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Find imported modules."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type

import argparse
from modulefinder import ModuleFinder
from os import getcwd, path


python_standard_libs = {
    '__builtin__',
    '__future__',
    '__main__',
    '_winreg',
    'abc',
    'aepack',
    'aetools',
    'aetypes',
    'aifc',
    'al',
    'AL',
    'anydbm',
    'applesingle',
    'argparse',
    'array',
    'ast',
    'asynchat',
    'asyncore',
    'atexit',
    'audioop',
    'autoGIL',
    'base64',
    'BaseHTTPServer',
    'Bastion',
    'bdb',
    'binascii',
    'binhex',
    'bisect',
    'bsddb',
    'buildtools',
    'bz2',
    'calendar',
    'Carbon',
    'cd',
    'cfmfile',
    'cgi',
    'CGIHTTPServer',
    'cgitb',
    'chunk',
    'cmath',
    'cmd',
    'code',
    'codecs',
    'codeop',
    'collections',
    'ColorPicker',
    'colorsys',
    'commands',
    'compileall',
    'compiler',
    'ConfigParser',
    'contextlib',
    'Cookie',
    'cookielib',
    'copy',
    'copy_reg',
    'cPickle',
    'cProfile',
    'crypt',
    'cStringIO',
    'csv',
    'ctypes',
    'curses',
    'datetime',
    'dbhash',
    'dbm',
    'decimal',
    'DEVICE',
    'difflib',
    'dircache',
    'dis',
    'distutils',
    'dl',
    'doctest',
    'DocXMLRPCServer',
    'dumbdbm',
    'dummy_thread',
    'dummy_threading',
    'EasyDialogs',
    'email',
    'encodings',
    'errno',
    'exceptions',
    'fcntl',
    'filecmp',
    'fileinput',
    'findertools',
    'FL',
    'fl',
    'flp',
    'fm',
    'fnmatch',
    'formatter',
    'fpectl',
    'fpformat',
    'fractions',
    'FrameWork',
    'ftplib',
    'functools',
    'future_builtins',
    'gc',
    'gdbm',
    'gensuitemodule',
    'getopt',
    'getpass',
    'gettext',
    'gl',
    'GL',
    'glob',
    'grp',
    'gzip',
    'hashlib',
    'heapq',
    'hmac',
    'hotshot',
    'htmlentitydefs',
    'htmllib',
    'HTMLParser',
    'httplib',
    'ic',
    'icopen',
    'imageop',
    'imaplib',
    'imgfile',
    'imghdr',
    'imp',
    'importlib',
    'imputil',
    'inspect',
    'io',
    'itertools',
    'jpeg',
    'json',
    'keyword',
    'lib2to3',
    'linecache',
    'locale',
    'logging',
    'macerrors',
    'MacOS',
    'macostools',
    'macpath',
    'macresource',
    'mailbox',
    'mailcap',
    'marshal',
    'math',
    'md5',
    'mhlib',
    'mimetools',
    'mimetypes',
    'MimeWriter',
    'mimify',
    'MiniAEFrame',
    'mmap',
    'modulefinder',
    'msilib',
    'msvcrt',
    'multifile',
    'multiprocessing',
    'mutex',
    'Nav',
    'netrc',
    'new',
    'nis',
    'nntplib',
    'numbers',
    'operator',
    'optparse',
    'os',
    'ossaudiodev',
    'parser',
    'pdb',
    'pickle',
    'pickletools',
    'pipes',
    'PixMapWrapper',
    'pkgutil',
    'platform',
    'plistlib',
    'popen2',
    'poplib',
    'posix',
    'posixfile',
    'pprint',
    'profile',
    'pstats',
    'pty',
    'pwd',
    'py_compile',
    'pyclbr',
    'pydoc',
    'Queue',
    'quopri',
    'random',
    're',
    'readline',
    'repr',
    'resource',
    'rexec',
    'rfc822',
    'rlcompleter',
    'robotparser',
    'runpy',
    'sched',
    'ScrolledText',
    'select',
    'sets',
    'sgmllib',
    'sha',
    'shelve',
    'shlex',
    'shutil',
    'signal',
    'SimpleHTTPServer',
    'SimpleXMLRPCServer',
    'site',
    'smtpd',
    'smtplib',
    'sndhdr',
    'socket',
    'SocketServer',
    'spwd',
    'sqlite3',
    'ssl',
    'stat',
    'statvfs',
    'string',
    'StringIO',
    'stringprep',
    'struct',
    'subprocess',
    'sunau',
    'sunaudiodev',
    'SUNAUDIODEV',
    'symbol',
    'symtable',
    'sys',
    'sysconfig',
    'syslog',
    'tabnanny',
    'tarfile',
    'telnetlib',
    'tempfile',
    'termios',
    'test',
    'textwrap',
    'thread',
    'threading',
    'time',
    'timeit',
    'Tix',
    'Tkinter',
    'token',
    'tokenize',
    'trace',
    'traceback',
    'ttk',
    'tty',
    'turtle',
    'types',
    'unicodedata',
    'unittest',
    'urllib',
    'urllib2',
    'urlparse',
    'user',
    'UserDict',
    'UserList',
    'UserString',
    'uu',
    'uuid',
    'videoreader',
    'W',
    'warnings',
    'wave',
    'weakref',
    'webbrowser',
    'whichdb',
    'winsound',
    'wsgiref',
    'xdrlib',
    'xml',
    'xmlrpclib',
    'zipfile',
    'zipimport',
    'zlib',
    }


def top_module_name(name):
    """Return the top-level module name.

    e.g. os.path -> os
    """
    return name.split(".", 1)[0]


def guess_module_name(filename):
    """Guess a module name from a filename.

    e.g. foo/bar.py -> bar
    """
    head, tail = path.splitext(filename)
    return path.basename(head)


def find_standard_library_modules(seed=python_standard_libs):
    """Find all standard-library modules."""
    finder = ModuleFinder()
    for name in seed:
        finder.import_module(name, name, None)
    return set(finder.modules)


argument_parser = argparse.ArgumentParser(description=__doc__)
argument_parser.add_argument(
    "-0", "--null", help="delimit output with null bytes",
    action="store_true", default=False)
argument_parser.add_argument(
    "filenames", nargs="+", metavar="FILENAME")


if __name__ == '__main__':
    options = argument_parser.parse_args()
    standard_libs = find_standard_library_modules()
    finder = ModuleFinder()
    for filename in options.filenames:
        finder.load_file(filename)
    # Collect modules from the finder, eliminating those from the standard
    # library.
    modules = (
        module for name, module in finder.modules.items()
        if top_module_name(name) not in standard_libs
        )
    # Collect the absolute paths for each module, eliminating those modules
    # with no filename.
    filenames = (
        path.abspath(module.__file__) for module in modules
        if module.__file__ is not None
        )
    # Narrow down to those modules not in the nearby source tree.
    here = getcwd()
    filenames = (
        filename for filename in filenames
        if not filename.startswith(here)
        )
    # Write it all out.
    end = b"\0" if options.null else None
    for filename in sorted(filenames):
        print(filename, end=end)
