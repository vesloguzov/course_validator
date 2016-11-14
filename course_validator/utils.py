# -*- coding: utf-8 -*-
import datetime
from collections import namedtuple
import os
import time
import logging
from functools import wraps

Report = namedtuple("Report", ["name", "head", "body", "warnings"])


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


def find_course_validation(course_key, path_saved_reports, parameters=None):
    """
    Находит в директории path_saved_reports последнюю проверку для
    course_key и возвращает словарь c username, date и path последней проверки
    :param course_key:
    :param path_saved_reports:
    :return:
    """
    if not os.path.exists(path_saved_reports):
        return None
    all_reports = os.listdir(path_saved_reports)
    this_course_reports = [r for r in all_reports if str(course_key) in r]
    if not this_course_reports:
        return None
    reporter_name, report_date = [], []
    today = datetime.datetime.now()

    for r in this_course_reports:
        try:
            current_report = r.split('.')
            if len(current_report) != 2:
                continue
            if current_report[-1] != 'csv':
                continue
            current_report = current_report[0]
            _, name, date = current_report.split("__")
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d_%H:%M:%S")
            reporter_name.append(name)
            report_date.append(date_obj)
        except ValueError as e:
            logging.error(e)

    if not report_date:
        return None
    deltas = [today - d for d in report_date]
    ind_of_latest = deltas.index(min(deltas))


    #return {
    #    "username": reporter_name[ind_of_latest],
    #    "date": report_date[ind_of_latest],
    #    "path": path_saved_reports + this_course_reports[ind_of_latest]
    #}


def get_path_saved_reports(course_key_string):
    from .settings import PATH_SAVED_REPORTS_TEMPLATE
    attributes = course_key_string.split(':')[-1]
    organization, course_number, course_run = attributes.split('+')
    return PATH_SAVED_REPORTS_TEMPLATE.format(organization=organization,
                                              course_number=course_number,
                                              course_run=course_run
                                              )


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        print '%r (%r, %r) %2.2f sec' % \
              (method.__name__, args, kw, te - ts)
        return result

    return timed


def validation_logger(method):
    _n = method.__name__.split("_")
    name = method.__name__

    if len(_n) > 1:
        if _n[0] == "val":
            name = "Validation '{}'".format(" ".join(_n[1:]))

    @wraps(method)
    def wrap(*args, **kwargs):
        message_in = "{} started.".format(name)
        message_out = "{} finished ".format(name)
        logging.info(message_in)
        ts = time.time()
        result = method(*args,**kwargs)
        te = time.time()

        message_out += "({:1.3f} s).".format(float(te-ts))
        logging.info(message_out)
        return result
    return wrap