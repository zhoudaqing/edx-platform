"""
Views handling read (GET) requests for the Learner Insights tab.
"""

from django.conf import settings
from django.utils.translation import ugettext_noop

from courseware.tabs import EnrolledTab
import django_comment_client.utils as utils
from xmodule.tabs import TabFragmentViewMixin


class LearnerInsightsTab(TabFragmentViewMixin, EnrolledTab):
    """
    A tab for the Learner Insights.
    """

    type = 'learner_insights'
    title = ugettext_noop('Learner Insights')
    priority = None
    view_name = 'learner_insights.views.learner_insights'
    fragment_view_name = 'learner_insights.views.LearnerInsightsFragmentView'
    body_class = 'learner-insights'
    online_help_token = 'learner_insights'

    @classmethod
    def is_enabled(cls, course, user=None):
        return True
