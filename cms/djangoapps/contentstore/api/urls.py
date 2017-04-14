""" Grades API URLs. """
from django.conf import settings
from django.conf.urls import (
    patterns,
    url,
)

from cms.djangoapps.contentstore.api import views

urlpatterns = patterns(
    '',
    url(
        r'^v0/courses/{course_id}/import/$'.format(
            course_id=settings.COURSE_ID_PATTERN,
        ),
        views.CourseImportView.as_view(), name='course_import'
    ),
)
