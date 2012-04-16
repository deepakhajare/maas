# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Initial maasserver migration."""

from __future__ import (
    # This breaks South.
    #unicode_literals,
    absolute_import,
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = []

# flake8: noqa
# SKIP this file when reformatting.
# The rest of this file was generated by South.

# encoding: utf-8
import datetime

from django.db import models
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Node'
        db.create_table('maasserver_node', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateField')()),
            ('updated', self.gf('django.db.models.fields.DateTimeField')()),
            ('system_id', self.gf('django.db.models.fields.CharField')(default=u'node-abe5fcd0-6f3a-11e1-b5bf-00219bd0a2de', unique=True, max_length=41)),
            ('hostname', self.gf('django.db.models.fields.CharField')(default=u'', max_length=255, blank=True)),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=0, max_length=10)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['auth.User'], null=True, blank=True)),
            ('after_commissioning_action', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('architecture', self.gf('django.db.models.fields.CharField')(default=u'i386', max_length=10)),
            ('power_type', self.gf('django.db.models.fields.CharField')(default=u'', max_length=10, blank=True)),
        ))
        db.send_create_signal('maasserver', ['Node'])

        # Adding model 'MACAddress'
        db.create_table('maasserver_macaddress', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateField')()),
            ('updated', self.gf('django.db.models.fields.DateTimeField')()),
            ('mac_address', self.gf('maasserver.fields.MACAddressField')()),
            ('node', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['maasserver.Node'])),
        ))
        db.send_create_signal('maasserver', ['MACAddress'])

        # Adding model 'UserProfile'
        db.create_table('maasserver_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
        ))
        db.send_create_signal('maasserver', ['UserProfile'])

        # Adding model 'SSHKeys'
        db.create_table('maasserver_sshkeys', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['maasserver.UserProfile'])),
            ('key', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('maasserver', ['SSHKeys'])

        # Adding model 'FileStorage'
        db.create_table('maasserver_filestorage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('filename', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('data', self.gf('django.db.models.fields.files.FileField')(max_length=255)),
        ))
        db.send_create_signal('maasserver', ['FileStorage'])

        # Adding model 'Config'
        db.create_table('maasserver_config', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('value', self.gf('maasserver.fields.JSONObjectField')(null=True)),
        ))
        db.send_create_signal('maasserver', ['Config'])


    def backwards(self, orm):
        
        # Deleting model 'Node'
        db.delete_table('maasserver_node')

        # Deleting model 'MACAddress'
        db.delete_table('maasserver_macaddress')

        # Deleting model 'UserProfile'
        db.delete_table('maasserver_userprofile')

        # Deleting model 'SSHKeys'
        db.delete_table('maasserver_sshkeys')

        # Deleting model 'FileStorage'
        db.delete_table('maasserver_filestorage')

        # Deleting model 'Config'
        db.delete_table('maasserver_config')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'maasserver.config': {
            'Meta': {'object_name': 'Config'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'value': ('maasserver.fields.JSONObjectField', [], {'null': 'True'})
        },
        'maasserver.filestorage': {
            'Meta': {'object_name': 'FileStorage'},
            'data': ('django.db.models.fields.files.FileField', [], {'max_length': '255'}),
            'filename': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'maasserver.macaddress': {
            'Meta': {'object_name': 'MACAddress'},
            'created': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mac_address': ('maasserver.fields.MACAddressField', [], {}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['maasserver.Node']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {})
        },
        'maasserver.node': {
            'Meta': {'object_name': 'Node'},
            'after_commissioning_action': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'architecture': ('django.db.models.fields.CharField', [], {'default': "u'i386'", 'max_length': '10'}),
            'created': ('django.db.models.fields.DateField', [], {}),
            'hostname': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'power_type': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '10', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0', 'max_length': '10'}),
            'system_id': ('django.db.models.fields.CharField', [], {'default': "u'node-abe7a9cc-6f3a-11e1-b5bf-00219bd0a2de'", 'unique': 'True', 'max_length': '41'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {})
        },
        'maasserver.sshkeys': {
            'Meta': {'object_name': 'SSHKeys'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['maasserver.UserProfile']"})
        },
        'maasserver.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['maasserver']
