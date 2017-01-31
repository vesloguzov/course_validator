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
from .analyzer import ChangeAnalyzer
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
    course_id = course_key_string
    course_key = CourseKey.from_string(course_id)
    course_module = modulestore().get_course(course_key)

    execute_url = reverse_validator_course_url(course_key)
    context = dict()
    cv = CourseValid(request, course_id)

    if request.method == 'POST':
        data = None
        form_data = dict(request.POST)
        type_ = form_data.pop("type-of-form")[0]
        branch = form_data.pop("branch", ["draft-branch"])[0]
        if type_ == u'new-validation':
            data = cv.get_new_validation(form_data, branch)
        elif type_ == u'old-validation':
            data = cv.get_old_validation(form_data)
        context['sections'] = data
        additional_info = cv.get_additional_info()
        context['info'] = additional_info
        res = render_to_response("validator_results.html", context)
        return JsonResponse({"html": str(res.content)})

    db = "draft-branch"
    analyzer_draft = ChangeAnalyzer(course_id, None)
    pb = "published-branch"
    analyzer_published = ChangeAnalyzer(course_id, pb)
    analyzer_report = {
        db: analyzer_draft.report(),
        pb: analyzer_published.report()
    }
    saved_reports = CourseValid.get_saved_reports_for_course(course_id)
    additional_info = cv.get_additional_info()
    additional_info["analyzer_report"] = analyzer_report
    context.update({
        "csrf": csrf_token,
        "course_id":course_id,
        "context_course": course_module,
        "validate_url": execute_url,
        "saved_reports": saved_reports,
        'info': additional_info
    })
    return render_to_response("validator.html", context)