# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
#Если длина видео в секундах больше значения этой переменной выводится предупреждение
MAX_VIDEO_DURATION = 3600

# См validator.py:CourseValid.val_xmodule
COUNT_N_CHECK_CAT = ["course",
               "chapter",
               "sequential",
               "vertical",
                ]
COUNT_NLY_CAT = ["problem",
                "video",
            ]
# Путь где сохраняются отчеты
PATH_SAVED_REPORTS = "/edx/var/edxapp/course_validation/"

# Настройка момента, относительно которого проводится проверка дат
# 2 - послезавтра, 1- завтра, 0 - сегодня, -1 -вчера
DELTA_DATE_CHECK = 1

APPEND_SLASH = False
