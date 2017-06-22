# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseReviewsToolConfiguration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('change_date', models.DateTimeField(auto_now_add=True, verbose_name='Change date')),
                ('enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('platform_key', models.CharField(help_text='The platform key associates CourseTalk widgets with your platform. Generally, it is the domain name for your platform. For example, if your platform is http://edx.org, the platform key is "edx".', max_length=50)),
                ('reviews_provider_fragment', models.CharField(help_text='The reviews provider fragment points to the fragment template that renders wherever the reviews tool shows up. The fragments all lie in the openedx/features/course_experience/templates/course_experience/course_reviews_modules directory. For example, to embed the coursetalk fragment, the reviews provider fragment is "coursetalk-reviews-fragment.html". ', max_length=50)),
                ('changed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, editable=False, to=settings.AUTH_USER_MODEL, null=True, verbose_name='Changed by')),
            ],
            options={
                'ordering': ('-change_date',),
                'abstract': False,
            },
        ),
    ]
