"""
Platform plugins to support the course experience.

This includes any locally defined CourseTools.
"""

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from . import UNIFIED_COURSE_TAB_FLAG
from course_tools import CourseTool


class CourseUpdatesTool(CourseTool):
    """
    The course updates tool.
    """
    @classmethod
    def title(cls):
        """
        Returns the title of this tool.
        """
        return _('Updates')

    @classmethod
    def icon_classes(cls):
        """
        Returns icon classes needed to represent this tool.
        """
        return 'fa fa-newspaper-o'

    @classmethod
    def is_enabled(cls, course_key):
        """
        Returns true if this tool is enabled for the specified course key.
        """
        return UNIFIED_COURSE_TAB_FLAG.is_enabled(course_key)

    @classmethod
    def url(cls, course_key):
        """
        Returns the URL for this tool for the specified course key.
        """
        return reverse('openedx.course_experience.course_updates', args=[course_key])
