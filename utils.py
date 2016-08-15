# -*- coding: utf-8 -*-
from collections import namedtuple
import json
from datetime import timedelta as td
import urllib
from django.utils.translation import ugettext as _



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


