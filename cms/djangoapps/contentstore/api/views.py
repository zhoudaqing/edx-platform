""" API v0 views. """
import base64
import logging
import os

from path import Path as path
from six import text_type

from django.conf import settings
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt

from django.core.files import File
from django.http import Http404
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from student.auth import has_course_author_access

from contentstore.storage import course_import_export_storage
from contentstore.tasks import import_olx
from openedx.core.lib.api.view_utils import DeveloperErrorViewMixin, view_auth_classes

log = logging.getLogger(__name__)


@view_auth_classes()
class CourseImportExportViewMixin(DeveloperErrorViewMixin):
    """
    Mixin class for course import/export related views.
    """
    def perform_authentication(self, request):
        """
        Ensures that the user is authenticated (e.g. not an AnonymousUser), unless DEBUG mode is enabled.
        """
        super(CourseImportExportViewMixin, self).perform_authentication(request)
        if request.user.is_anonymous():
            raise AuthenticationFailed

class CourseImportView(CourseImportExportViewMixin, GenericAPIView):
    """
    **Use Case**

        * Start an asynchronous task to import a course from a .tar.gz file into the specified course ID

    **Example Request**

        POST /api/courses/v0/import/course-v1:edX+DemoX+Demo_Course/

    **POST Parameters**

        A POST request may include the following parameters.

        * course_id: (required) A string representation of a Course ID.
        * course_data: (required) The course .tar.gz file to import

    **POST Response Values**

        If the import task is started successfully
        is successful, an HTTP 200 "OK" response is returned.

        The HTTP 200 response has the following values.

        * task_id: UUID of the created task, usable for checking status


    **Example POST Response**

        [{
            "task_id": "4b357bb3-2a1e-441d-9f6c-2210cf76606f"
        }]

    """
    def post(self, request, course_id):
        """
        Kicks off an asynchronous course import and returns an ID to be used to check
        the task's status

        Args:
            request (Request): Django request object.
            course_id (string): URI element specifying the course location.

        Return:
            The UUID of the task to check status on later
        """

        courselike_key = CourseKey.from_string(course_id)
        if not has_course_author_access(request.user, courselike_key):
             return self.make_error_response(
                 status_code=status.HTTP_403_FORBIDDEN,
                 developer_message='The user requested does not have the required permissions.',
                 error_code='user_mismatch'
             )
        try:
            filename = request.FILES['course_data'].name
            if not filename.endswith('.tar.gz'):
                return self.make_error_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    developer_message='We only support uploading a .tar.gz file.',
                    error_code='user_mismatch'
                )
            course_dir = path(settings.GITHUB_REPO_ROOT) / base64.urlsafe_b64encode(repr(courselike_key))
            temp_filepath = course_dir / filename
            if not course_dir.isdir():  # pylint: disable=no-value-for-parameter
                os.mkdir(course_dir)

            log.debug('importing course to {0}'.format(temp_filepath))
            with open(temp_filepath, "wb+") as temp_file:
                for chunk in request.FILES['course_data'].chunks():
                    temp_file.write(chunk)

            log.info("Course import %s: Upload complete", courselike_key)
            with open(temp_filepath, 'rb') as local_file:
                django_file = File(local_file)
                storage_path = course_import_export_storage.save(u'olx_import/' + filename, django_file)

            async_result = import_olx.delay(
                request.user.id, text_type(courselike_key), storage_path, filename, request.LANGUAGE_CODE)
            return Response([{
                'task_id': async_result.id
            }])
        except Exception as e:
            return self.make_error_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                developer_message=str(e),
                error_code='internal_error'
            )
