/**
 * ContainerUnitAccessEditor is a view that allows the user to restrict access to a unit on the studio container page.
 */
define(['js/views/baseview', 'js/views/utils/xblock_utils', 'js/views/modals/course_outline_modals'],
    function(BaseView, XBlockViewUtils, CourseOutlineModalsFactory) {
        var ContainerUnitAccessEditor = BaseView.extend({
            events: {
                'click .xblock-access-edit': 'loadAccessEditor'
            },

            // takes XBlockInfo as a model

            initialize: function() {
                BaseView.prototype.initialize.call(this);
                this.template = this.loadTemplate('container-unit-access-editor');
            },

            render: function() {
                this.$el.append(this.template({
                    value: this.model.escape(this.fieldName),
                    fieldName: this.fieldName,
                    fieldDisplayName: this.fieldDisplayName
                }));
                return this;
            },

            loadAccessEditor: function(event) {
                event.preventDefault();
                var modal = CourseOutlineModalsFactory.getModal('edit', this.model, {
                    parentInfo: this.parentInfo,
                });
                if (modal) {
                    modal.show();
                }
            }
        });

        return ContainerUnitAccessEditor;
    }); // end define();
