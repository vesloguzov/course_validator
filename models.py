from django.db import models
from django.utils.translation import ugettext as _
from datetime import datetime
from django.utils.dateparse import parse_datetime


class CourseValidationManager(models.Manager):
    def create(self, course_id, *args, **kwargs):
        course, _created = Course.objects.get_or_create(course_id=course_id)
        answ = super(CourseValidationManager,self).create(course=course, *args, **kwargs)
        return answ

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

class CourseUpdate(models.Model):
    course = models.ForeignKey(Course)
    created_at = models.DateTimeField(default=datetime.now().replace(microsecond=0),
                                      help_text=_("The date when validation was done"))
    user = models.CharField(max_length=100, blank=True, help_text="User who performed validation")
    items = models.TextField()