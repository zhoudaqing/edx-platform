"""Tests covering Programs utilities."""
# pylint: disable=no-member
import datetime
import json
import uuid

import ddt
import httpretty
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
import mock
from nose.plugins.attrib import attr
from pytz import utc

from course_modes.models import CourseMode
from lms.djangoapps.certificates.api import MODES
from lms.djangoapps.commerce.tests.test_utils import update_commerce_config
from lms.djangoapps.commerce.utils import EcommerceService
from openedx.core.djangoapps.catalog.tests.factories import (
    generate_course_run_key,
    ProgramFactory,
    CourseFactory,
    CourseRunFactory,
    SeatFactory,
)
from openedx.core.djangoapps.programs.tests.factories import ProgressFactory
from openedx.core.djangoapps.programs.utils import (
    DEFAULT_ENROLLMENT_START_DATE,
    ProgramProgressMeter,
    ProgramDataExtender,
    ProgramMarketingDataExtender,
    get_certificates,
)
from openedx.core.djangolib.testing.utils import skip_unless_lms
from student.tests.factories import AnonymousUserFactory, UserFactory, CourseEnrollmentFactory
from util.date_utils import strftime_localized
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory as ModuleStoreCourseFactory


CERTIFICATES_API_MODULE = 'lms.djangoapps.certificates.api'
ECOMMERCE_URL_ROOT = 'https://ecommerce.example.com'
UTILS_MODULE = 'openedx.core.djangoapps.programs.utils'


@ddt.ddt
@attr(shard=2)
@skip_unless_lms
@mock.patch(UTILS_MODULE + '.get_programs')
class TestProgramProgressMeter(TestCase):
    """Tests of the program progress utility class."""
    def setUp(self):
        super(TestProgramProgressMeter, self).setUp()

        self.user = UserFactory()

    def _create_enrollments(self, *course_run_ids):
        """Variadic helper used to create course run enrollments."""
        for course_run_id in course_run_ids:
            CourseEnrollmentFactory(user=self.user, course_id=course_run_id, mode='verified')

    def _assert_progress(self, meter, *progresses):
        """Variadic helper used to verify progress calculations."""
        self.assertEqual(meter.progress(), list(progresses))

    def _attach_detail_url(self, programs):
        """Add expected detail URLs to a list of program dicts."""
        for program in programs:
            program['detail_url'] = reverse('program_details_view', kwargs={'program_uuid': program['uuid']})

    def _make_certificate_result(self, **kwargs):
        """Helper to create dummy results from the certificates API."""
        result = {
            'username': 'dummy-username',
            'course_key': 'dummy-course',
            'type': 'dummy-type',
            'status': 'dummy-status',
            'download_url': 'http://www.example.com/cert.pdf',
            'grade': '0.98',
            'created': '2015-07-31T00:00:00Z',
            'modified': '2015-07-31T00:00:00Z',
        }

        result.update(**kwargs)

        return result

    def test_no_enrollments(self, mock_get_programs):
        """Verify behavior when programs exist, but no relevant enrollments do."""
        data = [ProgramFactory()]
        mock_get_programs.return_value = data

        meter = ProgramProgressMeter(self.user)

        self.assertEqual(meter.engaged_programs, [])
        self._assert_progress(meter)
        self.assertEqual(meter.completed_programs, [])

    def test_no_programs(self, mock_get_programs):
        """Verify behavior when enrollments exist, but no matching programs do."""
        mock_get_programs.return_value = []

        course_run_id = generate_course_run_key()
        self._create_enrollments(course_run_id)
        meter = ProgramProgressMeter(self.user)

        self.assertEqual(meter.engaged_programs, [])
        self._assert_progress(meter)
        self.assertEqual(meter.completed_programs, [])

    def test_single_program_engagement(self, mock_get_programs):
        """
        Verify that correct program is returned when the user is enrolled in a
        course run appearing in one program.
        """
        course_run_key = generate_course_run_key()
        data = [
            ProgramFactory(
                courses=[
                    CourseFactory(course_runs=[
                        CourseRunFactory(key=course_run_key),
                    ]),
                ]
            ),
            ProgramFactory(),
        ]
        mock_get_programs.return_value = data

        self._create_enrollments(course_run_key)
        meter = ProgramProgressMeter(self.user)

        self._attach_detail_url(data)
        program = data[0]
        self.assertEqual(meter.engaged_programs, [program])
        self._assert_progress(
            meter,
            ProgressFactory(uuid=program['uuid'], in_progress=1)
        )
        self.assertEqual(meter.completed_programs, [])

    def test_course_progress(self, mock_get_programs):
        """
        Verify that the progress meter can represent progress in terms of
        serialized courses.
        """
        course_run_key = generate_course_run_key()
        data = [
            ProgramFactory(
                courses=[
                    CourseFactory(course_runs=[
                        CourseRunFactory(key=course_run_key),
                    ]),
                ]
            )
        ]
        mock_get_programs.return_value = data

        self._create_enrollments(course_run_key)

        meter = ProgramProgressMeter(self.user)

        program = data[0]
        expected = [
            ProgressFactory(
                uuid=program['uuid'],
                completed=[],
                in_progress=[program['courses'][0]],
                not_started=[]
            )
        ]

        self.assertEqual(meter.progress(count_only=False), expected)

    def test_no_id_professional_in_progress(self, mock_get_programs):
        """
        Verify that the progress meter treats no-id-professional enrollments
        as professional.
        """
        course_run_key = generate_course_run_key()
        data = [
            ProgramFactory(
                courses=[
                    CourseFactory(course_runs=[
                        CourseRunFactory(key=course_run_key, type=CourseMode.PROFESSIONAL),
                    ]),
                ]
            )
        ]
        mock_get_programs.return_value = data

        CourseEnrollmentFactory(
            user=self.user, course_id=course_run_key,
            mode=CourseMode.NO_ID_PROFESSIONAL_MODE
        )

        meter = ProgramProgressMeter(self.user)

        program = data[0]
        expected = [
            ProgressFactory(
                uuid=program['uuid'],
                completed=[],
                in_progress=[program['courses'][0]],
                not_started=[]
            )
        ]

        self.assertEqual(meter.progress(count_only=False), expected)

    @ddt.data(None, 1, -1)
    def test_in_progress_course_upgrade_deadline_check(self, offset, mock_get_programs):
        """
        Verify that if the user's enrollment is not of the same type as the course run,
        the course will only count as in progress if there is another available seat with
        the right type for which the upgrade deadline has not passed.
        """
        course_run_key = generate_course_run_key()
        now = datetime.datetime.now(utc)
        upgrade_deadline = None if not offset else str(now + datetime.timedelta(days=offset))
        required_seat = SeatFactory(type='verified', upgrade_deadline=upgrade_deadline)
        enrolled_seat = SeatFactory(type='audit')
        seats = [required_seat, enrolled_seat]

        data = [
            ProgramFactory(
                courses=[
                    CourseFactory(course_runs=[
                        CourseRunFactory(key=course_run_key, type='verified', seats=seats),
                    ]),
                ]
            )
        ]
        mock_get_programs.return_value = data

        CourseEnrollmentFactory(user=self.user, course_id=course_run_key, mode='audit')

        meter = ProgramProgressMeter(self.user)

        program = data[0]
        expected = [
            ProgressFactory(
                uuid=program['uuid'],
                completed=0,
                in_progress=1 if offset in [None, 1] else 0,
                not_started=1 if offset in [-1] else 0
            )
        ]

        self.assertEqual(meter.progress(count_only=True), expected)

    def test_mutiple_program_engagement(self, mock_get_programs):
        """
        Verify that correct programs are returned in the correct order when the
        user is enrolled in course runs appearing in programs.
        """
        newer_course_run_key, older_course_run_key = (generate_course_run_key() for __ in range(2))
        data = [
            ProgramFactory(
                courses=[
                    CourseFactory(course_runs=[
                        CourseRunFactory(key=newer_course_run_key),
                    ]),
                ]
            ),
            ProgramFactory(
                courses=[
                    CourseFactory(course_runs=[
                        CourseRunFactory(key=older_course_run_key),
                    ]),
                ]
            ),
            ProgramFactory(),
        ]
        mock_get_programs.return_value = data

        # The creation time of the enrollments matters to the test. We want
        # the first_course_run_key to represent the newest enrollment.
        self._create_enrollments(older_course_run_key, newer_course_run_key)
        meter = ProgramProgressMeter(self.user)

        self._attach_detail_url(data)
        programs = data[:2]
        self.assertEqual(meter.engaged_programs, programs)
        self._assert_progress(
            meter,
            *(ProgressFactory(uuid=program['uuid'], in_progress=1) for program in programs)
        )
        self.assertEqual(meter.completed_programs, [])

    def test_shared_enrollment_engagement(self, mock_get_programs):
        """
        Verify that correct programs are returned when the user is enrolled in a
        single course run appearing in multiple programs.
        """
        shared_course_run_key, solo_course_run_key = (generate_course_run_key() for __ in range(2))

        batch = [
            ProgramFactory(
                courses=[
                    CourseFactory(course_runs=[
                        CourseRunFactory(key=shared_course_run_key),
                    ]),
                ]
            )
            for __ in range(2)
        ]

        joint_programs = sorted(batch, key=lambda program: program['title'])
        data = joint_programs + [
            ProgramFactory(
                courses=[
                    CourseFactory(course_runs=[
                        CourseRunFactory(key=solo_course_run_key),
                    ]),
                ]
            ),
            ProgramFactory(),
        ]

        mock_get_programs.return_value = data

        # Enrollment for the shared course run created last (most recently).
        self._create_enrollments(solo_course_run_key, shared_course_run_key)
        meter = ProgramProgressMeter(self.user)

        self._attach_detail_url(data)
        programs = data[:3]
        self.assertEqual(meter.engaged_programs, programs)
        self._assert_progress(
            meter,
            *(ProgressFactory(uuid=program['uuid'], in_progress=1) for program in programs)
        )
        self.assertEqual(meter.completed_programs, [])

    @mock.patch(UTILS_MODULE + '.ProgramProgressMeter.completed_course_runs', new_callable=mock.PropertyMock)
    def test_simulate_progress(self, mock_completed_course_runs, mock_get_programs):
        """Simulate the entirety of a user's progress through a program."""
        first_course_run_key, second_course_run_key = (generate_course_run_key() for __ in range(2))
        data = [
            ProgramFactory(
                courses=[
                    CourseFactory(course_runs=[
                        CourseRunFactory(key=first_course_run_key),
                    ]),
                    CourseFactory(course_runs=[
                        CourseRunFactory(key=second_course_run_key),
                    ]),
                ]
            ),
            ProgramFactory(),
        ]
        mock_get_programs.return_value = data

        # No enrollments, no programs in progress.
        meter = ProgramProgressMeter(self.user)
        self._assert_progress(meter)
        self.assertEqual(meter.completed_programs, [])

        # One enrollment, one program in progress.
        self._create_enrollments(first_course_run_key)
        meter = ProgramProgressMeter(self.user)
        program, program_uuid = data[0], data[0]['uuid']
        self._assert_progress(
            meter,
            ProgressFactory(uuid=program_uuid, in_progress=1, not_started=1)
        )
        self.assertEqual(meter.completed_programs, [])

        # Two enrollments, all courses in progress.
        self._create_enrollments(second_course_run_key)
        meter = ProgramProgressMeter(self.user)
        self._assert_progress(
            meter,
            ProgressFactory(uuid=program_uuid, in_progress=2)
        )
        self.assertEqual(meter.completed_programs, [])

        # One valid certificate earned, one course complete.
        mock_completed_course_runs.return_value = [
            {'course_run_id': first_course_run_key, 'type': MODES.verified},
        ]
        meter = ProgramProgressMeter(self.user)
        self._assert_progress(
            meter,
            ProgressFactory(uuid=program_uuid, completed=1, in_progress=1)
        )
        self.assertEqual(meter.completed_programs, [])

        # Invalid certificate earned, still one course to complete.
        mock_completed_course_runs.return_value = [
            {'course_run_id': first_course_run_key, 'type': MODES.verified},
            {'course_run_id': second_course_run_key, 'type': MODES.honor},
        ]
        meter = ProgramProgressMeter(self.user)
        self._assert_progress(
            meter,
            ProgressFactory(uuid=program_uuid, completed=1, in_progress=1)
        )
        self.assertEqual(meter.completed_programs, [])

        # Second valid certificate obtained, all courses complete.
        mock_completed_course_runs.return_value = [
            {'course_run_id': first_course_run_key, 'type': MODES.verified},
            {'course_run_id': second_course_run_key, 'type': MODES.verified},
        ]
        meter = ProgramProgressMeter(self.user)
        self._assert_progress(
            meter,
            ProgressFactory(uuid=program_uuid, completed=2)
        )
        self.assertEqual(meter.completed_programs, [program_uuid])

    @mock.patch(UTILS_MODULE + '.ProgramProgressMeter.completed_course_runs', new_callable=mock.PropertyMock)
    def test_nonverified_course_run_completion(self, mock_completed_course_runs, mock_get_programs):
        """
        Course runs aren't necessarily of type verified. Verify that a program can
        still be completed when this is the case.
        """
        course_run_key = generate_course_run_key()
        data = [
            ProgramFactory(
                courses=[
                    CourseFactory(course_runs=[
                        CourseRunFactory(key=course_run_key, type='honor'),
                        CourseRunFactory(),
                    ]),
                ]
            ),
            ProgramFactory(),
        ]
        mock_get_programs.return_value = data

        self._create_enrollments(course_run_key)
        mock_completed_course_runs.return_value = [
            {'course_run_id': course_run_key, 'type': MODES.honor},
        ]
        meter = ProgramProgressMeter(self.user)

        program, program_uuid = data[0], data[0]['uuid']
        self._assert_progress(
            meter,
            ProgressFactory(uuid=program_uuid, completed=1)
        )
        self.assertEqual(meter.completed_programs, [program_uuid])

    @mock.patch(UTILS_MODULE + '.ProgramProgressMeter.completed_course_runs', new_callable=mock.PropertyMock)
    def test_completed_programs(self, mock_completed_course_runs, mock_get_programs):
        """Verify that completed programs are correctly identified."""
        data = ProgramFactory.create_batch(3)
        mock_get_programs.return_value = data

        program_uuids = []
        course_run_keys = []
        for program in data:
            program_uuids.append(program['uuid'])

            for course in program['courses']:
                for course_run in course['course_runs']:
                    course_run_keys.append(course_run['key'])

        # Verify that no programs are complete.
        meter = ProgramProgressMeter(self.user)
        self.assertEqual(meter.completed_programs, [])

        # Complete all programs.
        self._create_enrollments(*course_run_keys)
        mock_completed_course_runs.return_value = [
            {'course_run_id': course_run_key, 'type': MODES.verified}
            for course_run_key in course_run_keys
        ]

        # Verify that all programs are complete.
        meter = ProgramProgressMeter(self.user)
        self.assertEqual(meter.completed_programs, program_uuids)

    @mock.patch(UTILS_MODULE + '.certificate_api.get_certificates_for_user')
    def test_completed_course_runs(self, mock_get_certificates_for_user, _mock_get_programs):
        """
        Verify that the method can find course run certificates when not mocked out.
        """
        mock_get_certificates_for_user.return_value = [
            self._make_certificate_result(status='downloadable', type='verified', course_key='downloadable-course'),
            self._make_certificate_result(status='generating', type='honor', course_key='generating-course'),
            self._make_certificate_result(status='unknown', course_key='unknown-course'),
        ]

        meter = ProgramProgressMeter(self.user)
        self.assertEqual(
            meter.completed_course_runs,
            [
                {'course_run_id': 'downloadable-course', 'type': 'verified'},
                {'course_run_id': 'generating-course', 'type': 'honor'},
            ]
        )
        mock_get_certificates_for_user.assert_called_with(self.user.username)

    @mock.patch(UTILS_MODULE + '.certificate_api.get_certificates_for_user')
    def test_program_completion_with_no_id_professional(self, mock_get_certificates_for_user, mock_get_programs):
        """
        Verify that 'no-id-professional' certificates are treated as if they were
        'professional' certificates when determining program completion.
        """
        # Create serialized course runs like the ones we expect to receive from
        # the discovery service's API. These runs are of type 'professional'.
        course_runs = CourseRunFactory.create_batch(2, type='professional')
        program = ProgramFactory(courses=[CourseFactory(course_runs=course_runs)])
        mock_get_programs.return_value = [program]

        # Verify that the test program is not complete.
        meter = ProgramProgressMeter(self.user)
        self.assertEqual(meter.completed_programs, [])

        # Grant a 'no-id-professional' certificate for one of the course runs,
        # thereby completing the program.
        mock_get_certificates_for_user.return_value = [
            self._make_certificate_result(status='downloadable', type='no-id-professional', course_key=course_runs[0]['key'])
        ]

        # Verify that the program is complete.
        meter = ProgramProgressMeter(self.user)
        self.assertEqual(meter.completed_programs, [program['uuid']])

    @mock.patch(UTILS_MODULE + '.ProgramProgressMeter.completed_course_runs', new_callable=mock.PropertyMock)
    def test_credit_course_counted_complete_for_verified(self, mock_completed_course_runs, mock_get_programs):
        """
        Verify that 'credit' course certificate type are treated as if they were
        "verified" when checking for course completion status.
        """
        course_run_key = generate_course_run_key()
        course = CourseFactory(course_runs=[
            CourseRunFactory(key=course_run_key, type='credit'),
        ])
        program = ProgramFactory(courses=[course])
        mock_get_programs.return_value = [program]
        self._create_enrollments(course_run_key)
        meter = ProgramProgressMeter(self.user)
        mock_completed_course_runs.return_value = [{'course_run_id': course_run_key, 'type': 'verified'}]
        self.assertEqual(meter._is_course_complete(course), True)


@ddt.ddt
@override_settings(ECOMMERCE_PUBLIC_URL_ROOT=ECOMMERCE_URL_ROOT)
@skip_unless_lms
class TestProgramDataExtender(ModuleStoreTestCase):
    """Tests of the program data extender utility class."""
    maxDiff = None
    sku = 'abc123'
    checkout_path = '/basket'

    def setUp(self):
        super(TestProgramDataExtender, self).setUp()

        self.course = ModuleStoreCourseFactory()
        self.course.start = datetime.datetime.now(utc) - datetime.timedelta(days=1)
        self.course.end = datetime.datetime.now(utc) + datetime.timedelta(days=1)
        self.course = self.update_course(self.course, self.user.id)

        self.course_run = CourseRunFactory(key=unicode(self.course.id))
        self.catalog_course = CourseFactory(course_runs=[self.course_run])
        self.program = ProgramFactory(courses=[self.catalog_course])

    def _assert_supplemented(self, actual, **kwargs):
        """DRY helper used to verify that program data is extended correctly."""
        self.course_run.update(
            dict(
                {
                    'certificate_url': None,
                    'course_url': reverse('course_root', args=[self.course.id]),
                    'enrollment_open_date': strftime_localized(DEFAULT_ENROLLMENT_START_DATE, 'SHORT_DATE'),
                    'is_course_ended': self.course.end < datetime.datetime.now(utc),
                    'is_enrolled': False,
                    'is_enrollment_open': True,
                    'upgrade_url': None,
                    'advertised_start': None,
                },
                **kwargs
            )
        )

        self.catalog_course['course_runs'] = [self.course_run]
        self.program['courses'] = [self.catalog_course]

        self.assertEqual(actual, self.program)

    @ddt.data(-1, 0, 1)
    def test_is_enrollment_open(self, days_offset):
        """
        Verify that changes to the course run end date do not affect our
        assessment of the course run being open for enrollment.
        """
        self.course.end = datetime.datetime.now(utc) + datetime.timedelta(days=days_offset)
        self.course = self.update_course(self.course, self.user.id)

        data = ProgramDataExtender(self.program, self.user).extend()

        self._assert_supplemented(data)

    @ddt.data(
        (False, None, False),
        (True, MODES.audit, True),
        (True, MODES.verified, False),
    )
    @ddt.unpack
    @mock.patch(UTILS_MODULE + '.CourseMode.mode_for_course')
    def test_student_enrollment_status(self, is_enrolled, enrolled_mode, is_upgrade_required, mock_get_mode):
        """Verify that program data is supplemented with the student's enrollment status."""
        expected_upgrade_url = '{root}/{path}?sku={sku}'.format(
            root=ECOMMERCE_URL_ROOT,
            path=self.checkout_path.strip('/'),
            sku=self.sku,
        )

        update_commerce_config(enabled=True, checkout_page=self.checkout_path)

        mock_mode = mock.Mock()
        mock_mode.sku = self.sku
        mock_get_mode.return_value = mock_mode

        if is_enrolled:
            CourseEnrollmentFactory(user=self.user, course_id=self.course.id, mode=enrolled_mode)

        data = ProgramDataExtender(self.program, self.user).extend()

        self._assert_supplemented(
            data,
            is_enrolled=is_enrolled,
            upgrade_url=expected_upgrade_url if is_upgrade_required else None
        )

    @ddt.data(MODES.audit, MODES.verified)
    def test_inactive_enrollment_no_upgrade(self, enrolled_mode):
        """
        Verify that a student with an inactive enrollment isn't encouraged to upgrade.
        """
        update_commerce_config(enabled=True, checkout_page=self.checkout_path)

        CourseEnrollmentFactory(
            user=self.user,
            course_id=self.course.id,
            mode=enrolled_mode,
            is_active=False,
        )

        data = ProgramDataExtender(self.program, self.user).extend()

        self._assert_supplemented(data)

    @mock.patch(UTILS_MODULE + '.CourseMode.mode_for_course')
    def test_ecommerce_disabled(self, mock_get_mode):
        """
        Verify that the utility can operate when the ecommerce service is disabled.
        """
        update_commerce_config(enabled=False, checkout_page=self.checkout_path)

        mock_mode = mock.Mock()
        mock_mode.sku = self.sku
        mock_get_mode.return_value = mock_mode

        CourseEnrollmentFactory(user=self.user, course_id=self.course.id, mode=MODES.audit)

        data = ProgramDataExtender(self.program, self.user).extend()

        self._assert_supplemented(data, is_enrolled=True, upgrade_url=None)

    @ddt.data(
        (1, 1, False),
        (1, -1, True),
    )
    @ddt.unpack
    def test_course_run_enrollment_status(self, start_offset, end_offset, is_enrollment_open):
        """
        Verify that course run enrollment status is reflected correctly.
        """
        self.course.enrollment_start = datetime.datetime.now(utc) - datetime.timedelta(days=start_offset)
        self.course.enrollment_end = datetime.datetime.now(utc) - datetime.timedelta(days=end_offset)

        self.course = self.update_course(self.course, self.user.id)

        data = ProgramDataExtender(self.program, self.user).extend()

        self._assert_supplemented(
            data,
            is_enrollment_open=is_enrollment_open,
            enrollment_open_date=strftime_localized(self.course.enrollment_start, 'SHORT_DATE'),
        )

    def test_no_enrollment_start_date(self):
        """
        Verify that a closed course run with no explicit enrollment start date
        doesn't cause an error. Regression test for ECOM-4973.
        """
        self.course.enrollment_end = datetime.datetime.now(utc) - datetime.timedelta(days=1)
        self.course = self.update_course(self.course, self.user.id)

        data = ProgramDataExtender(self.program, self.user).extend()

        self._assert_supplemented(
            data,
            is_enrollment_open=False,
        )

    @ddt.data(True, False)
    @mock.patch(UTILS_MODULE + '.certificate_api.certificate_downloadable_status')
    @mock.patch(CERTIFICATES_API_MODULE + '.has_html_certificates_enabled')
    def test_certificate_url_retrieval(self, is_uuid_available, mock_html_certs_enabled, mock_get_cert_data):
        """
        Verify that the student's run mode certificate is included,
        when available.
        """
        test_uuid = uuid.uuid4().hex
        mock_get_cert_data.return_value = {'uuid': test_uuid} if is_uuid_available else {}
        mock_html_certs_enabled.return_value = True

        data = ProgramDataExtender(self.program, self.user).extend()

        expected_url = reverse(
            'certificates:render_cert_by_uuid',
            kwargs={'certificate_uuid': test_uuid}
        ) if is_uuid_available else None

        self._assert_supplemented(data, certificate_url=expected_url)


@skip_unless_lms
@mock.patch(UTILS_MODULE + '.get_credentials')
class TestGetCertificates(TestCase):
    """
    Tests of the function used to get certificates associated with a program.
    """
    def setUp(self):
        super(TestGetCertificates, self).setUp()

        self.user = UserFactory()
        self.program = ProgramFactory()
        self.course_certificate_url = 'fake-course-certificate-url'
        self.program_certificate_url = 'fake-program-certificate-url'

    def test_get_certificates(self, mock_get_credentials):
        """
        Verify course and program certificates are found when present. Only one
        course run certificate should be returned for each course when the user
        has earned certificates in multiple runs of the same course.
        """
        expected = []
        for course in self.program['courses']:
            # Give all course runs a certificate URL, but only expect one to come
            # back. This verifies the break in the function under test that ensures
            # only one certificate per course comes back.
            for index, course_run in enumerate(course['course_runs']):
                course_run['certificate_url'] = self.course_certificate_url

                if index == 0:
                    expected.append({
                        'type': 'course',
                        'title': course_run['title'],
                        'url': self.course_certificate_url,
                    })

        expected.append({
            'type': 'program',
            'title': self.program['title'],
            'url': self.program_certificate_url,
        })

        mock_get_credentials.return_value = [{
            'certificate_url': self.program_certificate_url
        }]

        certificates = get_certificates(self.user, self.program)
        self.assertEqual(certificates, expected)

    def test_course_run_certificates_missing(self, mock_get_credentials):
        """
        Verify program certificates are retrieved even if the learner has not earned any course certificates.
        """
        expected = [{
            'type': 'program',
            'title': self.program['title'],
            'url': self.program_certificate_url,
        }]
        mock_get_credentials.return_value = [{'certificate_url': self.program_certificate_url}]

        certificates = get_certificates(self.user, self.program)
        self.assertTrue(mock_get_credentials.called)
        self.assertEqual(certificates, expected)

    def test_program_certificate_missing(self, mock_get_credentials):
        """
        Verify that the function can handle a missing program certificate.
        """
        expected = []
        for course in self.program['courses']:
            for index, course_run in enumerate(course['course_runs']):
                course_run['certificate_url'] = self.course_certificate_url

                if index == 0:
                    expected.append({
                        'type': 'course',
                        'title': course_run['title'],
                        'url': self.course_certificate_url,
                    })

        mock_get_credentials.return_value = []

        certificates = get_certificates(self.user, self.program)
        self.assertEqual(certificates, expected)


@ddt.ddt
@override_settings(ECOMMERCE_PUBLIC_URL_ROOT=ECOMMERCE_URL_ROOT)
@skip_unless_lms
class TestProgramMarketingDataExtender(ModuleStoreTestCase):
    """Tests of the program data extender utility class."""
    ECOMMERCE_CALCULATE_DISCOUNT_ENDPOINT = '{root}/api/v2/baskets/calculate/'.format(root=ECOMMERCE_URL_ROOT)
    instructors = {
        'instructors': [
            {
                'name': 'test-instructor1',
                'organization': 'TextX',
            },
            {
                'name': 'test-instructor2',
                'organization': 'TextX',
            }
        ]
    }

    def setUp(self):
        super(TestProgramMarketingDataExtender, self).setUp()

        # Ensure the E-Commerce service user exists
        UserFactory(username=settings.ECOMMERCE_SERVICE_WORKER_USERNAME, is_staff=True)

        self.course_price = 100
        self.number_of_courses = 2
        self.program = ProgramFactory(
            courses=[self._create_course(self.course_price) for __ in range(self.number_of_courses)]
        )

    def _create_course(self, course_price):
        """
        Creates the course in mongo and update it with the instructor data.
        Also creates catalog course with respect to course run.

        Returns:
            Catalog course dict.
        """
        course = ModuleStoreCourseFactory()
        course.start = datetime.datetime.now(utc) - datetime.timedelta(days=1)
        course.end = datetime.datetime.now(utc) + datetime.timedelta(days=1)
        course.instructor_info = self.instructors
        course = self.update_course(course, self.user.id)

        course_run = CourseRunFactory(
            key=unicode(course.id),
            seats=[SeatFactory(price=course_price)]
        )
        return CourseFactory(course_runs=[course_run])

    def _prepare_program_for_discounted_price_calculation_endpoint(self):
        """
        Program's applicable seat types should match some or all seat types of the seats that are a part of the program.
        Otherwise, ecommerce API endpoint for calculating the discounted price won't be called.

        Returns:
            seat: seat for which the discount is applicable
        """
        self.ecommerce_service = EcommerceService()
        seat = self.program['courses'][0]['course_runs'][0]['seats'][0]
        self.program['applicable_seat_types'] = [seat['type']]
        return seat

    def test_instructors(self):
        data = ProgramMarketingDataExtender(self.program, self.user).extend()

        self.program.update(self.instructors['instructors'])
        self.assertEqual(data, self.program)

    def test_course_pricing(self):
        data = ProgramMarketingDataExtender(self.program, self.user).extend()

        program_full_price = self.course_price * self.number_of_courses
        self.assertEqual(data['number_of_courses'], self.number_of_courses)
        self.assertEqual(data['full_program_price'], program_full_price)
        self.assertEqual(data['avg_price_per_course'], program_full_price / self.number_of_courses)

    def test_course_pricing_when_all_course_runs_have_no_seats(self):
        course = ModuleStoreCourseFactory()
        course = self.update_course(course, self.user.id)
        course_run = CourseRunFactory(key=unicode(course.id), seats=[])
        program = ProgramFactory(courses=[CourseFactory(course_runs=[course_run])])

        data = ProgramMarketingDataExtender(program, self.user).extend()

        self.assertEqual(data['number_of_courses'], len(program['courses']))
        self.assertEqual(data['full_program_price'], 0.0)
        self.assertEqual(data['avg_price_per_course'], 0.0)

    @ddt.data(True, False)
    @mock.patch(UTILS_MODULE + '.has_access')
    def test_can_enroll(self, can_enroll, mock_has_access):
        """
        Verify that the student's can_enroll status is included.
        """
        mock_has_access.return_value = can_enroll

        data = ProgramMarketingDataExtender(self.program, self.user).extend()

        self.assertEqual(data['courses'][0]['course_runs'][0]['can_enroll'], can_enroll)

    def test_learner_eligibility_for_one_click_purchase(self):
        """
        Learner should be eligible for one click purchase if:
            - program is eligible for one click purchase
            - learner is not enrolled in any of the course runs associated with the program
        """
        data = ProgramMarketingDataExtender(self.program, self.user).extend()
        self.assertTrue(data['is_learner_eligible_for_one_click_purchase'])

        courses = [self._create_course(self.course_price)]

        program = ProgramFactory(
            courses=courses,
            is_program_eligible_for_one_click_purchase=False
        )
        data = ProgramMarketingDataExtender(program, self.user).extend()
        self.assertFalse(data['is_learner_eligible_for_one_click_purchase'])

        course = self._create_course(self.course_price)
        CourseEnrollmentFactory(user=self.user, course_id=course['course_runs'][0]['key'])
        program2 = ProgramFactory(
            courses=[course],
            is_program_eligible_for_one_click_purchase=True
        )
        data = ProgramMarketingDataExtender(program2, self.user).extend()
        self.assertFalse(data['is_learner_eligible_for_one_click_purchase'])

    def test_multiple_published_course_runs(self):
        """
        Learner should not be eligible for one click purchase if:
            - program has a course with more than one published course run
        """
        course_run_1 = CourseRunFactory(
            key=str(ModuleStoreCourseFactory().id),
            status='published'
        )
        course_run_2 = CourseRunFactory(
            key=str(ModuleStoreCourseFactory().id),
            status='published'
        )
        course = CourseFactory(course_runs=[course_run_1, course_run_2])
        program = ProgramFactory(
            courses=[
                CourseFactory(course_runs=[
                    CourseRunFactory(
                        key=str(ModuleStoreCourseFactory().id),
                        status='published'
                    )
                ]),
                course,
                CourseFactory(course_runs=[
                    CourseRunFactory(
                        key=str(ModuleStoreCourseFactory().id),
                        status='published'
                    )
                ])
            ],
            is_program_eligible_for_one_click_purchase=True
        )
        data = ProgramMarketingDataExtender(program, self.user).extend()

        self.assertFalse(data['is_learner_eligible_for_one_click_purchase'])

        course_run_2['status'] = 'unpublished'
        data = ProgramMarketingDataExtender(program, self.user).extend()

        self.assertTrue(data['is_learner_eligible_for_one_click_purchase'])

    @httpretty.activate
    def test_fetching_program_discounted_price(self):
        """
        Authenticated users eligible for one click purchase should see the purchase button
            - displaying program's discounted price if it exists.
            - leading to ecommerce basket page
        """
        self._prepare_program_for_discounted_price_calculation_endpoint()
        mock_discount_data = {
            'total_incl_tax_excl_discounts': 200.0,
            'currency': "USD",
            'total_incl_tax': 50.0
        }
        httpretty.register_uri(
            httpretty.GET,
            self.ECOMMERCE_CALCULATE_DISCOUNT_ENDPOINT,
            body=json.dumps(mock_discount_data),
            content_type='application/json'
        )

        data = ProgramMarketingDataExtender(self.program, self.user).extend()

        self.assertEqual(
            data['skus'],
            [course['course_runs'][0]['seats'][0]['sku'] for course in self.program['courses']]
        )
        self.assertEqual(data['discount_data'], mock_discount_data)

    @httpretty.activate
    def test_fetching_program_discounted_price_as_anonymous_user(self):
        """
        Anonymous users should see the purchase button same way the authenticated users do
        when the program is eligible for one click purchase.
        """
        self._prepare_program_for_discounted_price_calculation_endpoint()
        mock_discount_data = {
            'total_incl_tax_excl_discounts': 200.0,
            'currency': "USD",
            'total_incl_tax': 50.0
        }
        httpretty.register_uri(
            httpretty.GET,
            self.ECOMMERCE_CALCULATE_DISCOUNT_ENDPOINT,
            body=json.dumps(mock_discount_data),
            content_type='application/json'
        )

        data = ProgramMarketingDataExtender(self.program, AnonymousUserFactory()).extend()

        self.assertEqual(
            data['skus'],
            [course['course_runs'][0]['seats'][0]['sku'] for course in self.program['courses']]
        )
        self.assertEqual(data['discount_data'], mock_discount_data)

    def test_fetching_program_discounted_price_no_applicable_seats(self):
        """
        User shouldn't be able to do a one click purchase of a program if a program has no applicable seat types.
        """
        data = ProgramMarketingDataExtender(self.program, self.user).extend()

        self.assertEqual(len(data['skus']), 0)

    @httpretty.activate
    def test_fetching_program_discounted_price_api_exception_caught(self):
        """
        User should be able to do a one click purchase of a program even if the ecommerce API throws an exception
        during the calculation of program discounted price.
        """
        self._prepare_program_for_discounted_price_calculation_endpoint()
        httpretty.register_uri(
            httpretty.GET,
            self.ECOMMERCE_CALCULATE_DISCOUNT_ENDPOINT,
            status=400,
            content_type='application/json'
        )

        data = ProgramMarketingDataExtender(self.program, self.user).extend()

        self.assertEqual(
            data['skus'],
            [course['course_runs'][0]['seats'][0]['sku'] for course in self.program['courses']]
        )
