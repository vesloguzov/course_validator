# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course_validator', '0005_auto_20170123_1314'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursevalidation',
            name='video_keys',
            field=models.TextField(default=b'', help_text=b'All video usage_keys in course for comparison at next validation'),
        ),
    ]
