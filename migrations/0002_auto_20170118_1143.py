# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course_validator', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='validated_at',
            field=models.DateTimeField(help_text='The date when course was last validated', null=True),
        ),
    ]
