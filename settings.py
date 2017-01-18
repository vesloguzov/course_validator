# -*- coding: utf-8 -*-
from django.utils.translation import ugettext as _


"""Настройки course_validator"""

"""
Путь куда сохраняются отчеты.
Может, но не обязана содержать переменные {organization}, {course_number}, {course_run}
"""
PATH_SAVED_REPORTS_TEMPLATE = "/edx/var/edxapp/data/{organization}/{course_number}/{course_run}/"


"""
Настройка момента, относительно которого проводится проверка дат
2 - послезавтра, 1- завтра, 0 - сегодня, -1 -вчера
"""
DELTA_DATE_CHECK = 1


"""
TLDR: Словарь {имя_метода_сценария(проверки) : отображаемое_название}

Словарь используется для двух целей.
1)В ключах перечислены названия проверок-сценариев(методов класса Validation) с отброшенным префиксом
'val_', т.е. 'grade' ~ Validation.val_grade. Ключи словаря используются для внутреннего обозначения доступных
 сценариев в форме валидатора, а при получении POST-запроса  - для определения, какие сценарии выбрал пользователь
2) Значения соответствуют отображаемым названиям для сценариев в форме
"""
SCENARIO_NAMES = {
    "grade": _("Grade"),
    "special_exams": _("Special exams"),
    "advanced_modules": _("Advanced Modules"),
    "group": _("Group"),
    "module": _("Module"),
    "cohorts": _(" Cohorts "),
    "proctoring": _("Proctoring"),
    "dates": _("Dates"),
    "items_visibility_by_group": _("Items visibility by group"),
    "response_types": _("Response types"),
    "video": _("Video full"),
    "openassessment": _("Open Response Assessment"),
}


"""
Перечисление долгих по выполнению сценариев.
Такие сценарии отключены в форме по умолчанию и при наведении на них мышки
выводится предупреждение.
Элементы должны входить в множество ключей SCENARIO_NAMES
"""
COSTLY_SCENARIOS = [
    "video",
    "dates",
]


"""
Настройка для сценария val_module.
Элементы категории COUNT_N_CHECK_CAT будут посчитаны, выведены как отдельная графа в результатах
и проверены на то, что они не пустые.
Элемент в COUNT_ONLY_CAT будут посчитаны и выведены как отдельная графа в результатах,
но НЕ будет проверено, что они не пустые.
"""
COUNT_N_CHECK_CAT = ["chapter",
               "sequential",
               "vertical",
                ]
COUNT_ONLY_CAT = ["problem",
                "video",
                  ]


"""
Настройка сценария val_module.
TLDR: {имя_категории: отображаемое название}
Ключи соответствуют item.category, для которых ведется отдельный подсчет.
Значения определяют название для соответствующей графы в таблице.

Можно также использовать ключа 'other' чтоб задать название соответствующей графы
"""
XMODULE_NAMES = {
    "chapter": _("Section"),
    "sequential": _("Subsection"),
    "vertical": _("Unit"),
    "problem": _("Problem"),
    "video": _("Video"),

    "other": _("Other")
}


"""
Настройка для сценария val_special_exams.
Элементы списка - аттрибуты, которые будут проверяться у объекта курса,
при истинности которых объект считается особым экзаменом.
"""
IS_SPECIAL_EXAM_FIELDS = ['is_entrance_exam',
                          'is_practice_exame',
                          'is_proctored_exam',
                          'is_time_limited'
                          ]


"""
Настройка для сценария visibility_by_group
Для каждой категории-ключа будет посчитано, сколько элементов
такой категории видит каждая группа. Значение ключа определяет отображаемое
название
"""
VISIBILITY_BY_GROUP_CATEGORIES = {
    "chapter": _("Section"),
    "sequential": _("Subsection"),
    "vertical": _("Unit"),
    "problem": _("Problem"),
    "video": _("Video"),

    "other": _("Other")
}


"""
Настройка для сценария response_types.
Перечисляет тэги, которые соответствуют разным типам problem
Взяты из common/lib/capa/capa/tests/test_responsetypes.py
"""
RESPONSE_TYPES = ["multiplechoiceresponse",
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


"""
Настройка сценария video
Если длина видео в секундах больше значения этой переменной выводится предупреждение
"""
MAX_VIDEO_DURATION = 3600


"""
Настройки для получения информации о видео с YouTube.
Для получения api_key:
        1.Зарегистрироваться на console.developers.google.com
        2. на главной YouTube API >YouTube Data API
        3. Включить Youtube Api
        4. В учетных данных (Credentials) взять ключ
"""
VALIDATOR_YOUTUBE_API_KEY = "AIzaSyCnxGGegKJ1_R-cEVseGUrAcFff5VHXgZ0"
VALIDATOR_YOUTUBE_PATTERN = "https://www.googleapis.com/youtube/v3/videos?id={video_id}&key=" + \
                  "{api_key}&part=contentDetails".format(api_key=VALIDATOR_YOUTUBE_API_KEY)
INSTALLED_APPS = []