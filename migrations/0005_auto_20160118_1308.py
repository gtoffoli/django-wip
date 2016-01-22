# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-01-18 12:08
from __future__ import unicode_literals

from django.db import migrations, models
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('wip', '0004_auto_20160106_1558'),
    ]

    operations = [
        migrations.AddField(
            model_name='fetched',
            name='body',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='fetched',
            name='ckecksum',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name='webpage',
            name='encoding',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='fetched',
            name='delay',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='fetched',
            name='time',
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True),
        ),
    ]
