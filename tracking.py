# -*- coding: utf-8 -*-
from django.dispatch.dispatcher import receiver
from django.contrib.auth.models import User
import logging

from opaque_keys.edx.keys import UsageKey
from track.backends import BaseBackend
from xmodule.modulestore.django import SignalHandler


class EventtrackingBackend(object):
    """
    Это бэкенд для пакета eventtracking. На данный момент(01.17) используется в edx мало где.
    """

    def send(self, event):
        """Send the event to the standard python logger"""
        pass
        #TODO: попробовать поймать полезные сигналы


class DjangoTrackerBackend(BaseBackend):
    """
    Это бэкенд к старой системе трекинга OpenEdx в виде djangoapp, ее можно найти в common/djagnoapps/track.
    С ее помощью пишется tracking.log. Из таких логов доступны фактически только url, по которым делались обращения
    """

    def send(self, event):
        """
        Если в url есть studio_view, значит преподаватель собирался что-то менять в блоке. Мы не можем таким образом
        узнать, были ли сделаны изменения, поэтому запоминаем блок как кандидата на проверку.
        :param event:
        :return:
        """
        username = event['username']
        if "studio_view" in event['event_type']:
            try:
                usage_id = event['event_type'].split('/')[2]
                usage_key = UsageKey.from_string(usage_id)
                course_id = str(usage_key.course_key)
                from course_validator.models import CourseUpdate
                # Этот импорт помещен здесь, т.к. бэкенды загружаются раньше course_validator и иначе выбрасывается Exception
                CourseUpdate.objects.create(course_id=course_id, username=username, change=CourseUpdate.candidate(usage_id))
            except Exception as e:
                print(e)


@receiver(SignalHandler.item_deleted)
def listen_for_item_delete(**kwargs):  # pylint: disable=unused-argument
    """
    Catches the item was deleted
    """
    try:
        # Этот импорт помещен здесь, т.к. бэкенды загружаются раньше course_validator и иначе выбрасывается Exception
        from course_validator.models import Course, CourseUpdate
        usage_key = kwargs['usage_key']
        if usage_key.branch:
            usage_key = usage_key.for_branch(None)
        user_id = kwargs['user_id']
        username = User.objects.get(id=int(user_id)).username
        course_id = str(usage_key.course_key)
        block_type = usage_key.block_type
        if block_type == "video":
            type_ = CourseUpdate.VIDEO_BLOCK
        elif block_type == "problem":
            type_ = CourseUpdate.PROBLEM_BLOCK
        else:
            type_ = CourseUpdate.COURSE_PART

        CourseUpdate.objects.create(course_id=course_id, username=username, change=type_)
    except Exception as e:
        logging.error(str(e))
