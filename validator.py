# -*- coding: utf-8 -*-

import datetime
from datetime import timedelta
import json
import logging
from django.dispatch import receiver

from contentstore.course_group_config import GroupConfiguration
from contentstore.utils import reverse_usage_url
from collections import Counter
from django.utils.translation import ugettext as _
from cms.djangoapps.models.settings.course_grading import CourseGradingModel
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.course_groups.cohorts import get_course_cohorts, get_course_cohort_settings
from xmodule.modulestore.django import modulestore

from .mixins import VideoMixin, ReportIOMixinDB
from .settings import *
from .utils import Report, validation_logger
from .analyzer import ChangeAnalyzer


class Validations:

    @validation_logger
    def val_video(self):
        """
        Проверка видео: наличие ссылки на YouTube либо edx_video_id.
        При наличии выводится длительнось видео, при отсутствии выводится и
        пишется в отчет
        предупреждение
        """
        items = self.items
        video_items = [i for i in items if i.category == "video"]
        video_strs = []
        warnings = []

        chapter_video_dict = dict()
        get_chapter = lambda x: x.get_parent().get_parent().get_parent()
        chapter_objects = []
        for vid in video_items:
            chap = get_chapter(vid)
            chap_name = chap.display_name
            if chap_name in chapter_video_dict.keys():
                chapter_video_dict[chap_name].append(vid)
            else:
                chapter_video_dict.update({chap_name: [vid]})
                chapter_objects.append(chap)
        for chap in chapter_video_dict:
            chapter_video_dict[chap].sort(key=lambda x: x.start)
        chapter_objects.sort(key=lambda x: x.start)
        # Суммирование длительностей всех видео
        total = timedelta()
        bold = lambda s: unicode("<div class='valmark'>" + s + "</div>")
        chap_strs = []
        # Проверка наличия апи - если его нет, то не надо для каждого видео стучать в evms
        api_found = self._api_set_up()

        if not api_found:
            warnings.append(_("Api is not set up. Contact your administrator"))
        for chap in chapter_objects:
            chap_total = timedelta()
            chap_key = chap.display_name
            full_chapter_strs = []
            for vid in chapter_video_dict[chap_key]:
                message_or_time = ""
                success = 0
                if not vid.youtube_id_1_0 and not vid.edx_video_id:
                    message_or_time = _("No source for video '{name}' in '{vertical}' "). \
                        format(name=vid.display_name, vertical=vid.get_parent().display_name)
                    warnings.append(message_or_time)

                if vid.youtube_id_1_0:
                    success, message = self.youtube_duration(vid.youtube_id_1_0)
                    if not success:
                        warnings.append(message)
                    message_or_time = message

                if vid.edx_video_id:
                    if api_found:
                        success, message = self.edx_id_duration(vid.edx_video_id)
                        if not success:
                            warnings.append(message)
                        message_or_time = message

                if success:
                    counted_time = message_or_time
                    total += counted_time
                    chap_total += message_or_time
                    if message_or_time > timedelta(seconds=MAX_VIDEO_DURATION):
                        warnings.append(_("Video {} is longer than 3600 secs").format(vid.display_name))

                full_chapter_strs.append([vid.display_name, unicode(message_or_time)])
            chapter_summary = [bold(chap_key), bold(unicode(self.format_timedelta(chap_total)))]
            full_chapter_strs.insert(0, chapter_summary)
            video_strs.extend(full_chapter_strs)
            chap_strs.append([chap_key,
                              self.format_timedelta(chap_total)
                              ])

        head = [_("Video name"), _("Video duration(sum: {})").format(self.format_timedelta(total))]
        head_chapter = [_("Chapter name"), _("Chapter summary video time")]
        results_full = Report(name=self.scenarios_names["video"],
                              head=head,
                              body=video_strs,
                              warnings=warnings,
                              )
        results_short = Report(name=_("Video short"),
                               head=head_chapter,
                               body=chap_strs,
                               warnings=[],
                               )
        return [results_short, results_full]

    @validation_logger
    def val_grade(self):
        """
        Проверка оценок:
        1)совпадение указанного и имеющегося количества заданий в каждой проверяемой категории,
        2)проверка равенства 100 суммы весов категории
        3)Отсутствие в курсе заданий с типом, не указанным в настройках
        """
        report = []
        course_details = CourseGradingModel.fetch(self.course_key)
        graders = course_details.graders
        grade_strs = []
        grade_attributes = ["type", "min_count", "drop_count", "weight"]
        grade_types = []
        grade_nums = []
        grade_weights = []

        # Вытаскиваем типы и количество заданий, прописанных в настройках
        for grd in graders:
            grade_strs.append([unicode(grd[attr]) for attr in grade_attributes])
            grade_types.append(unicode(grd["type"]))
            grade_nums.append(unicode(grd["min_count"]))
            try:
                grade_weights.append(float(grd["weight"]))
            except ValueError:
                report.append(_("Error occured during weight summation"))

        head = [_("Grade name"), _("Grade count"), _("Grade kicked"), _("Grade weight")]

        # Проверка суммы весов
        if sum(grade_weights) != 100:
            report.append(_("Tasks weight sum({}) is not equal to 100").format(sum(grade_weights)))

        # Проверка совпадения настроек заданий с материалом курса
        grade_items = [i for i in self.items if i.format is not None]
        for num, key in enumerate(grade_types):
            cur_items = [i for i in grade_items if unicode(i.format) == key]
            if len(cur_items) != int(grade_nums[num]):
                r = _("Task type '{name}': supposed to be {n1}, found in course {n2}"). \
                    format(name=key, n1=grade_nums[num], n2=len(cur_items))
                report.append(r)
        # Проверка отсутствия в материале курсе заданий с типом не указанным в настройках
        for item in grade_items:
            if item.format not in grade_types:
                report.append(_("Task of type '{}' in course, no such task type in grading settings"))

        results = Report(name=self.scenarios_names["grade"],
                         head=head,
                         body=grade_strs,
                         warnings=report,
                         )
        return results

    @validation_logger
    def val_group(self):
        """Проверка наличия и использования в курсе групп"""
        with self.store.bulk_operations(self.course_key):
            course = self.store.get_course(self.course_key)
            content_group_configuration = GroupConfiguration.get_or_create_content_group(self.store, course)
        groups = content_group_configuration["groups"]

        is_group_used = lambda x: bool(len(x["usage"]))
        # запись для каждой группы ее использования
        group_strs = [[g["name"], str(is_group_used(g))] for g in groups]
        head = [_("Group name"), _("Group used")]

        results = Report(name=self.scenarios_names["group"],
                         head=head,
                         body=group_strs,
                         warnings=[],
                         )
        return results

    @validation_logger
    def val_module(self):
        """Проверка отсутствия пустых блоков, подсчет количества каждой категории блоков"""
        head = [_("Module type"), _("Module count")]

        all_cat_dict = Counter([i.category for i in self.items])
        """
        Все категории разделены на первичные(ниже) и
        вторичные - problems, video, polls итд - записывается в others
        Элементы каждой первичной категории подсчитывается и выводятся.
        Для вторичных категорий выводится только сумма элементов всех
        вторичных категорий
        """
        primary_cat = COUNT_N_CHECK_CAT
        """
        Для additional_count_cat НЕ делается проверка вложенных блоков, но
        делается подсчет элементов
        """
        additional_count_cat = COUNT_ONLY_CAT
        secondary_cat = set(all_cat_dict.keys()) - set(primary_cat) \
                        - set(additional_count_cat)

        # Словарь категория:количество для категорий с подробным выводом
        verbose_dict = dict((k, (all_cat_dict[k])) for k in primary_cat + additional_count_cat)
        # Словарь категория:количество для категорий без подробного вывода
        silent_dict = {c: all_cat_dict[c] for c in secondary_cat}
        silent_dict_sum = sum(silent_dict.values())

        xmodule_names = self.xmodule_names
        rename = lambda x: xmodule_names.get(x, False) or x

        xmodule_strs = [[rename(k), str(v)] for k, v in verbose_dict.items()]
        xmodule_strs.append([xmodule_names["other"], unicode(silent_dict_sum)])
        report = []
        # Проверка отсутствия пустых элементов в перв кат кроме additional_count_cat
        check_empty_cat = [x for x in primary_cat]
        primary_items = [i for i in self.items if i.category in check_empty_cat]
        for prim_item in primary_items:
            if not len(prim_item.get_children()):
                report.append(_("Block '{name}'({cat}) doesn't have any inner blocks or tasks") \
                              .format(name=prim_item.display_name, cat=rename(prim_item.category)))

        results = Report(name=self.scenarios_names["module"],
                         head=head,
                         body=xmodule_strs,
                         warnings=report
                         )
        return results

    @validation_logger
    def val_dates(self):
        """
        Проверка дат:
        1)Даты старта дочерних блоков больше дат старта блока-родителя
        2)Наличие блоков с датой старта меньше $завтра
        3)Наличие среди стартовавших блоков видимых для студентов
        """
        report = []
        items = self.items
        # Проверка что дата старта child>parent
        for child in items:
            parent = child.get_parent()
            if not parent:
                continue
            if parent.start > child.start:
                mes = _("'{n1}' block has start date {d1}, but his parent '{n2}' has later start date {d2}"). \
                    format(n1=child.display_name, d1=child.start,
                           n2=parent.display_name, d2=parent.start)
                report.append(mes)

        date_check = datetime.datetime.now(items[0].start.tzinfo) + timedelta(days=DELTA_DATE_CHECK)
        # Проверка: Не все итемы имеют дату старта больше date_check
        items_by_date_check = [x for x in items if (x.start < date_check and x.category != "course")]

        if not items_by_date_check:
            report.append(_("All course release dates are later than {}").format(date_check))
        # Проверка: существуют элементы с датой меньше date_check, видимые для студентов и
        # это не элемент course
        elif all([not self.store.has_published_version(x) for x in items_by_date_check]):
            report.append(_("All stuff by tomorrow is not published"))
        elif all([x.visible_to_staff_only for x in items_by_date_check]):
            report.append(_("No visible for students stuff by tomorrow"))
        result = Report(name=self.scenarios_names["dates"],
                        head=[],
                        body=[],
                        warnings=report,
                        )
        return result

    @validation_logger
    def val_cohorts(self):
        """Проверка наличия в курсе когорт, для каждой вывод их численности либо сообщение об их отсутствии"""
        course = self.store.get_course(self.course_key)
        cohorts = get_course_cohorts(course)
        names = [getattr(x, "name") for x in cohorts]
        users = [getattr(x, "users").all() for x in cohorts]
        report = []
        cohort_strs = []
        for num, x in enumerate(names):
            cohort_strs.append([x, str(len(users[num]))])
        is_cohorted = get_course_cohort_settings(self.course_key).is_cohorted
        if not is_cohorted:
            cohort_strs = []
            report.append(_("Cohorts are disabled"))
        result = Report(name=self.scenarios_names["cohorts"],
                        head=[_(" Cohorts "), _("Population")],
                        body=cohort_strs,
                        warnings=report,
                        )
        return result

    @validation_logger
    def val_proctoring(self):
        """Проверка наличия proctored экзаменов"""
        course = self.store.get_course(self.course_key)
        check_avail_proctor_service = [_("Available proctoring services"),
                                       getattr(course, "available_proctoring_services", _("Not defined"))]
        check_proctor_service = [_("Proctoring Service"),
                                 unicode(getattr(course, "proctoring_service", _("Not defined")))]

        proctor_strs = [
            check_avail_proctor_service,
            check_proctor_service
        ]

        result = Report(name=self.scenarios_names["proctoring"],
                        head=[_("Parameter"), _("Value")],
                        body=proctor_strs,
                        warnings=[],
                        )
        return result

    @validation_logger
    def val_items_visibility_by_group(self):
        """Составление таблицы видимости элементов для групп"""
        with self.store.bulk_operations(self.course_key):
            course = self.store.get_course(self.course_key)
            content_group_configuration = GroupConfiguration.get_or_create_content_group(self.store, course)
        groups = content_group_configuration["groups"]
        group_names = [g["name"] for g in groups]
        head = [_("Item type"), _("Usual student")] + group_names
        visibility_by_group_categories = self.visibility_by_group_categories

        get_items_by_type = lambda x: [y for y in self.items if y.category == x]

        # Словарь (категория - итемы)
        cat_items = dict([(c, get_items_by_type(c)) for c in visibility_by_group_categories])

        # Словарь id группы - название группы
        group_id_dict = dict([(g["id"], g["name"]) for g in groups])

        conf_id = content_group_configuration["id"]
        group_visible_strs = []
        for cat in visibility_by_group_categories:
            items = cat_items[cat]
            vis = dict((g, 0) for g in group_names)
            vis["student"] = 0
            for it in items:
                if conf_id not in it.group_access:
                    for key in group_names:
                        vis[key] += 1
                else:
                    ids = it.group_access[conf_id]
                    item_vis_for_groups = [group_id_dict[i] for i in ids]
                    for group in item_vis_for_groups:
                        vis[group] += 1
                if not it.visible_to_staff_only:
                    vis["student"] += 1

            item_category = "{}({})".format(cat, len(items))
            stud_vis_for_cat = str(vis["student"])

            cat_list = [item_category] + [stud_vis_for_cat] + [str(vis[gn]) for gn in group_names]
            cat_str = cat_list
            group_visible_strs.append(cat_str)

        return Report(name=self.scenarios_names["items_visibility_by_group"],
                      head=head,
                      body=group_visible_strs,
                      warnings=[]
                      )

    @validation_logger
    def val_response_types(self):
        """Считает по всем типам problem количество блоков в курсе"""
        head = [_("Type"), _("Counts")]

        problems = [i for i in self.items if i.category == "problem"]
        response_types = self.response_types

        response_counts = dict((t, 0) for t in response_types)
        for prob in problems:
            text = prob.get_html()
            out = [prob.display_name]
            for resp in response_types:
                count = text.count("&lt;" + resp) + text.count("<" + resp)
                if count:
                    response_counts[resp] += 1
                    out.append(resp)
        rt_strs = []
        for resp in response_types:
            if response_counts[resp]:
                rt_strs.append([resp, str(response_counts[resp])])
        rt_strs.append([_("Responses sum"), unicode(sum(response_counts.values()))])
        rt_strs.append([_("Problems sum"), unicode(len(problems))])

        warnings = []

        if sum(response_counts.values()) < len(problems):
            warnings.append(_("Categorized {counted_num} problems out of {problems_num}").format(
                counted_num=sum(response_counts.values()), problems_num=len(problems)
            ))
        return Report(name=self.scenarios_names["response_types"],
                      head=head,
                      body=rt_strs,
                      warnings=warnings
                      )

    @validation_logger
    def val_advanced_modules(self):
        """
        Выводить все подключенные к OpenEdx модули
        """
        course = self.store.get_course(self.course_key)
        advanced_modules = [[x] for x in course.advanced_modules]
        head = [_("Module name")]
        return Report(name=self.scenarios_names["advanced_modules"],
                      head=head,
                      body=advanced_modules,
                      warnings=[]
                      )

    @validation_logger
    def val_special_exams(self):
        head = [_("Exam name"), _("Exam chapter"), _("Grade name"), _("Start date"),
                _("Duration limit"), _("Due date"), _("Is proctored exam"),
                ]

        def _check_special_exam(seq):
            """
            Проверяет является ли объект seq специальным экзаменом,
            т.е. верно ли хотя бы одно поле
            :param seq: Sequential
            :return: bool
            """
            is_special_exam_fields = self.is_special_exam_fields
            answ = sum([getattr(seq, y, False) for y in is_special_exam_fields])
            return bool(answ)

        sequentials = [i for i in self.items if i.category == 'sequential']
        special_exams = [i for i in sequentials if _check_special_exam(i)]

        body = []
        for se in special_exams:
            name = se.display_name
            chapter_name = se.get_parent().display_name
            grade = unicode(se.format)
            start = str(se.start)
            if se.is_time_limited:
                duration = self.format_timedelta(timedelta(minutes=se.default_time_limit_minutes))
            else:
                duration = 'None'
            due_date = str(se.due)

            proctored = se.is_proctored_exam
            body.append([name, chapter_name, grade, start, duration, due_date, proctored])
        return Report(name=self.scenarios_names["special_exams"],
                      head=head,
                      body=body,
                      warnings=[]
                      )

    @validation_logger
    def val_openassessment(self):
        head = [_("Name"), _("Location"), _("Publishing date"), _("Submission start"), _("Submission due"),
                _("Peer start"), _("Peer due"), _("Cohorts where visible"),
                _("Assessment steps")]

        openassessments = [i for i in self.items if i.category == "openassessment"]
        additional_info = {}
        body = []
        with self.store.bulk_operations(self.course_key):
            course = self.store.get_course(self.course_key)
            content_group_configuration = GroupConfiguration.get_or_create_content_group(self.store, course)
        groups = content_group_configuration["groups"]
        conf_id = content_group_configuration["id"]
        group_id_dict = dict([(g["id"], g["name"]) for g in groups])

        unicode2date = lambda x: datetime.strptime(x.split('+')[0], '%Y-%m-%dT%H:%M:%S')
        date2str = lambda x: x.strftime("%d.%m.%Y, %H:%M")
        for num, oa in enumerate(openassessments):
            url_key = (num, 0)
            additional_info[url_key] = reverse_usage_url("container_handler", oa.location)

            current = []
            name = oa.display_name
            current.append(name)

            parent = oa.get_parent()
            location = u"{}, {}".format(parent.display_name, parent.get_parent().display_name)
            current.append(location)

            publish_date = oa.published_on
            if publish_date:
                current.append(date2str(publish_date))
            else:
                current.append(_("Not published"))

            submission_start = unicode2date(oa.submission_start)
            current.append(date2str(submission_start))

            submission_due = unicode2date(oa.submission_due)
            current.append(date2str(submission_due))

            peer_start = unicode2date(oa.rubric_assessments[1]["start"])
            current.append(date2str(peer_start))

            peer_due = unicode2date(oa.rubric_assessments[1]["due"])
            current.append(date2str(peer_due))

            if conf_id in oa.group_access:
                accessed = oa.group_access[conf_id]
                visible_groups = u", ".join(group_id_dict[i] for i in accessed)
            else:
                visible_groups = _("Usual student")
            current.append(visible_groups)

            steps = oa.assessment_steps
            current.append(u",".join(str(s) for s in range(1, len(steps) + 1)))

            body.append(current)
        self.additional_info.update({self.scenarios_names["openassessment"]: additional_info})
        return Report(name=self.scenarios_names["openassessment"],
                      head=head,
                      body=body,
                      warnings=[]
                      )


class CourseValid(VideoMixin, ReportIOMixinDB, Validations):
    """
    Сюда вынесены методы, касающиеся ответов на запросы и процесса выполнения проверки в общем
    """

    scenarios_names = SCENARIO_NAMES
    xmodule_names = XMODULE_NAMES
    costly_scenarios = COSTLY_SCENARIOS
    is_special_exam_fields = IS_SPECIAL_EXAM_FIELDS
    visibility_by_group_categories = VISIBILITY_BY_GROUP_CATEGORIES
    response_types = RESPONSE_TYPES

    def __init__(self, request, course_key_string):
        self.request = request
        self.store = modulestore()
        self.course_key_string = course_key_string
        self.course_key = CourseKey.from_string(course_key_string)
        self.items = None
        self.reports = []
        self.additional_info = dict()

    def get_new_validation(self, form_data):
        self.items = self.store.get_items(self.course_key)
        scenarios = [s for s in form_data.keys() if s in CourseValid.scenarios_names]
        self._validate_scenarios(scenarios)
        self.send_log()
        return self.get_sections_for_rendering()

    def get_additional_info(self):
        info = {
            "costly_options": CourseValid.costly_scenarios,
            "validate_options": CourseValid.scenarios_names,
            "course_key_string": self.course_key_string,
        }
        info.update(self.additional_info)
        return info

    def get_old_validation(self, form_data):
        readable = form_data["previous-report"][0]
        course_id = form_data["course-id"][0]
        self.reports = self.load_validation_report(course_id, readable)
        return self.get_sections_for_rendering()

    def _validate_scenarios(self, scenarios=None):
        """Запуск сценариев проверок согласно списку scenarios"""
        try:
            import edxval.api as edxval_api
        except ImportError:
            logging.error("Course validator: no api for video")

        results = []

        for sc in scenarios:
            val_name = "val_{}".format(sc)
            validation = getattr(self, val_name)
            report = validation()
            if report is not None:
                if isinstance(report, list):
                    results.extend(report)
                else:
                    results.append(report)
        self.reports = results
        self.save_validation_report(self.reports)

    def get_sections_for_rendering(self):
        sections = []
        for rep in self.reports:
            sec = {"name": rep.name, "passed": not bool(len(rep.warnings))}
            if len(rep.body):
                sec["output"] = True
                sec["head"] = rep.head
                sec["body"] = rep.body
            else:
                sec["output"] = False

            if not len(rep.warnings):
                sec["warnings"] = ["OK"]
            else:
                sec["warnings"] = rep.warnings
            sections.append(sec)
        return sections

    @validation_logger
    def send_log(self):
        """
        Посылает в лог информацию о проверки в виде JSON:
        username, user_email: Данные проверяющего
        datetime: Дата и время
        passed: Пройдены ли без предупреждений проверки:
        warnings: словарь предупреждений (название проверки-предупреждения)
        """
        user = self.request.user
        log = {"username": user.username, "user_email": user.email, "datetime": str(datetime.datetime.now())}
        results = []
        passed = True
        for rep in self.reports:
            temp = ";".join(rep.warnings)
            if not len(temp):
                temp = "OK"
            else:
                passed = False
            results.append({rep.name: temp})
        log["warnings"] = results
        log["passed"] = passed
        mes = json.dumps(log)
        if passed:
            logging.info(mes)
        else:
            logging.warning(mes)
