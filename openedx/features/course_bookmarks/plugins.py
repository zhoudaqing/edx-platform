"""
Platform plugins to support course bookmarks.
"""

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _


class CourseBookmarksTool(object):
    """
    The course bookmarks tool.
    """
    @classmethod
    def title(cls):
        """
        Returns the title of this tool.
        """
        return _('Bookmarks')

    @classmethod
    def icon_classes(cls):
        """
        Returns the icon classes to represent this tool.
        """
        return 'icon fa fa-bookmark'

    @classmethod
    def is_enabled(cls, course_key):
        """
        Returns true if this tool is enabled for the specified course key.
        """
        return True

    @classmethod
    def url(cls, course_key):
        """
        Returns the title of this tool.
        """
        return reverse('openedx.course_bookmarks.home', args=[course_key])
