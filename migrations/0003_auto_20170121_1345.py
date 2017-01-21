# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('course_validator', '0002_auto_20170118_1143'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseupdate',
            name='created_at',
            field=models.DateTimeField(default=datetime.datetime(2017, 1, 21, 13, 45, 7), help_text='The date when validation was done'),
        ),
        migrations.AlterField(
            model_name='coursevalidation',
            name='created_at',
            field=models.DateTimeField(default=datetime.datetime(2017, 1, 21, 13, 45, 7), help_text='The date when validation was done'),
        ),
    ]
