# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('course_validator', '0003_auto_20170121_1345'),
    ]

    operations = [
        migrations.RenameField(
            model_name='courseupdate',
            old_name='items',
            new_name='change',
        ),
        migrations.RenameField(
            model_name='courseupdate',
            old_name='user',
            new_name='username',
        ),
        migrations.RenameField(
            model_name='coursevalidation',
            old_name='user',
            new_name='username',
        ),
    ]
