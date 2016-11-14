# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.core.context_processors import csrf
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import HttpResponse, JsonResponse
from edxmako.shortcuts import render_to_response
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore
from .validator import CourseValid


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
    csrf_token = csrf(request)['csrf_token']
    course_key = CourseKey.from_string(course_key_string)
    course_module = modulestore().get_course(course_key)

    execute_url = reverse_validator_course_url(course_key)
    context = dict()
    CV = CourseValid(request, course_key_string)

    if request.method == 'POST':
        data = None
        form_data = dict(request.POST)
        type_ = form_data.pop("type-of-form")[0]
        if type_ == u'new-validation':
            data = CV.get_new_validation(form_data)
        elif type_ == u'old-validation':
            data = CV.get_old_validation(form_data)
        context['sections'] = data
        additional_info = CV.get_additional_info()
        context['info'] = additional_info
        res = render_to_response("results.html", context)
        return JsonResponse({"html":str(res.content)})

    saved_reports = CourseValid.get_saved_reports_for_course(course_key_string)
    additional_info = CV.get_additional_info()
    context.update({
        "csrf": csrf_token,
        "context_course": course_module,
        "validate_url": execute_url,
        "saved_reports": saved_reports,
        'info':additional_info
    })
    return render_to_response("validator.html", context)
