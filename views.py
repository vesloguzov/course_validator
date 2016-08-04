# -*- coding: utf-8 -*-
from .validator import CourseValid
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore
from edxmako.shortcuts import render_to_response

@login_required
def course_validator_handler(request, course_key_string=None):
    """Обработчик url на проверку курса"""
    if request.method != 'GET':
        return redirect(reverse('course_handler', course_key_string))
    CV = CourseValid(request, course_key_string)
    CV.validate()
    CV.send_log()
    course_key = CourseKey.from_string(course_key_string)
    course_module = modulestore().get_course(course_key)

    return render_to_response("dev_course_validator.html", {

            "sections":CV.get_sections_for_rendering(),
            "context_course":course_module
            })
