# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course_validator', '0008_auto_20170130_1122'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coursevalidation',
            name='branch',
        ),
        migrations.AlterField(
            model_name='courseupdate',
            name='change_type',
            field=models.CharField(default=b'other', help_text=b'Type of change in course', max_length=100, choices=[(b'video_block', b'Video'), (b'course_part', b'Chapter/Subsequence/Vertical'), (b'candidate', b'Candidate'), (b'other', b'Other')]),
        ),
    ]
