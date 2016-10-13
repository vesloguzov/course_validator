# -*- coding: utf-8 -*-
import datetime
import json
import logging
import urllib
from datetime import timedelta as td

import codecs
import os
from django.utils.translation import ugettext as _

from course_validator.utils import Report


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
        api_key = "AIzaSyCnxGGegKJ1_R-cEVseGUrAcFff5VHXgZ0"
        searchUrl = "https://www.googleapis.com/youtube/v3/videos?id=" + video_id + "&key=" + api_key + "&part=contentDetails"
        try:
            response = urllib.urlopen(searchUrl).read()
        except IOError:
            return 0, _("No response from server.")
        data = json.loads(response)
        if data.get("error", False):
            return 0, _("Error occured while video duration check:{}").format(data["error"])
        all_data = data["items"]
        if not len(all_data):
            return 0, _("Can't find video with such id on youtube.")

        contentDetails = all_data[0]["contentDetails"]
        duration = self._youtube_time_expand(contentDetails["duration"])
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

    def _api_set_up(self):
        try:
            from openedx.core.djangoapps.video_evms.api import get_video_info
        except ImportError:
            return 0
        return 1

    def _youtube_time_expand(self, duration):
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

    def format_timdelta(self,tdobj):
        s = tdobj.total_seconds()
        return u"{:.0f}:{:.0f}:{:.0f}".format(s // 3600, s % 3600 // 60, s % 60)


class ReportIOMixin():
    """
    Сюда вынесены методы касающиеся чтения и записи отчетов
    """

    def write_validation(self, validation):
        try:

            report_name = self.reportinfo_to_string(self.course_key,
                                                    self.request.user.username,
                                                    datetime.datetime.now()
                                                    )
            if not os.path.exists(self.path_saved_reports):
                logging.warning(
                    "Report '{}' was not saved: no such directory '{}'".format(report_name, self.path_saved_reports))
            report_absolute_name = self.path_saved_reports + report_name

            delim = u'\t'
            dict_datas = [r._asdict() for r in validation]
            fields = Report._fields

            with codecs.open(report_absolute_name, "w", encoding="utf-8") as file:
                header = delim.join(fields)
                file.write(header.encode("utf8") + "\n")
                for pr in dict_datas:
                    line = delim.join((json.dumps(self._unicodize(pr[k]), ensure_ascii=False)) for k in fields)
                    file.write(line + "\n")
            logging.info("Report is saved:{}".format(report_absolute_name))

        except Exception as e:
            logging.error("Report wasn't saved:{}".format(str(e)))

    def read_validation(self, path, delim=u'\t'):
        reports = []
        with codecs.open(path, "r", encoding="utf-8") as file:
            header = file.readline()  # Don't need it actually
            for line in file:
                report_fields = [json.loads(field) for field in line.strip().split(delim)]
                kwargs = dict((Report._fields[k], report_fields[k]) for k, _ in enumerate(Report._fields))
                reports.append(Report(**kwargs))
        return reports

    def string_to_reportinfo(self, string):
        try:
            current_report = string.split('.')
            if len(current_report) != 2:
                return None, None, None
            if current_report[-1] != 'csv':
                return None, None, None
            current_report = current_report[0]
            course_key, name, date = current_report.split("__")
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d_%H:%M:%S")
            return course_key, name, date_obj
        except Exception as e:
            logging.error(str(e))
            return None, None, None

    def reportinfo_to_string(self, course_key, name, date_obj):
        name_parts = [str(course_key), str(name),
                      str(date_obj.replace(microsecond=0)).replace(" ", "_")]
        report_name = "__".join(name_parts) + ".csv"
        return report_name

    def _unicodize(self, item):
        itemn = item
        try:
            if isinstance(item, str) or isinstance(item, unicode):
                try:
                    itemn = unicode(item, encoding="utf-8")
                except TypeError:
                    itemn = item
            elif isinstance(item, dict):
                itemn = dict()
                for k in item.keys():
                    itemn[k] = self._unicodize(item[k])
            elif isinstance(item, list):
                itemn = list(self._unicodize(k) for k in item)

        except Exception as e:
            print("!", e, item)
        return itemn