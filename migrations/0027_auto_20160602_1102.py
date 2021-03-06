# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-06-02 09:02
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('django_diazo', '0001_initial'),
        ('wip', '0026_site_srx_initials'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteTheme',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='theme_used_for_site', to='wip.Site')),
                ('theme', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='site_using_theme', to='django_diazo.Theme')),
            ],
            options={
                'verbose_name': 'theme used for site',
                'verbose_name_plural': 'themes used for site',
            },
        ),
        migrations.AddField(
            model_name='site',
            name='themes',
            field=models.ManyToManyField(blank=True, related_name='site', through='wip.SiteTheme', to='django_diazo.Theme', verbose_name=b'diazo themes'),
        ),
    ]
