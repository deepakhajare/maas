/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI({ useBrowserConsole: true }).add('maas.morph.tests', function(Y) {

Y.log('loading maas.morph.tests');
var namespace = Y.namespace('maas.morph.tests');

var module = Y.maas.morph;
var suite = new Y.Test.Suite("maas.morph Tests");

suite.add(new Y.maas.testing.TestCase({
    name: 'test-morphing',

    testMorphing: function() {
        var cfg = {
            srcNode: '#panel-two',
            targetNode: '#panel-one'
        }
        morpher = new module.MorphWidget(cfg);
        Y.Assert.isFalse(
            Y.one('#panel-one').hasClass('hidden'),
            'The target panel should initially be visible');
        Y.Assert.isTrue(
            Y.one('#panel-two').hasClass('hidden'),
            'The source panel should initially be hidden');
        morpher.morph();
        Y.Assert.isTrue(
            Y.one('#panel-one').hasClass('hidden'),
            'The target panel should now be hidden');
        Y.Assert.isFalse(
            Y.one('#panel-two').hasClass('hidden'),
            'The source panel should now be visible');
    }
}));

namespace.suite = suite;

}, '0.1', {'requires': [
    'node-event-simulate', 'test', 'maas.testing', 'maas.morph']}
);
