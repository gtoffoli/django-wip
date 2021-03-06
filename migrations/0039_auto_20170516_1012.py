# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2017-05-16 08:12
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wip', '0038_auto_20161204_2356'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='segment',
            options={'verbose_name': 'segment', 'verbose_name_plural': 'segments'},
        ),
        migrations.RemoveField(
            model_name='translation',
            name='html',
        ),
        migrations.AddField(
            model_name='translation',
            name='alignment',
            field=models.TextField(blank=True, null=True, verbose_name=b'source to target alignment'),
        ),
        migrations.AddField(
            model_name='translation',
            name='alignment_type',
            field=models.IntegerField(choices=[(0, 'Unspecified'), (1, 'Translation Memory'), (2, 'Machine Translation'), (3, 'Manual')], default=0, verbose_name=b'alignment type'),
        ),
        migrations.AlterField(
            model_name='translation',
            name='language',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wip.Language', verbose_name=b'language'),
        ),
        migrations.AlterField(
            model_name='translation',
            name='segment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='segment_translation', to='wip.Segment', verbose_name=b'source segment'),
        ),
        migrations.AlterField(
            model_name='translation',
            name='text',
            field=models.TextField(blank=True, null=True, verbose_name=b'target text'),
        ),
    ]
