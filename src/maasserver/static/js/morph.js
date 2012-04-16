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

Morph._fade_out;
Morph._fade_in;
Morph._resize;

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
    initializer: function(cfg) {
        if (Y.Lang.isValue(cfg.animate)) {
            this._animate = cfg.animate;
        }
        else {
            this._animate = true;
        }
    },

    /**
     * Animate between the original and new content.
     *
     * @method morph
     * @param {Boolean} reverse: whether or not the widget should morph in the
            new content or return to the original content.
     */
    morph: function(reverse) {
        this._get_nodes(reverse);
        if (this._animate) {
            var self = this;
            this._create_morph_in();
            this._fade_out.on('end', function () {
                self._create_morph_in();
                self._fade_in.run();
                self._resize.run();
            });
            this._fade_out.run();
        }
        else {
            this.target_node.addClass('hidden');
            this.src_node.removeClass('hidden');
            this.fire('morphed');
        }
    },

    /**
     * Get the HTML nodes to morph between.
     *
     * @method _get_nodes
     * @param {Boolean} reverse: whether or not the returned nodes should morph
            in the new content or return to the original content.
     */
    _get_nodes: function(reverse) {
        if (reverse) {
            this.src_node = this.get('targetNode');
            this.target_node = this.get('srcNode');
        }
        else {
            this.src_node = this.get('srcNode');
            this.target_node = this.get('targetNode');
        }
    },

    /**
     * Create the animation for morphing out the original content.
     *
     * @method _create_morph_out
     */
    _create_morph_out: function() {
        this.target_height = this.target_node.getComputedStyle('height');
        this._fade_out = new Y.Anim({
            node: this.target_node,
            to: {opacity: 0},
            duration: 0.2,
            easing: 'easeOut'
            });
    },

    /**
     * Create the animation for morphing in the new content.
     *
     * @method _create_morph_in
     */
    _create_morph_in: function() {
        var self = this;
        this.target_node.addClass('hidden');
        this.src_node.setStyle('opacity', 0);
        this.src_node.removeClass('hidden');
        var src_height = this.src_node.getComputedStyle('height')
            .replace('px', '');
        this.src_node.setStyle('height', this.target_height);
        this._fade_in = new Y.Anim({
            node: this.src_node,
            to: {opacity: 1},
            duration: 1,
            easing: 'easeIn'
            });
        this._resize = new Y.Anim({
            node: this.src_node,
            to: {height: src_height},
            duration: 0.5,
            easing: 'easeOut'
            });
        this._resize.on('end', function () {
            self.src_node.setStyle('height', 'auto');
            self.fire('morphed');
        });
    }
});

module.Morph = Morph;

}, '0.1', {'requires': ['widget', 'node', 'anim']});
