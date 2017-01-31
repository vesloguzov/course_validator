# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course_validator', '0009_auto_20170131_0803'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='course_id',
            field=models.CharField(help_text='Course ID', max_length=100, serialize=False, primary_key=True),
        ),
    ]
