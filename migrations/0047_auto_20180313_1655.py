# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-03-13 15:55
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wip', '0046_auto_20180305_1203'),
    ]

    operations = [
        migrations.AddField(
            model_name='scan',
            name='extract_blocks',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='scan',
            name='scan_mode',
            field=models.IntegerField(choices=[(0, 'in background, asynchronously'), (1, 'in foreground, page by page')], default=0, verbose_name='scan mode'),
        ),
        migrations.AddField(
            model_name='scan',
            name='scan_type',
            field=models.IntegerField(choices=[(0, 'discover'), (1, 'crawl'), (2, 're-fetch')], default=0, verbose_name='scan type'),
        ),
        migrations.AddField(
            model_name='site',
            name='extra_body',
            field=models.TextField(blank=True, help_text='Code to be inserted before closing BODY tag', null=True, verbose_name='Extra body'),
        ),
        migrations.AlterField(
            model_name='scan',
            name='site',
            field=models.ForeignKey(blank=True, help_text='leave undefined for discovery', null=True, on_delete=django.db.models.deletion.CASCADE, to='wip.Site', verbose_name='site/project'),
        ),
    ]
