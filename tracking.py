# -*- coding: utf-8 -*-
from django.dispatch.dispatcher import receiver
from django.contrib.auth.models import User
from django.conf import settings
import json
import logging


from opaque_keys.edx.keys import UsageKey
from track.backends import BaseBackend
from xmodule.modulestore.django import SignalHandler
from eventtracking import tracker
from .models import CourseUpdate


class XBlockChangeProcessor(object):
    """
    Анализирует какие изменения в xblock были запрошены и сохраняет необходимые данные
    """

    def __init__(self, request, usage_key_string, response):
        self.request = request
        self.usage_id = usage_key_string
        self.response = response

        self.valid = self._is_valid_change()
        if self.valid:
            self._init()

    def _is_valid_change(self):
        if self.request.method == "POST":
            usage_id = json.loads(self.response.content).get("locator", None)
            if not usage_id:
                return False
            self.usage_id = usage_id
            return True
        if self.request.method in ["GET"]:
            return False
        if not self.usage_id:
            return False
        if not self.response.status_code / 100 == 2: #400+, 500+ etc
            return False
        return True

    def _init(self):
        self.data = self.request.json
        self.usage_key = UsageKey.from_string(self.usage_id)
        self.course_id = str(self.usage_key.course_key)
        self.category = self.usage_key.category
        self.user = self.request.user
        changed_fields = {}
        metadata = self.data.get('metadata', {})
        for k in metadata:
            if metadata[k]:
                changed_fields[k] = metadata[k]
        self.changed_fields = changed_fields

    def run(self):
        if not self.valid:
            return
        if self.request.method in ["DELETE", "POST"]:
            self._save_update()
            return
        if self.category == "video":
            self._process_video()
        else:
            self._process_course_part()

    def _process_video(self):
        if not self.category == "video":
            raise ValueError("Should be used to process videos only")
        vital_keys = ["youtube_id_1_0", "edx_video_id"]
        for k in vital_keys:
            if k in self.changed_fields:
                self._save_update()
                return

    def _process_course_part(self):
        if self.category in ["chapter", "sequential"]:
            if "due" or "graderType" in self.changed_fields:
                self._save_update(candidate=True)
        if self.category == "problem":
            return

    def _save_update(self, candidate=False):
        cu = CourseUpdate
        if candidate:
            CourseUpdate.create(username=self.user, course_id=self.course_id, change_type=cu.CANDIDATE, change=str(self.usage_id))
            return
        category_mapping = {
            "video": cu.VIDEO_BLOCK,
            "problem": cu.COURSE_PART,
            "vertical": cu.COURSE_PART,
            "sequential": cu.COURSE_PART,
            "chapter": cu.COURSE_PART,
            }
        change_type = category_mapping.get(self.category, cu.OTHER)
        CourseUpdate.create(username=self.user, course_id=self.course_id, change_type=change_type,
                            change=str(self.usage_id))


def validator_signal_wrap(handler):
    """
    Декоратор для cms.djangoapps.contentstore.views.items.xblock_handler
    Отслежвает изменения в XBlock
    :param handler:
    :return:
    """
    if not settings.FEATURES.get("COURSE_VALIDATOR"):
        return handler
    from functools import wraps

    @wraps(handler)
    def wrapper(request, usage_key_string):
        response = handler(request, usage_key_string)
        #_xblock_change_analyze(request, usage_key_string, response)
        processor = XBlockChangeProcessor(request, usage_key_string, response)
        processor.run()
        return response
    return wrapper


class EventtrackingBackend(object):
    """
    Это бэкенд для пакета eventtracking. На данный момент(01.17) используется в edx мало где.
    """

    def send(self, event):
        """Send the event to the standard python logger"""
        event_type = event['event_type']
        if not 'validator' in event_type:
            return

        usage_id = event['event']['usage_id']
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


#@receiver(SignalHandler.item_deleted)
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