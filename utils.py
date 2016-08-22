# -*- coding: utf-8 -*-
from collections import namedtuple
import json
from datetime import timedelta as td
import datetime
import urllib
from django.utils.translation import ugettext as _
from .settings import PATH_SAVED_REPORTS
import os


Report = namedtuple("Report", ["name", "head", "body", "warnings"])


def _youtube_time_expand(duration):
    timeunits = {
        'w':604800,
        'd':86400,
        'h':3600,
        'm':60,
        's':1,
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


def build_items_tree(items):
    """Построение дерева курса с корнем в итеме с category='course'"""
    course_root = None
    for num, i in enumerate(items):
        if i.category=="course":
            course_root = num
    if course_root is None:
        raise ValueError(_("No course root in {}").format([i.category for i in items]))
    edges = []
    ids = [i.url_name for i in items]

    def deep_search(item_num):
        item = items[item_num]
        children_ids = [x.url_name for x in item.get_children()]
        children_nums = [num for num, x in enumerate(ids) if x in children_ids]
        for c in children_nums:
            edges.append([item_num, c])
            deep_search(c)

    deep_search(course_root)
    return course_root, edges


def _print_all(item):
    ats = dir(item)
    for at in ats:
        try:
            t = getattr(item, at)
            if callable(t):
                print(at, "callable")
            else:
                print(at, t)
        except Exception as e:
            print(at, e.message)


def youtube_duration(video_id):
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
    if  not len(all_data):
        return 0, _("Can't find video with such id on youtube.")

    contentDetails = all_data[0]["contentDetails"]
    duration = _youtube_time_expand(contentDetails["duration"])
    dur = td(seconds=duration)
    return 1, dur


def edx_id_duration(edx_video_id):
    """
    Определяет длительность видео по предоставленному edx_video_id
    Returns: 1, Длительность
    или      0, текст ошибки
    """
    try:
        from openedx.core.djangoapps.video_evms.api import get_video_info
    except ImportError:
        return _("Can't check edx video id: no api")
    video = get_video_info(edx_video_id)
    if not video:
        return 0, _("No response from server.")
    if not video:
        return 0, _("No video for this edx_video_id:{}".format(edx_video_id))
    temp = video.get("duration", _("Error: didn't get duration from server"))
    dur = td(seconds=int(float(temp)))
    return 1, dur


def map_to_utf8(d):
    # iterate over the key/values pairings
    n = dict()
    for k, v in d.items():
        # if v is a list join and encode else just encode as it is a string
        n[k] = [json.dumps(z) for z in v] if isinstance(v, list) else json.dumps(v)
    return n


def dicts_to_csv(dict_datas, fields, path, delim=','):
    delim = unicode(delim)
    with open(path, "w") as file:
        header = u",".join(fields)
        file.write(header.encode("utf8") + "\n")
        for pr in dict_datas:
            line = delim.join([str(json.dumps(unicode(pr[k]))) for k in fields])
            file.write(line.encode("utf8") + "\n")

def last_course_validation(course_key):
    all_reports = os.listdir(PATH_SAVED_REPORTS)
    this_course_reports = [r for r in all_reports if str(course_key) in r]
    if not this_course_reports:
        return None, None
    reporter_name, report_date = [], []
    today = datetime.datetime.now()
    for r in this_course_reports:
        _, name, date = r.strip(".csv").split("__")
        date_obj = datetime.datetime.strptime(date, "%Y-%m-%d_%H:%M:%S.%f")
        reporter_name.append(name)
        report_date.append(date_obj)
    deltas = [today - d for d in report_date]
    ind = deltas.index(min(deltas))
    return reporter_name[ind], report_date[ind]


import time

def timeit(method):

    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        print '%r (%r, %r) %2.2f sec' % \
              (method.__name__, args, kw, te-ts)
        return result

    return timed

def format_timdelta(tdobj):
    s = tdobj.total_seconds()
    return u"{:.0f}:{:.0f}:{:.0f}".format(s // 3600, s % 3600 // 60, s % 60)


def check_special_exam(seq):
    """
    Проверяет является ли объект seq специальным экзаменом,
    т.е. верно ли хотя бы одно поле
    :param seq:
    :return:
    """
    fields = ['is_entrance_exam',
              'is_practice_exame',
              'is_proctored_exam',
              'is_time_limited'
              ]
    answ = sum([getattr(seq, y, False) for y in fields])
    return answ