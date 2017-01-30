# -*- coding: utf-8 -*-
import logging
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
        prev_keys = set(last_validation.get_video_keys())
        if curr_keys != prev_keys:
            return True
        date = last_validation.created_at
        updates = self._get_course_updates_from_validation(last_validation)
        updates = updates.filter(change_type=CourseUpdate.VIDEO_BLOCK)
        video_ids = [x.change for x in updates]

        for key in video_ids:
            video = self.store.get_item(UsageKey.from_string(key))
            if video.edited_on > date:
                return True
        return False

    def is_date_changed(self):
        try:
            last_validation = self._get_last_course_validation()
            if not last_validation:
                return True
            updates = self. _get_course_updates_from_validation(last_validation)
            updates = updates.exclude(change_type=CourseUpdate.VIDEO_BLOCK)
            if not updates:
                return False
            change_types = [x.change_type for x in updates]
            if CourseUpdate.COURSE_PART in change_types:
                return True
            if CourseUpdate.OTHER in change_types:
                logging.warning("Unclassified chnage in course was detected")
                return True

            date = last_validation.created_at
            usage_ids = [x.change for x in updates if x.change_type==CourseUpdate.CANDIDATE]
            usage_keys = [UsageKey.from_string(x) for x in usage_ids]
            store = modulestore()
            items = [store.get_item(x) for x in usage_keys]
            for it in items:
                if it.edited_on > date:
                    return True

        except Exception as e:
            logging.error("Date change analysis error: {}".format(str(e)))
            return True
        return False

    def report(self):
        report = []
        try:
            video_change = self.is_video_changed()
            date_change = self.is_date_changed()
        except Exception as e:
            mes = "Changes Analysis failed."
            report = [mes]
            logging.error(mes+u":{}".format(str(e)))
            return report

        video_dict = {"result": not video_change}
        if video_change:
            video_dict["text"] = "Videos were changed since last validation"
        else:
            video_dict["text"] = "Video were not changed since last validation"
        report.append(video_dict)

        date_dict = {"result": not date_change}
        if date_change:
            date_dict["text"] = "Dates were changed since last validation"
        else:
            date_dict["text"] = "Dates were not changed since last validation"
        report.append(date_dict)
        return report

