# -*- coding: utf-8 -*-
import json
import logging
from collections import Counter

from contentstore.course_group_config import GroupConfiguration
from django.utils.translation import ugettext as _
from models.settings.course_grading import CourseGradingModel
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore

from course_validator.mixins import VideoMixin, ReportIOMixin
from openedx.core.djangoapps.course_groups.cohorts import get_course_cohorts, get_course_cohort_settings
from .settings import *
from .utils import Report


class CourseValid(VideoMixin, ReportIOMixin):
    """Проверка сценариев и формирование логов"""

    scenarios_names_dict = {
            "grade":_("Grade"),
            "special_exams":_("Special exams"),
            "advanced_modules": _("Advanced Modules"),
            "group":_("Group"),
            "module":_("Module"),
            "cohorts":_(" Cohorts "),
            "proctoring":_("Proctoring"),
            "dates":_("Dates"),
            "items_visibility_by_group":_("Items visibility by group"),
            "response_types":_("Response types"),
            "video":_("Video full"),
            "openassessment":_("Open Response Assessment"),

        }
    costly_scenarios = [
            "video",
            "dates",
        ]

    def __init__(self, request, course_key_string):
        self.request = request
        self.store = modulestore()
        self.course_key_string = course_key_string
        self.course_key = CourseKey.from_string(course_key_string)
        self.reports = []

    def get_new_validation(self, form_data):
        self.items = self.store.get_items(self.course_key)
        scenarios = [s for s in form_data.keys() if s in CourseValid.scenarios_names_dict]
        self._validate_scenarios(scenarios)
        self.send_log()
        return self.get_sections_for_rendering()

    def get_old_validation(self, form_data):
        readable = form_data["previous-report"][0]
        path = self.get_path_for_readable(readable)
        self.reports = self.read_validation(path)
        return self.get_sections_for_rendering()

    def _validate_scenarios(self, scenarios=None):
        """Запуск всех сценариев проверок"""
        try:
            import edxval.api as edxval_api
            val_profiles = ["youtube", "desktop_webm", "desktop_mp4"]
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
        self.write_validation(self.reports)

    def get_sections_for_rendering(self):
        sections = []
        for r in self.reports:
            sec = {"name": r.name, "passed": not bool(len(r.warnings))}
            if len(r.body):
                sec["output"] = True
                sec["head"] = r.head
                sec["body"] = r.body
            else:
                sec["output"] = False

            if not len(r.warnings):
                sec["warnings"] = ["OK"]
            else:
                sec["warnings"] = r.warnings
            sections.append(sec)
        return sections

    def send_log(self):
        """
        Посылает в лог информацию о проверки в виде JSON:
        username, user_email: Данные проверяющего
        datetime: Дата и время
        passed: Пройдены ли без предупреждений проверки:
        warnings: словарь предупреждений (название проверки-предупреждения)
        """
        user = self.request.user
        log = {"username": user.username, "user_email": user.email, "datetime": str(datetime.now())}
        results = []
        passed = True
        for r in self.reports:
            temp = ";".join(r.warnings)
            if not len(temp):
                temp = "OK"
            else:
                passed = False
            results.append({r.name: temp})
        log["warnings"] = results
        log["passed"] = passed
        mes = json.dumps(log)
        if passed:
            logging.info(mes)
        else:
            logging.warning(mes)

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
        for v in video_items:
            chap = get_chapter(v)
            chap_name = chap.display_name
            if chap_name in chapter_video_dict.keys():
                chapter_video_dict[chap_name].append(v)
            else:
                chapter_video_dict.update({chap_name:[v]})
                chapter_objects.append(chap)
        for chap in chapter_video_dict:
            chapter_video_dict[chap].sort(key=lambda x:x.start)
        chapter_objects.sort(key=lambda x:x.start)
        # Суммирование длительностей всех видео
        total = timedelta()
        wrap_valmark = lambda s: unicode("<div class='valmark'>"+ s + "</div>")
        chap_strs = []
        #Проверка наличия апи - если его нет, то не надо для каждого видео стучать в evms
        api_found = self._api_set_up()

        if not api_found:
            warnings.append(_("Api is not set up. Contact your administrator"))
        for chap in chapter_objects:
            chap_total = timedelta()
            chap_key = chap.display_name
            full_chapter_strs = []
            for v in chapter_video_dict[chap_key]:
                mes = ""
                success = 0
                if not (v.youtube_id_1_0) and not (v.edx_video_id):
                    mes = _("No source for video '{name}' in '{vertical}' ").\
                        format(name=v.display_name, vertical=v.get_parent().display_name)
                    warnings.append(mes)

                if v.youtube_id_1_0:
                    success, cur_mes = self.youtube_duration(v.youtube_id_1_0)
                    if not success:
                        warnings.append(cur_mes)
                    mes = cur_mes

                if v.edx_video_id:
                    if api_found:
                        success, cur_mes = self.edx_id_duration(v.edx_video_id)
                        if not success:
                            warnings.append(cur_mes)
                        mes = cur_mes

                if success:
                    counted_time = mes
                    total += counted_time
                    chap_total += mes
                    if mes>timedelta(seconds=MAX_VIDEO_DURATION):
                        warnings.append(_("Video {} is longer than 3600 secs").format(v.display_name))

                full_chapter_strs.append([v.display_name, unicode(mes)])
            full_chapter_strs.insert(0, [wrap_valmark(chap_key),
                                        wrap_valmark(self.format_timdelta(chap_total))])
            video_strs.extend(full_chapter_strs)
            chap_strs.append([chap_key,
                                 self.format_timdelta(chap_total)
                                 ])

        head = [_("Video name"), _("Video duration(sum: {})").format(self.format_timdelta(total))]
        head_chapter = [_("Chapter name"), _("Chapter summary video time")]
        results_full = Report(name=_("Video full"),
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
        for g in graders:
            grade_strs.append([unicode(g[attr]) for attr in grade_attributes])
            grade_types.append(unicode(g["type"]))
            grade_nums.append(unicode(g["min_count"]))
            try:
                grade_weights.append(float(g["weight"]))
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
                r = _("Task type '{name}': supposed to be {n1}, found in course {n2}").\
                    format(name=key, n1=grade_nums[num], n2=len(cur_items))
                report.append(r)
        # Проверка отсутствия в материале курсе заданий с типом не указанным в настройках
        for item in grade_items:
            if item.format not in grade_types:
                r = _("Task of type '{}' in course, no such task type in grading settings")
                report.append(r)
        results = Report(name=_("Grade"),
            head=head,
            body=grade_strs,
            warnings=report,
            )
        return results

    def val_group(self):
        """Проверка наличия и использования в курсе групп"""
        with self.store.bulk_operations(self.course_key):
            course = self.store.get_course(self.course_key)
            content_group_configuration = GroupConfiguration.get_or_create_content_group(self.store, course)
        groups = content_group_configuration["groups"]

        is_g_used = lambda x: bool(len(x["usage"]))
        # запись для каждой группы ее использования
        group_strs = [[g["name"], str(is_g_used(g))] for g in groups]
        head = [_("Group name"), _("Group used")]
        report = []

        results = Report(name=_("Group"),
            head=head,
            body=group_strs,
            warnings=report,
            )
        return results

    def val_module(self):
        """Проверка отсутствия пустых блоков, подсчет количества каждой категории блоков"""
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
        additional_count_cat = COUNT_NLY_CAT
        secondary_cat = set(all_cat_dict.keys()) - set(primary_cat) \
                        - set(additional_count_cat)

        # Словарь категория:количество для категорий с подробным выводом
        verbose_dict = [(k, all_cat_dict[k]) for k in primary_cat + additional_count_cat]
        # Словарь категория:количество для категорий для элементов без подробного вывода
        silent_dict = {c: all_cat_dict[c] for c in secondary_cat}
        silent_sum = sum(silent_dict.values())

        xmodule_strs = [[str(k), str(v)] for k, v in verbose_dict]
        xmodule_strs.append([_("others"), unicode(silent_sum)])
        head = [_("Module type"), _("Module count")]
        report = []
        # Проверка отсутствия пустых элементов в перв кат кроме additional_count_cat
        check_empty_cat = [x for x in primary_cat]
        primary_items = [i for i in self.items if i.category in check_empty_cat]
        for i in primary_items:
            if not len(i.get_children()):
                s = _("Block '{name}'({cat}) doesn't have any inner blocks or tasks")\
                    .format(name=i.display_name, cat=i.category)
                report.append(s)
        results = Report(name=_("Module"),
            head=head,
            body=xmodule_strs,
            warnings=report
            )
        return results

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
            if not parent.start or not child.start:
                print("!?",parent.display_name, parent.start, child.display_name, child.start)
            if parent.start > child.start:
                mes = _("'{n1}' block has start date {d1}, but his parent '{n2}' has later start date {d2}").\
                    format(n1=child.display_name, d1=child.start,
                    n2=parent.display_name, d2=parent.start)
                report.append(mes)

        date_check = datetime.now(items[0].start.tzinfo) + timedelta(days=DELTA_DATE_CHECK)
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
        result = Report(name=_("Dates"),
            head=[],
            body=[],
            warnings=report,
            )
        return result

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
        result = Report(name=_(" Cohorts "),
            head=[_(" Cohorts "),_("Population")],
            body=cohort_strs,
            warnings=report,
            )
        return result

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

        result = Report(name=_("Proctoring"),
            head=[_("Parameter"), _("Value")],
            body=proctor_strs,
            warnings=[],
            )
        return result

    def val_items_visibility_by_group(self):
        """Составление таблицы видимости элементов для групп"""
        with self.store.bulk_operations(self.course_key):
            course = self.store.get_course(self.course_key)
            content_group_configuration = GroupConfiguration.get_or_create_content_group(self.store, course)
        groups = content_group_configuration["groups"]
        group_names = [g["name"] for g in groups]
        name = _("Items visibility by group")
        head = [_("Item type"),_("Usual student")] + group_names
        checked_cats = ["chapter",
             "sequential",
             "vertical",
             "problem",
             "video",
             ]

        get_items_by_type = lambda x: [y for y in self.items if y.category == x]

        # Словарь (категория - итемы)
        cat_items = dict([(t, get_items_by_type(t)) for t in checked_cats])

        # Словарь id группы - название группы
        group_id_dict = dict([(g["id"], g["name"]) for g in groups])

        conf_id = content_group_configuration["id"]
        gv_strs = []
        for cat in checked_cats:
            items = cat_items[cat]
            vis = dict((g, 0) for g in group_names)
            vis["student"] = 0
            for it in items:
                if conf_id not in it.group_access:
                    for key in group_names:
                        vis[key] += 1
                else:
                    ids = it.group_access[conf_id]
                    vis_gn_for_itme = [group_id_dict[i] for i in ids]
                    for gn in vis_gn_for_itme:
                        vis[gn] += 1
                if not it.visible_to_staff_only:
                    vis["student"] += 1

            item_category = "{}({})".format(cat, len(items))
            stud_vis_for_cat = str(vis["student"])

            cat_list = [item_category] + [stud_vis_for_cat] + [str(vis[gn]) for gn in group_names]
            cat_str = cat_list
            gv_strs.append(cat_str)

        return Report(name=name,
            head=head,
            body=gv_strs,
            warnings=[]
            )

    def val_response_types(self):
        """Считает по всем типам problem количество блоков в курсе"""
        problems = [i for i in self.items if i.category == "problem"]
        # Типы ответов. Взяты из common/lib/capa/capa/tests/test_responsetypes.py
        response_types = ["multiplechoiceresponse",
            "truefalseresponse",
            "imageresponse",
            "symbolicresponse",
            "optionresponse",
            "formularesponse",
            "stringresponse",
            "coderesponse",
            "choiceresponse",
            "javascriptresponse",
            "numericalresponse",
            "customresponse",
            "schematicresponse",
            "annotationresponse",
            "choicetextresponse",
        ]
        response_counts = dict((t, 0) for t in response_types)
        for prob in problems:
            text = prob.get_html()
            out = [prob.display_name]
            for resp in response_types:
                count = text.count("&lt;" + resp) + text.count("<" + resp)
                if count:
                    response_counts[resp] += 1
                    out.append(resp)
        name = _("Response types")
        head = [_("Type"),_("Counts")]
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
        return Report(name=name,
            head=head,
            body=rt_strs,
            warnings=warnings
        )

    def val_advanced_modules(self):
        """
        Выводить все подключенные к OpenEdx модули
        """
        course = self.store.get_course(self.course_key)
        advanced_modules = [[x] for x in course.advanced_modules]
        name = _("Advanced Modules")
        head = [_("Module name")]
        return Report(name=name,
                      head=head,
                      body=advanced_modules,
                      warnings=[]
        )

    def val_special_exams(self):
        sequentials = [i for i in self.items if i.category=='sequential']
        special_exams = [i for i in sequentials if self._check_special_exam(i)]
        head = [_("Exam name"),_("Exam chapter"),_("Grade name"), _("Start date"),
                  _("Duration limit"), _("Due date"), _("Is proctored exam"),
                  ]
        body = []
        for se in special_exams:
            name = se.display_name
            chapter_name = se.get_parent().display_name
            grade = unicode(se.format)
            start = str(se.start)
            if se.is_time_limited:
                duration = self.format_timdelta(timedelta(minutes=se.default_time_limit_minutes))
            else:
                duration = 'None'
            due_date = str(se.due)
            proctored = se.is_proctored_exam
            body.append([name, chapter_name, grade, start, duration, due_date, proctored])

        return Report(name=_("Special exams"),
                      head=head,
                      body=body,
                      warnings=[]
                      )

    def _check_special_exam(self, seq):
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

    def val_openassessment(self):
        openassessments = [i for i in self.items if i.category=="openassessment"]
        head = [_("Name"), _("Location"), _("Publishing date"), _("Start date"), _("Submission start"), _("Submission due"), _("Cohorts where visible"),
                _("Assessment steps")]
        body = []
        with self.store.bulk_operations(self.course_key):
            course = self.store.get_course(self.course_key)
            content_group_configuration = GroupConfiguration.get_or_create_content_group(self.store, course)
        groups = content_group_configuration["groups"]
        conf_id = content_group_configuration["id"]
        group_id_dict = dict([(g["id"], g["name"]) for g in groups])

        for oa in openassessments:
            current = []
            name = oa.display_name
            current.append(name)

            parent = oa.get_parent()
            location= u"{}, {}".format(parent.display_name, parent.get_parent().display_name)
            current.append(location)

            is_published = oa.published_on
            if is_published:
                current.append(str(is_published).split('.')[0])
            else:
                current.append(_("Not published"))
            start_date = oa.start
            current.append(str(start_date).split('+')[0])

            submission_start = oa.submission_start
            current.append(str(submission_start).split('+')[0])

            submission_due = oa.submission_due
            current.append(str(submission_due).split('+')[0])

            if conf_id in oa.group_access:
                accessed = oa.group_access[conf_id]
                visible_groups = u", ".join(group_id_dict[i] for i in accessed)
            else:
                visible_groups = _("Usual student")
            current.append(visible_groups)

            steps = oa.assessment_steps
            #current.append(u",".join(str(s) for s in steps))
            current.append(u",".join(str(s) for s in range(1,len(steps)+1)))

            body.append(current)
        return Report(name=self.scenarios_names_dict["openassessment"],
                      head=head,
                      body=body,
                      warnings=[]
                      )