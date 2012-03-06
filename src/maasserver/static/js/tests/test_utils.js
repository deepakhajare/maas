/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI({ useBrowserConsole: true }).add('maas.utils.tests', function(Y) {

Y.log('loading mass.utils.tests');
var namespace = Y.namespace('maas.utils.tests');

var module = Y.maas.utils;
var suite = new Y.Test.Suite("maas.utils Tests");

var title_form = Y.one('#title-form').getContent();

suite.add(new Y.maas.testing.TestCase({
    name: 'test-utils-flash',

    createNodeWithBaseColor: function(base_color) {
        var node = Y.Node.create('<span />')
            .set('text', "sample text");
        node.setStyle('backgroundColor', base_color);
        Y.one('#placeholder').empty().append(node);
        return node;
    },

    assertAnimRestoresBackground: function(anim, node, base_color) {
        var self = this;
        anim.on("end", function(){
            self.resume(function(){
                Y.Assert.areEqual(
                    base_color, node.getStyle('backgroundColor'));
            });
        });
        anim.run();
        // Make sure we wait long enough (duration is in seconds, wait uses
        // milliseconds (!)).
        this.wait(module.FLASH_DURATION*1000*1.5);
    },

    test_base_flash_restores_background_color: function() {
        var base_color = 'rgb(12, 11, 12)';
        var from_color = 'rgb(122, 211, 142)';
        var node = this.createNodeWithBaseColor(base_color);
        var anim = module.base_flash(node, from_color);
        this.assertAnimRestoresBackground(anim, node, base_color);
    },

    test_red_flash_restores_background_color: function() {
        var base_color = 'rgb(12, 11, 12)';
        var node = this.createNodeWithBaseColor(base_color);
        var anim = module.red_flash(node);
        this.assertAnimRestoresBackground(anim, node, base_color);
    },

    test_green_flash_restores_background_color: function() {
        var base_color = 'rgb(12, 11, 12)';
        var node = this.createNodeWithBaseColor(base_color);
        var anim = module.green_flash(node);
        this.assertAnimRestoresBackground(anim, node, base_color);
    }

}));


suite.add(new Y.maas.testing.TestCase({
    name: 'test-utils-titleeditwidget',

    setUp: function() {
        Y.one('#placeholder').empty().append(Y.Node.create(title_form));
    },

    createWidget: function() {
        var widget = new module.TitleEditWidget({srcNode: '#placeholder'});
        widget.render();
        return widget;
    },

    test_getInput_returns_input: function() {
        var widget = this.createWidget();
        input = widget.get('srcNode').one('input');
        Y.Assert.areEqual(input, widget.get('input'));
    },

    test_getTitle_returns_title: function() {
        var widget = this.createWidget();
        widget.get('srcNode').one('input').set('value', "Test value");
        Y.Assert.areEqual("Test value", widget.get('title'));
    },

    test_setTitle_changes_title: function() {
        var widget = this.createWidget();
        widget.set('title', "Another value");
        Y.Assert.areEqual(
            "Another value",
            widget.get('srcNode').one('input').get('value'));
    },

    test_hasSuffix_returns_true_if_suffix: function() {
        var widget = this.createWidget();
        widget.set('title', "Sample Title MaaS");
        Y.Assert.isTrue(widget.hasSuffix());
    },

    test_hasSuffix_returns_false_if_not_suffix: function() {
        var widget = this.createWidget();
        widget.set('title', "Sample Title");
        Y.Assert.isFalse(widget.hasSuffix());
    },

    test_removeSuffix_removes_suffix: function() {
        var widget = this.createWidget();
        widget.set('title', "Sample Title MaaS");
        widget.removeSuffix();
        Y.Assert.areEqual(
            "Sample Title", widget.get('title'));
    },

    test_removeSuffix_doesnothing_if_suffix_not_present: function() {
        var widget = this.createWidget();
        widget.set('title', "Sample Title");
        widget.removeSuffix();
        Y.Assert.areEqual(
            "Sample Title", widget.get('title'));
    },

    test_addSuffix_add_suffix: function() {
        var widget = this.createWidget();
        widget.set('title', "Sample Title");
        widget.addSuffix();
        Y.Assert.areEqual(
            "Sample Title MaaS", widget.get('title'));
    },

    test_titleEditStart_starts_editing: function() {
        var widget = this.createWidget();
        widget._editing = false;
        widget.set('title', "Sample Title MaaS");
        widget.titleEditStart();
        Y.Assert.isTrue(widget._editing);
        Y.Assert.areEqual(
            "Sample Title", widget.get('title'));
    },

    test_titleEditStart_does_nothing_if_already_editing: function() {
        var widget = this.createWidget();
        widget._editing = true;
        widget.set('title', "Sample Title MaaS");
        widget.titleEditStart();
        Y.Assert.isTrue(widget._editing);
        Y.Assert.areEqual(
            "Sample Title MaaS", widget.get('title'));
    },

    test_titleEditEnd_stops_editing_if_currently_editing: function() {
        var widget = this.createWidget();
        widget._editing = true;
        widget.set('title', "SampleTitle");
        var mockXhr = new Y.Base();
        var fired = false;
        mockXhr.send = function(url, cfg) {
            fired = true;
            Y.Assert.areEqual(MaaS_config.uris.maas_handler, url);
            Y.Assert.areEqual(
                "op=set_config&name=maas_name&value=SampleTitle",
                cfg.data);
        };
        this.mockIO(mockXhr, module);
        widget.titleEditEnd();
        Y.Assert.isTrue(fired);
        Y.Assert.isFalse(widget._editing);
        Y.Assert.areEqual(
            "SampleTitle MaaS", widget.get('title'));
    },

    test_titleEditEnd_does_nothing_if_not_editing: function() {
        var widget = this.createWidget();
        widget._editing = false;
        widget.set('title', "Sample Title");
        this.mockIOFired(module);
        widget.titleEditEnd();
        Y.Assert.isFalse(this.fired);
        Y.Assert.isFalse(widget._editing);
        Y.Assert.areEqual(
            "Sample Title", widget.get('title'));
    },

    test_input_click_starts_edition: function() {
        var widget = this.createWidget();
        widget._editing = false;
        this.mockIOFired(module); // Silent io.
        var input = widget.get('srcNode').one('input');
        input.simulate('click');
        Y.Assert.isTrue(widget._editing);
    },

    test_input_onchange_stops_editing: function() {
        var widget = this.createWidget();
        widget._editing = true;
        this.mockIOFired(module); // Silent io.
        var input = widget.get('srcNode').one('input');
        input.simulate('change');
        Y.Assert.isFalse(widget._editing);
    },

    test_input_enter_pressed_stops_editing: function() {
        var widget = this.createWidget();
        widget._editing = true;
        this.mockIOFired(module); // Silent io.
        var input = widget.get('srcNode').one('input');
        // Simulate 'Enter' being pressed.
        input.simulate("keypress", { keyCode: 13 });
        Y.Assert.isFalse(widget._editing);
    },

    xtestDeleteTokenCall: function() {
        // A click on the delete link calls the API to delete a token.
        var mockXhr = new Y.Base();
        var fired = false;
        mockXhr.send = function(url, cfg) {
            fired = true;
            Y.Assert.areEqual(MaaS_config.uris.account_handler, url);
            Y.Assert.areEqual(
                "op=delete_authorisation_token&token_key=tokenkey1",
                cfg.data);
        };
        this.mockIO(mockXhr, module);
        var widget = this.createWidget();
        this.addCleanup(function() { widget.destroy(); });
        widget.render();
        var link = widget.get('srcNode').one('.delete-link');
        link.simulate('click');
        Y.Assert.isTrue(fired);
    }


}));

namespace.suite = suite;

}, '0.1', {'requires': [
    'node', 'test', 'maas.testing', 'maas.utils', 'node-event-simulate']}
);
