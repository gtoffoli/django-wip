# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-04-04 15:10
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('wip', '0022_auto_20160401_1607'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlockEdge',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
            ],
            options={
                'verbose_name': 'block edge',
                'verbose_name_plural': 'block edges',
            },
        ),
        migrations.AlterModelOptions(
            name='blockinpage',
            options={'verbose_name': 'block in page', 'verbose_name_plural': 'blocks in page'},
        ),
        migrations.AddField(
            model_name='block',
            name='state',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='translatedblock',
            name='editor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='editor', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='translatedblock',
            name='revisor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='revisor', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='blockedge',
            name='child',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='Block_parent', to='wip.Block'),
        ),
        migrations.AddField(
            model_name='blockedge',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='Block_child', to='wip.Block'),
        ),
        migrations.AddField(
            model_name='block',
            name='children',
            field=models.ManyToManyField(blank=True, null=True, related_name='_parents', through='wip.BlockEdge', to='wip.Block'),
        ),
    ]
