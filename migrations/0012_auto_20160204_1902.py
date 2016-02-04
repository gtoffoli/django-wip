# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-02-04 18:02
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('wip', '0011_auto_20160203_2353'),
    ]

    operations = [
        migrations.AddField(
            model_name='block',
            name='webpages',
            field=models.ManyToManyField(blank=True, related_name='block_pages', through='wip.BlockInPage', to='wip.Webpage', verbose_name=b'pages'),
        ),
        migrations.AddField(
            model_name='translatedblock',
            name='revisor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='revisor', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='webpage',
            name='blocks',
            field=models.ManyToManyField(blank=True, related_name='page_blocks', through='wip.BlockInPage', to='wip.Block', verbose_name=b'blocks'),
        ),
        migrations.AlterField(
            model_name='blockinpage',
            name='block',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='block', to='wip.Block'),
        ),
        migrations.AlterField(
            model_name='blockinpage',
            name='webpage',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webpage', to='wip.Webpage'),
        ),
        migrations.AlterField(
            model_name='translatedblock',
            name='editor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='editor', to=settings.AUTH_USER_MODEL),
        ),
    ]
