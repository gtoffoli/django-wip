# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-01-18 12:44
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wip', '0005_auto_20160118_1308'),
    ]

    operations = [
        migrations.RenameField(
            model_name='fetched',
            old_name='ckecksum',
            new_name='checksum',
        ),
    ]
