/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Widget to fade and resize between two DOM nodes.
 *
 * @module Y.mass.morph
 */

YUI.add('maas.morph', function(Y) {

Y.log('loading mass.morph');

var module = Y.namespace('maas.morph');

var Morph = function(config) {
    Morph.superclass.constructor.apply(this, arguments);
};

Morph.NAME = 'morph';

Morph.ATTRS = {
    /**
     * The DOM node to be morphed from.
     *
     * @attribute targetNode
     * @type string
     */
    targetNode: {
        value: null,
        setter: function(val) {
            return Y.one(val);
        }
    }
};

Y.extend(Morph, Y.Widget, {
    morph: function(reverse) {
        if (reverse){
            var srcNode = this.get('targetNode');
            var targetNode = this.get('srcNode');
        }
        else {
            var srcNode = this.get('srcNode');
            var targetNode = this.get('targetNode');
        }
        
        target_height = targetNode.getComputedStyle('height');
        var fade_out = new Y.Anim({
            node: targetNode,
            to: {opacity: 0},
            duration: 0.2,
            easing: 'easeOut'
            });
        fade_out.run();
        fade_out.on('end', function () {
            targetNode.addClass('hidden');
            srcNode.setStyle('opacity', 0);
            srcNode.removeClass('hidden');
            src_height = srcNode.getComputedStyle('height').replace('px', '');
            srcNode.setStyle('height', target_height);
            var fade_in = new Y.Anim({
                node: srcNode,
                to: {opacity: 1},
                duration: 1,
                easing: 'easeIn'
                });
            var resize = new Y.Anim({
                node: srcNode,
                to: {height: src_height},
                duration: 0.5,
                easing: 'easeOut'
                });
            fade_in.run();
            resize.run();
        });
    }
});

module.Morph = Morph

}, '0.1', {'requires': ['widget', 'node', 'anim']});