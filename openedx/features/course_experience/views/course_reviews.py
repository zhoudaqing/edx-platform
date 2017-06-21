"""
Fragment for rendering the course reviews panel
"""
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from opaque_keys.edx.keys import CourseKey
from web_fragments.fragment import Fragment

from courseware.courses import get_course_with_access
from lms.djangoapps.courseware.views.views import CourseTabView
from openedx.core.djangoapps.plugin_api.views import EdxFragmentView
from openedx.features.course_experience import default_course_url_name
from openedx.features.coursetalk import models


class CourseReviewsView(CourseTabView):
    """
    The course reviews page.
    """

    @method_decorator(login_required)
    @method_decorator(cache_control(no_cache=True, no_store=True, must_revalidate=True))
    def get(self, request, course_id, **kwargs):
        """
        Displays the reviews page for the specified course.
        """
        return super(CourseReviewsView, self).get(request, course_id, 'courseware', **kwargs)

    def render_to_fragment(self, request, course=None, tab=None, **kwargs):
        course_id = unicode(course.id)
        reviews_fragment_view = CourseReviewsFragmentView()
        return reviews_fragment_view.render_to_fragment(request, course_id=course_id, **kwargs)


class CourseReviewsFragmentView(EdxFragmentView):
    """
    A fragment to display course reviews.
    """
    def render_to_fragment(self, request, course_id=None, **kwargs):
        """
        Fragment to render the course reviews fragment. The provider
        of the reviews can be set in the configuration file under the
        variable COURSE_REVIEWS_PROVIDER_TEMPLATE. This setting points 
        directly to the particular sub-fragment that should be used.
        
        For example, to use CourseTalk as a provider, one would set:
        settings.FEATURES.get('COURSE_REVIEWS_PROVIDER_TEMPLATE') 
            = 'coursetalk-reviews-fragment.html'
            
        """

        course_key = CourseKey.from_string(course_id)
        course = get_course_with_access(request.user, 'load', course_key, check_if_enrolled=True)
        course_url_name = default_course_url_name(request)
        course_url = reverse(course_url_name, kwargs={'course_id': unicode(course.id)})

        # Create the fragment
        course_reviews_provider_fragment = CourseReviewsModuleFragmentView().render_to_fragment(
                request,
                course=course,
                **kwargs
            )

        context = {
            'course': course,
            'course_url': course_url,
            'course_reviews_provider_fragment': course_reviews_provider_fragment
        }

        html = render_to_string('course_experience/course-reviews-fragment.html', context)
        return Fragment(html)


class CourseReviewsModuleFragmentView(EdxFragmentView):
    """
    A fragment to display the course reviews module as specified by 
    the configured template.
    """

    def render_to_fragment(self, request, course=None, **kwargs):
        """
        Renders the configured template as a module.
        """
        # Grab the fragment type from the configuration file
        course_reviews_fragment_provider_template = \
            settings.FEATURES.get('COURSE_REVIEWS_TOOL_PROVIDER_FRAGMENT_NAME')

        if course_reviews_fragment_provider_template is None:
            return None

        # Create the fragment from the given template
        provider_reviews_template = 'course_experience/course_reviews_modules/%s' \
                                    % course_reviews_fragment_provider_template

        context = {
            'course': course,
            'platform_key': models.CourseTalkWidgetConfiguration.get_platform_key()
        }

        html = render_to_string(provider_reviews_template, context)
        return Fragment(html)
