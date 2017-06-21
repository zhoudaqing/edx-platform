"""
Support for course tool plugins.
"""
from openedx.core.lib.api.plugins import PluginManager

# Stevedore extension point namespace
COURSE_TOOLS_NAMESPACE = 'openedx.course_tool'


class CourseTool(object):
    """
    This is an optional base class for Course Tool plugins.

    Plugin implementations can choose to subclass CourseTool to get
    useful default behavior, but it is not a requirement. A course tool
    plugin should define the following class methods:

     * is_enabled(cls, course_key):
       Returns true if this tool is enabled for the specified course key.
     * title(cls):
       Returns the title of this tool.
     * icon_classes(cls):
       Returns the icon classes needed to represent this tool.
     * url(cls, course_key):
       Returns the URL for this tool for the specified course key.
    """

    @classmethod
    def is_enabled(cls, course_key):
        """
        Returns true if this tool is enabled for the specified course key.
        """
        return True


class CourseToolsPluginManager(PluginManager):
    """
    Manager for all of the course tools that have been made available.

    Course tool implementation can subclass `CourseTool` or can implement
    the required class methods themselves.
    """
    NAMESPACE = COURSE_TOOLS_NAMESPACE

    @classmethod
    def get_course_tools(cls):
        """
        Returns the list of available course tools in their canonical order.
        """
        course_tools = cls.get_available_plugins().values()
        course_tools.sort(key=lambda course_tool: course_tool.title())
        return course_tools
