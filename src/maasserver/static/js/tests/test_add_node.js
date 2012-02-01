/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI({ useBrowserConsole: true }).use(
    'node-event-simulate', 'test', 'maas.add_node', function(Y){

    var namespace = Y.maas.add_node;
    var suite = new Y.Test.Suite("maas.add_node Tests");

    suite.add(new Y.Test.Case({
        name: 'test-add-node-widget-singleton',

        setUp: function() {
            // Silence io.
            var mockXhr = Y.Mock();
            Y.Mock.expect(mockXhr, {
                method: 'io',
                args: [MAAS_config.uris.nodes_handler, Y.Mock.Value.Any]
            });
            namespace._exchange = mockXhr;
        },

        testSingletonCreation: function() {
            // namespace._add_node_singleton is originally null.
            Y.Assert.isNull(namespace._add_node_singleton);
            namespace.showAddNodeWidget();
            // namespace._add_node_singleton is populated after the call to
            // namespace.showAddNodeWidget.
            Y.Assert.isNotNull(namespace._add_node_singleton);
        },

        testSingletonReCreation: function() {
            namespace.showAddNodeWidget();
            var overlay = namespace._add_node_singleton;

            // Make sure that a second call to showAddNodeWidget destroys
            // the old widget and creates a new one.
            var destroyed = false;
            overlay.on("destroy", function(){
                destroyed = true;
            });
            namespace.showAddNodeWidget();
            Y.Assert.isTrue(destroyed);
            Y.Assert.isNotNull(namespace._add_node_singleton);
        }
    }));

    suite.add(new Y.Test.Case({
        name: 'test-add-node-widget-add-node',

        testAddNodeAPICall: function() {
            var mockXhr = Y.Mock();
            Y.Mock.expect(mockXhr, {
                method: 'io',
                args: [MAAS_config.uris.nodes_handler, Y.Mock.Value.Any]
            });
            namespace._exchange = mockXhr;
            namespace.showAddNodeWidget();
            var overlay = namespace._add_node_singleton;
            overlay.get('srcNode').one('#id_hostname').set('value', 'host');
            var button = overlay.get('srcNode').one('button');
            button.simulate('click');
            Y.Mock.verify(mockXhr);
        },

        testNodeidPopulation: function() {
            var mockXhr = new Y.Base();
            mockXhr.io = function(url, cfg) {
                cfg.on.success(
                   3, {response:"{\"system_id\": 3}"});
            };
            namespace._exchange = mockXhr;
            namespace.showAddNodeWidget();
            var overlay = namespace._add_node_singleton;
            overlay.get('srcNode').one('#id_hostname').set('value', 'host');
            var button = overlay.get('srcNode').one('button');

            var fired = false;
            namespace.AddNodeDispatcher.on(
                namespace.NODE_ADDED_EVENT, function(e, node){
                Y.Assert.areEqual(3, node.system_id);
                fired = true;
            });
            button.simulate('click');
            Y.Assert.isTrue(fired);
        }

    }));

    Y.Test.Runner.add(suite);
    Y.Test.Runner.run();

});
