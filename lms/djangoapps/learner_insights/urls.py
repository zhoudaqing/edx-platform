"""
Forum urls for the django_comment_client.
"""
from django.conf.urls import url, patterns

from .views import LearnerInsightsFragmentView

urlpatterns = patterns(
    '',
    url(r'^$', LearnerInsightsFragmentView.as_view(), name='learner_insights'),
    'learner_insights.views',
    url(
        r'learner_insights_fragment_view$',
        LearnerInsightsFragmentView.as_view(),
        name='learner_insights_fragment_view'
    ),
)
