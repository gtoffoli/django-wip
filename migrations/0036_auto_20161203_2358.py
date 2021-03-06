# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-12-03 22:58
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wip', '0035_auto_20161124_2312'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userrole',
            name='creator',
            field=models.ForeignKey(blank=True, help_text=b'who granted this role', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='creator_user', to=settings.AUTH_USER_MODEL, verbose_name=b'role creator'),
        ),
    ]
