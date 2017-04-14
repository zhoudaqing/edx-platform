from django.contrib.auth.decorators import login_required
from openedx.core.djangoapps.plugin_api.views import EdxFragmentView
from opaque_keys.edx.keys import CourseKey
from django.template.loader import render_to_string
from web_fragments.fragment import Fragment
from edxmako.shortcuts import render_to_response
from django.views.generic.base import View
import insights_data
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required


class LearnerInsightsFragmentView(View):

    template_name = 'learner_insights/learner_insights.html'

    INSIGHTS_URL = "REPLACE"
    INSIGHTS_KEY = "REPLACE"

    def get_enrollments(self, course_id):
        client = insights_data.LMSInsightsClient(
            self.INSIGHTS_URL,
            api_key=self.INSIGHTS_KEY
        )
        enrollment_data = client.get_current_course_enrollment(course_id)
        # enrollment_data = {
        #         "course_id": "course-v1:LinuxFoundationX+LFS101x.2+1T2015",
        #         "date": "2017-03-26",
        #         "count": 236107,
        #         "created": "2017-03-28T012204"
        #       }
        return enrollment_data

    def get_course_enrollment_by_birth_year(self, course_id):
        client = insights_data.LMSInsightsClient(
            self.INSIGHTS_URL,
            api_key=self.INSIGHTS_KEY
        )
        # test_data = [
        #           {
        #             "course_id": "course-v1:LinuxFoundationX+LFS101x.2+1T2015",
        #             "date": "2017-03-26",
        #             "birth_year": 1984,
        #             "count": 6698,
        #             "created": "2017-03-28T014331"
        #           },
        #           {
        #             "course_id": "course-v1:LinuxFoundationX+LFS101x.2+1T2015",
        #             "date": "2017-03-26",
        #             "birth_year": 1985,
        #             "count": 7259,
        #             "created": "2017-03-28T014333"
        #           }
        #         ]
        # return test_data
        return client.get_current_course_enrollment_by_birth_year(course_id)

    def get_current_enrollment_education(self, course_id):
        client = insights_data.LMSInsightsClient(
            self.INSIGHTS_URL,
            api_key=self.INSIGHTS_KEY
        )
        # [
        #     ...,
        #     {
        #         "course_id": "course-v1:LinuxFoundationX+LFS101x.2+1T2015",
        #         "date": "2017-03-26",
        #         "education_level": "doctorate",
        #         "count": 4820,
        #         "created": "2017-03-28T013248"
        #     },
        #     {
        #         "course_id": "course-v1:LinuxFoundationX+LFS101x.2+1T2015",
        #         "date": "2017-03-26",
        #         "education_level": "junior_secondary",
        #         "count": 4101,
        #         "created": "2017-03-28T013249"
        #     },
        #     ...
        # ]
        return client.get_current_course_enrollment_by_education(course_id)

    def get_context(self, course_id):
        enrollment_data = self.get_enrollments(course_id)
        enrollment_birth_year = self.get_course_enrollment_by_birth_year(course_id)
        enrollment_ed = self.get_current_enrollment_education(course_id)

        context = {
            'disable_courseware_js': True,
            'uses_pattern_library': True,
            'search_course_id': '',
            'enrollment': enrollment_data,
            'enrollment_birth_year': enrollment_birth_year,
            'enrollment_ed': enrollment_ed,
        }
        return context

    def get(self, request):
        test_id = 'course-v1:LinuxFoundationX+LFS101x.2+1T2015'
        context = self.get_context(course_id=test_id)
        return render_to_response(self.template_name, context)

    def post(self, request):
        search_course_id = request.POST.get('course_id')

        context = self.get_context(course_id=search_course_id)

        return render_to_response(self.template_name, context)
