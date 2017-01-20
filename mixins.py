# -*- coding: utf-8 -*-
from datetime import timedelta as td
import json
import logging
import urllib

from django.utils.translation import ugettext as _

from .utils import validation_logger, Report
from .settings import *
from .models import CourseValidation

class VideoMixin:
    """
    Сюда вынесены меоды касающиеся работы с видео
    """

    def youtube_duration(self, video_id):
        """
        ATTENTION! В функции используется youtube_api. Необходим
        api_key. Для получения api_key:
        1.Зарегистрироваться на console.developers.google.com
        2. на главной YouTube API >YouTube Data API
        3. Включить Youtube Api
        4. В учетных данных (Credentials) взять ключ

        Определяет длительность видео с YouTube по video_id, гда
        video_id это часть url: https://youtu.be/$video_id$
        Returns: 1, Длительность
        или      0, текст ошибки
        """
        search_url = VALIDATOR_YOUTUBE_PATTERN.format(video_id=video_id)
        try:
            response = urllib.urlopen(search_url).read()
        except IOError:
            return 0, _("No response from server.")
        data = json.loads(response)
        if data.get("error", False):
            return 0, _("Error occured while video duration check:{}").format(data["error"])
        all_data = data["items"]
        if not len(all_data):
            return 0, _("Can't find video with such id on youtube.")

        content_details = all_data[0]["contentDetails"]
        duration = self._youtube_time_expand(content_details["duration"])
        dur = td(seconds=duration)
        return 1, dur

    def edx_id_duration(self, edx_video_id):
        """
        Определяет длительность видео по предоставленному edx_video_id
        Returns: 1, Длительность
        или      0, текст ошибки
        """
        if not self._api_set_up():
            return 0, _("Can't check edx video id: no api")

        from openedx.core.djangoapps.video_evms.api import get_video_info
        video = get_video_info(edx_video_id)
        if not video:
            return 0, _("No video for this edx_video_id:{}".format(edx_video_id))
        temp = video.get("duration", _("Error: didn't get duration from server"))
        dur = td(seconds=int(float(temp)))
        return 1, dur

    @staticmethod
    def _api_set_up():
        try:
            from openedx.core.djangoapps.video_evms.api import get_video_info
        except ImportError:
            return 0
        return 1

    @staticmethod
    def _youtube_time_expand(duration):
        timeunits = {
            'w': 604800,
            'd': 86400,
            'h': 3600,
            'm': 60,
            's': 1,
        }
        duration = duration.lower()

        secs = 0
        value = ''
        for c in duration:
            if c.isdigit():
                value += c
                continue
            if c in timeunits:
                secs += int(value) * timeunits[c]
            value = ''
        return secs

    @staticmethod
    def format_timedelta(tdobj):
        s = tdobj.total_seconds()
        return u"{:02d}:{:02d}:{:02d}".format(int(s // 3600), int(s % 3600 // 60), int(s % 60))


class ReportIOMixinDB():
    """Сюда вынесены методы касающиеся чтения и записи отчетов"""

    @validation_logger
    def save_validation_report(self, validation):
        try:
            delim = u'\t'
            dict_datas = [r._asdict() for r in validation]
            fields = Report._fields
            header = delim.join(fields)
            filetext = (header.encode("utf8"))

            for pr in dict_datas:
                line = delim.join((json.dumps(self._unicodize(pr[k]), ensure_ascii=False)) for k in fields)
                filetext += ("\n"+line)

            saved = CourseValidation.objects.create(course_id=self.course_key_string,
                                            user=self.request.user.username,
                                            full_validation_report=filetext,
                                            )
            info = "id:{}, readable:{}, pk:{}".format(self.course_key_string, saved.readable_name, saved.pk)
            logging.info("Report is saved:{}".format(info))

        except Exception as e:
            logging.error("Report wasn't saved:{}".format(str(e)))

    @validation_logger
    def load_validation_report(self, course_id, readable, delim=u'\t'):
        reports = []
        cv = CourseValidation.objects.by_readable_name(readable, course_id=course_id)
        full_report = cv.full_validation_report.split("\n")[1::]
        for line in full_report:
            parts = line.strip().split(delim)
            report_fields = [json.loads(field) for field in parts]
            kwargs = dict((Report._fields[k], report_fields[k]) for k, _ in enumerate(Report._fields))
            reports.append(Report(**kwargs))
        return reports

    @classmethod
    def get_saved_reports_for_course(cls, course_key_string):
        validations = CourseValidation.get_course_validations(course_key_string)
        return [v.readable_name for v in validations]

    def _unicodize(self, item):
        item_unicoded = item
        try:
            if isinstance(item, str) or isinstance(item, unicode):
                try:
                    item_unicoded = unicode(item, encoding="utf-8")
                except TypeError:
                    item_unicoded = item
            elif isinstance(item, dict):
                item_unicoded = dict()
                for k in item.keys():
                    item_unicoded[k] = self._unicodize(item[k])
            elif isinstance(item, list):
                item_unicoded = list(self._unicodize(k) for k in item)

        except Exception:
            pass
        return item_unicoded
