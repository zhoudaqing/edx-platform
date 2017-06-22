import json

import httpretty
import waffle
from django.core.cache import cache
from django.core.management import call_command

from openedx.core.djangoapps.catalog.cache import (
    PROGRAM_CACHE_KEY_TPL,
    PROGRAM_UUIDS_CACHE_KEY,
    SITE_PROGRAM_UUIDS_CACHE_KEY_TPL
)
from openedx.core.djangoapps.catalog.tests.factories import ProgramFactory
from openedx.core.djangoapps.catalog.tests.mixins import CatalogIntegrationMixin
from openedx.core.djangoapps.site_configuration.tests.mixins import SiteMixin
from openedx.core.djangolib.testing.utils import CacheIsolationTestCase, skip_unless_lms
from student.tests.factories import UserFactory


@skip_unless_lms
@httpretty.activate
class TestCachePrograms(CatalogIntegrationMixin, CacheIsolationTestCase, SiteMixin):
    ENABLED_CACHES = ['default']

    def setUp(self):
        super(TestCachePrograms, self).setUp()

        self.catalog_integration = self.create_catalog_integration()
        self.site_domain = 'testsite.com'
        self.set_up_site(
            self.site_domain,
            {
                'COURSE_CATALOG_API_URL': self.catalog_integration.get_internal_api_url().rstrip('/')
            }
        )

        self.list_url = self.catalog_integration.get_internal_api_url().rstrip('/') + '/programs/'
        self.detail_tpl = self.list_url.rstrip('/') + '/{uuid}/'

        self.programs = ProgramFactory.create_batch(3)
        self.uuids = [program['uuid'] for program in self.programs]

    def mock_list(self):
        def list_callback(request, uri, headers):
            expected = {
                'exclude_utm': ['1'],
                'status': ['active', 'retired'],
                'uuids_only': ['1']
            }
            self.assertEqual(request.querystring, expected)

            return (200, headers, json.dumps(self.uuids))

        httpretty.register_uri(
            httpretty.GET,
            self.list_url,
            body=list_callback,
            content_type='application/json'
        )

    def mock_detail(self, uuid, program):
        def detail_callback(request, uri, headers):
            expected = {
                'exclude_utm': ['1'],
            }
            self.assertEqual(request.querystring, expected)

            return (200, headers, json.dumps(program))

        httpretty.register_uri(
            httpretty.GET,
            self.detail_tpl.format(uuid=uuid),
            body=detail_callback,
            content_type='application/json'
        )

    @waffle.testutils.override_switch("populate-multitenant-programs", True)
    def test_handle_missing_service_user(self):
        """
        Verify that the command raises an exception when run without a service
        user, and that program UUIDs are not cached.
        """
        with self.assertRaises(Exception):
            call_command('cache_programs')

        cached_uuids = cache.get(SITE_PROGRAM_UUIDS_CACHE_KEY_TPL.format(domain=self.site_domain))
        self.assertEqual(cached_uuids, None)

    @waffle.testutils.override_switch("populate-multitenant-programs", True)
    def test_handle_missing_uuids(self):
        """
        Verify that the command raises an exception when it fails to retrieve
        program UUIDs.
        """
        UserFactory(username=self.catalog_integration.service_username)

        with self.assertRaises(SystemExit) as context:
            call_command('cache_programs')
            self.assertEqual(context.exception.code, 1)

        cached_uuids = cache.get(SITE_PROGRAM_UUIDS_CACHE_KEY_TPL.format(domain=self.site_domain))
        self.assertEqual(cached_uuids, [])

    @waffle.testutils.override_switch("populate-multitenant-programs", True)
    def test_handle_missing_programs(self):
        """
        Verify that a problem retrieving a program doesn't prevent the command
        from retrieving and caching other programs, but does cause it to exit
        with a non-zero exit code.
        """
        UserFactory(username=self.catalog_integration.service_username)

        all_programs = {
            PROGRAM_CACHE_KEY_TPL.format(uuid=program['uuid']): program for program in self.programs
        }
        partial_programs = {
            PROGRAM_CACHE_KEY_TPL.format(uuid=program['uuid']): program for program in self.programs[:2]
        }

        self.mock_list()

        for uuid in self.uuids[:2]:
            program = partial_programs[PROGRAM_CACHE_KEY_TPL.format(uuid=uuid)]
            self.mock_detail(uuid, program)

        with self.assertRaises(SystemExit) as context:
            call_command('cache_programs')

            self.assertEqual(context.exception.code, 1)

        cached_uuids = cache.get(SITE_PROGRAM_UUIDS_CACHE_KEY_TPL.format(domain=self.site_domain))
        self.assertEqual(
            set(cached_uuids),
            set(self.uuids)
        )

        program_keys = list(all_programs.keys())
        cached_programs = cache.get_many(program_keys)
        # One of the cache keys should result in a cache miss.
        self.assertEqual(
            set(cached_programs),
            set(partial_programs)
        )

        for key, program in cached_programs.items():
            self.assertEqual(program, partial_programs[key])
