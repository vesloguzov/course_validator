# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('course_id', models.CharField(help_text='Course ID', max_length=50, serialize=False, primary_key=True)),
                ('validated_at', models.DateTimeField(help_text='The date when course was last validated', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='CourseUpdate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(help_text='The date when validation was done', auto_now_add=True)),
                ('user', models.CharField(help_text=b'User who performed validation', max_length=100, blank=True)),
                ('items', models.TextField()),
                ('course', models.ForeignKey(to='course_validator.Course')),
            ],
        ),
        migrations.CreateModel(
            name='CourseValidation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(help_text='The date when validation was done', auto_now_add=True)),
                ('user', models.CharField(help_text=b'User who performed validation', max_length=100, blank=True)),
                ('is_correct', models.BooleanField(default=False)),
                ('full_validation_report', models.TextField(help_text=b'JSON-ized validation')),
                ('course', models.ForeignKey(help_text=b'Course that was validated', to='course_validator.Course')),
            ],
        ),
    ]
