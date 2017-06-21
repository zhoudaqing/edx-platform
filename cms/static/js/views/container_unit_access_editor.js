/**
 * ContainerUnitAccessEditor is a view that allows the user to inline edit an XBlock's unit access settings.
 * Clicking on the settings gear will bring up a modal that allows users to restrict access to the entire unit.
 */
define(['js/views/baseview', 'js/views/utils/xblock_utils', 'js/views/modals/course_outline_modals',
        'js/views/course_outline'],
    function(BaseView, XBlockViewUtils, UnitAccessEditor) {
        var ContainerUnitAccessEditor = BaseView.extend({
            events: {
                'click .xblock-container-access-edit': 'UnitAccessEditor',
            },

            // takes XBlockInfo as a model

            initialize: function () {
                BaseView.prototype.initialize.call(this);
                this.template = this.loadTemplate('container-unit-access-editor');
            },

            render: function () {
                return this;
            },
        });


        return ContainerUnitAccessEditor;
    }); // end define();
