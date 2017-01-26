# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course_validator', '0006_coursevalidation_video_keys'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseupdate',
            name='change_type',
            field=models.CharField(default=b'other', max_length=100, choices=[(b'problem_block', b'Problem'), (b'video_block', b'Video'), (b'course_part', b'Chapter/Subsequence/Vertical'), (b'grade', b'Grades'), (b'dates', b'Dates'), (b'candidate', b'Candidate'), (b'other', b'Other')]),
        ),
    ]
