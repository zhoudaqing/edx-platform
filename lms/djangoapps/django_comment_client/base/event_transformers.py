"""
Transformers for Discussion-related events.
"""
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from opaque_keys import InvalidKeyError
from opaque_keys.edx.locator import CourseLocator

from django_comment_client.utils import get_cached_discussion_id_map_by_course_id
from django_comment_client.base.views import add_truncated_title_to_event_data
from track.transformers import EventTransformer, EventTransformerRegistry


@EventTransformerRegistry.register
class ForumThreadViewedEventTransformer(EventTransformer):
    """
    Transformer to augment forum thread viewed Segment event from mobile apps
    with fields that are either not available or not efficiently accessible
    within the apps.
    """

    match_key = u'edx.forum.thread.viewed'

    def process_event(self):
        course_id_string = self.event.get('course_id')
        course_id = None
        if course_id_string:
            try:
                course_id = CourseLocator.from_string(course_id_string)
            except InvalidKeyError:
                pass

        commentable_id = self.event.get('commentable_id')
        thread_id = self.event.get('id')

        username = self.get('username')
        user = None
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                pass

        if course_id and commentable_id and user:
            id_map = get_cached_discussion_id_map_by_course_id(course_id, [commentable_id], user)
            if commentable_id in id_map:
                self.event['category_name'] = id_map[commentable_id]['title']
                self.event['category_id'] = commentable_id

        if course_id and commentable_id and thread_id:
            url_kwargs = {
                'course_id': course_id_string,
                'discussion_id': commentable_id,
                'thread_id': thread_id
            }
            self.event['url'] = reverse('single_thread', kwargs=url_kwargs)

        if course_id and user:
            self.event['user_forums_roles'] = [
                role.name for role in user.roles.filter(course_id=course_id)
            ]
            self.event['user_course_roles'] = [
                role.role for role in user.courseaccessrole_set.filter(course_id=course_id)
            ]

    	add_truncated_title_to_event_data(self.event, self.event.get('title'))

        if 'course_id' in self.event:
        	del self.event['course_id']
