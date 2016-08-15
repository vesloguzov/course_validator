# -*- coding: utf-8 -*-
from .validator import CourseValid
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore
from edxmako.shortcuts import render_to_response
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import ensure_csrf_cookie

__all__ = ["course_validator_handler"]

def reverse_validator_course_url(course_key):
    handler_name = "course_validator_handler"
    key_name = "course_key_string"
    kwargs_for_reverse = {key_name: unicode(course_key)}
    return reverse('course_validator.views.' + handler_name, kwargs=kwargs_for_reverse)


@login_required
@ensure_csrf_cookie
@require_GET
def course_validator_handler(request, course_key_string=None):
    """Обработчик url на проверку курса"""
    if request.method != 'GET':
        return redirect(reverse('course_handler', course_key_string))
    course_key = CourseKey.from_string(course_key_string)
    course_module = modulestore().get_course(course_key)

    requested_format = request.GET.get('_accept', request.META.get('HTTP_ACCEPT', 'text/html'))

    execute_url = reverse_validator_course_url(course_key)
    execute_url += "?_accept=exec"

    context = {
        "context_course": course_module,
        "course_key_string": course_key_string,
        "validate_url": execute_url,
    }

    if 'exec' in requested_format:
        CV = CourseValid(request, course_key_string)
        CV.validate()
        CV.send_log()
        context['sections'] = CV.get_sections_for_rendering()

    return render_to_response("validator.html", context)
