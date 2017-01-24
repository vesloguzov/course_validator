# -*- coding: utf-8 -*-

from datetime import datetime
from django.db import models
from django.utils.translation import ugettext as _
from django.utils.dateparse import parse_datetime

from xmodule.modulestore.django import modulestore
from opaque_keys.edx.keys import CourseKey


def now():
    return datetime.now().replace(microsecond=0)


class CourseRelatedManager(models.Manager):
    """Позволяет создавать моделям с внешним ключом на Course записи через course_id"""
    def create(self, course_id, *args, **kwargs):
        course, _created = Course.objects.get_or_create(course_id=course_id)
        return super(CourseRelatedManager,self).create(course=course, *args, **kwargs)


class CourseValidationManager(CourseRelatedManager):
    def by_readable_name(self, readable_name, course_id):
        username, date = readable_name.split(", ")
        date = parse_datetime(date)
        queryset = self.get_queryset().filter(username=username, created_at=date, course__course_id=course_id)
        if not queryset:
            return None
        return queryset[0]


class Course(models.Model):
    course_id = models.CharField(primary_key=True, max_length=50,  help_text=_("Course ID"))
    validated_at = models.DateTimeField(auto_now_add=False, null=True,
                                         help_text=_("The date when course was last validated"))


class CourseValidation(models.Model):
    course = models.ForeignKey(Course, help_text="Course that was validated")
    created_at = models.DateTimeField(default=now,
                                        help_text=_("The date when validation was done"))
    username = models.CharField(max_length=100, blank=True, help_text="User who performed validation")
    is_correct = models.BooleanField(default=False)
    full_validation_report = models.TextField(help_text="JSON-ized validation")
    video_keys = models.TextField(default="", help_text="All video usage_keys in course for comparison at next validation")

    objects = CourseValidationManager()

    @classmethod
    def get_course_validations(cls, course_key):
        course_key = str(course_key)
        return  CourseValidation.objects.all().filter(course__course_id=course_key)

    @property
    def readable_name(self):
        return u"{user}, {date}".format(user=str(self.username), date=str(self.created_at))

    def __unicode__(self):
        return u"{}, {}".format(self.readable_name, self.course.course_id)

    def save(self, *args, **kwargs):
        if not self.video_keys:
            keys = self.collect_video_keys(course_id=self.course.course_id)
            self.video_keys = ",".join(keys)
        super(CourseValidation, self).save(*args, **kwargs)

    @classmethod
    def collect_video_keys(cls, course_id):
        items = modulestore().get_items(CourseKey.from_string(course_id))
        videos = [i for i in items if i.category == "video"]
        return [str(i.location) for i in videos]


class CourseUpdateTypes(object):
    PROBLEM_BLOCK = 'nonvideo_block' #module, response_types, ora, items_visibility
    VIDEO_BLOCK = 'video_block' #video_full
    COURSE_PART = 'course_part' #module, response_types, ora, items_visibility, video_full
    GRADE = 'grade' #grade
    DATES = 'dates' #dates
    COHORTS = 'cohorts' #cohorts - НЕЛЬЗЯ ОТСЛЕДИТЬ - МЕНЯЕТСЯ В LMS
    OTHER = 'other' #proctoring, group, special_exams, advanced_modules
    CANDIDATE = "candidate" # возможно измененный блок


    @classmethod
    def candidate(cls, usage_id):
        return "{} {}".format(cls.CANDIDATE, usage_id)


class CourseUpdate(models.Model, CourseUpdateTypes):
    course = models.ForeignKey(Course)
    created_at = models.DateTimeField(default=now,
                                      help_text=_("The date when validation was done"))
    username = models.CharField(max_length=100, blank=True, help_text="User who performed validation")
    change = models.TextField()

    objects = CourseRelatedManager

    def __unicode__(self):
        return u"{}, {}:{}".format(str(self.course.course_id), str(self.created_at), self.change)