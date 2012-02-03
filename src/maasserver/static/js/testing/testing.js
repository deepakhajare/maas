/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI().add('maas.testing', function(Y) {

Y.log('loading mass.testing');

var module = Y.namespace('maas.testing');

module.TestCase = Y.Base.create('ioMockableTestCase', Y.Test.Case, [], {

   /**
    * Mock the '_io' field of the provided module.  This assumes that
    * the module has a internal reference to its io module named '_io'
    * and that all its io is done via module._io.io(...).
    *
    * @method mockIO
    * @param mock the mock object that should replace the module's io
    * @param module the module to monkey patch
    */
    mockIO: function(mock, module) {
        this.old_io = module._io;
        this.module = module;
        this.module._io = mock;
    },

    tearDown: function() {
        if (Y.Lang.isValue(this.old_io)) {
            this.module._io = this.old_io;
        }
        if (Y.Lang.isValue(this.handlers)) {
            var handler;
            while(handler=this.handlers.pop()) {
                handler.detach();
            }
        }
    },

    mockSuccess: function(response, module) {
        var mockXhr = {};
        mockXhr.io = function(url, cfg) {
           var out = {};
           out.response = response;
           cfg.on.success('4', out);
        };
        this.mockIO(mockXhr, module);
    },

   /**
    * Register a method to be fired when the event 'name' is triggered on
    * 'source'.  The handle will be cleaned up when the test finishes.
    *
    * @method registerListener
    * @param source the source of the event
    * @param name the name of the event to listen to
    * @param method the method to run
    * @param context the context in which the method should be run
    */
    registerListener: function(source, name, method, context) {
        var handle = source.on(name, method, context);
        this.cleanupHandler(handle);
        return handle;
    },

    cleanupHandler: function(handler) {
        if (!Y.Lang.isValue(this.handlers)) {
            this.handlers = [];
        }
        this.handlers.push(handler);
    }

});

}, '0.1', {'requires': ['test', 'base']}
);
