# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test maasserver API."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

import httplib

from django.contrib.auth.models import User
from lxml.html import fromstring
from maasserver.testing import LoggedInTestCase


class UserPrefsViewTest(LoggedInTestCase):

    def test_prefs_GET_profile(self):
        # The preferences page (profile tab) displays a form with the
        # user's personal information.
        user = self.logged_in_user
        user.first_name = 'Steve'
        user.last_name = 'Bam'
        user.save()
        response = self.client.get('/accounts/prefs/')
        doc = fromstring(response.content)
        self.assertSequenceEqual(
            ['User preferences for %s' % user.username],
            [elem.text for elem in doc.cssselect('h2')])
        self.assertSequenceEqual(
            ['Bam'],
            [elem.value for elem in
                doc.cssselect('input#id_profile-last_name')])
        self.assertSequenceEqual(
            ['Steve'],
            [elem.value for elem in
                doc.cssselect('input#id_profile-first_name')])

    def test_prefs_GET_api(self):
        # The preferences page (api tab) displays the API access tokens.
        user = self.logged_in_user
        response = self.client.get('/accounts/prefs/?tab=1')
        doc = fromstring(response.content)
        # The consumer key and the token key are displayed.
        self.assertSequenceEqual(
            [user.get_profile().get_authorisation_consumer().key],
            [elem.text.strip() for elem in
                doc.cssselect('div#consumer_key')])
        self.assertSequenceEqual(
            [user.get_profile().get_authorisation_token().key],
            [elem.text.strip() for elem in
                doc.cssselect('div#token_key')])

    def test_prefs_POST_profile(self):
        # The preferences page allows the user the update its profile
        # information.
        response = self.client.post(
            '/accounts/prefs/',
            {
                'profile_submit': 1, 'profile-first_name': 'John',
                'profile-last_name': 'Doe', 'profile-email': 'jon@example.com'
            })

        self.assertEqual(httplib.FOUND, response.status_code)
        user = User.objects.get(id=self.logged_in_user.id)
        self.assertEqual('John', user.first_name)
        self.assertEqual('Doe', user.last_name)
        self.assertEqual('jon@example.com', user.email)

    def test_prefs_POST_password(self):
        # The preferences page allows the user the change its password.
        old_pw = self.logged_in_user.password
        response = self.client.post(
            '/accounts/prefs/',
            {
                'password_submit': 1,
                'password-old_password': 'test',
                'password-new_password1': 'new',
                'password-new_password2': 'new',
            })
        self.assertEqual(httplib.FOUND, response.status_code)
        user = User.objects.get(id=self.logged_in_user.id)
        # The password is SHA1ized, we just make sure that it has changed.
        self.assertNotEqual(old_pw, user.password)
