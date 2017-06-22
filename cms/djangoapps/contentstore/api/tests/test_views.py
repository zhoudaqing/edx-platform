"""
Tests for the views
"""
import ddt
import os
import shutil
import tarfile
import tempfile
from datetime import datetime
from urllib import urlencode

from django.core.urlresolvers import reverse
from path import Path as path
from mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from lms.djangoapps.courseware.tests.factories import GlobalStaffFactory, StaffFactory
from student.tests.factories import UserFactory
from xmodule.modulestore.tests.django_utils import TEST_DATA_SPLIT_MODULESTORE, SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory


@ddt.ddt
class CourseImportViewTest(SharedModuleStoreTestCase, APITestCase):
    """
    Test importing courses via a RESTful API (POST method only)
    """
    MODULESTORE = TEST_DATA_SPLIT_MODULESTORE

    @classmethod
    def setUpClass(cls):
        super(CourseImportViewTest, cls).setUpClass()

        cls.course = CourseFactory.create(display_name='test course', run="Testing_course")
        cls.course_key = cls.course.id

        cls.restricted_course = CourseFactory.create(display_name='restricted test course', run="Restricted_course")
        cls.restricted_course_key = cls.restricted_course.id

        cls.password = 'test'
        cls.student = UserFactory(username='dummy', password=cls.password)
        cls.staff = StaffFactory(course_key=cls.course.id, password=cls.password)

        cls.content_dir = path(tempfile.mkdtemp())

        def touch(name):
            """ Equivalent to shell's 'touch'"""
            with file(name, 'a'):
                os.utime(name, None)

        # Create tar test files -----------------------------------------------
        # OK course:
        good_dir = tempfile.mkdtemp(dir=cls.content_dir)
        # test course being deeper down than top of tar file
        embedded_dir = os.path.join(good_dir, "grandparent", "parent")
        os.makedirs(os.path.join(embedded_dir, "course"))
        with open(os.path.join(embedded_dir, "course.xml"), "w+") as f:
            f.write('<course url_name="2013_Spring" org="EDx" course="0.00x"/>')

        with open(os.path.join(embedded_dir, "course", "2013_Spring.xml"), "w+") as f:
            f.write('<course></course>')

        cls.good_tar = os.path.join(cls.content_dir, "good.tar.gz")
        with tarfile.open(cls.good_tar, "w:gz") as gtar:
            gtar.add(good_dir)

        cls.namespaced_url = 'courses_api:course_import'

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.content_dir)
        cls.student.delete()
        cls.staff.delete()

    def setUp(self):
        super(CourseImportViewTest, self).setUp()

    def get_url(self, course_id=None):
        """
        Helper function to create the url
        """
        if(course_id is None):
            course_id = self.course_key
        base_url = reverse(
            self.namespaced_url,
            kwargs={
                'course_id': course_id
            }
        )
        query_string = ''
        return base_url + query_string

    def test_anonymous_import_fails(self):
        """
        Test that an anonymous user cannot access the API and an error is received.
        """
        with open(self.good_tar, 'rb') as fp:
            resp = self.client.post(self.get_url(), {'course_data': fp}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_import_fails(self):
        """
        Test that an student user cannot access the API and an error is received.
        """
        self.client.login(username=self.student.username, password=self.password)
        with open(self.good_tar, 'rb') as fp:
            resp = self.client.post(self.get_url(), {'course_data': fp}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_with_access_import_succeeds(self):
        """
        Test that an staff user can access the API and successfully upload a course
        """
        self.client.login(username=self.staff.username, password=self.password)
        with open(self.good_tar, 'rb') as fp:
            resp = self.client.post(self.get_url(), {'course_data': fp}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_staff_has_no_access_import_fails(self):
        """
        Test that an staff user can't access another course via the API
        """
        self.client.login(username=self.staff.username, password=self.password)
        with open(self.good_tar, 'rb') as fp:
            resp = self.client.post(self.get_url(self.restricted_course_key), {'course_data': fp}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_get_status_fails(self):
        """
        Test that an student user cannot access the API and an error is received.
        """
        self.client.login(username=self.student.username, password=self.password)
        resp = self.client.get(self.get_url(), {'task_id': '1234'})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_get_status_succeeds(self):
        """
        Test that an import followed by a get status results in success

        Note: This relies on the fact that we process imports synchronously during testing
        """
        self.client.login(username=self.staff.username, password=self.password)
        with open(self.good_tar, 'rb') as fp:
            resp = self.client.post(self.get_url(), {'course_data': fp}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.get(self.get_url(), {'task_id': resp.data['task_id']}, format='multipart')
        self.assertEqual(resp.data['state'], "Succeeded")  # @TODO Make this reference a constant
