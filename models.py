# -*- coding: utf-8 -*-
from datetime import datetime
from django.db import models
from django.utils.translation import ugettext as _
from django.utils.dateparse import parse_datetime

from xmodule.modulestore.django import modulestore
from opaque_keys.edx.keys import CourseKey


def now():
    return datetime.now().replace(microsecond=0)


def branched_key(course_id, branch=None):
    cid = course_id
    course_key = CourseKey.from_string(cid)
    if branch:
        if "draft" in branch:
            branch = None
    if not course_key.branch and branch:
        cid = str(course_key.for_branch(branch))
    return cid


class CourseManager(models.Manager):
    def save(self, **kwargs):
        course_id = kwargs.get("course_id", None)
        branch = kwargs.pop("branch", None)
        if course_id and branch:
            course_id = branched_key(course_id, branch)
            kwargs["course_id"] = course_id
        return super(CourseManager, self).save(**kwargs)


class CourseRelatedManager(models.Manager):
    """Позволяет создавать моделям с внешним ключом на Course записи через course_id"""
    def create(self, course_id, *args, **kwargs):
        course_id = branched_key(course_id, kwargs.get('branch', None))
        course, _created = Course.objects.get_or_create(course_id=course_id)
        return super(CourseRelatedManager,self).create(course=course, *args, **kwargs)


class CourseValidationManager(CourseRelatedManager):
    def by_readable_name(self, readable_name, course_id):
        branch, username, date = readable_name.split(", ")
        map = {
            "Draft":None,
            "Published":"published-branch"
        }
        branch = map[branch]
        date = parse_datetime(date)
        course_id = branched_key(course_id, branch)
        queryset = self.get_queryset().filter(username=username, created_at=date, course__course_id=course_id)
        if not queryset:
            return None
        return queryset[0]


class Course(models.Model):
    course_id = models.CharField(primary_key=True, max_length=100,  help_text=_("Course ID"))
    validated_at = models.DateTimeField(auto_now_add=False, null=True,
                                         help_text=_("The date when course was last validated"))
    objects = CourseManager()

    @property
    def branch(self):
        return CourseKey.from_string(self.course_id).branch


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
    def get_course_validations(cls, course_id, branch=None):
        course_id = branched_key(course_id, branch)
        return CourseValidation.objects.all().filter(course__course_id=course_id) or []

    @property
    def readable_name(self):
        branch = self.branch
        map = {
            "published-branch": "Published",
            None: "Draft",
        }
        branch = map[branch]
        return u"{branch}, {user}, {date}".format(branch=branch, user=str(self.username), date=str(self.created_at))

    @property
    def branch(self):
        return self.course_key.branch

    @property
    def course_key(self):
        try:
            return self._course_key
        except AttributeError:
            self._course_key = CourseKey.from_string(self.course.course_id)
            return self._course_key

    def __unicode__(self):
        return u"{}, {}".format(self.readable_name, self.course.course_id)

    def save(self, *args, **kwargs):
        if not self.video_keys:
            keys = self.collect_video_keys(course_id=self.course.course_id, branch=self.branch)
            self.video_keys = ",".join(keys)
        super(CourseValidation, self).save(*args, **kwargs)

    @classmethod
    def collect_video_keys(cls, course_id, branch=None):
        course_key = CourseKey.from_string(branched_key(course_id, branch))
        items = modulestore().get_items(course_key)
        videos = [i for i in items if i.category == "video"]
        return [str(i.location) for i in videos]

    def get_video_keys(self):
        vk = self.video_keys.split(",")
        if len(vk) == 1 and not vk[0]:
            return []
        return vk

    @staticmethod
    def branched_key(**kwargs):
        return branched_key(**kwargs)


class CourseUpdateTypes(object):
    VIDEO_BLOCK = 'video_block' #video_full
    COURSE_PART = 'course_part' #module, response_types, ora, items_visibility, video_full
    OTHER = 'other' #proctoring, group, special_exams, advanced_modules
    CANDIDATE = "candidate" # возможно измененный блок

    TYPES = (
        (VIDEO_BLOCK, "Video"),
        (COURSE_PART, "Chapter/Subsequence/Vertical"),
        (CANDIDATE, "Candidate"),
        (OTHER, "Other")
    )

    @classmethod
    def candidate(cls, usage_id):
        return "{} {}".format(cls.CANDIDATE, usage_id)


class CourseUpdate(models.Model, CourseUpdateTypes):
    course = models.ForeignKey(Course)
    created_at = models.DateTimeField(default=now,
                                      help_text=_("The date when validation was done"))
    username = models.CharField(max_length=100, blank=True, help_text="User who performed validation")
    change_type = models.CharField(max_length=100, choices=CourseUpdateTypes.TYPES, default=CourseUpdateTypes.OTHER,
                                   help_text="Type of change in course")
    change = models.TextField()

    objects = CourseRelatedManager()

    def __unicode__(self):
        return u"{}: {},{},{}".format(str(self.change_type), str(self.course.course_id), str(self.created_at), self.change)

    @staticmethod
    def create(*args, **kwargs):
        return CourseUpdate.objects.create(*args, **kwargs)