"""
Models for CourseTalk configurations
"""
from __future__ import unicode_literals

from config_models.models import ConfigurationModel
from django.db import models
from django.utils.translation import ugettext_lazy as _


class CourseReviewsToolConfiguration(ConfigurationModel):
    """
    This model represents enabling and disabling configuration
    for the course reviews tool. If the setting is enabled,
    the tool will be enabled on the the course reviews page
    and the course about page.
    """
    platform_key = models.fields.CharField(
        max_length=50,
        help_text=_(
            "The platform key associates CourseTalk widgets with your platform. "
            "Generally, it is the domain name for your platform. For example, "
            "if your platform is http://edx.org, the platform key is \"edx\"."
        )
    )

    reviews_provider_fragment = models.fields.CharField(
        max_length=50,
        help_text=_(
            "The reviews provider fragment points to the fragment template that renders "
            "wherever the reviews tool shows up. The fragments all lie in the "
            "openedx/features/course_experience/templates/course_experience"
            "/course_reviews_modules directory. For example, to embed the coursetalk "
            "fragment, the reviews provider fragment is \"coursetalk-reviews-fragment.html\". "
        )
    )

    @classmethod
    def get_platform_key(cls):
        """
        Return platform_key for current active configuration.
        If current configuration is not enabled - return empty string

        :return: Platform key
        :rtype: unicode
        """
        return cls.current().platform_key if cls.is_enabled() else ''

    @classmethod
    def get_reviews_provider_fragment(cls):
        """
        Return reviews_provider_fragment for current active configuration.
        If current configuration is not enabled - return empty string

        :return: Reviews Provider Fragment
        :rtype: unicode
        """
        return cls.current().reviews_provider_fragment if cls.is_enabled() else ''

    def __unicode__(self):
        return 'CourseReviewsToolConfiguration - {0}'.format(self.enabled)
