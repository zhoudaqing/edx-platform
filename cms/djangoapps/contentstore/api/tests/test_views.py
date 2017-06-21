"""
Tests for the views
"""
from datetime import datetime
from urllib import urlencode

import ddt
from django.core.urlresolvers import reverse
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
    Test the CourseImportView class for providing a RESTful API to import courses
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
        cls.other_student = UserFactory(username='foo', password=cls.password)
        cls.other_user = UserFactory(username='bar', password=cls.password)
        cls.staff = StaffFactory(course_key=cls.course.id, password=cls.password)
        cls.global_staff = GlobalStaffFactory.create()

        cls.namespaced_url = 'courses_api:course_import'

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

    def test_anonymous(self):
        """
        Test that an anonymous user cannot access the API and an error is received.
        """
        resp = self.client.post(self.get_url())
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student(self):
        """
        Test that an student user cannot access the API and an error is received.
        """
        self.client.login(username=self.student.username, password=self.password)
        resp = self.client.post(self.get_url())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_has_access(self):
        """
        Test that an staff user can access the API
        """
        self.client.login(username=self.staff.username, password=self.password)
        resp = self.client.post(self.get_url())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_has_no_access(self):
        """
        Test that an staff user can't access another course via the API
        """
        self.client.login(username=self.staff.username, password=self.password)
        resp = self.client.post(self.get_url(self.restricted_course_key))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
