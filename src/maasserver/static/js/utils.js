/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * MaaS utilities.
 *
 * @module Y.mass.utils
 */

YUI.add('maas.utils', function(Y) {

Y.log('loading mass.utils');
var module = Y.namespace('maas.utils');

// Only used to mockup io in tests.
module._io = new Y.IO();

var FLASH_DURATION = 1;

module.FLASH_DURATION = FLASH_DURATION;

var base_flash = function(obj, from_color) {
    old_bg_color = Y.one(obj).getStyle('backgroundColor');

    return new Y.Anim({
        node: obj,
        duration: FLASH_DURATION,
        from: { backgroundColor: from_color},
        to: { backgroundColor: old_bg_color}
    });
};

module.base_flash = base_flash;

/**
 * @function green_flash
 * @description A green flash and fade.
 * @return Y.Anim instance
 */

var green_flash = function(obj) {
    return base_flash(obj, '#00FF00');
};

module.green_flash = green_flash;


/**
 * @function red_flash
 * @description A red flash and fade, used to indicate errors.
 * @return Y.Anim instance
 */
var red_flash = function(obj) {
    return base_flash(obj, '#FF0000');
};

module.red_flash = red_flash;


var TitleEditWidget = function() {
    TitleEditWidget.superclass.constructor.apply(this, arguments);
};

TitleEditWidget.NAME = 'title-edit-widget';

TitleEditWidget.TITLE_SUFFIX = ' MaaS';

TitleEditWidget.ATTRS = {

   /**
    * MaaS's title input node.
    *
    * @attribute input
    * @type Node
    */
    input: {
        getter: function() {
            return this.get('srcNode').one('input');
        }
    },

   /**
    * MaaS's title.
    *
    * @attribute title
    * @type string
    */
    title: {
        getter: function() {
            return this.get('input').get('value');
        },
        setter: function(value) {
            this.get('input').set('value', value);
        }
    }

};


Y.extend(TitleEditWidget, Y.Widget, {

   initializer: function() {
        // A boolean indicating whether or not the user is currently editing
        // the title.
        this._editing = false;
    },

   /**
    * Does the input contain the suffix?
    *
    * @method hasSuffix
    */
    hasSuffix: function() {
        var title = this.get('title');
        var suffix = title.substring(
            title.length - TitleEditWidget.TITLE_SUFFIX.length, title.length);
        return (suffix === TitleEditWidget.TITLE_SUFFIX);
    },

   /**
    * Add the suffix to the input's content.
    *
    * @method addSuffix
    */
    addSuffix: function() {
        this.set('title', this.get('title') + TitleEditWidget.TITLE_SUFFIX);
    },

   /**
    * Remove the suffix to the input's content.
    *
    * @method removeSuffix
    */
    removeSuffix: function() {
        if (this.hasSuffix()) {
            var title = this.get('title');
            var new_title = title.substring(
                0, title.length - TitleEditWidget.TITLE_SUFFIX.length);
            this.set('title', new_title);
        }
        else {
            Y.log("Error: suffix not present in title.");
        }
    },

    bindUI: function() {
        var self = this;
        var input = this.get('input');
        // Click on the input node: start title edition.
        input.on('click', function(e) {
            e.preventDefault();
            self.titleEditStart(e.rangeOffset);
        });
        // Change is fired when the input text as changed and the focus is now
        // set another element.
        input.on('change', function(e) {
            e.preventDefault();
            self.titleEditEnd();
        });
        // Form submitted (Enter pressed in the input Node).
        this.get('srcNode').on('submit', function(e) {
            e.preventDefault();
            self.titleEditEnd();
        });
    },

   /**
    * Start of title edition: remove suffix and focus.
    *
    * @method titleEditStart
    */
    titleEditStart: function(rangeOffset) {
        if (!this._editing) {
            this._editing = true;
            this.removeSuffix();
            this.get('input').focus();
        }
    },

   /**
    * End of title edition: add suffix, persist the title and blur.
    *
    * @method titleEditEnd
    */
    titleEditEnd: function() {
        if (this._editing) {
            this.titlePersist();
            this.addSuffix();
            this._editing = false;
            this.get('input').blur();
        }
    },

   /**
    * Call the API to make the title persist.
    *
    * @method titlePersist
    */
    titlePersist: function() {
        var title = this.get('title');
        var input = this.get('input');
        var cfg = {
            method: 'POST',
            sync: false,
            data: Y.QueryString.stringify({
                op: 'set_config',
                name: 'maas_name',
                value: title
                }),
            on: {
                success: function(id, out) {
                    green_flash(input).run();
                },
                failure: function(id, out) {
                    red_flash(input).run();
                    Y.log(out);
                }
            }
        };
        var request = module._io.send(
            MaaS_config.uris.maas_handler, cfg);
    }
});

module.TitleEditWidget = TitleEditWidget;

}, '0.1', {'requires': ['base', 'widget', 'io', 'anim']}
);
