# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-10-30 21:04
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('wip', '0031_auto_20160826_1039'),
    ]

    operations = [
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.TextField()),
                ('status', models.IntegerField()),
                ('encoding', models.TextField()),
                ('size', models.IntegerField()),
                ('title', models.TextField()),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'followed link',
                'verbose_name_plural': 'followed links',
            },
        ),
        migrations.CreateModel(
            name='Scan',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
                ('start_urls', models.TextField()),
                ('allowed_domains', models.TextField()),
                ('allow', models.TextField()),
                ('deny', models.TextField()),
                ('max_pages', models.IntegerField()),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True)),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True)),
                ('task_id', models.IntegerField()),
                ('terminated', models.BooleanField(default=False)),
                ('language', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='wip.Language')),
                ('site', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='wip.Site')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'discovery scan',
                'verbose_name_plural': 'discovery scans',
            },
        ),
        migrations.CreateModel(
            name='SegmentCount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('segment', models.CharField(max_length=1000)),
                ('count', models.IntegerField()),
                ('scan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wip.Scan')),
            ],
            options={
                'verbose_name': 'segment count',
                'verbose_name_plural': 'segment counts',
            },
        ),
        migrations.CreateModel(
            name='WordCount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('word', models.CharField(max_length=100)),
                ('count', models.IntegerField()),
                ('scan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wip.Scan')),
            ],
            options={
                'verbose_name': 'word count',
                'verbose_name_plural': 'word counts',
            },
        ),
        migrations.AddField(
            model_name='link',
            name='scan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wip.Scan'),
        ),
    ]