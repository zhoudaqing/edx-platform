"""
Transformers for Discussion-related events.
"""
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from opaque_keys import InvalidKeyError
from opaque_keys.edx.locator import CourseLocator

from django_comment_client.utils import get_cached_discussion_id_map_by_course_id
from django_comment_client.base.views import add_truncated_title_to_event_data
from teams.models import CourseTeam
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
        """
        Transform incoming events.

        For events from mobile, enhance with fields that are not available
        within the apps, and remove unncessary fields.

        Pass-through other events.
        """

        # Do not transform non-mobile events; they should already have all the correct fields
        if self['event_source'] != 'mobile':
            return

        # Parse out course key; extract topic and thread IDs
        course_id_string = self.event.get('course_id')
        course_id = None
        if course_id_string:
            try:
                course_id = CourseLocator.from_string(course_id_string)
            except InvalidKeyError:
                pass
        commentable_id = self.event.get('commentable_id')
        thread_id = self.event.get('id')

        # Load user
        username = self.get('username')
        user = None
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                pass

        # If in a category, add category name and ID
        if course_id and commentable_id and user:
            id_map = get_cached_discussion_id_map_by_course_id(course_id, [commentable_id], user)
            if commentable_id in id_map:
                self.event['category_name'] = id_map[commentable_id]['title']
                self.event['category_id'] = commentable_id

        # Add thread URL
        if course_id and commentable_id and thread_id:
            url_kwargs = {
                'course_id': course_id_string,
                'discussion_id': commentable_id,
                'thread_id': thread_id
            }
            self.event['url'] = reverse('single_thread', kwargs=url_kwargs)

        # Add truncated title
        add_truncated_title_to_event_data(self.event, self.event.get('title'))

        # Add user's forum and course roles
        if course_id and user:
            self.event['user_forums_roles'] = [
                role.name for role in user.roles.filter(course_id=course_id)
            ]
            self.event['user_course_roles'] = [
                role.role for role in user.courseaccessrole_set.filter(course_id=course_id)
            ]

        # Add team ID
        if commentable_id:
            try:
                team = CourseTeam.objects.get(discussion_topic_id=commentable_id)
                self.event['team_id'] = team.team_id
            except CourseTeam.DoesNotExist:
                pass

        # Remove course ID field.
        # It is in the mobile event data because it is necessary in order to calculate the
        # user_forum_roles and user_course_roles fields; however, it is not required in
        # the final event.
        it is not needed in the final event.
        if 'course_id' in self.event:
            del self.event['course_id']
