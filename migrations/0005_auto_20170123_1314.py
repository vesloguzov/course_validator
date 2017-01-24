# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import course_validator.models


class Migration(migrations.Migration):

    dependencies = [
        ('course_validator', '0004_auto_20170123_1159'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseupdate',
            name='created_at',
            field=models.DateTimeField(default=course_validator.models.now, help_text='The date when validation was done'),
        ),
        migrations.AlterField(
            model_name='coursevalidation',
            name='created_at',
            field=models.DateTimeField(default=course_validator.models.now, help_text='The date when validation was done'),
        ),
    ]
