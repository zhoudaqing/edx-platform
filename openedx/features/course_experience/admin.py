"""Manage course reviews tool configuration. """
from config_models.admin import ConfigurationModelAdmin
from django.contrib import admin

from openedx.features.course_experience.models import CourseReviewsToolConfiguration

admin.site.register(CourseReviewsToolConfiguration, ConfigurationModelAdmin)
