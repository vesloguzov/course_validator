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
from django.http import HttpResponse, JsonResponse
from .utils import find_course_validation, get_path_saved_reports


__all__ = ["course_validator_handler"]

def reverse_validator_course_url(course_key):
    handler_name = "course_validator_handler"
    key_name = "course_key_string"
    kwargs_for_reverse = {key_name: unicode(course_key)}
    return reverse('course_validator.views.' + handler_name, kwargs=kwargs_for_reverse)


@login_required
@ensure_csrf_cookie
def course_validator_handler(request, course_key_string=None):
    """Обработчик url на проверку курса"""
    course_key = CourseKey.from_string(course_key_string)
    course_module = modulestore().get_course(course_key)

    execute_url = reverse_validator_course_url(course_key)
    context = dict()

    if request.method == 'POST':
        CV = CourseValid(request, course_key_string)
        data = None
        form_data = dict(request.POST)
        type_ = form_data.pop("type-of-form")[0]
        if type_ == u'new-validation':
            data = CV.get_new_validation(form_data)
        elif type_ == u'old-validation':
            data = CV.get_old_validation(form_data)
        context['sections'] = data

        res = render_to_response("results.html", context)
        return JsonResponse({"html":str(res.content)})

    saved_reports = CourseValid.get_course_report_readable(course_key_string)
    context.update({
        "context_course": course_module,
        "course_key_string": course_key_string,
        "validate_url": execute_url,
        "validate_options":CourseValid.scenarios_names_dict,
        "costly_options":CourseValid.costly_scenarios,
        "saved_reports": saved_reports
    })
    return render_to_response("validator.html", context)
