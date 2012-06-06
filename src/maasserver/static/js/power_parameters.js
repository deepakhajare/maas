/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Power parameters utilities.
 *
 * @module Y.maas.power_parameter
 */

// TODO: Replace "power_parameters" with module name throughout.
YUI.add('maas.power_parameters', function(Y) {

Y.log('loading maas.power_parameters');
var module = Y.namespace('maas.power_parameters');

// Only used to mockup io in tests.
module._io = new Y.IO();

var DynamicWidget;

/**
 * A widget view class to display a set of Nodes (Y.maas.node.Node).
 *
 */
DynamicWidget = function() {
    DynamicWidget.superclass.constructor.apply(this, arguments);
};

DynamicWidget.NAME = 'dynamic-widget';

Y.extend(DynamicWidget, Y.Widget, {

   /**
    * Initialize the widget.
    * - cfg.srcNode is the the node which will be updated when the
    *   selected value of the 'driver node' will change.
    * - cfg.driverNode is the node that must contain a 'select' element.  When
    *   the selected element will change, the srcNode HTML will be
    *   updated.
    * - cfg.driverEnum is an dictionary which contains all the possible values
    *   of the driverNode's select element.
    * - cfg.templatePrefix is the prefix string which will be used to fetch
    *   all the templates for each possible value of driverEnum.
    *
    * @method initializer
    */
    initializer: function(cfg) {
        this.driverNode = cfg.driverNode;
        this.driverEnum = cfg.driverEnum;
        this.templatePrefix = cfg.templatePrefix;
        this.initTemplates();
        this.setVisibility();
    },

   /**
    * Create a dictionary containing the templates for all the possible
    * values from 'this.driverEnum'.
    *
    * @method initTemplates
    */
    initTemplates: function() {
        this.templates = {};
        var driverValue;
        for (driverValue in this.driverEnum) {
            if (this.driverEnum.hasOwnProperty(driverValue)) {
                var type = this.driverEnum[driverValue];
                var template = Y.one(
                    this.templatePrefix + type).getContent();
                this.templates[type] = template;
            }
        }
    },

   /**
    * Make 'srcNode' as hidden if the value of the 'driverNode' is the empty
    * string and as not hidden if it's not the case.
    *
    * @method setVisibility
    */
    setVisibility: function() {
        var driverValue = Y.one(this.driverNode).one('select').get('value');
        if (driverValue === '') {
            this.get('srcNode').addClass('hidden');
        }
        else {
            this.get('srcNode').removeClass('hidden');
        }
    },

   /**
    * React to a new value of the driver node: update the HTML of
    * 'srcNode'.
    *
    * @method switchTo
    */
    switchTo: function(newDriverValue) {
        // Remove old fieldset if any.
        var srcNode = this.get('srcNode');
        srcNode.all('fieldset').remove();
        // Insert the template fragment corresponding to the new value
        // of the driver in 'srcNode'.
        var old_innerHTML = srcNode.get('innerHTML');
        srcNode.set(
            'innerHTML', old_innerHTML + this.templates[newDriverValue]);
        this.setVisibility();
    },

   /**
    * Bind the widget's events: hook up the driver's 'change' event to
    * 'this.switchTo(newValue)'.
    *
    * @method bindUI
    */
    bindUI: function() {
        var self = this;
        Y.one(this.driverNode).one('select').on('change', function(e) {
            var newDriverValue = e.currentTarget.get('value');
            self.switchTo(newDriverValue);
        });
    }

});

module.DynamicWidget = DynamicWidget;

}, '0.1', {'requires': ['widget', 'io', 'maas.enums']}
);
