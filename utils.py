# -*- coding: utf-8 -*-
import datetime
import json
import urllib
from collections import namedtuple
import os
from django.utils.translation import ugettext as _
import codecs

Report = namedtuple("Report", ["name", "head", "body", "warnings"])


def build_items_tree(items):
    """Построение дерева курса с корнем в итеме с category='course'"""
    course_root = None
    for num, i in enumerate(items):
        if i.category == "course":
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


def map_to_utf8(d):
    # iterate over the key/values pairings
    n = dict()
    for k, v in d.items():
        # if v is a list join and encode else just encode as it is a string
        n[k] = [json.dumps(z) for z in v] if isinstance(v, list) else json.dumps(v)
    return n


def _unicodize(item):
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
                itemn[k] = _unicodize(item[k])
        elif isinstance(item, list):
            itemn = list(_unicodize(k) for k in item)

    except Exception as e:
        print("!", e, item)
    return itemn


def dicts_to_csv(dict_datas, fields, path, delim=u'\t'):
    delim = unicode(delim)
    with codecs.open(path, "w", encoding="utf-8") as file:
        header = delim.join(fields)
        file.write(header.encode("utf8") + "\n")
        for pr in dict_datas:
            line = delim.join((json.dumps(_unicodize(pr[k]), ensure_ascii=False)) for k in fields)
            file.write(line + "\n")


def last_course_validation(course_key, path_saved_reports):
    if not os.path.exists(path_saved_reports):
        return None, None
    all_reports = os.listdir(path_saved_reports)
    this_course_reports = [r for r in all_reports if str(course_key) in r]
    if not this_course_reports:
        return None, None
    reporter_name, report_date = [], []
    today = datetime.datetime.now()
    for r in this_course_reports:
        try:
            current_report = r.split('.')
            if len(current_report) != 2:
                continue
            if current_report[1] != 'csv':
                continue
            current_report = current_report[0]
            _, name, date = current_report.split("__")
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d_%H:%M:%S.%f")
            reporter_name.append(name)
            report_date.append(date_obj)
        except ValueError:
            pass
    if not report_date:
        return None, None
    deltas = [today - d for d in report_date]
    ind = deltas.index(min(deltas))
    return reporter_name[ind], report_date[ind]


def path_saved_reports(course_key_string):
    from .settings import PATH_SAVED_REPORTS_TEMPLATE
    attributes = course_key_string.split(':')[-1]
    organization, course_number, course_run = attributes.split('+')
    return PATH_SAVED_REPORTS_TEMPLATE.format(organization=organization,
                                              course_number=course_number,
                                              course_run=course_run
                                              )


import time


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        print '%r (%r, %r) %2.2f sec' % \
              (method.__name__, args, kw, te - ts)
        return result

    return timed
