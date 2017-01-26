# -*- coding: utf-8 -*-
from xmodule.modulestore.django import modulestore
from opaque_keys.edx.keys import CourseKey, UsageKey
from .models import CourseValidation, CourseUpdate

class ChangeAnalyzer(object):
    """
    Анализ изменения с предыдущей валидации
    """
    def __init__(self, course_id):
        self.store = modulestore()
        self.course_key = CourseKey.from_string(course_id)

    def _get_last_course_validation(self):
        validations = CourseValidation.objects.filter(course__course_id=str(self.course_key))
        if not validations:
            return None
        else:
            return validations.order_by('-created_at')[0]

    def _get_course_updates_from_validation(self, validation):
        date = validation.created_at
        return CourseUpdate.objects.filter(course__course_id=str(self.course_key), created_at__gte=date)

    def is_video_changed(self):
        last_validation = self._get_last_course_validation()
        if not last_validation:
            return True
        curr_keys = set(CourseValidation.collect_video_keys(course_id=str(self.course_key)))
        prev_keys = set(last_validation.video_keys.split(","))
        if curr_keys != prev_keys:
            return True
        date = last_validation.created_at
        for key in curr_keys:
            video = self.store.get_item(UsageKey.from_string(key))
            if video.edited_on > date:
                return True
        return False

    def report(self):
        if self.is_video_changed():
            return "Video was changed since last validation"
        else:
            return "Video wasn't changed since last validation"