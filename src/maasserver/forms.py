# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Forms."""

from __future__ import (
    print_function,
    unicode_literals,
    )

__metaclass__ = type
__all__ = [
    "NodeForm",
    "MACAddressForm",
    ]

from django import forms
from django.forms import ModelForm
from maasserver.macaddress import MACAddressFormField
from maasserver.models import (
    MACAddress,
    Node,
    )


class NodeForm(ModelForm):
    system_id = forms.CharField(
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False)

    class Meta:
        model = Node
        fields = ('hostname', 'system_id')


class MACAddressForm(ModelForm):
    class Meta:
        model = MACAddress


class MACAddressForm(ModelForm):
    class Meta:
        model = MACAddress


class MultipleMACAddressField(forms.MultiValueField):
    def __init__(self, nb_macs=1, *args, **kwargs):
        fields = [MACAddressFormField() for i in xrange(nb_macs)]
        super(MultipleMACAddressField, self).__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            return data_list
        return []


class NodeWithMACAddressesForm(NodeForm):

    def __init__(self, *args, **kwargs):
        super(NodeWithMACAddressesForm, self).__init__(*args, **kwargs)
        macs = self.data.getlist('macaddresses')
        self.fields['macaddresses'] = MultipleMACAddressField(len(macs))
        self.data['macaddresses'] = macs

    def save(self):
        node = super(NodeWithMACAddressesForm, self).save()
        for mac in self.cleaned_data['macaddresses']:
            node.add_mac_address(mac)
        return node