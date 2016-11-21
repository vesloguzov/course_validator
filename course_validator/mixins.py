    # -*- coding: utf-8 -*-
import codecs
import datetime
from datetime import timedelta as td
from django.utils.translation import ugettext as _
import json
import logging
import os
import urllib
from .utils import validation_logger, Report
from .settings import *


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


class ReportIOMixin():
    """
    Сюда вынесены методы касающиеся чтения и записи отчетов
    """

    class SavedReport():
        """
        Класс для работы с названиями сохраненных файлов. Дает два полных предаставления:
        словарь с именем пользователя, course_key_string и датой(datetime)
        и название для файла отчета с .csv расширением
        """

        def __init__(self, dict_=None, relpath=None, **kwargs):
            if not (dict_ is None):
                self.dict = dict_
                self.relpath = self._dict2relpath(dict_)
                return
            if not relpath is None:
                self.relpath = relpath
                self.dict = self._relpath2dict(relpath)
                return
            course_key = kwargs.get("course_key", False)
            username = kwargs.get("username", False)
            date = kwargs.get("date", False)
            if course_key and username and date:
                self.dict = dict(course_key=course_key,
                                 username=username,
                                 date=date)
                self.relpath = self._dict2relpath(self.dict)

        def _dict2relpath(self, _dict):
            course_key = _dict["course_key"]
            username = _dict["username"]
            date_obj = _dict["date"]
            name_parts = [str(course_key), str(username),
                          self.str_date(date_obj).replace(" ", "_")]
            report_name = "__".join(name_parts) + ".csv"
            return report_name

        def _relpath2dict(self, relpath):
            d = lambda x, y, z: dict(course_key=x, username=y, date=z)

            try:
                current_report = relpath.split('.')
                if len(current_report) != 2:
                    return d(None, None, None)
                if current_report[-1] != 'csv':
                    return d(None, None, None)
                current_report = current_report[0]
                course_key, name, date = current_report.split("__")
                date_obj = datetime.datetime.strptime(date, "%Y-%m-%d_%H:%M:%S")
                return d(course_key, name, date_obj)
            except Exception as e:
                logging.error(str(e))
                return d(None, None, None)

        def readable(self):
            username = self.dict["username"]
            date_obj = self.dict["date"]
            name_parts = [str(username),
                          self.str_date(date_obj)]
            return ", ".join(name_parts)

        def str_date(self, date):
            if date is None:
                return u'No date'
            return str(date.replace(microsecond=0))

    @validation_logger
    def save_validation_report(self, validation):
        cls = self.__class__
        path_saved_reports = cls.get_path_saved_reports(self.course_key_string)
        try:
            saved_report = self.SavedReport(course_key=self.course_key_string,
                                            username=self.request.user.username,
                                            date=datetime.datetime.now()
                                            )
            report_relpath = saved_report.relpath
            if not os.path.exists(path_saved_reports):
                logging.error(
                    "Report '{}' was not saved: no such directory '{}'".format(report_relpath, path_saved_reports))
            report_abspath = path_saved_reports + report_relpath

            delim = u'\t'
            dict_datas = [r._asdict() for r in validation]
            fields = Report._fields
            with codecs.open(report_abspath, "w", encoding="utf-8") as file:
                header = delim.join(fields)
                file.write(header.encode("utf8") + "\n")
                for pr in dict_datas:
                    line = delim.join((json.dumps(self._unicodize(pr[k]), ensure_ascii=False)) for k in fields)
                    file.write(line + "\n")

            logging.info("Report is saved:{}".format(report_abspath))

        except Exception as e:
            logging.error("Report wasn't saved:{}".format(str(e)))

    @validation_logger
    def load_validation_report(self, path, delim=u'\t'):
        reports = []
        with codecs.open(path, "r", encoding="utf-8") as file:
            header = file.readline()  # Don't need it actually
            for line in file:
                report_fields = [json.loads(field) for field in line.strip().split(delim)]
                kwargs = dict((Report._fields[k], report_fields[k]) for k, _ in enumerate(Report._fields))
                reports.append(Report(**kwargs))
        return reports

    def get_path_for_readable(self, readable):
        cls = self.__class__
        paths = cls.get_course_report_abspaths(self.course_key_string)
        readables = cls.get_saved_reports_for_course(self.course_key_string)
        for num, path in enumerate(paths):
            if readables[num] == readable:
                return path
        return False

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
            pass
        return itemn

    @classmethod
    def get_path_saved_reports(cls, course_key_string):
        from .settings import PATH_SAVED_REPORTS_TEMPLATE
        attributes = course_key_string.split(':')[-1]
        organization, course_number, course_run = attributes.split('+')
        return PATH_SAVED_REPORTS_TEMPLATE.format(organization=organization,
                                                  course_number=course_number,
                                                  course_run=course_run
                                                  )

    @classmethod
    def get_course_report_abspaths(cls, course_key_string):
        """
            Находит в директории path_saved_reports последнюю проверку для
            course_key и возвращает словарь c username, date и path последней проверки
            :param course_key:
            :param path_saved_reports:
            :return:
            """
        path_saved_reports = cls.get_path_saved_reports(course_key_string)

        if not os.path.exists(path_saved_reports):
            return None
        all_reports = os.listdir(path_saved_reports)
        supposed_course_reports = [report_name for report_name in all_reports if course_key_string in report_name]
        if not supposed_course_reports:
            return None

        confirmed_course_report_files = []
        for report_name in supposed_course_reports:
            try:
                current_report = report_name.split('.')
                if len(current_report) != 2:
                    continue
                if current_report[-1] != 'csv':
                    continue
                confirmed_course_report_files.append(path_saved_reports + report_name)
            except ValueError as e:
                logging.error(e)

        return confirmed_course_report_files

    @classmethod
    def get_saved_reports_for_course(cls, course_key_string):
        report_files = cls.get_course_report_abspaths(course_key_string)
        if report_files is None:
            return None
        processing = lambda x: (cls.SavedReport(relpath=x.split("/")[-1]))
        saved_reports = [processing(x) for x in report_files]
        saved_reports_sorted = sorted(saved_reports, key=lambda x: x.dict["date"], reverse=True)
        return [s.readable() for s in saved_reports_sorted]



