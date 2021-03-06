# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-03-15 17:39
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wip', '0019_auto_20160313_2334'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='string',
            options={'ordering': ('text',), 'verbose_name': 'string', 'verbose_name_plural': 'strings'},
        ),
        migrations.AlterModelOptions(
            name='txu',
            options={'ordering': ('-created',), 'verbose_name': 'translation unit', 'verbose_name_plural': 'translation units'},
        ),
        migrations.AddField(
            model_name='txu',
            name='en',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='txu',
            name='es',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='txu',
            name='fr',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='txu',
            name='it',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='string',
            name='txu',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='string', to='wip.Txu'),
        ),
    ]
