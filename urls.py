from django.conf import settings
from django.conf.urls import patterns, url
from .views import course_validator_handler


urlpatterns = patterns(
    url(r'^check_course$', course_validator_handler, name='course_validator'),
    url(r'', course_validator_handler, name='course_validator'),
)
