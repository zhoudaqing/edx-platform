"""
Support for course tool plugins.
"""
from openedx.core.lib.api.plugins import PluginManager

# Stevedore extension point namespaces
COURSE_TOOLS_NAMESPACE = 'openedx.course_tool'


class CourseToolsPluginManager(PluginManager):
    """
    Manager for all of the course tools that have been made available.

    All course tabs should implement `CourseTab`.
    """
    NAMESPACE = COURSE_TOOLS_NAMESPACE

    @classmethod
    def get_course_tools(cls):
        """
        Returns the list of available course tools in their canonical order.
        """
        def compare_tools(first_tool, second_tool):
            """
            Compares two course tools, for use in sorting.
            """
            first_tool = first_tool.title()
            second_tool = second_tool.title()
            if first_tool < second_tool:
                return -1
            elif first_tool == second_tool:
                return 0
            else:
                return 1
        course_tools = cls.get_available_plugins().values()
        course_tools.sort(cmp=compare_tools)
        return course_tools
