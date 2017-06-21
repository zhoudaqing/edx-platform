/**
 * XBlockStringFieldEditor is a view that allows the user to inline edit an XBlock string field.
 * Clicking on the field value will hide the text and replace it with an input to allow the user
 * to change the value. Once the user leaves the field, a request will be sent to update the
 * XBlock field's value if it has been changed. If the user presses Escape, then any changes will
 * be removed and the input hidden again.
 */
define(['js/views/baseview', 'js/views/utils/xblock_utils', 'js/views/modals/course_outline_modals'],
    function(BaseView, XBlockViewUtils, CourseOutlineModalsFactory) {
        var XBlockUnitAccessEditor = BaseView.extend({
            events: {
                'click .xblock-access-edit': 'loadAccessEditor'
            },

            // takes XBlockInfo as a model

            initialize: function() {
                BaseView.prototype.initialize.call(this);
                this.template = this.loadTemplate('xblock-unit-access-editor');
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

        return XBlockUnitAccessEditor;
    }); // end define();
