# -*- coding: utf-8 -*-

from datetime import datetime

from django.db import models
from django.utils.translation import ugettext as _
from django.utils.dateparse import parse_datetime
from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User

from xmodule.modulestore.django import SignalHandler, modulestore
from openedx.core.djangoapps.course_groups.models import CohortMembership


class CourseRelatedManager(models.Manager):
    """Позволяет создавать моделям с внешним ключом на Course записи через course_id"""
    def create(self, course_id, *args, **kwargs):
        course, _created = Course.objects.get_or_create(course_id=course_id)
        return super(CourseRelatedManager,self).create(course=course, *args, **kwargs)

class CourseValidationManager(CourseRelatedManager):
    def by_readable_name(self, readable_name, course_id):
        user, date = readable_name.split(", ")
        date = parse_datetime(date)
        queryset = self.get_queryset().filter(user=user, created_at=date, course__course_id=course_id)
        if not queryset:
            return None
        return queryset[0]


class Course(models.Model):
    course_id = models.CharField(primary_key=True, max_length=50,  help_text=_("Course ID"))
    validated_at = models.DateTimeField(auto_now_add=False, null=True,
                                         help_text=_("The date when course was last validated"))


class CourseValidation(models.Model):
    course = models.ForeignKey(Course, help_text="Course that was validated")
    created_at = models.DateTimeField(default=datetime.now().replace(microsecond=0),
                                        help_text=_("The date when validation was done"))
    user = models.CharField(max_length=100, blank=True, help_text="User who performed validation")
    is_correct = models.BooleanField(default=False)
    full_validation_report = models.TextField(help_text="JSON-ized validation")

    objects = CourseValidationManager()

    @classmethod
    def get_course_validations(cls, course_key):
        course_key = str(course_key)
        validations = CourseValidation.objects.all().filter(course__course_id=course_key)
        return validations

    @property
    def readable_name(self):
        return u"{user}, {date}".format(user=str(self.user), date=str(self.created_at))

    def __unicode__(self):
        return u"{}, {}".format(self.readable_name, self.course.course_id)


class CourseUpdateTypes(object):
    PROBLEM_BLOCK = 'nonvideo_block' #module, response_types, ora, items_visibility
    VIDEO_BLOCK = 'video_block' #video_full
    COURSE_PART = 'course_part' #module, response_types, ora, items_visibility, video_full
    GRADE = 'grade' #grade
    DATES = 'dates' #dates
    COHORTS = 'cohorts' #cohorts - НЕЛЬЗЯ ОТСЛЕДИТЬ - МЕНЯЕТСЯ В LMS
    OTHER = 'other' #proctoring, group, special_exams, advanced_modules

    TYPE_OF_UPDATE = (
        PROBLEM_BLOCK,
        VIDEO_BLOCK,
        COURSE_PART,
        GRADE,
        DATES,
        COHORTS,
        OTHER
    )


class CourseUpdate(models.Model, CourseUpdateTypes):
    course = models.ForeignKey(Course)
    created_at = models.DateTimeField(default=datetime.now().replace(microsecond=0),
                                      help_text=_("The date when validation was done"))
    user = models.CharField(max_length=100, blank=True, help_text="User who performed validation")
    items = models.TextField()

    objects = CourseRelatedManager

    @staticmethod
    @receiver(SignalHandler.item_deleted)
    def listen_for_item_delete(**kwargs):  # pylint: disable=unused-argument
        """
        Catches the signal that a course has been published in Studio
        """
        # course = modulestore().get_course(course_key)
        usage_key = kwargs['usage_key']
        user_id = kwargs['user_id']
        user = User.objects.get(id=int(user_id)).username
        course_key = usage_key.course_key
        block_type = usage_key.block_type
        if block_type == "video":
            type_ = CourseUpdate.VIDEO_BLOCK
        elif block_type == "problem":
            type_ = CourseUpdate.VIDEO_BLOCK
        else:
            type_ = CourseUpdate.COURSE_PART

        CourseUpdate.objects.create(course_id=course_key, user=user, items=type_)

    """
    @staticmethod
    @receiver(post_save, sender=CohortMembership)
    def remove_user_from_cohort(sender, instance, **kwargs):  # pylint: disable=unused-argument
        print("COHORT_SIGNAL")\
    """