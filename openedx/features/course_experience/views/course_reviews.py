"""
Fragment for rendering the course reviews panel
"""
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from opaque_keys.edx.keys import CourseKey
from web_fragments.fragment import Fragment

from courseware.courses import get_course_with_access
from lms.djangoapps.courseware.views.views import CourseTabView
from openedx.core.djangoapps.coursetalk import models
from openedx.core.djangoapps.coursetalk.helpers import get_coursetalk_course_key
from openedx.core.djangoapps.plugin_api.views import EdxFragmentView
from openedx.features.course_experience import default_course_url_name


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
        Render the course reviews fragment.
        """

        course_key = CourseKey.from_string(course_id)
        course = get_course_with_access(request.user, 'load', course_key, check_if_enrolled=True)
        course_url_name = default_course_url_name(request)
        course_url = reverse(course_url_name, kwargs={'course_id': unicode(course.id)})

        context = {
            'course': course,
            'course_url': course_url,
            'course_review_key': get_coursetalk_course_key(course_key),
            'platform_key': models.CourseTalkWidgetConfiguration.get_platform_key()
        }

        html = render_to_string('course_experience/course-reviews-fragment.html', context)
        return Fragment(html)
